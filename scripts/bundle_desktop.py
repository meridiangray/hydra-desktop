"""bundle_desktop.py [--shell EXE] [--out DIR] [--no-clean]

Makes the portable desktop folder (Windows): dist/Hydra/ in hydra-desktop
    Hydra.exe          the Saucer shell (shell/main.cpp), renamed
    python/            the official embeddable CPython, with hydra, hydra_desktop and hydra-mcp (and their wheels)
                       installed in it
Started with no arguments, Hydra.exe starts python\\python.exe -m hydra_desktop --serve itself (hidden) and shows the
welcome screen. `python\\python.exe -m hydra_mcp` is the MCP server from the same runtime.

hydra (hydra-git) and hydra-mcp are taken from beside this project. The shell is not built here: build it first
(cmake -S shell -B shell/build-X; cmake --build ... --config Release) and pass --shell, or let this find
shell/build-s1 / shell/build.
"""
import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

PYTHON = "3.13.14"
PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON}/python-{PYTHON}-embed-amd64.zip"
PYTHON_SHA256 = "90b4e5b9898b72d744650524bff92377c367f44bd5fbd09e3148656c080ad907"

ROOT = Path(__file__).resolve().parents[1]                  # hydra-desktop
HYDRA = ROOT.parent / "hydra-git"                           # open-hydra, which hydra-desktop and hydra-mcp depend on
MCP = ROOT.parent / "hydra-mcp"


def find_shell(given):
    if given:
        return Path(given).resolve()
    for build in ("build-s1", "build"):
        exe = ROOT / "shell" / build / "Release" / "hydra-desktop-shell.exe"
        if exe.is_file():
            return exe
    sys.exit("bundle: build the shell first (see the top of this file) and pass --shell")


def download(dest: Path):
    if not dest.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"bundle: downloading {PYTHON_URL}")
        with urllib.request.urlopen(PYTHON_URL, timeout=120) as response:
            dest.write_bytes(response.read())
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    if digest != PYTHON_SHA256:
        dest.unlink()
        sys.exit(f"bundle: {dest.name} has sha256 {digest}, expected {PYTHON_SHA256}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shell")
    ap.add_argument("--out", default=str(ROOT / "dist" / "Hydra"))
    ap.add_argument("--no-clean", action="store_true", help="keep an existing output folder and reinstall into it")
    a = ap.parse_args()
    if sys.platform != "win32":
        sys.exit("bundle: Windows only for now")
    if sys.version_info[:2] != (3, 13):
        sys.exit("bundle: run this with CPython 3.13, so the wheels pip picks match the embedded runtime")
    shell, out = find_shell(a.shell), Path(a.out).resolve()
    if out.exists() and not a.no_clean:
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    archive = ROOT / "dist" / ".cache" / Path(PYTHON_URL).name
    download(archive)
    runtime = out / "python"
    with zipfile.ZipFile(archive) as z:
        z.extractall(runtime)
    pth = next(runtime.glob("python*._pth"))                  # let the runtime see site-packages and run its .pth files
    text = re.sub(r"^#\s*import site", "import site", pth.read_text(), flags=re.M)
    if "site-packages" not in text:
        text = re.sub(r"^\.[ \t\r]*$", ".\nLib/site-packages", text, count=1, flags=re.M)
    pth.write_text(text)
    site = runtime / "Lib" / "site-packages"
    site.mkdir(parents=True, exist_ok=True)

    if not (HYDRA / "pyproject.toml").is_file():
        sys.exit(f"bundle: hydra not found at {HYDRA} (hydra-git beside hydra-desktop)")
    targets = [str(HYDRA), str(ROOT)] + ([str(MCP)] if MCP.is_dir() else [])     # pip takes open-hydra from HYDRA
    subprocess.run([sys.executable, "-m", "pip", "install", "--target", str(site), "--upgrade",
                    "--only-binary", "pydantic-core", "--no-warn-script-location", *targets],
                   check=True)
    for scripts in (site / "bin", site / "Scripts"):          # console-script launchers do not belong in the bundle
        shutil.rmtree(scripts, ignore_errors=True)

    shutil.copy2(shell, out / "Hydra.exe")
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"bundle: {out} ({size / 2**20:.0f} MiB). Run {out / 'Hydra.exe'}")


if __name__ == "__main__":
    main()
