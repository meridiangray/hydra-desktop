"""Desktop pages are template files (hydra_desktop/pages, served through hydra's templating.for_package): they render,
escape user text, and carry their data in a JSON block."""
import json
import re

import pytest

from hydra import templating
from hydra_desktop import home as desktop_home, profile as desktop_profile

EVIL = "</script><script>alert(1)</script>"
PAGES = templating.for_package("hydra_desktop")


def boot(page: str) -> dict:
    m = re.search(r'<script type="application/json" id="boot">(.*?)</script>', page, re.S)
    assert m, "no JSON block"
    return json.loads(m.group(1))


@pytest.fixture(autouse=True)
def _config(tmp_path, monkeypatch):
    monkeypatch.setenv("HYDRA_CONFIG_DIR", str(tmp_path))


def test_home_renders_and_escapes(tmp_path):
    (tmp_path / "pack").mkdir()
    page = desktop_home.render_home([str(tmp_path / "pack"), str(tmp_path / ("gone" + EVIL))], tmp_path / "pack",
                                    'tok"</script>', start='/x"y', auto_open=EVIL)
    assert "<script>alert(1)" not in page and "</script><script>" not in page
    assert 'data-path="' in page and "Not found" in page and 'href="/x&#34;y"' in page
    assert boot(page) == {"token": 'tok"</script>', "auto_open": EVIL}
    assert page.count("<script>") == 1                       # the one script is the file's, never user text


def test_home_without_recents_or_current():
    page = desktop_home.render_home([], None, "t")
    assert 'class="dirs"' not in page and 'class="current"' not in page
    assert boot(page) == {"token": "t", "auto_open": ""}


def test_profile_renders_and_json_parses():
    page = desktop_profile.render(None, 'to"k</script>')
    data = boot(page)
    assert data["token"] == 'to"k</script>' and data["limits"]["name"] and "kinds" in data
    assert "TOKEN=BOOT.token" in page and "<script>alert" not in page


def test_raw_is_not_a_template_and_is_cached():
    css = PAGES.raw("home.css")
    assert "{{" not in css and css is PAGES.raw("home.css")


def test_undefined_name_is_an_error():
    with pytest.raises(Exception):
        PAGES.render("profile.html", look={"mode": "light"})
