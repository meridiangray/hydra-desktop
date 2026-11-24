# hydra-desktop

Hydra's desktop app: a [Saucer](https://github.com/saucer/saucer) window over a Hydra archive's wiki. The welcome screen opens `.hydra` packs or archive folders, remembers recently opened paths and starts new projects; the window bar adds Archives, Save and the Profile page. It builds on [hydra](https://github.com/meridiangray/open-hydra) (`open-hydra`), which sits beside it as `hydra-git/`.

Packs are read-only: missing builds are made in a temporary copy, without changing the `.hydra` file. A stale archive folder opens on its last build and is rebuilt behind the reader.

## Install and run

```
pip install -e ../hydra-git -e .
hydra-desktop                 # the welcome screen
hydra-desktop PATH            # an archive folder or .hydra pack
```

`python -m hydra_desktop` runs the same. `--theme NAME` picks a wiki theme, `--build` rebuilds a stale archive before opening, `--shell PATH` (or `HYDRA_DESKTOP_SHELL`) names a shell built elsewhere.

## Build the window shell

The shell is C++ (`shell/`). From this folder:

```
cmake -S shell -B shell/build
cmake --build shell/build --config Release
```

`hydra-desktop` looks for it at `shell/build/Release/hydra-desktop-shell.exe` (or `shell/build/hydra-desktop-shell`). The build reads hydra's window bar (`wiki/assets/windowbar.js`) from the CMake cache variable `HYDRA_SRC`, by default `../hydra-git/src/hydra` beside this project; pass `-DHYDRA_SRC=PATH/src/hydra` when hydra is elsewhere.

`scripts/bundle_desktop.py` (Windows) makes a portable `dist/Hydra/`: the shell as `Hydra.exe` and an embedded Python with hydra, hydra_desktop and hydra-mcp, taken from beside this project.

## Tests

```
python -m pytest tests
```

hydra must be importable (installed, or `hydra-git/src` on the path).
