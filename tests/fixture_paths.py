"""Locations and provenance of the frozen Haplina fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TESTS = Path(__file__).resolve().parent
GOLDEN = TESTS / "golden" / "haplina_naxx"
PROVENANCE_PATH = GOLDEN / "provenance.json"
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"


def provenance() -> dict[str, Any]:
    data = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def golden_path(relative: str) -> Path:
    return (GOLDEN / relative).resolve()


def raw_export_path() -> Path:
    return golden_path(provenance()["rawExport"]["path"])


def raw_entries_path() -> Path:
    return golden_path(provenance()["rawExport"]["entriesManifest"]["path"])


def subset_path() -> Path:
    return golden_path(provenance()["subset"]["path"])


def subset_entries_path() -> Path:
    return golden_path(provenance()["subset"]["entriesManifest"]["path"])


def is_lfs_pointer(path: Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(len(LFS_POINTER_PREFIX)) == LFS_POINTER_PREFIX
