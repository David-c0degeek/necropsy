"""Instance, scope and unknown-state counterexamples for hostile aura windows."""

import json
from collections.abc import Iterator
from dataclasses import replace

import duckdb
import pytest

from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.analysis.context import ParticipantFight
from necropsy.analysis.encounters.windows import encounter_auras
from necropsy.analysis.evidence import EvidenceLevel
from necropsy.normalize.coverage import has_complete_encounter_coverage
from necropsy.normalize.schema import ALL_TABLES
from necropsy.report.analysis_json import CoverageReference
from necropsy.report.render.playbook_view import with_strategy
from necropsy.report.serialize import to_data
from necropsy.snapshot.model import ActorRole

PF = ParticipantFight(
    "REPORT", 1, 1, "Priest", None, "you", "Majordomo", 50671, None, 0, 10000, True
)


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    with duckdb.connect(":memory:") as connection:
        for table in ALL_TABLES:
            connection.execute(table.ddl())
        connection.execute("INSERT INTO snapshot_meta (zone_id,partition_id) VALUES (2000,1)")
        connection.execute(
            "INSERT INTO actors (report_code,actor_id,type,game_id,name) VALUES "
            "('REPORT',50,'NPC',12018,'Majordomo'),('REPORT',5,'NPC',11664,'Elite'),"
            "('REPORT',6,'NPC',11663,'Healer'),('REPORT',7,'NPC',12099,'Foreign')"
        )
        connection.execute(
            "INSERT INTO stream_coverage (report_code,fight_id,actor_id,role,direction,status,"
            "boundary_ambiguities,multiplicity_mismatches,raw_events) "
            "VALUES ('REPORT',1,NULL,'encounter','all','complete',0,0,0)"
        )
        yield connection


def event(
    con: duckdb.DuckDBPyConnection,
    timestamp: int,
    kind: str,
    instance: object,
    *,
    target: int = 5,
    source: int = 50,
    ability: int = 20619,
    in_encounter: bool = True,
) -> None:
    index = con.execute("SELECT count(*) FROM events").fetchone()
    assert index
    con.execute(
        "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,type,"
        "source_id,target_id,ability_game_id,raw) VALUES ('REPORT',1,?,0,?,?,?,?,?,?)",
        [
            str(index[0]),
            timestamp,
            kind,
            source,
            target,
            ability,
            json.dumps({"targetInstance": instance}),
        ],
    )
    if in_encounter:
        con.execute("UPDATE stream_coverage SET raw_events=raw_events+1 WHERE role='encounter'")


@pytest.mark.parametrize("flag,active", [(True, 8.0), (False, 1.0), (None, None), (1, None)])
def test_npc_aura_lifecycle_distinguishes_feign_from_real_or_ambiguous_death(
    con: duckdb.DuckDBPyConnection, flag: object, active: float | None
) -> None:
    event(con, 2000, "applybuff", 1)
    event(con, 3000, "death", 1, ability=0)
    con.execute(
        "UPDATE events SET raw=? WHERE type='death'",
        [json.dumps({"targetInstance": 1, "feign": flag})],
    )
    aura = encounter_auras(con, PF)[0]
    assert aura.targets[0].known_active_s.value == active


@pytest.mark.parametrize(
    "case",
    [
        "one",
        "missing-fight",
        "missing-roster",
        "missing-count",
        "repeated",
        "zero",
        "boolean",
        "fraction",
        "text",
        "wrong-actor",
        "wrong-game-id",
        "duplicate-actor",
        "duplicate-fight",
        "non-list",
        "non-object",
    ],
)
def test_unnumbered_boss_windows_require_exact_singleton_fight_metadata(
    con: duckdb.DuckDBPyConnection, case: str
) -> None:
    con.execute("UPDATE snapshot_meta SET zone_id=2005")
    con.execute("UPDATE actors SET game_id=15517 WHERE actor_id=5")
    roster: object = [{"id": 5, "gameID": 15517, "instanceCount": 1}]
    if case == "missing-roster":
        roster = None
    elif case == "non-list":
        roster = {"id": 5, "gameID": 15517, "instanceCount": 1}
    elif case == "non-object":
        roster = [5]
    elif case in {"missing-count", "repeated", "zero", "boolean", "fraction", "text"}:
        roster = [
            {
                "id": 5,
                "gameID": 15517,
                **(
                    {}
                    if case == "missing-count"
                    else {
                        "instanceCount": {
                            "repeated": 2,
                            "zero": 0,
                            "boolean": True,
                            "fraction": 1.0,
                            "text": "1",
                        }[case]
                    }
                ),
            }
        ]
    elif case == "wrong-actor":
        roster = [{"id": 6, "gameID": 15517, "instanceCount": 1}]
    elif case == "wrong-game-id":
        roster = [{"id": 5, "gameID": 12018, "instanceCount": 1}]
    elif case == "duplicate-actor":
        roster = [
            {"id": 5, "gameID": 15517, "instanceCount": 1},
            {"id": 5, "gameID": 15517, "instanceCount": 1},
        ]
    for _ in range(2 if case == "duplicate-fight" else 0 if case == "missing-fight" else 1):
        con.execute(
            "INSERT INTO fights (report_code,fight_id,enemy_npcs) VALUES ('REPORT',1,?)",
            [json.dumps(roster)],
        )
    event(con, 1000, "applybuff", None, source=5, ability=26615)
    event(con, 6000, "removebuff", None, source=5, ability=26615)
    pf = replace(PF, encounter_id=50716, boss="Ouro")
    (aura,) = encounter_auras(con, pf)
    assert aura.applications.value == 1
    assert len(aura.transitions.value or ()) == 2
    (target,) = aura.targets
    assert target.instance is None
    assert "fights" in {ref.source for ref in target.windows.refs}
    if case == "one":
        assert target.windows.value == ((0, 1, None), (1, 6, True), (6, 10, False))
        assert target.known_active_s.value == 5
        assert target.unknown_state_s.value == 1
    else:
        assert target.windows.value is None
        assert target.known_active_s.value is None
        assert target.unknown_state_s.value is None


def test_same_actor_different_instances_keep_distinct_windows_and_rendered_values(
    con: duckdb.DuckDBPyConnection,
) -> None:
    event(con, 1000, "applybuff", 1)
    event(con, 2000, "applybuff", 2)
    event(con, 3000, "removebuff", 1)
    event(con, 8000, "removebuff", 2)
    aura, shield = encounter_auras(con, PF)
    assert aura.applications.value == 2 and shield.applications.value == 0
    one, two = aura.targets
    assert one.windows.value == ((0, 1, None), (1, 3, True), (3, 10, False))
    assert two.windows.value == ((0, 2, None), (2, 8, True), (8, 10, False))
    assert (one.known_active_s.value, two.known_active_s.value) == (2, 6)
    assert (one.unknown_state_s.value, two.unknown_state_s.value) == (1, 2)
    assert one.windows.coverage[0].actor_id is None
    assert to_data(one.windows)["coverage"][0]["role"] == "encounter"
    view = with_strategy({}, {"target_aura_windows": to_data((aura, shield))})
    text = " ".join(line["text"] for line in view["pull_during"])
    assert "Elite · instance 1: 2.00s known active; 1.00s with unknown state." in text
    assert "Elite · instance 2: 6.00s known active; 2.00s with unknown state." in text


@pytest.mark.parametrize(
    "scope", ["critical", "player", "incomplete", "boundary", "overlap", "extra"]
)
def test_actor_or_filtered_scope_and_ambiguous_streams_cannot_certify_windows(
    con: duckdb.DuckDBPyConnection,
    scope: str,
) -> None:
    event(con, 1000, "applybuff", 1)
    if scope in {"critical", "player"}:
        con.execute("UPDATE stream_coverage SET role=?", [scope])
    elif scope == "incomplete":
        con.execute("UPDATE stream_coverage SET status='incomplete'")
    elif scope == "extra":
        con.execute("INSERT INTO stream_coverage SELECT * FROM stream_coverage")
    else:
        column = "boundary_ambiguities" if scope == "boundary" else "multiplicity_mismatches"
        con.execute(f"UPDATE stream_coverage SET {column}=1")
    aura, shield = encounter_auras(con, PF)
    assert not has_complete_encounter_coverage(con, "REPORT", 1)
    assert aura.applications.value is None and shield.applications.value is None
    assert aura.targets[0].windows.value is None
    assert aura.transitions.level is EvidenceLevel.OBSERVED
    assert aura.transitions.value == ((1, "applybuff", 5, 1),)


@pytest.mark.parametrize(
    "scenario,applications,active,uncertain",
    [
        ("censored", 1, 9, 1),
        ("remove-first", 0, 0, 1),
        ("death", 1, 1.5, 8.5),
        ("contradiction", 1, 0, 10),
        ("missing-instance", 1, None, None),
        ("missing-removal-instance", 1, None, None),
        ("boolean-instance", None, None, None),
        ("unknown-caster", None, None, None),
        ("wrong-caster", 0, None, None),
        ("wrong-target", 0, None, None),
        ("cast-only", 0, None, None),
        ("foreign-buff", 0, None, None),
        ("conflicting-catalog", None, None, None),
        ("wrong-kind", 0, None, None),
    ],
)
def test_only_exact_native_applications_and_observed_transitions_establish_state(
    con: duckdb.DuckDBPyConnection,
    scenario: str,
    applications: int | None,
    active: float | None,
    uncertain: float | None,
) -> None:
    event(
        con,
        1000,
        "removebuff"
        if scenario == "remove-first"
        else "cast"
        if scenario == "cast-only"
        else "applydebuff"
        if scenario == "wrong-kind"
        else "applybuff",
        None if scenario == "missing-instance" else True if scenario == "boolean-instance" else 1,
        source=999 if scenario == "unknown-caster" else 7 if scenario == "wrong-caster" else 50,
        target=7 if scenario == "wrong-target" else 5,
        ability=20620 if scenario == "foreign-buff" else 20619,
    )
    if scenario == "death":
        event(con, 2500, "death", 1, ability=0)
    if scenario == "contradiction":
        event(con, 1000, "removebuff", 1)
    if scenario == "missing-removal-instance":
        event(con, 3000, "removebuff", None)
    if scenario == "conflicting-catalog":
        con.execute(
            "INSERT INTO actors (report_code,actor_id,type,game_id,name) "
            "VALUES ('REPORT',5,'NPC',11663,'Different')"
        )
    aura, _ = encounter_auras(con, PF)
    assert aura.applications.value == applications
    if aura.targets:
        assert aura.targets[0].known_active_s.value == active
        assert aura.targets[0].unknown_state_s.value == uncertain
    else:
        assert active is None and uncertain is None


def test_short_no_transition_kill_cannot_invent_a_buff_timer(
    con: duckdb.DuckDBPyConnection,
) -> None:
    aura, shield = encounter_auras(con, PF)
    assert aura.applications.value == shield.applications.value == 0
    assert aura.targets == shield.targets == ()
    assert "Initial state stays unknown" in aura.limitation
    assert with_strategy({}, {}) == {}
    con.execute("UPDATE snapshot_meta SET partition_id=3")
    assert encounter_auras(con, PF) == ()
    with pytest.raises(ValueError, match="actorless"):
        has_complete_encounter_coverage(con, "REPORT", 1, ActorRole.PLAYER)


@pytest.mark.parametrize(
    "actor,direction,role",
    [
        (None, "all", None),
        (1, "all", "encounter"),
        (None, "target", "encounter"),
        (None, "source", None),
    ],
)
def test_saved_coverage_cannot_confuse_actor_and_encounter_scopes(
    actor: int | None,
    direction: str,
    role: str | None,
) -> None:
    with pytest.raises(ValueError):
        CoverageReference.model_validate(
            dict(
                report="REPORT",
                fight=1,
                actor=actor,
                direction=direction,
                trusted=True,
                role=role,
            )
        )


GARR = replace(PF, boss="Garr", encounter_id=50666)


def warlock(
    con: duckdb.DuckDBPyConnection, actor: int = 10, subtype: str | None = "Warlock"
) -> None:
    con.execute(
        "INSERT INTO actors (report_code,actor_id,type,sub_type,name) "
        "VALUES ('REPORT',?,'Player',?,?)",
        [actor, subtype, f"Caster{actor}"],
    )


@pytest.mark.parametrize("subtype", CLASS_NAMES.values())
def test_banish_requires_a_known_player_warlock_without_using_subject_class(
    con: duckdb.DuckDBPyConnection, subtype: str
) -> None:
    warlock(con, subtype=subtype)
    event(con, 1000, "applydebuff", 1, target=7, source=10, ability=710)
    one, two = encounter_auras(con, GARR)
    assert two.applications.value == 0
    assert one.applications.value == (1 if subtype == "Warlock" else 0)
    if subtype == "Warlock":
        assert one.targets[0].known_active_s.value == 9
        assert one.targets[0].unknown_state_s.value == 1
        assert one.applications.coverage[0].actor_id is None
        assert one.label.startswith("Encounter-wide")
        assert GARR.actor_id != 10  # another caster's effect is never personal uptime
    else:
        assert one.targets == ()


def test_banish_ranks_and_same_actor_instances_keep_independent_observed_state(
    con: duckdb.DuckDBPyConnection,
) -> None:
    for actor in (10, 11, 12):
        warlock(con, actor)
    event(con, 1000, "applydebuff", 1, target=7, source=10, ability=710)
    event(con, 2000, "applydebuff", 2, target=7, source=11, ability=710)
    event(con, 3000, "removedebuff", 1, target=7, source=10, ability=710)
    event(con, 5000, "applydebuff", 3, target=7, source=12, ability=18647)
    one, two = encounter_auras(con, GARR)
    assert (one.applications.value, two.applications.value) == (2, 1)
    assert [(t.instance, t.known_active_s.value, t.unknown_state_s.value) for t in one.targets] == [
        (1, 2, 1),
        (2, 8, 2),
    ]
    assert [(t.instance, t.known_active_s.value, t.unknown_state_s.value) for t in two.targets] == [
        (3, 5, 5)
    ]


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("missing-class", None),
        ("invalid-class", None),
        ("missing-caster", None),
        ("ambiguous-class", None),
        ("ambiguous-name", None),
        ("npc", 0),
        ("pet", 0),
        ("cast", 0),
        ("buff", 0),
        ("foreign-target", 0),
        ("foreign-spell", 0),
        ("partial", None),
        ("critical", None),
        ("personal", None),
        ("missing-instance", 1),
        ("boolean-instance", None),
    ],
)
def test_control_identity_kind_instance_and_scope_counterexamples(
    con: duckdb.DuckDBPyConnection, scenario: str, expected: int | None
) -> None:
    warlock(
        con,
        subtype=None
        if scenario == "missing-class"
        else "unknown"
        if scenario == "invalid-class"
        else "Warlock",
    )
    if scenario in {"npc", "pet"}:
        con.execute(
            "UPDATE actors SET type=? WHERE actor_id=10", ["NPC" if scenario == "npc" else "Pet"]
        )
    if scenario.startswith("ambiguous"):
        con.execute(
            "INSERT INTO actors (report_code,actor_id,type,sub_type,name) "
            "VALUES ('REPORT',10,'Player',?,?)",
            ["Mage" if scenario == "ambiguous-class" else "Warlock", "Other"],
        )
    if scenario in {"partial", "critical", "personal"}:
        column, value = (
            ("status", "incomplete")
            if scenario == "partial"
            else ("role", "critical" if scenario == "critical" else "player")
        )
        con.execute(f"UPDATE stream_coverage SET {column}=?", [value])
    event(
        con,
        1000,
        "cast" if scenario == "cast" else "applybuff" if scenario == "buff" else "applydebuff",
        None if scenario == "missing-instance" else True if scenario == "boolean-instance" else 1,
        target=5 if scenario == "foreign-target" else 7,
        source=999 if scenario == "missing-caster" else 10,
        ability=8994 if scenario == "foreign-spell" else 710,
    )
    one, _ = encounter_auras(con, GARR)
    assert one.applications.value == expected
    if one.targets:
        assert one.targets[0].known_active_s.value is None
    if scenario in {"partial", "critical", "personal"}:
        assert one.transitions.level is EvidenceLevel.OBSERVED
    if scenario in {
        "missing-class",
        "invalid-class",
        "missing-caster",
        "ambiguous-class",
        "ambiguous-name",
        "boolean-instance",
    }:
        assert one.transitions.value is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("sourceID", True),
        ("sourceID", 10.5),
        ("targetID", True),
        ("targetID", 7.5),
        ("abilityGameID", True),
        ("abilityGameID", 710.5),
    ],
)
def test_control_raw_identity_coercion_cannot_certify_an_application(
    con: duckdb.DuckDBPyConnection, field: str, value: object
) -> None:
    warlock(con)
    event(con, 1000, "applydebuff", 1, target=7, source=10, ability=710)
    raw = {"sourceID": 10, "targetID": 7, "abilityGameID": 710, "targetInstance": 1, field: value}
    con.execute("UPDATE events SET raw=?", [json.dumps(raw)])
    one, _ = encounter_auras(con, GARR)
    assert one.applications.value is None and one.transitions.value is None
    assert one.targets == ()


@pytest.mark.parametrize("kind", ["death", "resurrect"])
def test_malformed_lifecycle_identity_withholds_control_windows(
    con: duckdb.DuckDBPyConnection, kind: str
) -> None:
    warlock(con)
    event(con, 1000, "applydebuff", 1, target=7, source=10, ability=710)
    event(con, 2000, kind, 1, target=7, source=10, ability=0)
    con.execute(
        "UPDATE events SET raw=? WHERE type=?",
        [json.dumps({"targetID": True, "targetInstance": 1}), kind],
    )
    one, _ = encounter_auras(con, GARR)
    assert one.applications.value == 1
    assert one.targets[0].windows.value is None


def test_cohort_control_display_identifies_a_fight_instead_of_personal_uptime(
    con: duckdb.DuckDBPyConnection,
) -> None:
    warlock(con)
    event(con, 1000, "applydebuff", 1, target=7, source=10, ability=710)
    auras = encounter_auras(con, GARR)
    view = with_strategy(
        {},
        {
            "cohort_target_aura_windows": [
                {"player": "Forand", "auras": to_data(auras)},
            ]
        },
    )
    line = view["pull_during"][0]
    assert line["text"].startswith("In Forand's fight: Encounter-wide Firesworn Banish")
    assert "assignments may differ" in line["note"]


@pytest.mark.parametrize("field,column", [("sourceID", "source_id"), ("targetID", "target_id")])
def test_coerced_identity_is_unknown_before_wrong_class_or_target_exclusion(
    con: duckdb.DuckDBPyConnection, field: str, column: str
) -> None:
    warlock(con)
    con.execute(
        "INSERT INTO actors (report_code,actor_id,type,sub_type,name) "
        "VALUES ('REPORT',1,'Player','Priest','Priest')"
    )
    event(con, 1000, "applydebuff", 1, target=7, source=10, ability=710)
    raw = {"sourceID": 10, "targetID": 7, "abilityGameID": 710, "targetInstance": 1, field: True}
    con.execute(f"UPDATE events SET {column}=1,raw=?", [json.dumps(raw)])
    one, _ = encounter_auras(con, GARR)
    assert one.applications.value is None and one.targets == ()


@pytest.mark.parametrize("target,raw_target", [(1, True), (1, 1.5), (None, None)])
def test_unresolved_lifecycle_cannot_hide_as_a_different_or_missing_actor(
    con: duckdb.DuckDBPyConnection, target: int | None, raw_target: object
) -> None:
    warlock(con)
    event(con, 1000, "applydebuff", 1, target=7, source=10, ability=710)
    event(con, 2000, "death", 1, target=7, ability=0)
    con.execute(
        "UPDATE events SET target_id=?,raw=? WHERE type='death'",
        [target, json.dumps({"targetID": raw_target, "targetInstance": 1})],
    )
    one, _ = encounter_auras(con, GARR)
    assert one.applications.value == 1
    assert one.targets[0].windows.value is None
    assert one.targets[0].windows.refs[-1].actor_id is None
    assert (
        one.targets[0].windows.refs[-1].detail
        == "lifecycle rows with unresolved recipient identities"
    )


@pytest.mark.parametrize("extra", ["application", "removal", "death", "copy"])
def test_complete_all_scope_cannot_certify_aura_rows_added_by_another_stream(
    con: duckdb.DuckDBPyConnection, extra: str
) -> None:
    event(con, 2000, "applybuff", 1, in_encounter=extra != "application")
    event(con, 6000, "removebuff", 1, in_encounter=extra != "removal")
    if extra == "death":
        event(con, 4000, "death", 1, ability=0, in_encounter=False)
    elif extra == "copy":
        con.execute(
            "INSERT INTO events SELECT * REPLACE (1 AS copy_index) FROM events "
            "WHERE type='applybuff'"
        )
    aura = next(a for a in encounter_auras(con, PF) if a.ability_id == 20619)
    assert aura.applications.value is None
    assert aura.transitions.level is EvidenceLevel.OBSERVED
    assert aura.transitions.value
    assert all(target.windows.value is None for target in aura.targets)
    assert all(target.known_active_s.value is None for target in aura.targets)


@pytest.mark.parametrize("count", [None, -1, 3])
def test_aura_bounds_require_consistent_all_occurrence_metadata(
    con: duckdb.DuckDBPyConnection, count: int | None
) -> None:
    event(con, 2000, "applybuff", 1)
    event(con, 6000, "removebuff", 1)
    con.execute("UPDATE stream_coverage SET raw_events=?", [count])
    aura = next(a for a in encounter_auras(con, PF) if a.ability_id == 20619)
    assert aura.applications.value is None
    assert aura.transitions.value == ((2.0, "applybuff", 5, 1), (6.0, "removebuff", 5, 1))
    assert aura.targets[0].windows.value is None
