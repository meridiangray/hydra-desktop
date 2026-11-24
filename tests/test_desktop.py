import json
import os
import re
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
import urllib.error
import urllib.request

import pytest

from hydra.archive import layout
from hydra_desktop import app as desktop
from hydra.cli.pack import pack
from hydra.universe import build as ubuild
from conftest import dynasty


def test_desktop_serves_existing_wiki_and_closes_with_shell(tmp_path, monkeypatch):
    root = dynasty(tmp_path)
    shell = tmp_path / "hydra-desktop.exe"
    shell.touch()
    seen = []

    def run(args, **kwargs):
        assert args[0] == str(shell)
        seen.append(args[1])
        with urllib.request.urlopen(args[1], timeout=5) as response:
            html = response.read().decode()
        assert "Old King" in html
        assert "@view-transition{navigation:auto}" in html
        assert "hydra-windowbar" not in html
        with urllib.request.urlopen(args[1] + "wiki.css", timeout=5) as response:
            assert response.headers.get_content_type() == "text/css"
        return 0

    monkeypatch.setattr(desktop, "run_shell", run)
    assert desktop.launch(root, shell, settings=tmp_path / "settings.json") == 0
    with pytest.raises(OSError):
        urllib.request.urlopen(seen[0], timeout=1)


def test_desktop_closes_server_when_shell_fails(tmp_path, monkeypatch):
    root = dynasty(tmp_path)
    shell = tmp_path / "hydra-desktop.exe"
    shell.touch()
    seen = []

    def run(args, **kwargs):
        seen.append(args[1])
        raise OSError("cannot start shell")

    monkeypatch.setattr(desktop, "run_shell", run)
    with pytest.raises(OSError, match="cannot start shell"):
        desktop.launch(root, shell, settings=tmp_path / "settings.json")
    with pytest.raises(OSError):
        urllib.request.urlopen(seen[0], timeout=1)


def test_shell_exit_code_and_timeout():
    assert desktop.run_shell([sys.executable, "-c", "raise SystemExit(7)"]) == 7
    with pytest.raises(subprocess.TimeoutExpired):
        desktop.run_shell([sys.executable, "-c", "import time; time.sleep(60)"], timeout=0.1)


def test_missing_shell_fails_before_opening_archive(tmp_path):
    with pytest.raises(FileNotFoundError, match="Build the Saucer shell"):
        desktop.launch(tmp_path / "not-an-archive", tmp_path / "missing.exe")


def test_launch_without_archive_shows_welcome(tmp_path, monkeypatch):
    shell = tmp_path / "hydra-desktop.exe"
    shell.touch()

    def run(args, **kwargs):
        with urllib.request.urlopen(args[1], timeout=5) as response:
            html = response.read().decode()
            assert "Open archive folder" in html
            assert 'id="loading" role="status" aria-live="polite" hidden' in html
            assert ".loader-fill" in html and "prefers-reduced-motion:reduce" in html
            assert "const started=showLoading(path,build)" in html
            assert "hideLoading()" in html and "await attempt(true)" in html
            assert "/_desktop/progress" in html and "loading-fill" in html and 'role="progressbar"' in html and "loader-ring:before" not in html
        return 0

    monkeypatch.setattr(desktop, "run_shell", run)
    assert desktop.launch(shell=shell, settings=tmp_path / "settings.json") == 0


def test_stale_archive_opens_the_window_on_its_last_build(tmp_path, monkeypatch):
    """P6: the window opens on the last build at once; the rebuild runs in a child process (rebuilder.py), never in
    the launch itself."""
    root = dynasty(tmp_path)
    shell = tmp_path / "hydra-desktop.exe"
    shell.touch()
    monkeypatch.setattr(desktop.ubuild, "pages_current", lambda root: False)
    monkeypatch.setattr(desktop.ubuild, "build", lambda root: pytest.fail("the launch itself must not rebuild"))
    seen = []

    def run(args, **kwargs):
        with urllib.request.urlopen(args[1], timeout=5) as response:
            seen.append(response.read().decode())
        return 0

    monkeypatch.setattr(desktop, "run_shell", run)
    assert desktop.launch(root, shell, settings=tmp_path / "settings.json") == 0
    assert "openArchive(" not in seen[0] and "<html" in seen[0]          # the archive's own page, not the welcome's loader


@contextmanager
def running_app(tmp_path):
    app = desktop.Desktop(settings=tmp_path / "settings.json")
    server = desktop.serve_desktop(app)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield app, f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
        app.close()


def request(url, app, action, data, *, token=None):
    payload = json.dumps(data).encode()
    req = urllib.request.Request(url + "/_desktop/" + action, data=payload,
                                 headers={"Content-Type": "application/json",
                                          "X-Hydra-Token": app.token if token is None else token})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_welcome_switches_archives_and_preserves_current_on_error(tmp_path):
    first = dynasty(tmp_path)
    second = dynasty(tmp_path / "second")
    collection = second / "collections" / "dyn.json"
    records = json.loads(collection.read_text(encoding="utf-8"))
    records[0]["properties"]["name"] = ["Second King"]
    collection.write_text(json.dumps(records), encoding="utf-8")
    ubuild.build(second)
    with running_app(tmp_path) as (app, url):
        with urllib.request.urlopen(url + "/", timeout=5) as response:
            home = response.read().decode()
        assert "Open .hydra file" in home
        assert request(url, app, "open", {"path": str(first)}, token="wrong")[0] == 403
        assert request(url, app, "open", {"path": str(first)}) == (200, {"ok": True, "start": "/"})
        with urllib.request.urlopen(url + "/", timeout=5) as response:
            assert "Old King" in response.read().decode()
        with urllib.request.urlopen(url + "/search?q=Old+King", timeout=5) as response:
            assert response.geturl().startswith(url + "/e/")
        bad_pack = tmp_path / "bad.hydra"
        bad_pack.write_bytes(b"not a pack")
        assert request(url, app, "open", {"path": str(bad_pack)})[0] == 400
        assert request(url, app, "open", {"path": str(tmp_path / "missing")})[0] == 400
        assert app.current == first
        assert request(url, app, "open", {"path": str(second)}) == (200, {"ok": True, "start": "/"})
        assert [Path(p) for p in app.recent] == [second, first]
        with urllib.request.urlopen(url + "/search.json", timeout=5) as response:
            assert "Second King" in response.read().decode()
        with urllib.request.urlopen(url + "/_desktop/", timeout=5) as response:
            home = response.read().decode()
        assert str(first) in home and str(second) in home and "Return to" in home
        assert request(url, app, "close", {}) == (200, {"ok": True})
        with urllib.request.urlopen(url + "/", timeout=5) as response:
            assert "Open archive folder" in response.read().decode()


def test_the_wikis_caching_reaches_the_window(tmp_path):
    """Owner 2026-11-20 ("no needless lag"): the window keeps the wiki's hashed assets; pages stay no-store."""
    root = dynasty(tmp_path)
    with running_app(tmp_path) as (app, url):
        assert request(url, app, "open", {"path": str(root)})[0] == 200
        with urllib.request.urlopen(url + "/", timeout=5) as response:
            page = response.read().decode()
            assert response.headers["Cache-Control"] == "no-store"
        asset = re.search(r"/a/[\w-]+\.[0-9a-f]{8}\.(?:js|css)", page).group(0)
        with urllib.request.urlopen(url + asset, timeout=5) as response:
            assert "immutable" in response.headers["Cache-Control"]


def test_picker_cancel_does_not_close_welcome(tmp_path, monkeypatch):
    monkeypatch.setattr(desktop, "pick_archive", lambda kind: "")
    with running_app(tmp_path) as (app, url):
        assert request(url, app, "pick", {"kind": "file"}) == (200, {"path": ""})
        assert app.current is None
        with urllib.request.urlopen(url, timeout=5) as response:
            assert "Open archive folder" in response.read().decode()


def test_picker_uses_a_ui_process_not_the_http_thread(monkeypatch, tmp_path):
    found = subprocess.run([sys.executable, "-c", "import importlib.util as u; print(u.find_spec('hydra_desktop.picker').origin)"],
                           capture_output=True, text=True, env=desktop.child_env(), cwd=tmp_path, timeout=60)
    assert found.returncode == 0, found.stderr
    assert Path(found.stdout.strip()).resolve().parent == Path(desktop.__file__).resolve().parent     # the child finds this package
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, "E:/archive.hydra\n", "")

    monkeypatch.setattr(desktop.subprocess, "run", run)
    assert desktop.pick_archive("file") == "E:/archive.hydra"
    assert calls[0][0] == [sys.executable, "-m", "hydra_desktop.picker", "file"]
    assert calls[0][1]["capture_output"] is True and calls[0][1]["env"] == desktop.child_env()


def _rebuilt(app, timeout=120):
    import time
    deadline = time.monotonic() + timeout
    time.sleep(.2)
    while app.rebuild_state["running"] and time.monotonic() < deadline:
        time.sleep(.1)
    assert not app.rebuild_state["running"]


def test_a_stale_folder_opens_at_once_and_is_rebuilt_behind_the_reader(tmp_path):
    """P6: no "rebuild?" for a stale archive whose last build this code made: it opens, the build runs in a child
    process, and the wiki reads the new generation when it is done. A folder with no build still asks."""
    from hydra.build import rebuilder
    root = dynasty(tmp_path)
    (root / "universe" / "wiki.yaml").write_text("title: changed\n", encoding="utf-8")
    pages = root / layout.UNIVERSE_PARSED / "pages.jsonl"
    os.utime(pages, (pages.stat().st_mtime - 5, pages.stat().st_mtime - 5))
    assert rebuilder.stale(root)[1] and rebuilder.built_by_this_code(root)
    with running_app(tmp_path) as (app, url):
        assert request(url, app, "open", {"path": str(root)}) == (200, {"ok": True, "start": "/"})
        assert app.current == root.resolve() and json.loads(app.settings.read_text())["recent"] == [str(root)]
        with urllib.request.urlopen(url + "/_desktop/rebuild", timeout=5) as response:
            assert json.loads(response.read())["shown"] is True
        _rebuilt(app)
        assert app.rebuild_state["n"] == 1 and not any(rebuilder.stale(root))
        assert request(url, app, "open", {"path": str(root), "build": True}) == (200, {"ok": True, "start": "/"})   # still on hand
    pages.unlink()
    with running_app(tmp_path) as (app, url):
        code, result = request(url, app, "open", {"path": str(root)})
        assert code == 409 and result["requires_build"] and app.current is None
    root.rename(tmp_path / "moved")
    with running_app(tmp_path) as (app, url):
        with urllib.request.urlopen(url + "/", timeout=5) as response:
            assert "Not found" in response.read().decode()
        assert request(url, app, "open", {"path": str(root)})[0] == 400
        assert app.recent == [str(root)]


def test_changed_collections_are_rebuilt_behind_the_reader_and_after_a_write(tmp_path):
    from hydra.build import run as archive_build, freshness

    root = dynasty(tmp_path)
    archive_build.build_archive(root)
    assert freshness.up_to_date(root)
    collection = root / "collections" / "dyn.json"
    records = json.loads(collection.read_text(encoding="utf-8"))
    records[0]["properties"]["name"] = ["New King"]
    collection.write_text(json.dumps(records), encoding="utf-8")
    with running_app(tmp_path) as (app, url):
        assert request(url, app, "open", {"path": str(root)})[0] == 200        # the last build, at once
        _rebuilt(app)
        with urllib.request.urlopen(url + "/search.json", timeout=5) as response:
            assert "New King" in response.read().decode()
        records[0]["properties"]["name"] = ["Newer King"]                    # a write that does not rebuild
        collection.write_text(json.dumps(records), encoding="utf-8")
        app.after_write()
        assert app.rebuild_state["shown"] is False                           # quiet
        _rebuilt(app)
        assert freshness.up_to_date(root)
        with urllib.request.urlopen(url + "/search.json", timeout=5) as response:
            assert "Newer King" in response.read().decode()


def test_progress_is_readable_during_a_build(tmp_path, monkeypatch):
    root = dynasty(tmp_path)
    pages = root / layout.UNIVERSE_PARSED / "pages.jsonl"
    os.utime(pages, (pages.stat().st_mtime - 5, pages.stat().st_mtime - 5))
    started, release = threading.Event(), threading.Event()
    original = desktop.ubuild.build
    with running_app(tmp_path) as (app, url):
        def delayed_build(path, **kwargs):
            if kwargs.get("pages", True):
                app.report_progress("Compiling entries", .35)
                started.set()
                assert release.wait(15)
            return original(path, **kwargs)

        monkeypatch.setattr(desktop.ubuild, "build", delayed_build)
        result = []
        worker = threading.Thread(target=lambda: result.append(request(url, app, "open",
                                                                         {"path": str(root), "build": True})))
        worker.start()
        try:
            assert started.wait(15)
            query = urllib.request.Request(url + "/_desktop/progress", headers={"X-Hydra-Token": app.token})
            with urllib.request.urlopen(query, timeout=3) as response:
                seen = json.loads(response.read())          # the opening's own meter reports too, and only moves forward
                assert set(seen) == {"stage", "fraction"} and 0 < seen["fraction"] < 1
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(url + "/_desktop/progress", timeout=3)
            assert exc.value.code == 403
        finally:
            release.set()
            worker.join(15)
        assert result == [(200, {"ok": True, "start": "/"})]
        with urllib.request.urlopen(query, timeout=3) as response:
            assert json.loads(response.read()) == {"stage": "Ready", "fraction": 1.0}


def test_welcome_scaffolds_the_new_project_wizard(tmp_path):
    with running_app(tmp_path) as (app, url):
        with urllib.request.urlopen(url + "/", timeout=5) as response:
            html = response.read().decode()
        for s in ("New project", 'name="view"', "Geo", "Radial", "Org Chart", "Communications",
                  'name="theme"', "request('new'", "newfolder", "documents"):
            assert s in html


def test_new_project_creates_and_opens_an_archive(tmp_path):
    src = tmp_path / "evidence.txt"
    src.write_text("A letter from the minister, March 1991.", encoding="utf-8")
    dest = tmp_path / "projects" / "case"
    (tmp_path / "projects").mkdir()
    with running_app(tmp_path) as (app, url):
        code, result = request(url, app, "new", {"path": str(dest), "name": "Case File",
                                                 "view": "radial", "theme": "tide",
                                                 "sources": [str(src)]})
        assert (code, result) == (200, {"ok": True, "empty": False, "start": "/radial"})
        assert app.current == dest
        conf = (dest / "universe" / "wiki.yaml").read_text(encoding="utf-8")
        assert "view: radial" in conf and "base: tide" in conf
        assert (dest / ".hydra" / "sources" / "files" / "setup" / "evidence.txt").is_file()
        entries = dest / ".hydra" / "sources" / "entries" / "setup.json"
        records = json.loads(entries.read_text(encoding="utf-8"))
        assert records[0]["schema"] == "Document" and records[0]["id"].startswith("doc-")
        with urllib.request.urlopen(url + "/", timeout=5) as response:
            assert "Case File" in response.read().decode()
        with urllib.request.urlopen(url + "/radial", timeout=5) as response:
            assert "id=radial-data" in response.read().decode()
        with urllib.request.urlopen(url + "/_desktop/", timeout=5) as response:
            assert 'class="current" href="/radial"' in response.read().decode()
        assert app.recent[0] == str(dest)


def test_new_project_without_sources_is_created_but_not_opened(tmp_path):
    dest = tmp_path / "empty-proj"
    with running_app(tmp_path) as (app, url):
        code, result = request(url, app, "new", {"path": str(dest), "name": "Empty",
                                                 "view": "messaging", "theme": "", "sources": []})
        assert (code, result) == (200, {"ok": True, "empty": True})
        assert app.current is None
        assert app.recent == [str(dest)]
        assert "view: messaging" in (dest / "universe" / "wiki.yaml").read_text(encoding="utf-8")


def test_new_project_validates_input(tmp_path):
    with running_app(tmp_path) as (app, url):
        assert request(url, app, "new", {"path": "", "name": "x", "view": "wiki"})[0] == 400
        assert request(url, app, "new", {"path": str(tmp_path), "name": "", "view": "wiki"})[0] == 400
        assert request(url, app, "new", {"path": str(tmp_path / "p"), "name": "x",
                                       "view": "spherical"})[0] == 400
        assert request(url, app, "new", {"path": str(tmp_path / "p"), "name": "x",
                                       "view": "wiki", "theme": "plaid"})[0] == 400
        assert request(url, app, "new", {"path": str(tmp_path / "p"), "name": "x", "view": "wiki"},
                               token="wrong")[0] == 403
        # an existing non-empty folder is refused
        taken = tmp_path / "taken"
        taken.mkdir()
        (taken / "file.txt").write_text("occupied", encoding="utf-8")
        assert request(url, app, "new", {"path": str(taken), "name": "x", "view": "wiki"})[0] == 400


def test_pack_without_build_is_built_aside_and_does_not_change_pack(tmp_path):
    root = dynasty(tmp_path)
    packed, _, _ = pack(root, tmp_path / "case.hydra", with_parsed=False)
    before = packed.read_bytes()
    with running_app(tmp_path) as (app, url):
        assert request(url, app, "open", {"path": str(packed)}) == (200, {"ok": True, "start": "/"})
        assert app.view is not None
        view_path = Path(app.view.name)
        with urllib.request.urlopen(url + "/", timeout=5) as response:
            assert "Old King" in response.read().decode()
        assert packed.read_bytes() == before
        assert request(url, app, "close", {}) == (200, {"ok": True})
        assert not view_path.exists()


def post_save(url, data, header=True):
    req = urllib.request.Request(url + "/_desktop/save", data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json", **({"X-Hydra-Save": "1"} if header else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def get_json(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read())


def test_save_endpoints_pending_and_save(tmp_path):
    from hydra.archive import history
    root = dynasty(tmp_path)
    with running_app(tmp_path) as (app, url):
        assert get_json(url + "/_desktop/pending") == {"dirty": False, "writable": False}      # nothing open
        assert request(url, app, "open", {"path": str(root)})[0] == 200
        history.auto(root, "a step")
        assert get_json(url + "/_desktop/pending?brief=1")["dirty"] is True
        full = get_json(url + "/_desktop/pending")
        assert full["dirty"] and full["writable"] and full["signing"] is False
        import getpass
        assert full["author"] == desktop.Desktop.author(root) and full["author"] != getpass.getuser()   # the Profile's, never the system user
        assert all(c["title"] for c in full["collections"])
        assert post_save(url, {"message": "x"}, header=False)[0] == 403
        assert post_save(url, {"message": " "})[0] == 400
        code, body = post_save(url, {"message": "Named change", "description": "why", "entities": []})
        assert code == 200 and body["ok"]
        snap = history.snap(root, body["id"])
        assert snap["kind"] == "save" and snap["fields"]["entities"] == [] and snap["fields"]["description"] == "why"
        assert get_json(url + "/_desktop/pending?brief=1")["dirty"] is False
        assert post_save(url, {"message": "x", "sign": True})[0] == 400                          # no signing configured
        history.auto(root, "another step")
        code, body = post_save(url, {"message": "Mine", "author": "  The editors "})
        assert code == 200 and history.snap(root, body["id"])["author"] == "The editors"      # what the owner typed
        history.auto(root, "one more")
        code, body = post_save(url, {"message": "Nobody", "author": ""})
        import getpass
        assert history.snap(root, body["id"])["author"] != getpass.getuser() or getpass.getuser() == "unknown"


def test_chrome_extension_is_served_and_pack_cannot_save(tmp_path):
    root = dynasty(tmp_path)
    packed, _, _ = pack(root, tmp_path / "d.hydra")
    with running_app(tmp_path) as (app, url):
        with urllib.request.urlopen(url + "/_desktop/chrome-ext.js", timeout=5) as response:
            assert response.headers["Content-Type"].startswith("text/javascript") and b"hydra-save" in response.read()
        assert request(url, app, "open", {"path": str(packed)})[0] == 200
        assert get_json(url + "/_desktop/pending")["writable"] is False
        assert post_save(url, {"message": "x"})[0] == 400


def test_remembering_archives_keeps_machine_signing_settings(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"signing": {"method": "gpg", "key": "K"}}), encoding="utf-8")
    app = desktop.Desktop(settings=settings)
    app._remember(tmp_path)
    assert json.loads(settings.read_text(encoding="utf-8"))["signing"] == {"method": "gpg", "key": "K"}


def test_wiki_posts_are_forwarded_to_the_open_archive(tmp_path):
    root = dynasty(tmp_path)

    def post(url, route, data):
        req = urllib.request.Request(url + route, data=json.dumps(data).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Hydra-Review": "1"})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    with running_app(tmp_path) as (app, url):
        assert post(url, "/suggest/cast", {"body": "x"})[0] == 409                       # no archive open
        assert request(url, app, "open", {"path": str(root)}) == (200, {"ok": True, "start": "/"})
        code, data = post(url, "/suggest/cast", {"body": "nope", "id": "x"})
        assert (code, data["error"]) == (400, "No such entry.")                          # the wiki answered, not a 404
        assert post(url, "/bazaar/install", {})[0] != 404


def test_opening_a_stale_archive_reports_a_bar_that_only_grows(tmp_path):
    root = dynasty(tmp_path)
    pages = root / layout.UNIVERSE_PARSED / "pages.jsonl"
    os.utime(pages, (pages.stat().st_mtime - 5, pages.stat().st_mtime - 5))
    seen = []
    app = desktop.Desktop(settings=tmp_path / "settings.json")
    try:
        app.open(root, build=True, progress=lambda stage, fraction=None: seen.append((stage, fraction)))
    finally:
        app._close_current()
    fractions = [f for _, f in seen]
    assert fractions and all(f is not None for f in fractions)
    assert fractions == sorted(fractions)
    assert fractions[-1] == 1.0 and seen[-1][0] == "Ready"
    assert 1.0 not in fractions[:-1]
    assert {"Building pages", "Starting reader"} <= {stage for stage, _ in seen}


def post_desk(url, route, data):
    req = urllib.request.Request(url + "/_desktop/" + route, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json", "X-Hydra-Save": "1"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_save_dialog_routes_plan_hold_tag_discard_log_restore(tmp_path):
    from hydra.archive import history
    root = dynasty(tmp_path)
    with running_app(tmp_path) as (app, url):
        assert request(url, app, "open", {"path": str(root)})[0] == 200
        history.auto(root, "a step")
        full = get_json(url + "/_desktop/pending")
        assert full["collections"] and all(c["title"] for c in full["collections"]) and "review" in full
        assert post_save(url, {"message": "First", "tag": "bad tag"})[0] == 400       # the version is checked before saving
        code, body = post_save(url, {"message": "First", "tag": "v1"})
        assert code == 200 and history.tags(root)["v1"] == body["id"]
        assert post_save(url, {"message": "Again", "tag": "v1"})[0] == 400
        col = sorted((root / "collections").glob("*.json"))[0]
        rel = f"collections/{col.name}"
        recs = json.loads(col.read_text(encoding="utf-8"))
        recs[0]["properties"]["name"] = ["Changed Name"]
        col.write_text(json.dumps(recs), encoding="utf-8")
        history.auto(root, "rename")
        rid = recs[0]["id"]
        d = get_json(url + f"/_desktop/diff?path={rel}&id={rid}")
        assert d["change"] == "changed" and d["fields"][0]["after"] == ["Changed Name"]
        code, body = post_save(url, {"message": "Held", "hold": {"records": [[rel, rid]], "files": []}})
        assert code == 200 and get_json(url + "/_desktop/pending?brief=1")["dirty"] is True    # what was left out lights the dot
        assert post_desk(url, "discard", {"path": rel, "id": rid})[0] == 200
        assert json.loads(col.read_text(encoding="utf-8"))[0]["properties"]["name"] != ["Changed Name"]
        log = get_json(url + "/_desktop/log")
        assert [s["message"] for s in log["saves"]] == ["Held", "First"] and log["saves"][1]["tags"] == ["v1"]
        assert post_desk(url, "tag", {"name": "v2", "at": log["saves"][0]["id"]})[0] == 200
        assert post_desk(url, "amend", {"message": "Held back"})[0] == 400              # v2 holds the newest save
        pv = get_json(url + f"/_desktop/restore?at={log['saves'][1]['id']}")
        assert pv["id"] == log["saves"][1]["id"]
        code, out = post_desk(url, "restore", {"at": log["saves"][1]["id"], "confirm": True})
        assert code == 200 and out["ok"]
        req = urllib.request.Request(url + "/_desktop/discard", data=b"{}", headers={"Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=10)
        assert exc.value.code == 403                                                     # the header keeps other sites out


def test_landing_follows_the_look_of_the_archive_last_opened(tmp_path):
    from hydra_desktop import look as desktop_look
    root = dynasty(tmp_path)
    with running_app(tmp_path) as (app, url):
        def page(route="/_desktop/"):
            with urllib.request.urlopen(url + route, timeout=10) as response:
                return response.read().decode()

        def report(look, header=True):
            req = urllib.request.Request(url + "/_desktop/look", data=json.dumps(look).encode(), method="POST",
                                         headers={"Content-Type": "application/json", **({"X-Hydra-Look": "1"} if header else {})})
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    return response.status, json.loads(response.read())
            except urllib.error.HTTPError as exc:
                return exc.code, json.loads(exc.read())

        light_blue = desktop_look.DEFAULT                                   # nothing kept yet: the owner's Light + Blue
        assert light_blue["theme"] == "light" and light_blue["mode"] == "light"
        home = page()
        assert '<html lang="en" data-mode="light">' in home and "--link:#3366cc" in home and "--bg:#ffffff" in home
        assert "color-scheme:light}" in home and "localStorage" not in home
        assert 'data-mode="light"' in page("/_desktop/profile") and "--link:#3366cc" in page("/_desktop/profile")

        assert request(url, app, "open", {"path": str(root)})[0] == 200
        assert "/_desktop/look.js" in page("/")                              # a wiki page reports its look
        with urllib.request.urlopen(url + "/_desktop/look.js", timeout=5) as response:
            assert response.headers["Content-Type"].startswith("text/javascript") and b"/_desktop/look" in response.read()

        dark = {"theme": "tide", "mode": "dark", "vars": {"bg": "#11171d", "ink": "#e3e9ee", "muted": "#93a3ad", "line": "#2a3540",
                "link": "#7fc6bc", "panel": "#18212a", "serif": "Georgia,serif", "evil": "x}</style><script>", "nope": "#fff"}}
        assert report(dark, header=False)[0] == 403
        assert report(dark) == (200, {"changed": True})
        assert report(dark) == (200, {"changed": False})
        kept = json.loads((tmp_path / "look.json").read_text(encoding="utf-8"))   # beside the desktop settings, never in the archive
        assert kept["theme"] == "tide" and kept["mode"] == "dark" and "evil" not in kept["vars"] and "nope" not in kept["vars"]
        assert not list(root.rglob("look.json"))
        home = page()
        assert 'data-mode="dark"' in home and "--bg:#11171d" in home and "--link:#7fc6bc" in home and "--serif:Georgia,serif" in home
        assert "color-scheme:dark}" in home and "<script>" not in home.split("</style>")[0].split("<title>")[1]
        assert "--bg:#11171d" in page("/_desktop/profile")
        assert report({"mode": "dark", "vars": {}})[0] == 400                # no colours: not a look
        assert report({"mode": "sepia", "vars": {"bg": "#fff", "ink": "#000"}})[0] == 400
        assert desktop.Desktop(settings=tmp_path / "settings.json").look()["theme"] == "tide"   # kept across runs
