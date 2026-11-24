"""hydra_desktop/look.py — the look of the archive last opened, kept for the Archives landing page and the Profile page.

An open wiki page reports the colours, fonts and mode it is drawn in (`LOOK_JS`, added to every page the desktop
proxies); the desktop keeps the latest at `<config>/look.json` (machine-wide, never in an archive). The landing page
and the Profile page are drawn from it, so they follow the archive's theme and the reader's Settings choices.
With nothing kept yet, `DEFAULT` is the owner's Light + Blue: hydra's built-in `light` theme (white, blue links),
light mode."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from hydra.wiki import site

KEYS = ("bg", "ink", "muted", "line", "soft", "head", "headink", "link", "visited", "red", "warn", "warnline", "panel",
        "input", "chip", "accent", "accent2", "radius", "serif", "sans")
MODES = ("light", "dark")
_BAD = re.compile(r"[{}<>;\\]|url\(|@import|expression\(", re.I)
MAX_BODY = 16384


def _theme_values(name: str) -> dict:
    return {k: str(v) for k, v in site.THEMES[name].items() if k in KEYS}


DEFAULT = {"theme": "light", "mode": "light", "vars": _theme_values("light")}


def clean(data) -> dict | None:
    """A reported look as stored, or None when it is not one (an unknown variable or an unsafe value is dropped)."""
    if not isinstance(data, dict) or data.get("mode") not in MODES:
        return None
    theme = data.get("theme")
    theme = theme if isinstance(theme, str) and len(theme) <= 100 and not _BAD.search(theme) else ""
    raw = data.get("vars") if isinstance(data.get("vars"), dict) else {}
    out = {k: v.strip() for k, v in raw.items() if k in KEYS and isinstance(v, str) and 0 < len(v.strip()) <= 400
           and not _BAD.search(v)}
    if not out.get("bg") or not out.get("ink"):
        return None
    return {"theme": theme, "mode": data["mode"], "vars": out}


def path(settings) -> Path:
    return Path(settings).parent / "look.json" if settings else Path(os.environ.get("HYDRA_CONFIG_DIR") or ".") / "look.json"


def load(settings) -> dict:
    try:
        got = clean(json.loads(path(settings).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        got = None
    return got or DEFAULT


def save(settings, data) -> bool:
    """Keep a reported look; True when it changed what was kept."""
    got = clean(data)
    if not got:
        raise ValueError("not a look")
    if got == load(settings) and path(settings).is_file():
        return False
    f = path(settings)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(got, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, f)
    return True


_SHADE = {
    "light": "--hi:inset 0 1px 0 rgba(255,255,255,.75);--card-shadow:0 1px 2px rgba(34,32,29,.045),0 12px 30px -14px rgba(52,32,18,.1);"
             "--ctl-shadow:0 1px 2px rgba(34,32,29,.05),var(--hi);--ring-sw:inset 0 0 0 1px rgba(34,32,29,.16);",
    "dark": "--hi:inset 0 1px 0 rgba(255,255,255,.05);--card-shadow:0 1px 2px rgba(0,0,0,.38),0 14px 32px -12px rgba(0,0,0,.54);"
            "--ctl-shadow:0 1px 2px rgba(0,0,0,.26),var(--hi);--ring-sw:inset 0 0 0 1px rgba(255,255,255,.2);"}


def css(look: dict) -> str:
    """The look as a stylesheet over the page's own tokens (--paper, --ink, --quiet, --line, --accent, --panel, --danger,
    --serif, --sans, --radius); the page keeps its layout, only colours and type follow."""
    v = look["vars"]
    own = "".join(f"--{k}:{x};" for k, x in v.items())
    maps = "--paper:var(--bg);--glow:transparent;" + "".join(
        f"--{to}:var(--{src});" for to, src in (("quiet", "muted"), ("accent", "link"), ("danger", "red")) if src in v)
    return f":root:root:root{{{own}{maps}{_SHADE[look['mode']]}color-scheme:{look['mode']}}}"


LOOK_JS = r"""(()=>{
if(location.pathname.indexOf('/_desktop/')===0||window.__hydraLook)return;window.__hydraLook=1;
const KEYS=%KEYS%,r=document.documentElement;let timer=0,last='';
function read(){const cs=getComputedStyle(r),vars={};
 KEYS.forEach(k=>{const x=cs.getPropertyValue('--'+k).trim();if(x)vars[k]=x});
 const m=r.getAttribute('data-mode')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
 return {theme:r.getAttribute('data-theme')||'',mode:m,vars}}
function send(){timer=0;const l=read(),s=JSON.stringify(l);if(s===last||!l.vars.bg)return;last=s;
 try{fetch('/_desktop/look',{method:'POST',keepalive:true,headers:{'Content-Type':'application/json','X-Hydra-Look':'1'},body:s}).catch(()=>{})}catch(e){}}
function later(){if(!timer)timer=setTimeout(send,350)}
new MutationObserver(later).observe(r,{attributes:true,attributeFilter:['data-mode','data-theme']});
new MutationObserver(later).observe(document.head,{childList:true,subtree:true,attributes:true,attributeFilter:['href']});
document.addEventListener('load',later,true);
addEventListener('pageshow',later);addEventListener('load',later);matchMedia('(prefers-color-scheme: dark)').addEventListener('change',later);later();
})();
""".replace("%KEYS%", json.dumps(list(KEYS)))

INJECT = '<script src="/_desktop/look.js"></script>'
