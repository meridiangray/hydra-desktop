"""Generate the Windows icon: the tome (game-icons.net spell-book, by Delapouite, CC BY 3.0) in near-white on the blue tile
with a pale-blue border (teal until 2026-11-20; hydra-teal.ico keeps it), the mark the window bar shows (owner, 2026-11-20). Each size is drawn by headless Edge at that size,
so small sizes are rasterised for themselves, then packed as PNG entries into hydra.ico.

    python shell/make_icon.py [path-to-msedge.exe]        (from hydra-desktop/)
"""
from __future__ import annotations

import re
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOME = HERE.parents[1] / "hydra-git/src/hydra/template/.hydra/resources/icons/game-spell-book.svg"   # hydra, beside hydra-desktop
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def svg() -> str:
    d = re.search(r'<path[^>]*\sd="([^"]+)"', TOME.read_text(encoding="utf-8")).group(1)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
            '<rect x="20" y="20" width="472" height="472" rx="104" fill="#1d4f9e" stroke="#a9c3ea" stroke-width="28"/>'
            f'<g transform="translate(104 104) scale(.59375)" fill="#f4f7fd"><path d="{d}"/></g></svg>')


def png(size: int, edge: str, work: Path) -> bytes:
    page = work / f"i{size}.html"
    out = work / f"i{size}.png"
    page.write_text(f"<!doctype html><html><body style='margin:0;background:transparent'>"
                    f"<div style='width:{size}px;height:{size}px'>{svg().replace('<svg ', f'<svg width=\"{size}\" height=\"{size}\" ')}</div></body></html>",
                    encoding="utf-8")
    subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
                    f"--user-data-dir={work / 'profile'}", f"--window-size={size},{size}", f"--screenshot={out}", page.as_uri()],
                   check=True, capture_output=True, timeout=60)
    for _ in range(200):                     # msedge.exe hands off and returns; the screenshot lands a moment later
        if out.is_file() and out.stat().st_size:
            time.sleep(.2)
            return out.read_bytes()
        time.sleep(.1)
    raise SystemExit(f"Edge drew no {out.name}")


def main() -> None:
    edge = sys.argv[1] if len(sys.argv) > 1 else EDGE
    with tempfile.TemporaryDirectory() as tmp:
        images = [png(size, edge, Path(tmp)) for size in SIZES]
    offset = 6 + len(SIZES) * 16
    entries = []
    for size, image in zip(SIZES, images):
        entries.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(image), offset))
        offset += len(image)
    output = HERE / "hydra.ico"
    output.write_bytes(struct.pack("<HHH", 0, 1, len(SIZES)) + b"".join(entries) + b"".join(images))
    print(f"{output} ({', '.join(map(str, SIZES))})")


if __name__ == "__main__":
    main()
