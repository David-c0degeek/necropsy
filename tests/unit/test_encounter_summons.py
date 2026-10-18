"""Summon event bounds preserve scope, instance identity and unknown endpoints."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import duckdb
import pytest

from necropsy.analysis.context import ParticipantFight
from necropsy.analysis.encounters.summons import summon_observations
from necropsy.analysis.evidence import EvidenceLevel
from necropsy.normalize.schema import ALL_TABLES
from necropsy.report.render.playbook_view import with_strategy
from necropsy.report.serialize import to_data

PF = ParticipantFight(
    "REPORT", 1, 1, "Hunter", None, "you", "Skeram", 50709, None, 1000, 11000, True
)


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    with duckdb.connect(":memory:") as db:
        for table in ALL_TABLES:
            db.execute(table.ddl())
        db.execute("INSERT INTO snapshot_meta (zone_id,partition_id) VALUES (2005,1)")
        db.execute(
            "INSERT INTO actors (report_code,actor_id,type,game_id,name) VALUES "
            "('REPORT',50,'NPC',15263,'Skeram'),('REPORT',5,'NPC',176525,'Image'),"
            "('REPORT',6,'NPC',9999,'Foreign'),('REPORT',1,'Player',NULL,'Hunter')"
        )
        db.execute(
            "INSERT INTO fights (report_code,fight_id,enemy_npcs) VALUES ('REPORT',1,?)",
            [
                json.dumps(
                    [
                        {"id": 50, "gameID": 15263, "instanceCount": 1},
                        {"id": 5, "gameID": 176525, "instanceCount": 6},
                    ]
                )
            ],
        )
        db.execute(
            "INSERT INTO stream_coverage (report_code,fight_id,actor_id,role,direction,status,"
            "boundary_ambiguities,multiplicity_mismatches,raw_events) "
            "VALUES ('REPORT',1,NULL,'encounter','all','complete',0,0,0)"
        )
        yield db


def event(
    con: duckdb.DuckDBPyConnection,
    timestamp: int,
    kind: str,
    instance: object = 1,
    *,
    source: int = 50,
    target: int = 5,
    ability: int = 747,
    raw: dict[str, Any] | None = None,
    in_encounter: bool = True,
) -> None:
    row = con.execute("SELECT count(*) FROM events").fetchone()
    assert row is not None
    payload = {
        "timestamp": timestamp,
        "type": kind,
        "sourceID": source,
        "targetID": target,
        "abilityGameID": ability,
        "targetInstance": instance,
    }
    payload.update(raw or {})
    con.execute(
        "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,type,"
        "source_id,target_id,ability_game_id,raw) VALUES ('REPORT',1,?,0,?,?,?,?,?,?)",
        [str(row[0]), timestamp, kind, source, target, ability, json.dumps(payload)],
    )
    if in_encounter:
        con.execute("UPDATE stream_coverage SET raw_events=raw_events+1 WHERE role='encounter'")


def hit(
    con: duckdb.DuckDBPyConnection, timestamp: int = 5000, instance: object = 1, **raw: Any
) -> None:
    event(
        con,
        timestamp,
        "damage",
        instance,
        source=1,
        ability=75,
        raw={"amount": 10, "overkill": 2, **raw},
    )


def test_overlapping_groups_keep_separate_bounds_and_missing_endpoints(
    con: duckdb.DuckDBPyConnection,
) -> None:
    event(con, 2000, "summon", 1)
    event(con, 4000, "summon", 2)
    event(con, 6000, "summon", 3)
    hit(con, 5000, 1)
    hit(con, 7000, 2)
    [result] = summon_observations(con, PF)
    assert result.summons.value == 3
    assert result.transitions.value == ((1.0, 50, 5, 1), (3.0, 50, 5, 2), (5.0, 50, 5, 3))
    assert [target.elapsed_to_overkill_s.value for target in result.targets] == [3.0, 3.0, None]
    assert result.targets[2].first_positive_overkill_s.value is None
    assert result.targets[0].first_positive_overkill_s.value == 4.0
    assert "attackability" in result.limitation
    view = with_strategy({}, {"summon_observations": to_data((result,))})
    text = " ".join(line["text"] for line in view["pull_during"])
    assert "3 recorded summons" in text and "3.00s from summon" in text
    assert "Unknown from summon" in text


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "missing"),
        ("role", "critical"),
        ("direction", "source"),
        ("boundary_ambiguities", 1),
        ("multiplicity_mismatches", 1),
    ],
)
def test_partial_or_wrong_scope_keeps_positive_events_without_bounds(
    con: duckdb.DuckDBPyConnection,
    field: str,
    value: object,
) -> None:
    con.execute(f"UPDATE stream_coverage SET {field}=?", [value])
    event(con, 2000, "summon")
    hit(con)
    [result] = summon_observations(con, PF)
    assert result.transitions.level is EvidenceLevel.OBSERVED
    assert result.summons.value is None
    assert result.targets[0].elapsed_to_overkill_s.value is None


@pytest.mark.parametrize(
    "case",
    [
        "repeat",
        "same-time",
        "before",
        "later-damage",
        "resurrect",
        "real-death",
        "bad-death",
        "malformed-amount",
        "malformed-overkill",
        "zero-amount",
        "wrong-raw-target",
        "wrong-raw-instance",
        "unresolved-lifecycle",
    ],
)
def test_conflicting_or_invalid_boundaries_do_not_create_elapsed_time(
    con: duckdb.DuckDBPyConnection,
    case: str,
) -> None:
    event(con, 2000, "summon")
    if case == "repeat":
        event(con, 3000, "summon")
    elif case == "later-damage":
        hit(con, 6000, overkill=0)
    elif case in {"resurrect", "real-death", "bad-death"}:
        event(
            con,
            4500,
            "resurrect" if case == "resurrect" else "death",
            ability=0,
            raw={"feign": 1 if case == "bad-death" else False},
        )
    elif case == "unresolved-lifecycle":
        event(con, 4500, "death", ability=0, raw={"targetID": True})
    values: dict[str, Any] = {}
    if case == "malformed-amount":
        values["amount"] = True
    if case == "malformed-overkill":
        values["overkill"] = "2"
    if case == "zero-amount":
        values["amount"] = 0
    if case == "wrong-raw-target":
        values["targetID"] = 6
    if case == "wrong-raw-instance":
        values["targetInstance"] = True
    hit(con, 2000 if case == "same-time" else 1500 if case == "before" else 5000, **values)
    [result] = summon_observations(con, PF)
    assert result.targets[0].elapsed_to_overkill_s.value is None


@pytest.mark.parametrize("value", [None, True, "1", 0, -1, 7])
def test_missing_or_malformed_numbered_instance_is_not_invented(
    con: duckdb.DuckDBPyConnection,
    value: object,
) -> None:
    event(con, 2000, "summon", value)
    hit(con)
    [result] = summon_observations(con, PF)
    assert result.summons.value is None
    assert result.targets == ()


@pytest.mark.parametrize("overkill", [0, -1, None, True, "2"])
def test_nonpositive_or_invalid_overkill_does_not_supply_an_endpoint(
    con: duckdb.DuckDBPyConnection,
    overkill: object,
) -> None:
    event(con, 2000, "summon")
    hit(con, overkill=overkill)
    [result] = summon_observations(con, PF)
    assert result.targets[0].elapsed_to_overkill_s.value is None


def test_same_time_damage_is_unordered_and_feign_is_not_a_terminal_marker(
    con: duckdb.DuckDBPyConnection,
) -> None:
    event(con, 2000, "summon")
    event(con, 3000, "death", ability=0, raw={"feign": True})
    [without_marker] = summon_observations(con, PF)
    assert without_marker.targets[0].elapsed_to_overkill_s.value is None
    hit(con)
    hit(con, overkill=0)
    [result] = summon_observations(con, PF)
    assert result.targets[0].elapsed_to_overkill_s.value == 3.0


@pytest.mark.parametrize(
    "case", ["wrong-caster", "ambiguous-caster", "bad-cardinality", "duplicate-roster"]
)
def test_summon_source_and_fight_cardinality_are_qualified(
    con: duckdb.DuckDBPyConnection,
    case: str,
) -> None:
    if case == "wrong-caster":
        event(con, 2000, "summon", source=6)
    else:
        if case == "ambiguous-caster":
            con.execute(
                "INSERT INTO actors (report_code,actor_id,type,game_id,name) "
                "VALUES ('REPORT',50,'NPC',9999,'Other')"
            )
        else:
            roster = [
                {
                    "id": 50,
                    "gameID": 15263,
                    "instanceCount": True if case == "bad-cardinality" else 1,
                },
                {"id": 5, "gameID": 176525, "instanceCount": 6},
            ]
            if case == "duplicate-roster":
                roster.append(roster[0])
            con.execute("UPDATE fights SET enemy_npcs=?", [json.dumps(roster)])
        event(con, 2000, "summon")
    hit(con)
    [result] = summon_observations(con, PF)
    assert result.targets == ()
    assert result.summons.value == (0 if case == "wrong-caster" else None)


@pytest.mark.parametrize("zone,partition", [(2006, 1), (2000, 1), (2005, 3)])
def test_wrong_raid_or_variant_does_not_apply(
    con: duckdb.DuckDBPyConnection,
    zone: int,
    partition: int,
) -> None:
    con.execute("UPDATE snapshot_meta SET zone_id=?,partition_id=?", [zone, partition])
    assert summon_observations(con, PF) == ()


@pytest.mark.parametrize("actor", [5, 50])
def test_conflicting_catalog_and_raw_fight_identity_is_not_known_absence(
    con: duckdb.DuckDBPyConnection, actor: int
) -> None:
    con.execute("UPDATE actors SET game_id=9999 WHERE actor_id=?", [actor])
    event(con, 2000, "summon")
    hit(con)
    [result] = summon_observations(con, PF)
    assert result.summons.value is None
    assert result.targets == ()


@pytest.mark.parametrize("key", ["sourceID", "targetID", "abilityGameID", "timestamp"])
@pytest.mark.parametrize("value", [True, None, "50", 50.25])
def test_coerced_raw_summon_ids_cannot_certify_counts(
    con: duckdb.DuckDBPyConnection, key: str, value: object
) -> None:
    event(con, 2000, "summon", raw={key: value})
    hit(con)
    [result] = summon_observations(con, PF)
    assert result.summons.value is None
    assert result.targets == ()


def test_raw_event_kind_must_agree_with_normalized_projection(
    con: duckdb.DuckDBPyConnection,
) -> None:
    event(con, 2000, "summon", raw={"type": "cast"})
    [result] = summon_observations(con, PF)
    assert result.summons.value is None
    assert result.targets == ()


def test_zero_summons_require_complete_all_coverage(con: duckdb.DuckDBPyConnection) -> None:
    [complete] = summon_observations(con, PF)
    assert complete.summons.value == 0 and complete.transitions.value == ()
    con.execute("DELETE FROM stream_coverage")
    [missing] = summon_observations(con, PF)
    assert missing.summons.value is None and missing.transitions.value is None


@pytest.mark.parametrize("count", [None, True, 0, -1, 1.25, "6"])
def test_invalid_target_cardinality_cannot_qualify_a_numbered_instance(
    con: duckdb.DuckDBPyConnection, count: object
) -> None:
    roster = [
        {"id": 50, "gameID": 15263, "instanceCount": 1},
        {"id": 5, "gameID": 176525, "instanceCount": count},
    ]
    con.execute("UPDATE fights SET enemy_npcs=?", [json.dumps(roster)])
    event(con, 2000, "summon")
    hit(con)
    [result] = summon_observations(con, PF)
    assert result.summons.value is None and result.targets == ()


def test_fight_truncation_does_not_invent_endpoint_and_examples_remain_labelled(
    con: duckdb.DuckDBPyConnection,
) -> None:
    event(con, 2000, "summon")
    hit(con, 11001)
    [result] = summon_observations(con, PF)
    assert result.targets[0].elapsed_to_overkill_s.value is None
    view = with_strategy(
        {}, {"cohort_summon_observations": [{"player": "Example", "summons": to_data((result,))}]}
    )
    text = " ".join(line["text"] for line in view["pull_during"])
    assert "In Example's fight: Summon Images: 1 recorded summons." in text
    assert "In Example's fight: Image · instance 1: Unknown" in text


@pytest.mark.parametrize("extra", ["summon", "overkill", "copy"])
def test_trusted_all_scope_cannot_certify_rows_added_only_by_other_streams(
    con: duckdb.DuckDBPyConnection, extra: str
) -> None:
    event(con, 2000, "summon", in_encounter=extra != "summon")
    event(
        con,
        5000,
        "damage",
        source=1,
        ability=75,
        raw={"amount": 10, "overkill": 2},
        in_encounter=extra != "overkill",
    )
    if extra == "copy":
        con.execute(
            "INSERT INTO events SELECT * REPLACE (1 AS copy_index) FROM events WHERE type='summon'"
        )
    [result] = summon_observations(con, PF)
    assert result.summons.value is None
    assert result.transitions.level is EvidenceLevel.OBSERVED
    assert all(target.elapsed_to_overkill_s.value is None for target in result.targets)


@pytest.mark.parametrize("count", [None, -1, 3])
def test_missing_or_inconsistent_all_event_count_withholds_bounds(
    con: duckdb.DuckDBPyConnection, count: int | None
) -> None:
    event(con, 2000, "summon")
    hit(con)
    con.execute("UPDATE stream_coverage SET raw_events=?", [count])
    [result] = summon_observations(con, PF)
    assert result.targets[0].elapsed_to_overkill_s.value is None


@pytest.mark.parametrize("kind", ["damage", "death", "resurrect"])
@pytest.mark.parametrize("conflicting_target", [False, True])
def test_unrelated_malformed_chronology_requires_agreeing_recipient_identity(
    con: duckdb.DuckDBPyConnection, kind: str, conflicting_target: bool
) -> None:
    event(con, 2000, "summon")
    hit(con)
    event(
        con,
        3000,
        kind,
        target=6,
        raw={"timestamp": "invalid", "targetID": 5 if conflicting_target else 6},
    )
    [result] = summon_observations(con, PF)
    assert result.targets[0].elapsed_to_overkill_s.value == (None if conflicting_target else 3.0)
