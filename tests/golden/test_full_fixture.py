"""Checks over the full raw export. Needs the Git LFS object (uv run pytest -m golden)."""

from __future__ import annotations

import zlib
from pathlib import Path

import pytest

from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest
from scripts.fixture_tools import build_subset
from tests.fixture_paths import (
    is_lfs_pointer,
    provenance,
    raw_entries_path,
    raw_export_path,
    subset_entries_path,
    subset_path,
)

pytestmark = pytest.mark.golden


@pytest.fixture(scope="module")
def raw_export() -> Path:
    path = raw_export_path()
    if not path.is_file():
        pytest.fail(f"full fixture missing: {path}. Run `git lfs pull` first.")
    if is_lfs_pointer(path):
        pytest.fail(f"{path.name} is a Git LFS pointer, not the archive. Run `git lfs pull` first.")
    return path


def test_full_export_matches_provenance_and_every_member_digest(raw_export: Path) -> None:
    prov = provenance()["rawExport"]
    entries = load_entries_manifest(raw_entries_path())
    with VerifiedArchive(raw_export, expected_sha256=prov["sha256"], entries=entries) as archive:
        assert len(archive.names()) == prov["entriesManifest"]["members"]
        for name in archive.names():
            archive.read_bytes(name)
        manifest = archive.read_json("manifest.json")
        assert manifest["clientSecretIncludedInExport"] is False
        assert manifest["userAccessTokenIncludedInExport"] is False
        assert manifest["errors"] == []
        assert manifest["selectedFightCount"] == 89


def test_subset_regenerates_identically(raw_export: Path, tmp_path: Path) -> None:
    out_zip = tmp_path / "subset.zip"
    out_entries = tmp_path / "subset.sha256"
    build_subset(raw_export, raw_entries_path(), out_zip, out_entries)
    assert out_entries.read_bytes() == subset_entries_path().read_bytes()
    recorded_zlib = provenance()["subset"]["zlibRuntimeVersion"]
    if recorded_zlib != zlib.ZLIB_RUNTIME_VERSION:
        pytest.skip(f"zip bytes depend on zlib ({zlib.ZLIB_RUNTIME_VERSION} != {recorded_zlib})")
    assert out_zip.read_bytes() == subset_path().read_bytes()
