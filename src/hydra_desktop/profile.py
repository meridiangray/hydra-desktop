"""The desktop's Profile page, `/_desktop/profile`, and the routes behind it. Works with or without an archive open.

    GET  /_desktop/profile            the page
    GET  /_desktop/profile.json       the profile (what the window bar's avatar reads)
    GET  /_desktop/profile/<file>     the portrait
    POST /_desktop/profile.json       save (JSON body)
    POST /_desktop/profile/reroll     a new code name
    POST /_desktop/profile/portrait   the image as the body (PNG, JPEG, GIF, WebP; 2 MB)

The data and its checks are profile.py's; the profile never leaves this machine.
"""
from __future__ import annotations

import json
import re

from markupsafe import Markup

from hydra import templating
from hydra.machine import profile
from hydra_desktop import look as desktop_look

PAGES = templating.for_package("hydra_desktop")      # hydra_desktop/pages/

CONTENT_TYPES = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}


def view(root=None) -> dict:
    p = profile.load()
    return {k: p[k] for k in ("codename", "name", "handle", "bio", "portrait", "fields", "badges")}


def get(path: str, root=None, token: str = "", look: dict | None = None):
    """(status, body, content type) for a GET under /_desktop/profile, else None."""
    path = path.split("?")[0]
    if path == "/_desktop/profile":
        return 200, render(root, token, look).encode("utf-8"), "text/html; charset=utf-8"
    if path == "/_desktop/profile.json":
        return 200, json.dumps(view(root)).encode("utf-8"), "application/json"
    m = re.fullmatch(r"/_desktop/profile/(portrait-[0-9a-f]{8}\.\w+)", path)
    if m:
        f = profile.portrait_path(m.group(1))
        if f:
            return 200, f.read_bytes(), CONTENT_TYPES.get(f.suffix[1:], "application/octet-stream")
        return 404, b"Not found", "text/plain"
    return None


def post(path: str, body: bytes, root=None) -> tuple[int, dict]:
    """(status, JSON) for a POST under /_desktop/profile. The caller has checked the token and the size."""
    try:
        if path == "/_desktop/profile.json":
            data = json.loads(body)
            profile.save(data)
            return 200, view(root)
        if path == "/_desktop/profile/reroll":
            return 200, {"codename": profile.reroll()["codename"]}
        if path == "/_desktop/profile/portrait":
            return 200, {"portrait": profile.set_portrait(body)}
    except (ValueError, OSError) as exc:
        return 400, {"error": str(exc)}
    return 404, {"error": "Not found"}


def render(root=None, token: str = "", look: dict | None = None) -> str:
    boot = {"profile": view(root), "kinds": list(profile.KINDS), "token": token,
            "hosts": profile.HOSTS, "limits": {"name": profile.NAME_MAX, "handle": profile.HANDLE_MAX,
                                               "bio": profile.BIO_MAX, "label": profile.LABEL_MAX,
                                               "value": profile.VALUE_MAX, "fields": profile.FIELDS_MAX}}
    look = look or desktop_look.DEFAULT
    return PAGES.render("profile.html", look=look, boot=boot,
                        css=PAGES.raw("profile.css"), js=PAGES.raw("profile.js"),
                        look_css=Markup(desktop_look.css(look)))   # values vetted by desktop_look.clean
