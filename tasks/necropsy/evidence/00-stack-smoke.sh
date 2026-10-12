set -u
run(){ echo "\$ $*"; "$@"; echo "exit=$?"; }
run uv --version
run uv init --package --python 3.14 smoke -q
cd smoke
run uv add -q duckdb==1.5.6 pydantic==2.14.1 typer==0.27.3 jinja2==3.1.6 httpx==0.28.1 keyring==25.7.0 pyyaml==6.0.3
run uv add -q --dev pytest==9.1.1 ruff==0.17.0 mypy==2.4.0 respx==0.23.1 types-PyYAML
cat >> pyproject.toml <<'TOML'

[tool.mypy]
strict = true

[tool.pytest.ini_options]
addopts = "--strict-markers"
markers = ["golden: full fixture", "live: live WCL"]
TOML
mkdir -p tests
cat > src/smoke/probe.py <<'PY'
import sys

import duckdb
import httpx
import jinja2
import keyring
import pydantic
import typer
import yaml


def versions() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "duckdb": duckdb.__version__,
        "pydantic": pydantic.VERSION,
        "typer": typer.__version__,
        "jinja2": jinja2.__version__,
        "httpx": httpx.__version__,
        "yaml": yaml.__version__,
        "keyring_backend": type(keyring.get_keyring()).__name__,
    }


def read_events(path: str) -> int:
    con = duckdb.connect()
    row = con.sql(
        "select len(data) from read_json(?, columns={'data': 'JSON[]', 'nextPageTimestamp': 'DOUBLE'})",
        params=[path],
    ).fetchone()
    assert row is not None
    return int(row[0])
PY
cat > tests/test_probe.py <<'PY'
import os

import pytest

from smoke.probe import read_events, versions

PAGE = r"D:/repos/wcl_access_test/exports/wcl_hunter_deep_export_20261012_145328/events/13tcpDvzm4TqJ9AC/fight_1/player_18_Ixtlan/source_001.json"


def test_versions() -> None:
    v = versions()
    print(v)
    assert v["python"].startswith("3.14")


@pytest.mark.skipif(not os.path.exists(PAGE), reason="raw export not present")
def test_read_real_event_page() -> None:
    assert read_events(PAGE) == 245


@pytest.mark.golden
def test_marker_registered() -> None:
    assert True
PY
run uv run pytest -q -s
run uv run ruff check .
run uv run ruff format --check .
run uv run mypy src tests
run uv build -q
echo "uv.lock sha256: $(sha256sum uv.lock | cut -c1-64)"
echo "--- pyproject.toml"; cat pyproject.toml
