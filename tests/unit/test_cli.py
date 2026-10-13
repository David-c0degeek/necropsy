import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from necropsy import __version__
from necropsy.cli import app
from tests.fixture_paths import subset_path


def test_version_option() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"necropsy {__version__}"


def test_help_lists_program() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Local-first Warcraft Logs forensics" in result.output


def test_module_entry_point_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "necropsy", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip() == f"necropsy {__version__}"


def test_offline_reports_a_missing_snapshot(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app, ["offline", str(tmp_path / "missing.zip"), "--out", str(tmp_path / "out")]
    )
    assert result.exit_code == 1
    assert "offline analysis failed" in result.output
    assert not (tmp_path / "out").exists()


def test_offline_refuses_a_wrong_checksum(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["offline", str(subset_path()), "--out", str(tmp_path / "out"), "--sha256", "0" * 64],
    )
    assert result.exit_code == 1
    assert not (tmp_path / "out").exists()


def _subset_analysis(tmp_path: Path) -> dict[str, Any]:
    out = tmp_path / "first"
    result = CliRunner().invoke(
        app, ["offline", str(subset_path()), "--out", str(out), "--no-package"]
    )
    assert result.exit_code == 0, result.output
    data: dict[str, Any] = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    return data


@pytest.mark.parametrize("damage", ["hunter", "evidence"])
def test_render_reports_malformed_analysis_cleanly(tmp_path: Path, damage: str) -> None:
    document = _subset_analysis(tmp_path)
    boss = document["bosses"][0]
    if damage == "hunter":
        boss["subject"]["hunter"] = {}
    else:
        boss["recommendations"][0]["evidence"] = ["subject.no_such_field"]
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(document), encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "report.html").write_text("previous", encoding="utf-8")
    result = CliRunner().invoke(app, ["render", str(broken), "--out", str(out)])
    assert result.exit_code == 1
    assert "render failed: analysis.json lacks data the report needs" in result.output
    assert "Traceback" not in result.output
    assert (out / "report.html").read_text(encoding="utf-8") == "previous"
    assert sorted(p.name for p in out.iterdir()) == ["report.html"]
