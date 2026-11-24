"""The window bar's extras (hydra_desktop/chrome.js) beside hydra's mini rail (hydra-git tests/test_minirail.py): the
bar has no rail button of its own; its profile circle is where the embedded rail stands."""
from hydra_desktop import app as desktop


def test_the_window_bar_has_no_rail_of_its_own():
    chrome = desktop.CHROME_EXT.read_text(encoding="utf-8")
    assert "window-rail" not in chrome and "window-archives" in chrome and ".window-profile[data-rail]" in chrome
