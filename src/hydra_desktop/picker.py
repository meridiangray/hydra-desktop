"""Run the OS picker on its own UI main thread, not in an HTTP handler."""
from __future__ import annotations

import sys
import tkinter
from tkinter import filedialog


def pick(kind: str) -> str:
    window = tkinter.Tk()
    window.withdraw()
    window.attributes("-topmost", True)
    try:
        if kind == "file":
            return filedialog.askopenfilename(parent=window, title="Open a Hydra pack",
                                              filetypes=[("Hydra archives", "*.hydra")])
        if kind == "folder":
            return filedialog.askdirectory(parent=window, title="Open a Hydra archive", mustexist=True)
        if kind == "newfolder":
            return filedialog.askdirectory(parent=window, title="Choose a folder for the new project",
                                           mustexist=False)
        if kind == "documents":
            return "\n".join(filedialog.askopenfilenames(parent=window,
                                                         title="Choose source documents"))
        raise ValueError("Choose a file, a folder or documents")
    finally:
        window.destroy()


if __name__ == "__main__":
    print(pick(sys.argv[1]), end="")
