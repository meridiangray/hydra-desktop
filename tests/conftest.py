"""hydra-desktop's test setup, as hydra's own suite sets it (hydra-git/tests/conftest.py), which these tests came from.

Every test process gets its own empty machine folders (config, geo register): a test must never read or write the
person's real `%APPDATA%/Hydra` or register store. Archives are built with hydra's suite policy `same_name: merge`.
`dynasty(tmp_path)` is the small archive the desktop tests open (a copy of hydra-git/tests/test_wiki.py's)."""
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from hydra.cli import init as hinit
from hydra.identity import classify
from hydra.universe import build

os.environ.setdefault("HYDRA_NO_WARM", "1")      # the live wiki's warm-up requests stay out of tests


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: a heavy test (8 s or more); skip in targeted runs with -m 'not slow'")
    machine = tempfile.mkdtemp(prefix="hydra-test-machine-")
    for var, sub in (("HYDRA_CONFIG_DIR", "config"), ("HYDRA_REGISTER_DIR", "register")):
        os.environ[var] = os.path.join(machine, sub)
    classify.DEFAULT_SAME_NAME = "merge"


def pytest_collection_modifyitems(config, items):
    """The desktop tests race each other under xdist: keep them on one worker (`--dist loadgroup`); they are slow."""
    for item in items:
        if item.path.name == "test_desktop.py":
            item.add_marker(pytest.mark.xdist_group("desktop"))
            item.add_marker(pytest.mark.slow)


_TEMPLATES: dict = {}


def built_copy(key, make, dest):
    """An archive built once per test process by `make(root)`, copied to `dest` for each test that asks."""
    if key not in _TEMPLATES:
        _TEMPLATES[key] = Path(make(Path(tempfile.mkdtemp(prefix="hydra-tpl-")) / Path(dest).name))
    shutil.copytree(_TEMPLATES[key], dest)
    return Path(dest)


P = lambda i, s, **p: {"id": i, "schema": s, "properties": {k: v if isinstance(v, list) else [v] for k, v in p.items()}}


def dynasty(tmp_path):
    """The dynasty archive at tmp_path/dyn: built once per process, copied for each caller."""
    return built_copy("dynasty", _make_dynasty, tmp_path / "dyn")


def _make_dynasty(root):
    root = hinit.create(root, name="dyn", prefix="dyn")
    recs = [
        P("k", "Person", name="Old King", gender="male", nationality="sa", birthDate="1900", deathDate="1960",
          notes="House: Testa\nSource: https://en.wikipedia.org/wiki/Old_King"),
        P("q", "Person", name="The Queen", gender="female"),
        P("a", "Person", name="Amir One", gender="male", birthDate="1925", deathDate="1990"),
        P("b", "Person", name="Amira Two", gender="female", birthDate="1930"),
        P("m", "PublicBody", name="Ministry of Tests", country="sa"),
        P("pos", "Position", name="Minister of Tests", organization="Ministry of Tests"),
        P("o1", "Occupancy", holder="Old King", post="Minister of Tests", startDate="1940", endDate="1950",
          notes="Recorded as: Minister of Tests 1940–50"),
        P("o2", "Occupancy", holder="Amir One", post="Minister of Tests", startDate="1950", endDate="1951"),
        P("f1", "Family", person="Amir One", relative="Old King", relationship="father"),
        P("f2", "Family", person="Amira Two", relative="Old King", relationship="father"),
        P("f3", "Family", person="Amir One", relative="The Queen", relationship="mother",
          publisherUrl="https://en.wikipedia.org/wiki/Amir_One"),
        P("f4", "Family", person="Amira Two", relative="Nobody Recorded", relationship="mother"),
    ]
    (root / "collections" / "dyn.json").write_text(json.dumps(recs), encoding="utf-8")
    build.build(root)
    return root
