"""Verify the missing-runtime branch without changing the real Windows runtime."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell bootstrap helpers")
@pytest.mark.parametrize(
    "installed,trusted,expected", [(True, True, 0), (False, True, 0), (False, False, 1)]
)
def test_runtime_is_reused_or_installed_only_from_a_trusted_download(
    tmp_path: Path,
    installed: bool,
    trusted: bool,
    expected: int,
) -> None:
    source = (ROOT / "install.ps1").read_text(encoding="utf-8")
    helpers = []
    for name in ("Test-WebView2", "Ensure-WebView2"):
        match = re.search(r"function " + re.escape(name) + r" .*?\n}\n", source, re.DOTALL)
        assert match is not None
        helpers.append(match[0])
    script = tmp_path / "runtime-check.ps1"
    script.write_text(
        "\n".join(helpers)
        + """
$ErrorActionPreference = 'Stop'
$global:runtimePresent = $env:TEST_INSTALLED -eq '1'
$global:downloaded = $false
$global:started = $false
function Get-ItemProperty {
    param($LiteralPath, $Name, $ErrorAction)
    if ($global:runtimePresent) { return [pscustomobject]@{pv='150.0.0.0'} }
}
function Invoke-WebRequest {
    param($OutFile, [switch]$UseBasicParsing, $Uri)
    $global:downloaded = $true
}
function Get-AuthenticodeSignature {
    param($LiteralPath)
    $status = if ($env:TEST_TRUSTED -eq '1') { 'Valid' } else { 'NotSigned' }
    $certificate = [pscustomobject]@{Subject='CN=Microsoft, O=Microsoft Corporation, C=US'}
    return [pscustomobject]@{Status=$status;SignerCertificate=$certificate}
}
function Start-Process {
    param($FilePath, $ArgumentList, [switch]$Wait, [switch]$PassThru, $WindowStyle)
    $global:started = $true
    $global:runtimePresent = $true
    return [pscustomobject]@{ExitCode=0}
}
try {
    Ensure-WebView2 $env:TEST_DIRECTORY
    if ($env:TEST_INSTALLED -eq '1' -and ($global:downloaded -or $global:started)) { exit 2 }
    if ($env:TEST_INSTALLED -ne '1' -and -not $global:started) { exit 3 }
} catch {
    if ($global:started) { exit 4 }
    Write-Output $_.Exception.Message
    exit 1
}
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-File", str(script)],
        env={
            **os.environ,
            "TEST_INSTALLED": str(int(installed)),
            "TEST_TRUSTED": str(int(trusted)),
            "TEST_DIRECTORY": str(tmp_path),
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    if expected:
        assert "not trusted" in result.stdout
