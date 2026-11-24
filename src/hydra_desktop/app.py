from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.error
import urllib.request
import zipfile

from hydra_desktop import look as desktop_look, new as desktop_new, profile as desktop_profile
from hydra.machine import userdirs, profile
from hydra.build import freshness, run as archive_build, rebuilder, gencache
from hydra.sources import sourcetitle
from hydra.archive import layout, resources, history, collmeta, writelock
from hydra_desktop.home import render_home
from hydra.universe import build as ubuild
from hydra.wiki import site
from hydra.wiki.look import themes
from hydra.cli.pack import unpack
from hydra_desktop.progress import Meter

SLOW = 0.25                                         # seconds: a page or call slower than this is noted in slow.log


def slow_log(method: str, path: str, t0: float) -> None:
    """Note a slow request in `<config>/slow.log` (time, method, path, ms), so a lag the person feels can be traced to
    the request that caused it. The path is cut at its query; nothing else about the request is kept."""
    ms = (time.perf_counter() - t0) * 1000
    if ms < SLOW * 1000:
        return
    try:
        d = userdirs.config_dir()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "slow.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{method}\t{path.split('?')[0]}\t{ms:.0f}\n")
    except OSError:
        pass


CHROME_EXT = Path(__file__).with_name("chrome.js")      # the window bar's extras, served so the bar changes without a rebuild


def shell_path(given=None) -> Path:
    given = given or os.environ.get("HYDRA_DESKTOP_SHELL")
    if given:
        path = Path(given).expanduser().resolve()
    else:
        name = "hydra-desktop-shell.exe" if os.name == "nt" else "hydra-desktop-shell"
        base = Path(__file__).resolve().parents[2] / "shell" / "build"      # hydra-desktop/shell/build
        candidates = [base / "Release" / name, base / name]
        found = shutil.which(name)
        path = next((p for p in candidates if p.is_file()), Path(found) if found else candidates[0])
    if not path.is_file():
        raise FileNotFoundError(f"Build the Saucer shell first, in hydra-desktop: cmake -S shell -B shell/build; "
                                f"cmake --build shell/build --config Release. "
                                f"Use --shell PATH for a shell outside this checkout (looked for {path}).")
    return path


def child_env() -> dict:
    """The environment of a child `python -m hydra_desktop...`: this package's folder first on PYTHONPATH, so the
    child finds it as this process did (a source checkout run with `pythonpath = src`, not only an install)."""
    here = str(Path(__file__).resolve().parents[1])
    rest = os.environ.get("PYTHONPATH")
    return {**os.environ, "PYTHONPATH": os.pathsep.join([here, rest] if rest else [here])}


def pick_archive(kind="folder") -> str:
    result = subprocess.run([sys.executable, "-m", "hydra_desktop.picker", kind],
                            capture_output=True, text=True, encoding="utf-8", env=child_env())
    if result.returncode:
        raise ValueError(f"Could not open the archive picker: {result.stderr.strip() or result.returncode}")
    return result.stdout.strip()


def debug_env(port: int) -> dict:
    """Environment that makes the shell's WebView2 listen for a DevTools client (hydra-git/scripts/uicheck.py --attach PORT).
    It gets its own profile folder: WebView2 refuses a second app with the same profile but other browser arguments."""
    if not 0 < port < 65536:
        raise ValueError("--debug-port must be a TCP port number")
    return {**os.environ,
            "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": f"--remote-debugging-port={port}",
            "WEBVIEW2_USER_DATA_FOLDER": str(Path(tempfile.gettempdir()) / f"hydra-desktop-debug-{port}")}


def run_shell(args, timeout=None, env=None) -> int:
    with subprocess.Popen(args, env=env) as process:
        try:
            return process.wait(timeout=timeout)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def settings_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "Hydra" / "desktop.json"


class NeedsBuild(ValueError):
    pass


class Desktop:
    def __init__(self, settings=None, theme=None):
        self.settings = Path(settings) if settings is not None else settings_path()
        self.theme = theme
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.progress_lock = threading.Lock()
        self.progress_state = {"stage": "Waiting", "fraction": None}
        self.current = None
        self.wiki = None
        self.worker = None
        self.view = None
        self.start = "/"
        self.auto_open = None                       # a stale archive given on the command line: the welcome page builds it behind the loader
        self.recent = self._load_recent()
        self.rebuilders = {}                        # archive -> its Rebuilder: the build behind the reader (P6)
        self.rebuild_state = {"running": False, "shown": False, "stage": "", "fraction": None, "n": 0}

    def look(self) -> dict:
        """The look of the archive last opened (desktop_look): the landing and the Profile page are drawn in it."""
        return desktop_look.load(self.settings)

    def keep_look(self, data) -> bool:
        with self.lock:
            return desktop_look.save(self.settings, data)

    def _load_recent(self):
        try:
            data = json.loads(self.settings.read_text(encoding="utf-8"))
            return [p for p in data.get("recent", []) if isinstance(p, str)][:12]
        except (OSError, ValueError, TypeError, AttributeError):
            return []

    def _remember(self, path):
        self.recent = [str(path), *(p for p in self.recent if p != str(path))][:12]
        try:
            self.settings.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.settings.with_suffix(".tmp")
            try:                                    # machine settings hold more than the recent list (`signing`)
                kept = json.loads(self.settings.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                kept = {}
            kept = {**(kept if isinstance(kept, dict) else {}), "recent": self.recent}
            tmp.write_text(json.dumps(kept, indent=2) + "\n", encoding="utf-8")
            tmp.replace(self.settings)
        except OSError as exc:
            print(f"hydra-desktop: could not save recent archives: {exc}", file=sys.stderr)

    def report_progress(self, stage: str, fraction: float | None = None):
        """Opening phases are indeterminate until a build reports a real fraction (0..1)."""
        if fraction is not None and not 0 <= fraction <= 1:
            raise ValueError("Progress fraction must be between 0 and 1")
        with self.progress_lock:
            self.progress_state = {"stage": stage, "fraction": fraction}

    def open(self, path, *, build=False, progress=None):
        """Open a path; `progress(stage, fraction=None)` may report measured work as 0..1."""
        path = Path(path).expanduser().resolve()
        report = progress or (lambda stage, fraction=None: None)
        with self.lock:
            meter = Meter(report, ("Building archive data", "Building pages", "Starting reader"))
            try:
                self._open(path, build, report, meter)
            finally:
                meter.done()
            report("Ready", 1.0)

    def _open(self, path, build, report, meter):
        if not (resources.is_archive(path) or resources.is_pack(path)):
            raise ValueError(f"{path} is not a Hydra archive folder or .hydra file")
        view = None
        wiki = worker = None
        try:
            if resources.is_pack(path):
                meter.plan(("Unpacking archive", "Building archive data", "Building pages", "Starting reader"))
                meter.phase("Unpacking archive")
                view = tempfile.TemporaryDirectory(prefix="hydra-desktop-")
                root, _ = unpack(path, Path(view.name) / path.stem)
                root = resources.archive(root, read_only=True)
                if not (root / layout.BUILD_YAML).is_file():
                    meter.phase("Building archive data")
                    archive_build.ensure_built(root, label=path)
                elif not freshness.built_by_this_code(root):     # G13: a build made by other code is rebuilt, never misread
                    meter.phase("Building archive data")
                    archive_build.build_archive(root, progress=meter.measured)
            else:
                root = resources.archive(path, read_only=True)
                self._settle(root)                  # a build still running behind the reader: its files first
            needs_pages = not ubuild.pages_current(root)
            needs_archive = not view and (
                not freshness.up_to_date(root) if (root / layout.BUILD_YAML).is_file() else needs_pages)
            behind = False
            if (needs_archive or needs_pages) and not view and not build:
                if rebuilder.built_by_this_code(root):        # P6: the last build opens at once; the new one is made behind it
                    behind, needs_archive, needs_pages = True, False, False
                elif not (root / layout.BUILD_YAML).is_file() or not (root / layout.UNIVERSE_PARSED / "pages.jsonl").is_file():
                    raise NeedsBuild("This archive's wiki pages are missing. Build this folder to open it?")
                # else: built by other code, so not read as it is: rebuilt first, behind the loader (only derived files change)
            meter.plan(tuple(st for st, need in (("Building archive data", needs_archive),
                                                 ("Building pages", needs_archive or needs_pages),
                                                 ("Starting reader", True)) if need))
            if needs_archive or needs_pages:
                if needs_archive:
                    meter.phase("Building archive data")
                    archive_build.build_archive(root, progress=meter.measured)
                meter.phase("Building pages")
                ubuild.build(root, progress=meter.measured)
            meter.phase("Starting reader")
            wiki, reader = site.serve(root, port=0, host="127.0.0.1", theme=self.theme,
                                      writable=not view)        # a pack opens as a throwaway copy: no decisions
            worker = threading.Thread(target=wiki.serve_forever, name="hydra-wiki", daemon=True)
            worker.start()
        except BaseException:
            if wiki:
                wiki.server_close()
            if view:
                view.cleanup()
            raise
        self._close_current()
        self.current, self.wiki, self.worker, self.view = path, wiki, worker, view
        self.start = desktop_new.start(reader.conf.get("view"))
        self._remember(path)
        if behind:
            self._rebuild(root, shown=True).request(0)

    # ---- the build behind the reader (P6): on a stale open, and after the app's writes that do not rebuild ----------

    def _rebuild(self, root, shown: bool):
        """The archive's Rebuilder; `shown`: the window shows its progress and reloads the page when it is done."""
        key = str(Path(root).resolve())
        r = self.rebuilders.get(key)
        if r is None:
            r = self.rebuilders[key] = rebuilder.Rebuilder(root)
        state = self.rebuild_state

        def report(stage, fraction=None):
            state.update(stage=stage, fraction=fraction)

        def done(result):
            if result == "built":
                with self.lock:                     # the archive still open: its server reads the new generation
                    httpd = self.wiki if self.current and str(Path(self.current).resolve()) == key else None
                if httpd is not None:
                    try:
                        httpd.reload_now()
                    except Exception as exc:        # the reader keeps the last build
                        print(f"hydra-desktop: could not read the new build: {exc}", file=sys.stderr)
                state["n"] += 1
            state.update(running=False, fraction=1.0 if result == "built" else state.get("fraction"))
        r.report, r.done = report, done
        state.update(running=True, shown=shown or (state["running"] and state["shown"]), stage="", fraction=0.0)
        return r

    def after_write(self):
        """A write of the open archive went through: once writes stop for a moment, a build it left stale is made
        quietly behind the reader (P6). Nothing happens when the write rebuilt, or wrote nothing a build reads."""
        root = self.save_root()
        if root:
            r = self.rebuilders.get(str(Path(root).resolve()))
            if r is None or not r.running:
                self._rebuild(root, shown=False).request(3.0)
            else:
                r.request(3.0)

    def _settle(self, root):
        """Wait for a build behind the reader of this archive to end (it writes the files the open reads)."""
        r = self.rebuilders.get(str(Path(root).resolve()))
        while r is not None and r.running:
            time.sleep(0.1)

    def new(self, path, name, view, theme, sources, progress=None) -> bool:
        """Create a project at `path` and open it. Returns False when the archive was created but
        holds no records yet: it is remembered, but there is nothing to read."""
        report = progress or (lambda stage, fraction=None: None)
        with self.lock:
            report("Creating project")
            dest = desktop_new.create(path, name, view=view, theme=theme)
            if sources:
                report("Filing sources")
                desktop_new.add_file_sources(dest, sources)
            try:
                self.open(dest, build=True, progress=report)
            except archive_build.NothingToBuild:
                self._remember(dest)
                return False
            return True

    def save_root(self):
        """The open archive's folder when a save can be made there (not a throwaway copy of a .hydra file)."""
        return self.current if self.current and not self.view and self.wiki else None

    def pending(self, brief=False) -> dict:
        """What the Save dialog shows (`history.plan`, the author and whether this machine signs), or, brief, only
        whether the dot is lit: steps since the last save, or a save that left changes out."""
        root = self.save_root()
        if not root or not history.enabled(root):
            return {"dirty": False, "writable": False}
        if brief:
            top, last = history.head(root)[1], history.last_save(root)
            moved = bool(top) and (not last or history.snap(root, top)["files"] != history.snap(root, last)["files"])
            return {"dirty": moved or history.held_open(root), "writable": True}     # a discard back to the save leaves nothing
        data = history.plan(root)
        for c in data["collections"]:
            c["title"] = collmeta.collection_title(root, c["name"])
        for r in data["sources"]:
            r["label"] = sourcetitle.scrub(r["label"]) or r["label"]       # a scraped title's UI words left out
        return {**data, "writable": True, "author": self.author(root),
                "signing": history.signing_config(self.settings) is not None,
                "tags": sorted(history.tags(root))}

    @staticmethod
    def author(root) -> str:
        """Who a save names: the Profile's author, else hydra.yaml `author:`, else "" (never the system user)."""
        try:
            who = str(profile.author() or "").strip()
        except Exception:                           # no Profile yet, or an unreadable one: the archive's own setting
            who = ""
        return who or history.configured_author(root)

    def save(self, data: dict) -> dict:
        root = self.save_root()
        if not root:
            raise ValueError("Nothing to save here: no archive is open for writing")
        picked = data.get("entities")
        entities = None
        if isinstance(picked, list) and "hold" not in data:       # the first dialog: what the save says it covers
            pending = history.since_last_save(root)
            keep = {(str(k[0]), str(k[1])) for k in picked if isinstance(k, list) and len(k) == 2}
            entities = [e for e in pending["entities"] if (e["path"], e["id"]) in keep]
        cfg = history.signing_config(self.settings) if data.get("sign") is True else None
        if data.get("sign") is True and not cfg:
            raise ValueError("Signing is not set up on this machine")
        tag = str(data.get("tag") or "").strip()
        if tag and not history.REF.match(tag):
            raise ValueError(f"'{tag}' cannot name a version: letters, digits, '.', '-', '_' and '/'")
        if tag and tag in history.tags(root):
            raise ValueError(f"Version {tag} exists")
        who = str(data.get("author") or "").strip()[:200] or self.author(root) or "unknown"
        sid = history.save(root, str(data.get("message") or ""), str(data.get("description") or "")[:4000], entities,
                           sign=cfg, who=who, hold=data.get("hold") if isinstance(data.get("hold"), dict) else None)
        if tag:
            history.tag(root, tag, sid)
        return {"ok": True, "id": sid}

    def history_get(self, route: str, query: dict) -> dict:
        """The Save dialog's reads: GET /_desktop/diff?path=&id= (one record before and after), /_desktop/restore?at=
        (what restoring a save would change) and /_desktop/log (the newest saves)."""
        root = self.save_root()
        if not root:
            raise ValueError("No archive is open for writing")
        if route == "diff":
            return history.record_diff(root, query.get("path", ""), query.get("id", ""))
        if route == "restore":
            return history.restore_preview(root, query.get("at", ""))
        rows = history.recent(root, 13)
        return {"saves": rows[:12], "more": len(rows) > 12}

    def history_post(self, route: str, data: dict) -> dict:
        """The Save dialog's other writes: discard (a record or files back to the last save, a step), restore (the
        files back to a save, a snapshot; without `confirm` a preview), tag (a version on a save), amend (the newest
        save's words), refresh (build again and reopen, once, after discards or a restore)."""
        root = self.save_root()
        if not root:
            raise ValueError("No archive is open for writing")
        who = self.author(root) or None
        if route == "discard":
            files = data.get("files")
            rid = data.get("id")
            return {"ok": True, **history.discard(root, data.get("path"), None if rid is None else str(rid),
                                                  files if isinstance(files, list) else None, who=who)}
        if route == "restore":
            if data.get("confirm") is not True:
                return history.restore_preview(root, str(data.get("at") or ""))
            return {"ok": True, **history.restore_to(root, str(data.get("at") or ""), who=who)}
        if route == "tag":
            name = str(data.get("name") or "").strip()
            return {"ok": True, "id": history.tag(root, name, str(data.get("at") or "") or None), "name": name}
        if route == "amend":
            desc = data.get("description")
            return {"ok": True, **history.amend(root, str(data.get("message") or ""),
                                                desc[:4000] if isinstance(desc, str) else None,
                                                sign=history.signing_config(self.settings))}
        if route == "refresh":
            self.open(self.current, build=True, progress=self.report_progress)
            return {"ok": True, "start": self.start}
        raise ValueError("Not found")

    def icon_root(self):
        """The open archive's folder, where its icons and packages' icons are looked up (None: this machine's only)."""
        return self.current if self.current and Path(self.current).is_dir() else None

    def _close_current(self):
        if self.wiki:
            self.wiki.shutdown()
            self.wiki.server_close()
            self.worker.join()
        if self.view:
            self.view.cleanup()
        self.current = self.wiki = self.worker = self.view = None
        self.start = "/"

    def close(self):
        with self.lock:
            self._close_current()


SAVE_POSTS = ("/_desktop/save", "/_desktop/discard", "/_desktop/restore", "/_desktop/tag", "/_desktop/amend",
              "/_desktop/refresh")                 # the Save dialog's writes: each needs the X-Hydra-Save header
MAX_FORWARD = 23 * 2**20                                    # a bit over the wiki's largest route (the photo upload: 2 x 10 MiB + 2 MiB)
PASSED = ("Location", "Cache-Control", "ETag", "Content-Encoding", "Vary")


def passed(headers) -> dict:
    """The wiki's response headers the window should see: where to go, and how long it may keep what it got."""
    return {k: headers[k] for k in PASSED if headers.get(k)}


def serve_desktop(app):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect)

    class Handler(BaseHTTPRequestHandler):
        def local_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_address[1]}"

        def send(self, code, body=b"", content_type="text/html; charset=utf-8", headers=None):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if "Cache-Control" not in (headers or {}):       # the wiki's own caching (assets, flags, ETags) passes through
                self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def respond(self, code, data):
            self.send(code, json.dumps(data).encode("utf-8"), "application/json")

        def do_GET(self):
            if not self.local_host():
                return self.send(403, b"Forbidden", "text/plain")
            gencache.touch()                        # hand-edited files are looked at again once per request (P2)
            if self.path == "/_desktop/progress":
                if self.headers.get("X-Hydra-Token") != app.token:
                    return self.respond(403, {"error": "Unauthorized"})
                with app.progress_lock:
                    return self.respond(200, app.progress_state.copy())
            if self.path == "/_desktop/look.js":
                return self.send(200, desktop_look.LOOK_JS.encode("utf-8"), "text/javascript; charset=utf-8")
            if self.path == "/_desktop/chrome-ext.js":
                return self.send(200, CHROME_EXT.read_bytes(), "text/javascript; charset=utf-8")
            if self.path == "/_desktop/rebuild":                      # the build behind the reader: the window's thin bar
                return self.respond(200, dict(app.rebuild_state))
            if self.path.split("?")[0] == "/_desktop/pending":
                with app.lock:
                    return self.respond(200, app.pending(brief="brief=1" in self.path))
            if self.path.split("?")[0] in ("/_desktop/diff", "/_desktop/log", "/_desktop/restore"):   # the Save dialog's reads
                from urllib.parse import parse_qsl, urlsplit
                parts = urlsplit(self.path)
                try:
                    with app.lock:
                        return self.respond(200, app.history_get(parts.path.rsplit("/", 1)[1], dict(parse_qsl(parts.query))))
                except (OSError, ValueError, SystemExit) as exc:
                    return self.respond(400, {"error": str(exc).removeprefix("hydra: ")})
            if self.path.startswith("/_desktop/profile"):
                got = desktop_profile.get(self.path, app.icon_root(), app.token, look=app.look())
                if got:
                    return self.send(*got)
            if self.path.split("?")[0] == "/_desktop/":
                with app.lock:
                    page = render_home(app.recent, app.current, app.token, app.start, app.auto_open, look=app.look())
                    app.auto_open = None
                return self.send(200, page.encode("utf-8"))
            with app.lock:                          # the lock covers which wiki is open, not the request itself:
                if not app.wiki:                    # a map asks for many tiles at once, some fetched from afar
                    return self.send(302, headers={"Location": "/_desktop/"})
                url = f"http://127.0.0.1:{app.wiki.server_address[1]}{self.path}"
            t0 = time.perf_counter()
            # the wiki's caching reaches the window (owner 2026-11-20: "no needless lag"): its hashed assets, flags and
            # ETag'd data are kept by the browser and asked again with If-None-Match, instead of fetched anew every page
            ask = {k: self.headers[k] for k in ("If-None-Match", "Accept-Encoding") if self.headers.get(k)}
            try:
                with opener.open(urllib.request.Request(url, headers=ask), timeout=30) as response:
                    body, kept = response.read(), passed(response.headers)
                    ctype = response.headers.get("Content-Type", "text/html")
                    if ctype.startswith("text/html") and response.status == 200:        # the page reports its look (desktop_look)
                        if kept.get("Content-Encoding") == "gzip":
                            body, kept = gzip.decompress(body), {k: v for k, v in kept.items() if k != "Content-Encoding"}
                        tag = desktop_look.INJECT.encode()
                        body = body.replace(b"</body>", tag + b"</body>", 1) if b"</body>" in body else body + tag
                    self.send(response.status, body, ctype, kept)
                slow_log("GET", self.path, t0)
            except urllib.error.HTTPError as exc:
                if exc.code == 304:                                  # the window has these bytes: no body
                    self.send_response(304)
                    for k, v in passed(exc.headers).items():
                        self.send_header(k, v)
                    self.end_headers()
                    return
                self.send(exc.code, exc.read(), exc.headers.get("Content-Type", "text/html"), passed(exc.headers))
            except (OSError, ValueError):
                self.send(502, b"Archive view is unavailable", "text/plain")

        def do_POST(self):
            if not self.local_host():
                return self.respond(403, {"error": "Unauthorized"})
            gencache.touch()
            if not self.path.startswith("/_desktop/"):               # every other POST belongs to the open archive's wiki
                size = int(self.headers.get("Content-Length") or 0)    # (Review, Symbology, Suggestions, Bazaar, photos ...);
                if not 0 <= size <= MAX_FORWARD:                       # the wiki enforces each route's own limit
                    return self.respond(413, {"error": "Request too large"})
                body = self.rfile.read(size)
                with app.lock:
                    if not app.wiki:
                        return self.respond(409, {"error": "No archive is open"})
                    headers = {k: v for k, v in self.headers.items() if k.lower().startswith("x-hydra-")}
                    headers["Content-Type"] = self.headers.get("Content-Type") or "application/json"
                    req = urllib.request.Request(f"http://127.0.0.1:{app.wiki.server_address[1]}{self.path}", data=body,
                                                 method="POST", headers=headers)
                    t0 = time.perf_counter()
                    try:
                        with opener.open(req, timeout=600) as response:
                            self.send(response.status, response.read(), response.headers.get("Content-Type", "application/json"))
                            app.after_write()                   # a write that did not rebuild is rebuilt quietly, once writes stop
                            return slow_log("POST", self.path, t0)
                    except urllib.error.HTTPError as exc:
                        return self.send(exc.code, exc.read(), exc.headers.get("Content-Type", "application/json"))
                    except (OSError, ValueError):
                        return self.respond(502, {"error": "Archive view is unavailable"})
            if self.path == "/_desktop/look":                        # the open page's colours, fonts and mode, kept machine-wide
                if self.headers.get("X-Hydra-Look") != "1":
                    return self.respond(403, {"error": "Unauthorized"})
                size = int(self.headers.get("Content-Length") or 0)
                if not 0 < size <= desktop_look.MAX_BODY:
                    return self.respond(413, {"error": "Request too large"})
                try:
                    return self.respond(200, {"changed": app.keep_look(json.loads(self.rfile.read(size)))})
                except (OSError, ValueError) as exc:
                    return self.respond(400, {"error": str(exc)})
            if self.path.startswith("/_desktop/profile"):            # the person's own profile: this machine only
                size = int(self.headers.get("Content-Length") or 0)
                if self.headers.get("X-Hydra-Token") != app.token:
                    return self.respond(403, {"error": "Unauthorized"})
                if not 0 <= size <= 3 << 20:
                    return self.respond(413, {"error": "Request too large"})
                return self.respond(*desktop_profile.post(self.path, self.rfile.read(size), app.icon_root()))
            if self.path in SAVE_POSTS:                            # same origin as the wiki pages; the header keeps other sites out
                if self.headers.get("X-Hydra-Save") != "1":
                    return self.respond(403, {"error": "Unauthorized"})
                try:
                    size = int(self.headers.get("Content-Length") or 0)
                    if not 0 < size <= 1 << 20:
                        return self.respond(413, {"error": "Request too large"})
                    data = json.loads(self.rfile.read(size))
                    if not isinstance(data, dict):
                        raise ValueError("Expected an object")
                    with app.lock:
                        if self.path == "/_desktop/save":
                            return self.respond(200, app.save(data))
                        return self.respond(200, app.history_post(self.path.rsplit("/", 1)[1], data))
                except writelock.Busy as exc:                      # another writer holds the archive: say so, change nothing
                    return self.respond(409, {"error": f"{exc.payload['why']} {exc.payload.get('do', '')}".strip(), "busy": True})
                except (OSError, ValueError, SystemExit) as exc:
                    return self.respond(400, {"error": str(exc).removeprefix("hydra: ")})
            if self.path not in ("/_desktop/open", "/_desktop/pick", "/_desktop/close", "/_desktop/new"):
                return self.respond(404, {"error": "Not found"})
            if self.headers.get("X-Hydra-Token") != app.token:
                return self.respond(403, {"error": "Unauthorized"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 <= size <= 65536:
                    return self.respond(413, {"error": "Request too large"})
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("Expected an object")
                if self.path == "/_desktop/pick":
                    kind = data.get("kind")
                    if kind not in ("file", "folder", "newfolder", "documents"):
                        raise ValueError("Choose a file, a folder or documents")
                    picked = pick_archive(kind)
                    if kind == "documents":
                        return self.respond(200, {"paths": [p for p in picked.split("\n") if p.strip()]})
                    return self.respond(200, {"path": picked})
                if self.path == "/_desktop/new":
                    name = str(data.get("name") or "").strip()
                    if not name or len(name) > 120:
                        raise ValueError("Give the project a name (120 characters at most)")
                    path = data.get("path")
                    if not isinstance(path, str) or not path.strip():
                        raise ValueError("Choose a folder for the project")
                    sources = data.get("sources") or []
                    if not isinstance(sources, list) or not all(isinstance(s, str) for s in sources):
                        raise ValueError("sources must be a list of file paths")
                    opened = app.new(path.strip(), name, str(data.get("view") or "wiki"),
                                   str(data.get("theme") or ""), sources, progress=app.report_progress)
                    return self.respond(200, {"ok": True, "empty": not opened, **({"start": app.start} if opened else {})})
                if self.path == "/_desktop/close":
                    app.close()
                else:
                    path = data.get("path")
                    if not isinstance(path, str) or not path.strip():
                        raise ValueError("Choose an archive path")
                    app.open(path, build=data.get("build") is True, progress=app.report_progress)
                    return self.respond(200, {"ok": True, "start": app.start})
                return self.respond(200, {"ok": True})
            except NeedsBuild as exc:
                return self.respond(409, {"error": str(exc), "requires_build": True})
            except (OSError, ValueError, SystemExit, zipfile.BadZipFile) as exc:
                return self.respond(400, {"error": str(exc).removeprefix("hydra: ")})

        def log_message(self, fmt, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


def launch(archive=None, shell=None, *, build=False, theme=None, smoke_test=False, settings=None, debug_port=None) -> int:
    executable = shell_path(shell)
    env = debug_env(debug_port) if debug_port else None
    app = Desktop(settings=settings, theme=theme)
    if archive:
        try:
            app.open(archive, build=build, progress=app.report_progress)
        except NeedsBuild:                          # open the window anyway; the welcome page runs the build behind its loader
            app.auto_open = str(Path(archive).expanduser().resolve())
    server = serve_desktop(app)
    worker = threading.Thread(target=server.serve_forever, name="hydra-desktop", daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    args = [str(executable), url]
    if smoke_test:
        args.append("--smoke-test")
    try:
        return run_shell(args, timeout=45 if smoke_test else None, **({"env": env} if env else {}))
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
        app.close()


def serve_only(archive=None, theme=None, settings=None) -> int:
    """No window: serve the desktop pages on a loopback port, print its address, and keep serving. The packaged
    shell starts this from its bundled Python and reads the address from the first line."""
    app = Desktop(settings=settings, theme=theme)
    server = serve_desktop(app)
    print(f"http://127.0.0.1:{server.server_address[1]}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    finally:
        server.server_close()
        app.close()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Open a Hydra archive in a Saucer desktop window.")
    parser.add_argument("archive", nargs="?", help="Archive folder or .hydra pack; omitted opens the welcome screen")
    parser.add_argument("--shell", help="Path to the built hydra-desktop executable")
    parser.add_argument("--build", action="store_true", help="Explicitly rebuild missing or stale universe pages")
    parser.add_argument("--theme", help="a theme's name (hydra-ctl wiki themes lists them) or a path to a theme file")
    parser.add_argument("--debug-port", type=int, metavar="PORT",
                        help="let a DevTools client drive the window on this port (hydra-git/scripts/uicheck.py --attach PORT)")
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)      # used by the packaged shell
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.theme:
        try:
            themes.load(args.theme)
        except themes.ThemeError as exc:
            print(f"hydra-desktop: {exc}", file=sys.stderr)
            return 2
    try:
        if args.serve:
            return serve_only(theme=args.theme)
        return launch(args.archive, args.shell, build=args.build, theme=args.theme, smoke_test=args.smoke_test,
                      debug_port=args.debug_port)
    except (OSError, ValueError, SystemExit, subprocess.TimeoutExpired) as exc:
        print(f"hydra-desktop: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
