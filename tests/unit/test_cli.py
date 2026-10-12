import subprocess
import sys

from typer.testing import CliRunner

from necropsy import __version__
from necropsy.cli import app


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
