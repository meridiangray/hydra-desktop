"""The desktop's welcome screen: a New project wizard beside the open/recents controls.
Wizard views come from `new.VIEWS`; themes from `site.THEMES`."""
from __future__ import annotations

from pathlib import Path

from markupsafe import Markup

from hydra import templating
from hydra.wiki import site
from hydra_desktop import look as desktop_look, new as desktop_new

PAGES = templating.for_package("hydra_desktop")      # hydra_desktop/pages/


def _svg(body: str, size: int = 15, stroke: float = 2) -> str:
    """A Lucide icon (ISC, lucide.dev), inline so it takes the text's colour."""
    return (f"<svg viewBox='0 0 24 24' width='{size}' height='{size}' fill='none' stroke='currentColor' "
            f"stroke-width='{stroke:g}' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'>{body}</svg>")


def _fill(body: str, viewbox: str, size: int) -> str:
    """A filled icon (the Wikipedia W is a letterform, not a stroke drawing)."""
    return (f"<svg viewBox='{viewbox}' width='{size}' height='{size}' fill='currentColor' "
            f"aria-hidden='true'>{body}</svg>")


FOLDER = _svg("<path d='M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9"
              "A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z'/>")   # lucide/folder
FOLDER_OPEN = _svg("<path d='m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6"
                   "a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2"
                   "a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2'/>", 17)          # lucide/folder-open
FILE_ICON = _svg("<path d='M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706"
                 "l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z'/><path d='M14 2v5a1 1 0 0 0 1 1h5'/>", 17)  # lucide/file
FILE_PLUS = _svg("<path d='M4 22h14a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v4'/><path d='M14 2v4a2 2 0 0 0 2 2h4"
                 "M3 15h6m-3-3v6'/>", 34, 1.55)                         # lucide/file-plus-2

# the icon washed into a view card's background
WIKIPEDIA_W = ("M640 51.2l-.3 12.2c-28.1.8-45 15.8-55.8 40.3-25 57.8-103.3 240-155.3 358.6H415l-81.9-193.1"
               "c-32.5 63.6-68.3 130-99.2 193.1-.3.3-15 0-15-.3C172 352.3 122.8 243.4 75.8 133.4 64.4 106.7"
               " 26.4 63.4.2 63.7c0-3.1-.3-10-.3-14.2h161.9v13.9c-19.2 1.1-52.8 13.3-43.3 34.2 21.9 49.7"
               " 103.6 240.3 125.6 288.6 15-29.7 57.8-109.2 75.3-142.8-13.9-28.3-58.6-133.9-72.8-160-9.7"
               "-17.8-36.1-19.4-55.8-19.7V49.8l142.5.3v13.1c-19.4.6-38.1 7.8-29.4 26.1 18.9 40 30.6 68.1"
               " 48.1 104.7 5.6-10.8 34.7-69.4 48.1-100.8 8.9-20.6-3.9-28.6-38.6-29.4.3-3.6 0-10.3.3-13.6"
               " 44.4-.3 111.1-.3 123.1-.6v13.6c-22.5.8-45.8 12.8-58.1 31.7l-59.2 122.8c6.4 16.1 63.3 142.8"
               " 69.2 156.7L559.2 91.8c-8.6-23.1-36.4-28.1-47.2-28.3V49.6l127.8 1.1.2.5z")  # FA wikipedia-w, CC BY 4.0
VIEW_ICON = {
    "wiki":      _fill(f"<path d='{WIKIPEDIA_W}'/>", "0 0 640 512", 66),
    "geo":       _fill("<path fill='currentColor' d='M8.904 16.5h3.618q-.021.248-.022.5c0 1.201.457 2.361 1.272 3.488c-.54.959-1.157 1.511-1.772 1.511c-1.197 0-2.4-2.094-3.038-5.204zm-.23-1.5h4.2a5.52 5.52 0 0 1 2.627-2.901v-.098q0-1.03-.076-2h-6.85l-.033.488A26 26 0 0 0 8.674 15M18 11.5a5.48 5.48 0 0 1 3.935 1.658A10.1 10.1 0 0 0 21.802 10h-4.87l.038.657q.022.463.029.934q.488-.09 1.001-.091M3.066 16.501h4.306c.364 2.082.983 3.854 1.792 5.093a10.03 10.03 0 0 1-5.952-4.814zm-.867-6.5h4.87a28 28 0 0 0 .033 4.42l.057.58H2.456a10.05 10.05 0 0 1-.258-5m12.745-7.424l-.108-.17A10.03 10.03 0 0 1 21.373 8.5h-4.59c-.316-2.416-.957-4.492-1.838-5.923m-5.902-.133l.122-.037C8.283 3.757 7.628 5.736 7.28 8.06l-.062.44H2.63a10.03 10.03 0 0 1 6.413-6.057M12 2.002c1.319 0 2.646 2.542 3.214 6.183l.047.315H8.739C9.28 4.691 10.644 2.002 12 2.002M22.5 17a4.5 4.5 0 0 0-9 0c0 1.863 1.42 3.815 4.2 5.9a.5.5 0 0 0 .6 0c2.78-2.085 4.2-4.037 4.2-5.9m-6 0a1.5 1.5 0 1 1 3 0a1.5 1.5 0 0 1-3 0'/>", "0 0 24 24", 64),  # fluent globe-location

    "radial":    _svg("<path fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M10 19a2 2 0 1 0-4 0a2 2 0 0 0 4 0m8-14a2 2 0 1 0-4 0a2 2 0 0 0 4 0m-8 0a2 2 0 1 0-4 0a2 2 0 0 0 4 0m-4 7a2 2 0 1 0-4 0a2 2 0 0 0 4 0m12 7a2 2 0 1 0-4 0a2 2 0 0 0 4 0m-4-7a2 2 0 1 0-4 0a2 2 0 0 0 4 0m8 0a2 2 0 1 0-4 0a2 2 0 0 0 4 0M6 12h4m4 0h4m-3-5l-2 3M9 7l2 3m0 4l-2 3m4-3l2 3'/>", 64),  # tabler topology-star-3
    "org":       _svg("<rect x='16' y='16' width='6' height='6' rx='1'/><rect x='2' y='16' width='6' height='6' rx='1'/>"
                      "<rect x='9' y='2' width='6' height='6' rx='1'/><path d='M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3'/>"
                      "<path d='M12 12V8'/>", 64),  # lucide network
    "messaging": _fill("<path fill='currentColor' d='M21 7.511a3.25 3.25 0 0 1 1.5 2.739v6c0 2.9-2.35 5.25-5.25 5.25h-9A3.25 3.25 0 0 1 5.511 20H17.25A3.75 3.75 0 0 0 21 16.25zm-1 .599v7.64a3.25 3.25 0 0 1-3.066 3.245L16.75 19H5.25a3.25 3.25 0 0 1-3.245-3.066L2 15.75V8.11l8.65 4.554a.75.75 0 0 0 .7 0zM5.25 4h11.5a3.25 3.25 0 0 1 3.155 2.466L11 11.153L2.095 6.466a3.25 3.25 0 0 1 2.966-2.46z'/>", "0 0 24 24", 64),  # fluent mail-multiple
    "agentic":   _svg("<path d='M12 8V4H8'/><rect width='16' height='12' x='4' y='8' rx='2'/><path d='M2 14h2m16 0h2m-7-1v2m-6-2v2'/>", 64),  # lucide bot
    "blank":     _svg("<rect width='18' height='18' x='3' y='3' rx='2'/>", 64),  # lucide square
}


def _recent_entries(recent: list[str]) -> list[dict]:
    entries = []
    for path in recent:
        is_pack = path.lower().endswith(".hydra")
        entries.append({"path": path, "label": Path(path).stem if is_pack else Path(path).name,
                        "available": Path(path).is_file() if is_pack else Path(path).is_dir()})
    return entries


def _view_cards() -> list[dict]:
    return [{"key": key, "label": v["label"], "flow": bool(v.get("flow")), "checked": key == "wiki",
             "icon": Markup(VIEW_ICON[key])} for key, v in desktop_new.VIEWS.items()]


def _theme_cards() -> list[dict]:
    return [{"name": name, "checked": name == site.DEFAULT_THEME,
             "dots": [t["bg"], t["head"], t["link"], t["warnline"]]} for name, t in site.THEMES.items()]


def render_home(recent: list[str], current: Path | None, token: str, start: str = "/", auto_open: str | None = None,
                look: dict | None = None) -> str:
    look = look or desktop_look.DEFAULT
    icons = {"file_plus": FILE_PLUS, "file": FILE_ICON, "folder": FOLDER, "folder_open": FOLDER_OPEN}
    return PAGES.render(
        "home.html", look=look, icons={k: Markup(v) for k, v in icons.items()},
        css=PAGES.raw("home.css"), js=PAGES.raw("home.js"),
        look_css=Markup(desktop_look.css(look)),      # values are vetted by desktop_look.clean (no quotes of markup)
        current=(current.stem if current.is_file() else current.name) if current else "", start=start,
        recents=_recent_entries(recent), views=_view_cards(), themes=_theme_cards(),
        boot={"token": token, "auto_open": auto_open or ""})
