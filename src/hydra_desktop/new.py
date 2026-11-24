"""hydra_desktop/new.py — the desktop's New project flow.

An archive plus `view:` and `theme.base:` in universe/wiki.yaml. A ready view has a
`path` in the wiki the project opens at (`start`); the rest are planned views and
open at the main page. Wizard picks
are filed like hydra-mcp evidence: the file under .hydra/sources/files/setup/,
a Document record in entries/setup.json.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
from datetime import date
from pathlib import Path

from hydra.archive import layout

VIEWS = {
    "wiki":      {"label": "Wiki", "ready": True, "path": "/", "blurb": "Entries as articles."},
    "geo":       {"label": "Atlas", "ready": False, "blurb": "Entries on a map."},
    "radial":    {"label": "Radial", "ready": True, "path": "/radial", "blurb": "Connections as a graph."},
    "org":       {"label": "Org Chart", "ready": True, "path": "/org", "blurb": "Bodies, posts and who held them."},
    "messaging": {"label": "Communications", "ready": False, "blurb": "Letters as conversations."},
    "agentic":   {"label": "Agentic", "ready": False, "blurb": "", "flow": True},
    "blank":     {"label": "Blank", "ready": False, "blurb": "", "flow": True},
}
SETUP = "setup"                                     # the collection the wizard's sources are filed under

_B32 = "0123456789abcdefghjkmnpqrstvwxyz"           # Crockford base32, as hydra-mcp's mint uses


def _doc_id(content_hash: str) -> str:
    """A document's id from its file hash: one file, one id wherever it lands."""
    n = int(hashlib.sha1(content_hash.encode()).hexdigest(), 16) >> (160 - 5 * 10)
    return "doc-" + "".join(_B32[(n >> (5 * i)) & 31] for i in range(9, -1, -1))


def start(view) -> str:
    """Where a project whose wiki.yaml says `view:` opens: its view's page, else the main page."""
    return (VIEWS.get(view) or {}).get("path") or "/"


def create(dest, name: str, view: str = "wiki", theme: str = "") -> Path:
    """A new archive at `dest` (new or empty folder) with its view and theme recorded."""
    from hydra.cli import init  # lazy: startup
    from hydra.wiki import site  # lazy: startup
    if view not in VIEWS:
        raise ValueError(f"view must be one of {', '.join(VIEWS)}")
    if theme and theme not in site.THEMES:
        from hydra.wiki.look import themes  # lazy: startup
        if theme not in themes.catalog():
            raise ValueError(f"no theme {theme!r} (hydra-ctl wiki themes lists them)")
    dest = Path(dest).expanduser()
    if not dest.parent.is_dir():
        raise ValueError(f"{dest.parent} does not exist")
    init.create(dest, name)
    wiki = dest / layout.UNIVERSE_WIKI
    wiki.write_text(f"view: {view}\ntheme:\n  base: {theme or site.DEFAULT_THEME}\n", encoding="utf-8")
    return dest


def _free_name(taken: set, name: str) -> str:
    if name not in taken:
        return name
    stem, dot, ext = name.rpartition(".")
    for i in range(2, 100):
        cand = f"{stem or name}-{i}{dot}{ext}" if dot else f"{name}-{i}"
        if cand not in taken:
            return cand
    raise ValueError(f"too many files named {name}")


def add_file_sources(root, files) -> list[dict]:
    """File the wizard's picks as source documents: the original under
    `.hydra/sources/files/setup/`, a Document record each in `entries/setup.json`.
    Returns the records written."""
    root, seen = Path(root), {}
    records, taken = [], set()
    for f in files:
        path = Path(f).expanduser()
        if not path.is_file():
            raise ValueError(f"{path} is not a file")
        key = str(path.resolve())
        if key in seen:
            continue
        seen[key] = True
        data = path.read_bytes()
        name = _free_name(taken, path.name)
        taken.add(name)
        target = root / layout.SOURCES_DIR / "files" / SETUP / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        sha1 = hashlib.sha1(data).hexdigest()
        records.append({"id": _doc_id(sha1), "schema": "Document",
                        "properties": {"title": [path.stem], "fileName": [name],
                                       "mimeType": [mimetypes.guess_type(path.name)[0] or ""],
                                       "contentHash": [sha1], "fileSize": [str(len(data))],
                                       "retrievedAt": [date.today().isoformat()]}})
    if records:
        entries = root / layout.SOURCE_ENTRIES / f"{SETUP}.json"
        entries.parent.mkdir(parents=True, exist_ok=True)
        entries.write_text(json.dumps(records, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return records
