"""The desktop app's profile routes (hydra.machine.profile itself is tested in hydra-git)."""
import json
import threading
import urllib.error
import urllib.request

import pytest

from hydra.machine import profile
from hydra_desktop import app as desktop

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32


@pytest.fixture(autouse=True)
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("HYDRA_CONFIG_DIR", str(tmp_path / "cfg"))


def test_desktop_routes(tmp_path):
    app = desktop.Desktop(settings=tmp_path / "d.json")
    server = desktop.serve_desktop(app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def call(path, data=None, token=True, ctype="application/json"):
        headers = {"Content-Type": ctype, **({"X-Hydra-Token": app.token} if token else {})}
        req = urllib.request.Request(base + path, data=data, headers=headers, method="POST" if data is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
    try:
        code, page = call("/_desktop/profile")
        assert code == 200 and app.token.encode() in page and b"Profile" in page
        code, body = call("/_desktop/profile.json")
        assert json.loads(body)["codename"] == profile.load()["codename"]
        assert call("/_desktop/profile.json", b"{}", token=False)[0] == 403
        code, body = call("/_desktop/profile/portrait", PNG, ctype="image/png")
        name = json.loads(body)["portrait"]
        assert call("/_desktop/profile/portrait", b"junk")[0] == 400
        code, body = call("/_desktop/profile.json", json.dumps({"name": "Ada", "portrait": name}).encode())
        assert code == 200 and json.loads(body)["name"] == "Ada"
        assert call(f"/_desktop/profile/{name}") == (200, PNG)
        assert call("/_desktop/profile.json", b'{"handle": "a b"}')[0] == 400
        assert call("/_desktop/profile/reroll", b"{}")[0] == 200
    finally:
        server.shutdown()
