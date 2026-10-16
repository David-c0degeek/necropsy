"""A WCL score can survive missing pets; it must never repair event evidence."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import duckdb
import pytest

from necropsy.analysis.context import ParticipantFight
from necropsy.analysis.evidence import EvidenceLevel
from necropsy.analysis.generic.catalog import recorded_hunter_dps


def _participant(kind: str = "top") -> ParticipantFight:
    return ParticipantFight(
        "YhxTZy3BDQN7nkcV",
        34,
        42,
        "Charies",
        "Mankrik",
        kind,
        "Patchwerk",
        51118,
        2,
        0,
        109356,
        True,
    )


def _row(**changes: Any) -> dict[str, Any]:
    return {
        "report": {"code": "YhxTZy3BDQN7nkcV", "fightID": 34},
        "name": "Charies",
        "class": "Hunter",
        "amount": 1367.86,
        "server": {"name": "Mankrik"},
        "spec": "Marksmanship",
        "hardModeLevel": 0,
        **changes,
    }


def _db(
    rows: list[dict[str, Any]],
    *,
    kind: str = "leaderboard",
    role: str = "dps",
) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("CREATE TABLE snapshot_meta (mode VARCHAR, partition_id INT, acquisition JSON)")
    key = {
        name: {"value": value, "status": "enforced"}
        for name, value in {
            "site": "vanilla.warcraftlogs.com",
            "game": "classic_era",
            "zone": 2006,
            "partition": 1,
            "encounter": 51118,
            "role": role,
            "class_name": "Hunter",
            "difficulty": 0,
            "spec": "Marksmanship",
        }.items()
    }
    con.execute(
        "INSERT INTO snapshot_meta VALUES ('live', 1, ?)",
        [
            json.dumps(
                {
                    "bosses": [{"encounter_id": 51118, "key": key}],
                }
            )
        ],
    )
    con.execute("""CREATE TABLE rankings (source VARCHAR, row_index INT, player VARCHAR,
        raw JSON, kind VARCHAR, encounter_id INT, report_code VARCHAR, fight_id INT)""")
    for index, row in enumerate(rows):
        con.execute(
            "INSERT INTO rankings VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                "saved.json",
                index,
                "Charies",
                json.dumps(row),
                kind,
                51118,
                "YhxTZy3BDQN7nkcV",
                34,
            ],
        )
    return con


def test_exact_recorded_score_and_source_are_preserved() -> None:
    score = recorded_hunter_dps(_db([_row(), _row()]), _participant())
    assert score.level is EvidenceLevel.OBSERVED and score.value == 1367.86
    assert len(score.refs) == 2 and score.refs[0].fight_id == 34
    assert score.note and "Recorded WCL DPS" in score.note
    assert score.coverage == ()  # Does not claim complete event acquisition.


def test_subject_score_uses_subject_rows() -> None:
    row = _row(**{"class": 3})
    row.pop("name")  # WCL subject rows do not carry the character's name.
    assert recorded_hunter_dps(_db([row], kind="subject"), _participant("you")).value == 1367.86
    assert recorded_hunter_dps(_db([row]), _participant("you")).value is None


@pytest.mark.parametrize(
    "changes",
    [
        {"amount": True},
        {"amount": -1},
        {"amount": "1367"},
        {"amount": None},
        {"amount": float("inf")},
        {"amount": float("nan")},
        {"name": "Other"},
        {"class": "Warrior"},
        {"class": True},
        {"hardModeLevel": 1},
        {"hardModeLevel": False},
        {"spec": "Survival"},
        {"server": {"name": "Firemaw"}},
        {"report": {"code": "Other", "fightID": 34}},
        {"report": {"code": "YhxTZy3BDQN7nkcV", "fightID": 35}},
    ],
)
def test_invalid_or_mismatching_raw_rows_are_not_scores(changes: dict[str, Any]) -> None:
    assert recorded_hunter_dps(_db([_row(**changes)]), _participant()).value is None


def test_conflicts_missing_identity_and_wrong_category_remain_unknown() -> None:
    assert recorded_hunter_dps(_db([_row(), _row(amount=1300)]), _participant()).value is None
    assert recorded_hunter_dps(_db([_row()]), replace(_participant(), fight_id=35)).value is None
    assert recorded_hunter_dps(_db([_row()], role="hps"), _participant()).value is None
    con = _db([_row()])
    con.execute("UPDATE snapshot_meta SET mode = 'historical'")
    assert recorded_hunter_dps(con, _participant()).value is None


def test_zero_is_a_valid_recorded_score() -> None:
    assert recorded_hunter_dps(_db([_row(amount=0)]), _participant()).value == 0
