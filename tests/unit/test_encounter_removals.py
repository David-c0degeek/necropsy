"""Removal ownership and chronology must survive raw/projection disagreement."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.analysis.context import ParticipantFight, participant_fights
from necropsy.analysis.encounters.effects import mechanic_removals
from necropsy.analysis.evidence import EvidenceLevel, ScopedCoverageRef
from necropsy.normalize.ingest import ingest
from tests.class_fixture import snapshot


@pytest.fixture
def context(tmp_path: Path) -> Iterator[tuple[duckdb.DuckDBPyConnection, ParticipantFight]]:
    archive = snapshot(tmp_path, 7, "Holy", "Flash Heal", "healer", include_reference=False)
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE snapshot_meta SET zone_id=2002, partition_id=1")
        con.execute("UPDATE fights SET encounter_id=50616")
        con.execute("UPDATE benchmark_participants SET encounter_id=50616")
        con.execute(
            "INSERT INTO stream_coverage (report_code,fight_id,actor_id,role,direction,status,"
            "boundary_ambiguities,multiplicity_mismatches,raw_events) "
            "SELECT 'REPORT1',7,NULL,'encounter','all','complete',0,0,count(*) FROM events"
        )
        pf = next(p for p in participant_fights(con) if p.kind == "you")
        yield con, pf


def effect(
    con: duckdb.DuckDBPyConnection,
    *,
    raw: dict[str, Any] | None = None,
    normalized: dict[str, Any] | None = None,
    in_all: bool = True,
    omit_raw: tuple[str, ...] = (),
) -> None:
    payload = {
        "type": "dispel",
        "timestamp": 5000,
        "sourceID": 1,
        "targetID": 1,
        "abilityGameID": 988,
        "extraAbilityGameID": 23153,
        "isBuff": False,
        "fight": 7,
        **(raw or {}),
    }
    values = {
        "type": "dispel",
        "timestamp": 5000,
        "source_id": 1,
        "target_id": 1,
        "ability_game_id": 988,
        **(normalized or {}),
    }
    for key in omit_raw:
        payload.pop(key)
    [count] = con.execute("SELECT count(*) FROM events").fetchone() or (0,)
    con.execute(
        "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,type,"
        "source_id,target_id,ability_game_id,raw) VALUES ('REPORT1',7,?,0,?,?,?,?,?,?)",
        [
            f"removal-{count}",
            values["timestamp"],
            values["type"],
            values["source_id"],
            values["target_id"],
            values["ability_game_id"],
            json.dumps(payload),
        ],
    )
    if in_all:
        con.execute("UPDATE stream_coverage SET raw_events=raw_events+1 WHERE role='encounter'")


@pytest.mark.parametrize("ability", [527, 988])
def test_both_magic_dispel_ranks_count_effects_once_with_both_coverage_contracts(
    context: tuple[duckdb.DuckDBPyConnection, ParticipantFight], ability: int
) -> None:
    con, pf = context
    effect(con, raw={"abilityGameID": ability}, normalized={"ability_game_id": ability})
    [finding] = mechanic_removals(con, pf)
    assert finding.removals.value == 1
    assert finding.observations.value == ((5, 1, ability, 23153),)
    assert {(c.actor_id, c.direction) for c in finding.removals.coverage} == {
        (1, "source"),
        (None, "all"),
    }
    assert (
        next(c for c in finding.removals.coverage if isinstance(c, ScopedCoverageRef)).role
        == "encounter"
    )


@pytest.mark.parametrize(
    "raw",
    [
        {"sourceID": 2},
        {"sourceID": True},
        {"sourceID": 1.0},
        {"sourceID": None},
        {"targetID": 2},
        {"targetID": True},
        {"abilityGameID": 988.0},
        {"timestamp": 5001},
        {"timestamp": 5000.0},
        {"type": "cast"},
        {"extraAbilityGameID": 0},
        {"extraAbilityGameID": -1},
        {"extraAbilityGameID": True},
        {"isBuff": 0},
        {"fight": True},
        {"fight": 8},
    ],
)
def test_raw_identity_and_required_metadata_conflicts_withhold_counts(
    context: tuple[duckdb.DuckDBPyConnection, ParticipantFight], raw: dict[str, Any]
) -> None:
    con, pf = context
    effect(con, raw=raw)
    [finding] = mechanic_removals(con, pf)
    assert finding.removals.value is None
    assert finding.observations.value is None
    assert finding.removals.refs[-1].actor_id is None


@pytest.mark.parametrize(
    "normalized",
    [
        {"source_id": 2, "target_id": 50},
        {"source_id": None, "target_id": 50},
        {"type": "cast"},
        {"ability_game_id": 475},
        {"timestamp": 200000},
    ],
)
def test_raw_owned_candidates_cannot_hide_behind_normalized_query_filters(
    context: tuple[duckdb.DuckDBPyConnection, ParticipantFight], normalized: dict[str, Any]
) -> None:
    con, pf = context
    effect(con, normalized=normalized)
    [finding] = mechanic_removals(con, pf)
    assert finding.removals.value is None and finding.observations.value is None


@pytest.mark.parametrize("case", ["other-source", "other-mechanic", "buff", "cast"])
def test_definitively_unrelated_effects_and_casts_do_not_become_owned_removals(
    context: tuple[duckdb.DuckDBPyConnection, ParticipantFight], case: str
) -> None:
    con, pf = context
    choices: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
        "other-source": ({"sourceID": 2}, {"source_id": 2}),
        "other-mechanic": ({"extraAbilityGameID": 23154}, {}),
        "buff": ({"isBuff": True}, {}),
        "cast": ({"type": "cast"}, {"type": "cast"}),
    }
    raw, normalized = choices[case]
    effect(con, raw=raw, normalized=normalized)
    [finding] = mechanic_removals(con, pf)
    assert finding.removals.value == 0 and finding.observations.value == ()


@pytest.mark.parametrize("scope", ["source", "encounter", "extra-row"])
def test_missing_scope_keeps_positive_removals_without_certifying_a_count(
    context: tuple[duckdb.DuckDBPyConnection, ParticipantFight], scope: str
) -> None:
    con, pf = context
    effect(con, in_all=scope != "extra-row")
    if scope == "source":
        con.execute("UPDATE stream_coverage SET status='incomplete' WHERE direction='source'")
    elif scope == "encounter":
        con.execute("DELETE FROM stream_coverage WHERE role='encounter'")
    [finding] = mechanic_removals(con, pf)
    assert finding.removals.value is None
    assert finding.observations.level is EvidenceLevel.OBSERVED
    assert finding.observations.value == ((5, 1, 988, 23153),)


def test_valid_positive_is_preserved_alongside_a_conflicting_owned_candidate(
    context: tuple[duckdb.DuckDBPyConnection, ParticipantFight],
) -> None:
    con, pf = context
    effect(con)
    effect(con, normalized={"source_id": 2, "target_id": 50})
    [finding] = mechanic_removals(con, pf)
    assert finding.removals.value is None
    assert finding.observations.value == ((5, 1, 988, 23153),)


@pytest.mark.parametrize(
    "column,key",
    [
        ("type", "type"),
        ("timestamp", "timestamp"),
        ("source_id", "sourceID"),
        ("ability_game_id", "abilityGameID"),
    ],
)
def test_nullable_normalized_identity_without_raw_support_cannot_certify_zero(
    context: tuple[duckdb.DuckDBPyConnection, ParticipantFight], column: str, key: str
) -> None:
    con, pf = context
    effect(con, normalized={column: None}, omit_raw=(key,))
    [finding] = mechanic_removals(con, pf)
    assert finding.removals.value is None and finding.observations.value is None


@pytest.mark.parametrize("payload", ["null", "[]", "true"])
@pytest.mark.parametrize("timestamp", [None, 5000])
def test_malformed_raw_payload_with_nullable_time_cannot_crash_or_certify_absence(
    context: tuple[duckdb.DuckDBPyConnection, ParticipantFight],
    payload: str,
    timestamp: int | None,
) -> None:
    con, pf = context
    effect(con, normalized={"timestamp": timestamp})
    con.execute("UPDATE events SET raw=? WHERE event_uid LIKE 'removal-%'", [payload])
    [finding] = mechanic_removals(con, pf)
    assert finding.removals.value is None and finding.observations.value is None
