"""Instance, scope and unknown-state counterexamples for hostile aura windows."""

import json
from collections.abc import Iterator

import duckdb
import pytest

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
            "boundary_ambiguities,multiplicity_mismatches) "
            "VALUES ('REPORT',1,NULL,'encounter','all','complete',0,0)"
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
