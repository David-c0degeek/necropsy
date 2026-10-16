"""Public installers remain usable when a release is assembled on Windows."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from necropsy import __version__
from scripts import build_release


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_release_installers_have_unix_line_endings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, newline: str
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    monkeypatch.setattr(build_release, "__file__", str(repository / "scripts/build_release.py"))
    scripts = {
        "install.sh": f"#!/bin/sh\nversion={__version__}\nprintf '%s\\n' ready\n",
        "install.ps1": f"$necropsyVersion = '{__version__}'\nWrite-Host 'ready'\n",
    }
    for name, content in scripts.items():
        (repository / name).write_bytes(content.replace("\n", newline).encode())
    out = tmp_path / "release"
    out.mkdir()
    for name in (f"necropsy-{__version__}-py3-none-any.whl", f"necropsy-{__version__}.tar.gz"):
        (out / name).write_bytes(b"package fixture")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    build_release.build(out)
    manifest = (out / "SHA256SUMS").read_text(encoding="utf-8")
    for name, content in scripts.items():
        actual = (out / name).read_bytes()
        assert actual == content.encode()
        assert f"{hashlib.sha256(actual).hexdigest()}  {name}\n" in manifest
