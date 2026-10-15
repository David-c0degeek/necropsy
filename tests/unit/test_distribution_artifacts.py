"""Distribution checks reject private payloads and unsafe archive paths before scanning."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts.check_distribution import audit


@pytest.mark.parametrize(
    "name",
    [
        "../credentials",
        "/absolute",
        "necropsy/../../outside",
        "necropsy\\..\\..\\outside",
        "C:/credentials",
        "workspace/cache.json",
        "tests/raw.zip",
        "necropsy/private.duckdb",
        "necropsy/export.zip",
    ],
)
def test_unexpected_artifact_members_are_refused(tmp_path: Path, name: str) -> None:
    wheel = tmp_path / "sample.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(name, b"private data")
    with pytest.raises(ValueError):
        audit(wheel, tmp_path / "extracted")


def test_developer_paths_are_refused(tmp_path: Path) -> None:
    wheel = tmp_path / "sample.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("necropsy/example.txt", b"C:/repos/private/export.json")
    with pytest.raises(ValueError, match="developer-local"):
        audit(wheel, tmp_path / "extracted")


def test_unavailable_scanner_cannot_pass_artifact_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wheel = tmp_path / "sample.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("necropsy/__init__.py", b"")
    monkeypatch.setattr(
        "scripts.check_distribution.secret_scan", lambda path: {"status": "unavailable"}
    )
    with pytest.raises(RuntimeError, match="unavailable"):
        audit(wheel, tmp_path / "extracted")
