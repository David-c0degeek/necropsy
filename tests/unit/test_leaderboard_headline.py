"""Saved rank-one metadata must stay distinct from acquired event benchmarks."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import Mock

import duckdb
import pytest

from necropsy.analysis.benchmark import BossData
from necropsy.report.analysis_json import _leaderboard_top, _overall_top
from necropsy.report.serialize import to_data
from necropsy.wcl.cohort import cohort_key
from necropsy.wcl.sites import VANILLA
from tests.unit.test_wcl_acquire import PATCHWERK, _context


def _setup(row: dict[str, Any]) -> tuple[duckdb.DuckDBPyConnection, BossData]:
    con = duckdb.connect()
    key = to_data(cohort_key(VANILLA, _context(), PATCHWERK))
    acq = {"bosses": [{"encounter_id": PATCHWERK, "key": key}]}
    con.execute(
        "CREATE TABLE snapshot_meta(mode VARCHAR, partition_id INT, acquisition JSON, zone_id INT)"
    )
    con.execute("INSERT INTO snapshot_meta VALUES ('live', 3, ?, 2006)", [json.dumps(acq)])
    con.execute(
        "CREATE TABLE rankings(source VARCHAR, kind VARCHAR, encounter_id INT, "
        "page INT, row_index INT, raw JSON)"
    )
    con.execute(
        "INSERT INTO rankings VALUES ('leaderboards/51118_Patchwerk.json','leaderboard',?,1,0,?)",
        [PATCHWERK, json.dumps(row)],
    )
    boss = Mock(spec=BossData, encounter_id=PATCHWERK)
    return con, boss


def _row() -> dict[str, Any]:
    return {
        "name": "OtherFaction",
        "class": "Hunter",
        "amount": 1409.79,
        "hardModeLevel": 0,
        "duration": 100000,
        "report": {"code": "RPlayer", "fightID": 1},
        "guild": {"faction": 1},
    }


def test_metadata_score_is_observed_and_not_an_event_sample() -> None:
    con, boss = _setup(_row())
    try:
        value = _leaderboard_top(con, boss)
        assert value is not None and value["ranked_dps"] == 1409.79
        assert value["ranked_dps_evidence"]["level"] == "observed"
        assert value["faction"]["value"] is None  # guild does not prove character faction
        assert value["event_sample_acquired"] is False and value["captured_at"] is None
        assert value["source_member"].startswith("leaderboards/")
    finally:
        con.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount", True),
        ("amount", -1),
        ("amount", "1409.79"),
        ("amount", None),
        ("class", "Mage"),
        ("class", 3.0),
        ("hardModeLevel", False),
        ("hardModeLevel", 1),
        ("rank", 2),
        ("position", True),
        ("name", " "),
    ],
)
def test_invalid_first_row_does_not_become_rank_one(field: str, value: Any) -> None:
    row = _row()
    row[field] = value
    con, boss = _setup(row)
    try:
        assert _leaderboard_top(con, boss) is None
    finally:
        con.close()


def test_ambiguous_first_rows_and_wrong_partition_stay_unknown() -> None:
    con, boss = _setup(_row())
    try:
        con.execute("UPDATE snapshot_meta SET partition_id=1")
        assert _leaderboard_top(con, boss) is None
        con.execute("UPDATE snapshot_meta SET partition_id=3")
        con.execute("INSERT INTO rankings SELECT * FROM rankings")
        assert _leaderboard_top(con, boss) is None
    finally:
        con.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("player", "Different"),
        ("report_code", "OtherReport"),
        ("fight_id", 2),
    ],
)
def test_conflicting_rank_one_identities_do_not_choose_either_source(
    field: str, value: Any
) -> None:
    con, boss = _setup(_row())
    entry = Mock(ranked_dps=None)
    entry.participant.leaderboard_position = 1
    entry.participant.player = "OtherFaction"
    entry.participant.report_code = "RPlayer"
    entry.participant.fight_id = 1
    setattr(entry.participant, field, value)
    boss = Mock(spec=BossData, encounter_id=PATCHWERK, cohort=(entry,))
    try:
        top, reason = _overall_top(con, boss)
        assert top is None and reason is not None and "identity conflicts" in reason
    finally:
        con.close()
