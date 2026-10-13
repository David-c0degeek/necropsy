"""Item names and parse percentiles from recorded ranking rows."""

from __future__ import annotations

import json
from typing import Any

import duckdb
import pytest

from necropsy.analysis.context import ParticipantFight
from necropsy.analysis.evidence import EvidenceLevel
from necropsy.analysis.generic.catalog import item_catalog, rank_percent


def _db(rows: list[tuple[str, dict[str, Any]]]) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("CREATE TABLE rankings (source VARCHAR, kind VARCHAR, row_index INTEGER, raw JSON)")
    for i, (kind, raw) in enumerate(rows):
        con.execute(
            "INSERT INTO rankings VALUES (?, ?, ?, ?)", [f"{kind}.json", kind, i, json.dumps(raw)]
        )
    return con


def _pf(kind: str = "you", code: str = "R1", fight: int = 7) -> ParticipantFight:
    return ParticipantFight(code, fight, 1, "P", None, kind, "Boss", 1, None, 0, 1000, True)


def test_names_come_from_ranking_rows_with_conflicts_left_unnamed() -> None:
    con = _db(
        [
            ("leaderboard", {"gear": [{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Beta"}]}),
            (
                "leaderboard",
                {"gear": [{"id": 2, "name": "Beta (alt)"}, {"id": 3, "name": "Unknown Item"}]},
            ),
            ("subject", {"gear": [{"id": 1, "name": "Alpha"}, "not-a-dict"]}),
        ]
    )
    catalog = item_catalog(con)
    assert (catalog[1].name, catalog[1].source) == ("Alpha", "wcl-rankings-gear")
    assert catalog[2].name is None and catalog[2].source == "conflict"
    assert catalog[2].note and "Beta (alt)" in catalog[2].note
    assert 3 not in catalog or catalog[3].source == "rules-items"


def test_static_names_fill_in_without_rankings() -> None:
    catalog = item_catalog(_db([]))
    sources = {n.source for n in catalog.values()}
    assert catalog and sources <= {"game-client-data", "rules-items"}
    assert catalog[22812].source == "game-client-data"  # client data wins over items.yaml


def _ranking(code: str, fight: int, percent: float, today: float = 99.0) -> dict[str, Any]:
    return {
        "report": {"code": code, "fightID": fight},
        "rankPercent": percent,
        "todayPercent": today,
        "rankTotalParses": 20000,
        "bracketData": 85,
    }


def test_percentile_matches_report_and_fight_exactly() -> None:
    con = _db([("subject", _ranking("R1", 7, 95.5, 96.0)), ("subject", _ranking("R1", 8, 50.0))])
    found = rank_percent(con, _pf())
    assert found.level is EvidenceLevel.OBSERVED and found.value is not None
    assert (found.value.percent, found.value.today_percent) == (95.5, 96.0)
    assert (found.value.total_parses, found.value.bracket) == (20000, 85)


@pytest.mark.parametrize(
    ("rows", "pf"),
    [
        ([], _pf()),
        ([("subject", _ranking("R1", 8, 50.0))], _pf()),
        ([("subject", _ranking("R1", 7, 95.0)), ("subject", _ranking("R1", 7, 90.0))], _pf()),
        ([("leaderboard", _ranking("R1", 7, 95.0))], _pf()),
        ([("subject", _ranking("R1", 7, 95.0))], _pf(kind="top")),
    ],
)
def test_percentile_is_unknown_rather_than_guessed(rows: Any, pf: ParticipantFight) -> None:
    found = rank_percent(_db(rows), pf)
    assert found.level is EvidenceLevel.UNKNOWN and found.value is None


@pytest.mark.parametrize(
    "rows",
    [
        [_ranking("R1", 7, 95.0, 96.0), _ranking("R1", 7, 95.0, 40.0)],
        [_ranking("R1", 7, 95.0, 96.0), {**_ranking("R1", 7, 95.0), "todayPercent": None}],
        [_ranking("R1", 7, 95.0), {**_ranking("R1", 7, 95.0), "rankTotalParses": 999}],
        [_ranking("R1", 7, 95.0), {**_ranking("R1", 7, 95.0), "bracketData": 99}],
    ],
)
def test_duplicate_rows_must_agree_on_every_field(rows: list[dict[str, Any]]) -> None:
    found = rank_percent(_db([("subject", r) for r in rows]), _pf())
    assert found.level is EvidenceLevel.UNKNOWN and "disagree" in (found.note or "")


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), -1.0, 100.5, "95"])
def test_invalid_percentiles_are_not_observed(bad: Any) -> None:
    row = {**_ranking("R1", 7, 95.0), "rankPercent": bad}
    found = rank_percent(_db([("subject", row)]), _pf())
    assert found.level is EvidenceLevel.UNKNOWN


def test_an_invalid_today_percent_is_dropped_not_trusted() -> None:
    row = {**_ranking("R1", 7, 95.0), "todayPercent": 140.0}
    found = rank_percent(_db([("subject", row)]), _pf())
    assert found.value is not None and found.value.today_percent is None
