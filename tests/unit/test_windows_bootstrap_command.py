"""The pasted Windows setup command downloads one complete script and uses -File."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.check_bootstrap import documented_command, downloaded_setup

REPOSITORY = Path(__file__).resolve().parents[2]


def test_windows_install_guides_share_saved_file_command() -> None:
    documented_command(REPOSITORY)


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell entry point")
@pytest.mark.parametrize("host", ["powershell.exe", "pwsh.exe"])
@pytest.mark.parametrize("download_ok", [True, False])
def test_pasted_command_downloads_before_execution(
    tmp_path: Path, host: str, download_ok: bool
) -> None:
    executable = shutil.which(host)
    if executable is None:
        pytest.skip(f"{host} unavailable")
    download = tmp_path / "download folder with spaces"
    download.mkdir()
    result_file = tmp_path / "result.txt"
    script = (
        b"[CmdletBinding()]\nparam()\n"
        b"[IO.File]::WriteAllText($env:NECROPSY_TEST_RESULT, 'complete script ran')\n"
    )
    env = dict(os.environ, TEMP=str(download), NECROPSY_TEST_RESULT=str(result_file))
    with downloaded_setup(REPOSITORY, script) as command:
        if not download_ok:
            command = command.replace("/install.ps1", "/missing.ps1")
        result = subprocess.run(
            [executable, "-NoProfile", "-Command", command],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
    if download_ok:
        assert result.returncode == 0, result.stdout + result.stderr
        assert result_file.read_text(encoding="utf-8") == "complete script ran"
        saved = list(download.glob("necropsy-setup-*.ps1"))
        assert len(saved) == 1
        assert saved[0].read_bytes() == script
    else:
        assert result.returncode != 0
        assert not result_file.exists()
