"""test_network_guard.py: no new outbound network call site in hydra_desktop (as hydra's tests/test_network_guard.py,
which scanned these modules while they lived in hydra).

The desktop talks only to itself: its server proxies the window's requests to the open archive's wiki on 127.0.0.1.
`CALLS` and `IMPORTS` list today's sites, each with its reason; they only shrink: the test fails on a new site and on a
listed site that is gone (delete its row in the same change). The pages and the window bar's script may not name an
http(s) address in fetch(), script src, url() or import."""
from __future__ import annotations

import ast
import re
import warnings
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "hydra_desktop"

CALL_NAMES = {"urlopen", "create_connection", "HTTPConnection", "HTTPSConnection", "getaddrinfo", "gethostbyname",
              "FTP", "SMTP", "SMTP_SSL", "build_opener"}
NET_MODULES = {"urllib.request", "http.client", "socket", "requests", "httpx", "aiohttp", "ftplib", "smtplib",
               "webbrowser", "websocket", "websockets"}
SHELL_NETS = {"curl", "wget"}

# (module, function) -> why. Today (2026-11-24).
CALLS = {
    ("hydra_desktop.app", "serve_desktop"): "loopback: the desktop shell proxies to its own wiki on 127.0.0.1",
}

# (module) -> why: modules allowed to import a network module.
IMPORTS = {
    "hydra_desktop.app": "loopback proxy to its own wiki",
}


def _files():
    for p in sorted(SRC.rglob("*.py")):
        parts = ["hydra_desktop", *p.relative_to(SRC).with_suffix("").parts]
        if parts[-1] == "__init__":
            parts = parts[:-1]
        yield ".".join(parts), p


def _scan():
    calls, imports = set(), set()
    for mod, p in _files():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(p.read_text(encoding="utf-8"))

        def walk(node, scope):
            for ch in ast.iter_child_nodes(node):
                if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    walk(ch, scope + [ch.name])
                    continue
                if isinstance(ch, ast.Import):
                    if any(a.name in NET_MODULES for a in ch.names):
                        imports.add(mod)
                elif isinstance(ch, ast.ImportFrom):
                    base = ch.module or ""
                    if base in NET_MODULES or any(f"{base}.{a.name}" in NET_MODULES for a in ch.names):
                        imports.add(mod)
                elif isinstance(ch, ast.Call):
                    f = ch.func
                    name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
                    root = f
                    while isinstance(root, ast.Attribute):
                        root = root.value
                    if name in CALL_NAMES or (isinstance(root, ast.Name) and root.id in ("requests", "httpx", "aiohttp")):
                        calls.add((mod, ".".join(scope) or "<module>"))
                    if name in ("run", "Popen", "call", "check_output") and any(
                            isinstance(a, ast.Constant) and a.value in SHELL_NETS
                            for arg in ch.args if isinstance(arg, (ast.List, ast.Tuple)) for a in arg.elts):
                        calls.add((mod, ".".join(scope) or "<module>"))
                walk(ch, scope)
        walk(tree, [])
    return calls, imports


def test_no_new_network_call_site():
    calls, _ = _scan()
    new, gone = sorted(calls - set(CALLS)), sorted(set(CALLS) - calls)
    assert not new, f"new network call site(s) {new}: the desktop makes no request the person did not ask for"
    assert not gone, f"listed network call site(s) no longer there {gone}: delete the row from CALLS"


def test_no_new_network_importer():
    _, imports = _scan()
    new, gone = sorted(imports - set(IMPORTS)), sorted(set(IMPORTS) - imports)
    assert not new, f"module(s) import a network library {new}: list in IMPORTS with a reason"
    assert not gone, f"listed importer(s) no longer import one {gone}: delete the row from IMPORTS"


JS_BAD = [re.compile(p) for p in (
    r"""fetch\(\s*[`'"]https?:""",
    r"""<script[^>]*\ssrc=["']?https?:""",
    r"""url\(\s*["']?https?:""",
    r"""import\s*\(?\s*["']https?:""",
    r"""\bsrc\s*=\s*["'`]https?:""",
    r"""new\s+(?:WebSocket|EventSource)\(\s*[`'"]""",
    r"""sendBeacon\(\s*[`'"]https?:""",
)]


def test_pages_name_no_outside_address():
    files = [SRC / "chrome.js", *sorted((SRC / "pages").glob("*.*"))]
    bad = [f"{p.name}: {m.group(0)[:60]}" for p in files for rx in JS_BAD
           for m in rx.finditer(p.read_text(encoding="utf-8", errors="replace"))]
    assert files[1:] and not bad, f"a desktop page reaches an outside address: {bad}"
