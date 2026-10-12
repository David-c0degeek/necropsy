"""Ingest of the full raw export (uv run pytest -m golden)."""

from __future__ import annotations

import time
from pathlib import Path

import duckdb
import pytest

from necropsy.normalize.ingest import ingest
from necropsy.snapshot.archive import load_entries_manifest
from tests.fixture_paths import is_lfs_pointer, provenance, raw_entries_path, raw_export_path
from tests.independent_count import merged_event_count

pytestmark = pytest.mark.golden

# Independently profiled from the raw export (canonical-JSON identity, maximum
# multiplicity per fight); the profiling script and output are kept with the
# development notes.
EXPECTED_EVENTS = 863_536
EXPECTED_STREAM_EVENTS = 3_674_640


def test_full_export_ingest(tmp_path: Path) -> None:
    raw = raw_export_path()
    if not raw.is_file() or is_lfs_pointer(raw):
        pytest.fail(f"{raw.name} is missing or an LFS pointer. Run `git lfs pull` first.")
    started = time.perf_counter()
    summary = ingest(
        raw,
        tmp_path / "full.duckdb",
        expected_sha256=provenance()["rawExport"]["sha256"],
        entries=load_entries_manifest(raw_entries_path()),
    )
    elapsed = time.perf_counter() - started
    print(f"full ingest: {elapsed:.1f} s")
    assert summary.scope == "full"
    assert summary.fights == 89
    assert summary.streams == 762
    assert summary.incomplete_streams == 0
    assert summary.anomalies == 0
    assert summary.issues == 0
    assert summary.stream_events == EXPECTED_STREAM_EVENTS
    assert summary.events == EXPECTED_EVENTS
    con = duckdb.connect(str(summary.database), read_only=True)
    try:
        row = con.execute(
            "SELECT count(*) FROM stream_coverage WHERE status = 'complete' "
            "AND boundary_ambiguities = 0 AND multiplicity_mismatches = 0"
        ).fetchone()
        assert row == (762,)
    finally:
        con.close()


def test_independent_count_matches_profile() -> None:
    assert merged_event_count(raw_export_path()) == EXPECTED_EVENTS
