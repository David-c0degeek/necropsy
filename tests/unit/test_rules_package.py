"""Rule files ship inside the wheel and load from an installed package."""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from necropsy.rules import RuleError, load_rules

REPO = Path(__file__).resolve().parents[2]
PROBE = (
    "import necropsy.rules as r, sys; "
    "assert 'site-packages' in r.__file__, r.__file__; "
    "assert r.load_rules('classic_era', 'druid')['minimum_role_actions'] == 3; "
    "from necropsy.analysis.classes import plugin_for; "
    "assert plugin_for('classic_era', 2).name == 'Druid'; "
    "print(r.load_rules('classic_era', 'racials')['racials'][0]['race'])"
)


def test_rules_load_from_package() -> None:
    assert load_rules("classic_era", "externals")["factions"][1] == "Alliance"
    with pytest.raises(RuleError):
        load_rules("classic_era", "missing")


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not available")
def test_rules_load_from_an_installed_wheel(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist)],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    wheel = next(dist.glob("necropsy-*.whl"))
    with zipfile.ZipFile(wheel) as zf:
        assert "necropsy/rules/classic_era/racials.yaml" in zf.namelist()
        assert "necropsy/rules/classic_era/druid.yaml" in zf.namelist()
        assert "necropsy/report/render/templates/class-report.html.j2" in zf.namelist()
    venv = tmp_path / "venv"
    subprocess.run(
        ["uv", "venv", str(venv), "--python", sys.executable], check=True, capture_output=True
    )
    python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    subprocess.run(
        ["uv", "pip", "install", "--python", str(python), str(wheel)],
        check=True,
        capture_output=True,
    )
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    env = {k: v for k, v in __import__("os").environ.items() if k != "PYTHONPATH"}
    result = subprocess.run(
        [str(python), "-c", PROBE], cwd=outside, check=True, capture_output=True, text=True, env=env
    )
    assert result.stdout.strip() == "Orc"
