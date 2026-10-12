"""Ingest of the committed 12-fight subset (fast suite)."""

from __future__ import annotations

import json
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.normalize.coverage import has_complete_coverage
from necropsy.normalize.ingest import IngestSummary, ingest
from necropsy.snapshot.archive import load_entries_manifest
from necropsy.snapshot.model import Direction
from tests.fixture_paths import provenance, subset_entries_path, subset_path
from tests.independent_count import merged_event_count


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[IngestSummary, Path]:
    db = tmp_path_factory.mktemp("subset") / "subset.duckdb"
    summary = ingest(
        subset_path(),
        db,
        expected_sha256=provenance()["subset"]["sha256"],
        entries=load_entries_manifest(subset_entries_path()),
    )
    return summary, db


@pytest.fixture
def con(built: tuple[IngestSummary, Path]) -> Iterator[duckdb.DuckDBPyConnection]:
    connection = duckdb.connect(str(built[1]), read_only=True)
    yield connection
    connection.close()


def _one(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None) -> Any:
    row = con.execute(sql, params or []).fetchone()
    assert row is not None
    return row[0]


def _unselected_actor_dirs() -> frozenset[str]:
    """Dwarfazz shares a selected Gothik fight but is not a subset participant."""
    with zipfile.ZipFile(subset_path()) as zf:
        player = next(n for n in zf.namelist() if "/player_5_Dwarfazz/" in n)
        code, fight = player.split("/")[1:3]
        pets = json.loads(zf.read(f"events/{code}/{fight}/player_5_Dwarfazz/pets.json"))
        dirs = {
            n.split("/")[3]
            for n in zf.namelist()
            if n.startswith(f"events/{code}/{fight}/")
            and (
                n.split("/")[3] == "player_5_Dwarfazz"
                or any(n.split("/")[3].startswith(f"pet_{p['id']}_") for p in pets)
            )
        }
    return frozenset(f"{code}/{fight}/{d}" for d in dirs)


def test_summary(built: tuple[IngestSummary, Path]) -> None:
    summary, _ = built
    assert summary.scope == "subset"
    assert summary.fights == 12
    assert summary.streams == 114
    assert summary.incomplete_streams == 0
    assert summary.anomalies == 0


def test_event_total_matches_independent_count(
    built: tuple[IngestSummary, Path], con: duckdb.DuckDBPyConnection
) -> None:
    expected = merged_event_count(subset_path(), _unselected_actor_dirs())
    assert built[0].events == expected
    assert _one(con, "SELECT count(*) FROM events") == expected


def test_subset_never_claims_full_coverage(con: duckdb.DuckDBPyConnection) -> None:
    assert _one(con, "SELECT scope FROM snapshot_meta") == "subset"
    assert _one(con, "SELECT selected_fights FROM snapshot_meta") == 12
    assert _one(con, "SELECT source_fight_count FROM snapshot_meta") == 89
    assert _one(con, "SELECT count(DISTINCT (report_code, fight_id)) FROM fights") == 12


def test_unselected_actor_data_is_reported_not_ingested(con: duckdb.DuckDBPyConnection) -> None:
    issues = [r[0] for r in con.execute("SELECT issue FROM snapshot_issues").fetchall()]
    assert any("player_5_Dwarfazz: no selected participant" in i for i in issues)
    assert _one(con, "SELECT count(*) FROM benchmark_participants WHERE player = 'Dwarfazz'") == 0


def test_haplina_patchwerk_coverage_and_talents(con: duckdb.DuckDBPyConnection) -> None:
    report, fight = con.execute(
        "SELECT report_code, fight_id FROM benchmark_participants "
        "WHERE player = 'Haplina' AND boss = 'Patchwerk'"
    ).fetchone() or (None, None)
    actor = _one(
        con,
        "SELECT actor_id FROM actors WHERE report_code = ? AND name = 'Haplina' "
        "AND type = 'Player'",
        [report],
    )
    assert has_complete_coverage(con, report, fight, actor, Direction.SOURCE)
    assert (
        _one(
            con,
            "SELECT talent_points FROM combatant_info WHERE report_code = ? AND "
            "fight_id = ? AND actor_id = ?",
            [report, fight, actor],
        )
        == "12/33/6"
    )
