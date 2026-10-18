"""Raid context never transfers credit or hides uncertain rows behind zero."""

import json
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.analysis.context import ParticipantFight, participant_fights
from necropsy.analysis.encounters.interrupts import contexts
from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import build_document
from necropsy.report.render import build_view, render_playbook, render_report
from tests.class_fixture import snapshot


@pytest.fixture
def context(tmp_path: Path) -> Iterator[tuple[duckdb.DuckDBPyConnection, ParticipantFight]]:
    ingest(
        snapshot(tmp_path, 9, "Restoration", "Chain Heal", "healer", include_reference=False),
        tmp_path / "analysis.duckdb",
    )
    with duckdb.connect(str(tmp_path / "analysis.duckdb")) as con:
        con.execute("UPDATE snapshot_meta SET zone_id=2000, partition_id=1")
        con.execute(
            "UPDATE fights SET encounter_id=50669,friendly_players='[1,3]', "
            'enemy_npcs=\'[{"id":50,"gameID":11662,"instanceCount":4}]\''
        )
        con.execute("UPDATE benchmark_participants SET encounter_id=50669")
        con.execute("UPDATE actors SET game_id=11662 WHERE actor_id=50")
        con.execute(
            "INSERT INTO actors (report_code,actor_id,name,type,sub_type) "
            "VALUES ('REPORT1',3,'Other Shaman','Player','Shaman')"
        )
        con.execute(
            "INSERT INTO stream_coverage (report_code,fight_id,actor_id,role,direction,status,"
            "boundary_ambiguities,multiplicity_mismatches,raw_events) "
            "SELECT 'REPORT1',7,NULL,'encounter','all','complete',0,0,count(*) FROM events"
        )
        add(con)
        yield con, next(p for p in participant_fights(con) if p.kind == "you")


def add(
    con: duckdb.DuckDBPyConnection, uid: str = "interrupt", copy: int = 0, **changes: Any
) -> None:
    raw = (
        dict(
            type="interrupt",
            timestamp=10000,
            sourceID=3,
            targetID=50,
            targetInstance=3,
            abilityGameID=8042,
            extraAbilityGameID=19775,
            fight=7,
        )
        | changes
    )
    con.execute(
        "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,type,source_id,"
        "target_id,target_instance,ability_game_id,extra_ability_game_id,raw) "
        "VALUES ('REPORT1',7,?,?,10000,'interrupt',3,50,3,8042,19775,?)",
        [uid, copy, json.dumps(raw)],
    )
    con.execute("UPDATE stream_coverage SET raw_events=raw_events+1 WHERE role='encounter'")


def finding(context: tuple[Any, ...]) -> dict[str, Any]:
    con, pf = context
    return contexts(con, [pf])[0]


def test_raid_effect_separate_from_selected_player_on_both_pages(context: tuple[Any, ...]) -> None:
    con, pf = context
    result = finding(context)
    assert result["interrupts"].value == 1
    assert result["interrupts"].coverage[0].actor_id is None
    event = result["observations"][0]
    assert event.value["source_actor_id"] == 3 != pf.actor_id
    assert event.value["target_instance"] == 3
    assert event.value["elapsed_ms"] == 10000
    assert event.refs[0].actor_id == 3
    # There is deliberately no SOURCE stream for raid actor3.
    assert con.execute("SELECT count(*) FROM stream_coverage WHERE actor_id=3").fetchone() == (0,)
    document = build_document(con)
    playbook = document["bosses"][0]["playbook"]
    assert len(playbook["raid_interrupt_contexts"]) == 1
    for renderer in (render_report, render_playbook):
        html = renderer(build_view(document, "0" * 64))
        assert "Other Shaman (raid Shaman 3)" in html
        assert "not credited to the selected player or ranking category" in html
        assert "instance 3" in html
    del playbook["raid_interrupt_contexts"]
    for renderer in (render_report, render_playbook):
        assert "Raid interruption context" not in renderer(build_view(document, "0" * 64))


def test_context_dedup_and_selected_actor_does_not_transfer_credit(
    context: tuple[Any, ...],
) -> None:
    con, pf = context
    assert contexts(con, [pf, pf, replace(pf, actor_id=3, player="Other Shaman")]) == [
        finding(context)
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        "partial-all",
        "missing-all",
        "critical-only",
        "extra-row",
        "missing-count",
        "duplicate-actor",
        "missing-caster",
        "unknown-class",
        "unknown-other-class",
        "duplicate-player",
        "float-player",
        "missing-selected",
        "missing-enemy",
        "wrong-npc",
        "duplicate-enemy",
        "float-enemy",
        "float-count",
        "zero-count",
        "duplicate-fight",
        "duplicate-report",
        "wrong-bounds",
        "missing-revision",
    ],
)
def test_uncertain_scope_never_certifies_count(context: tuple[Any, ...], mutation: str) -> None:
    con, pf = context
    queries = {
        "partial-all": "UPDATE stream_coverage SET status='partial' WHERE role='encounter'",
        "missing-all": "DELETE FROM stream_coverage WHERE role='encounter'",
        "critical-only": "UPDATE stream_coverage SET role='critical' WHERE role='encounter'",
        "extra-row": "UPDATE stream_coverage SET raw_events=raw_events-1 WHERE role='encounter'",
        "missing-count": "UPDATE stream_coverage SET raw_events=NULL WHERE role='encounter'",
        "duplicate-actor": "INSERT INTO actors SELECT * FROM actors WHERE actor_id=3",
        "missing-caster": "DELETE FROM actors WHERE actor_id=3",
        "unknown-class": "UPDATE actors SET sub_type=NULL WHERE actor_id=3",
        "unknown-other-class": "UPDATE actors SET sub_type='Unknown' WHERE actor_id=1",
        "duplicate-player": "UPDATE fights SET friendly_players='[1,3,3]'",
        "float-player": "UPDATE fights SET friendly_players='[1,3.0]'",
        "missing-selected": "UPDATE fights SET friendly_players='[3]'",
        "missing-enemy": "UPDATE fights SET enemy_npcs='[]'",
        "wrong-npc": "UPDATE actors SET game_id=123 WHERE actor_id=50",
        "duplicate-enemy": (
            'UPDATE fights SET enemy_npcs=\'[{"id":50,"gameID":11662,"instanceCount":4},'
            '{"id":50,"gameID":11662,"instanceCount":4}]\''
        ),
        "float-enemy": (
            'UPDATE fights SET enemy_npcs=\'[{"id":50.0,"gameID":11662,"instanceCount":4}]\''
        ),
        "float-count": (
            'UPDATE fights SET enemy_npcs=\'[{"id":50,"gameID":11662,"instanceCount":4.0}]\''
        ),
        "zero-count": (
            'UPDATE fights SET enemy_npcs=\'[{"id":50,"gameID":11662,"instanceCount":0}]\''
        ),
        "duplicate-fight": "INSERT INTO fights SELECT * FROM fights",
        "duplicate-report": "INSERT INTO reports SELECT * FROM reports",
        "wrong-bounds": "UPDATE fights SET end_time=1",
        "missing-revision": "UPDATE reports SET revision=NULL",
    }
    con.execute(queries[mutation])
    assert contexts(con, [pf])[0]["interrupts"].value is None


@pytest.mark.parametrize(
    "changes",
    [
        {"sourceID": 3.0},
        {"sourceID": True},
        {"sourceID": None},
        {"sourceID": 4},
        {"targetID": 50.0},
        {"targetID": None},
        {"targetID": 1},
        {"type": "cast"},
        {"type": None},
        {"timestamp": 10000.0},
        {"timestamp": -1},
        {"timestamp": 999999},
        {"fight": 7.0},
        {"fight": 8},
        {"abilityGameID": True},
        {"extraAbilityGameID": 19775.0},
        {"targetInstance": 5},
        {"targetInstance": 3.0},
    ],
)
def test_bad_row_withholds_total_but_retains_other_positive(
    context: tuple[Any, ...],
    changes: dict[str, Any],
) -> None:
    con, _ = context
    add(con, "unresolved", **changes)
    result = finding(context)
    assert result["interrupts"].value is None
    assert len(result["observations"]) == 1
    assert result["interrupts"].refs[0].actor_id is None
    assert result["interrupts"].refs[0].event_count == 1


@pytest.mark.parametrize(
    "field",
    [
        "source_id",
        "target_id",
        "type",
        "timestamp",
        "extra_ability_game_id",
        "ability_game_id",
        "target_instance",
    ],
)
def test_missing_both_representations_cannot_hide_candidate(
    context: tuple[Any, ...],
    field: str,
) -> None:
    con, _ = context
    rawkey = {
        "source_id": "sourceID",
        "target_id": "targetID",
        "type": "type",
        "timestamp": "timestamp",
        "extra_ability_game_id": "extraAbilityGameID",
        "ability_game_id": "abilityGameID",
        "target_instance": "targetInstance",
    }[field]
    raw = json.loads(
        con.execute("SELECT raw FROM events WHERE event_uid='interrupt'").fetchone()[0]
    )
    raw.pop(rawkey)
    con.execute(
        f"UPDATE events SET {field}=NULL,raw=? WHERE event_uid='interrupt'", [json.dumps(raw)]
    )
    result = finding(context)
    if field == "target_instance":
        assert result["interrupts"].value == 1
        assert result["observations"][0].value["target_instance"] is None
    else:
        assert result["interrupts"].value is None


def test_complete_zero_is_raid_observation_not_nonuse(context: tuple[Any, ...]) -> None:
    con, _ = context
    con.execute("UPDATE actors SET sub_type='Rogue' WHERE actor_id=3")
    assert finding(context)["interrupts"].value == 0
    document = build_document(con)
    for renderer in (render_report, render_playbook):
        assert "No matching raid-roster Shaman interruptions recorded in this fight." in renderer(
            build_view(document, "0" * 64)
        )


def test_multiplicity_and_ability_metadata_do_not_change_observed_effects(
    context: tuple[Any, ...],
) -> None:
    con, _ = context
    add(con, copy=1)
    con.execute("INSERT INTO abilities SELECT * FROM abilities")
    assert finding(context)["interrupts"].value == 2


def test_missing_relevant_npc_binding_withholds_total(context: tuple[Any, ...]) -> None:
    con, _ = context
    con.execute(
        "INSERT INTO actors (report_code,actor_id,type,game_id) VALUES ('REPORT1',51,'NPC',11662)"
    )
    add(con, "missing-priest", targetID=51)
    con.execute("UPDATE events SET target_id=51 WHERE event_uid='missing-priest'")
    assert finding(context)["interrupts"].value is None
    assert len(finding(context)["observations"]) == 1


def test_partial_scope_preserves_positive_without_certifying_total(
    context: tuple[Any, ...],
) -> None:
    con, _ = context
    con.execute("UPDATE stream_coverage SET status='partial' WHERE role='encounter'")
    assert finding(context)["interrupts"].value is None
    assert len(finding(context)["observations"]) == 1


def test_nonshaman_report_build_preserves_optional_field_absence(tmp_path: Path) -> None:
    ingest(
        snapshot(tmp_path, 7, "Holy", "Flash Heal", "healer", include_reference=False),
        tmp_path / "analysis.duckdb",
    )
    with duckdb.connect(str(tmp_path / "analysis.duckdb")) as con:
        con.execute("UPDATE snapshot_meta SET zone_id=2000, partition_id=1")
        con.execute("UPDATE fights SET encounter_id=50669")
        con.execute("UPDATE benchmark_participants SET encounter_id=50669")
        assert "raid_interrupt_contexts" not in build_document(con)["bosses"][0]["playbook"]


@pytest.mark.parametrize(
    "class_id,zone,partition,encounter",
    [
        (6, 2000, 1, 50669),
        (5, 2000, 1, 50669),
        (9, 2000, 3, 50669),
        (9, 2002, 1, 50669),
        (9, 2000, 1, 50668),
    ],
)
def test_scope_is_explicit(
    context: tuple[Any, ...], class_id: int, zone: int, partition: int, encounter: int
) -> None:
    con, pf = context
    con.execute(
        "UPDATE snapshot_meta SET subject_class_id=?,zone_id=?,partition_id=?",
        [class_id, zone, partition],
    )
    assert contexts(con, [replace(pf, encounter_id=encounter)]) == []
