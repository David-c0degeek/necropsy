"""Shared, built-once analysis databases for tests."""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache
from pathlib import Path

import duckdb

from necropsy.normalize.ingest import ingest
from necropsy.snapshot.archive import load_entries_manifest
from tests.fixture_paths import (
    provenance,
    raw_entries_path,
    raw_export_path,
    subset_entries_path,
    subset_path,
)

_WORKDIR = Path(tempfile.mkdtemp(prefix="necropsy-test-db-"))


@cache
def subset_db() -> Path:
    db = _WORKDIR / "subset.duckdb"
    ingest(
        subset_path(),
        db,
        expected_sha256=provenance()["subset"]["sha256"],
        entries=load_entries_manifest(subset_entries_path()),
    )
    return db


@cache
def full_db() -> Path:
    db = _WORKDIR / "full.duckdb"
    ingest(
        raw_export_path(),
        db,
        expected_sha256=provenance()["rawExport"]["sha256"],
        entries=load_entries_manifest(raw_entries_path()),
    )
    return db


@contextmanager
def connect(db: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    con = duckdb.connect(str(db), read_only=True)
    try:
        yield con
    finally:
        con.close()
