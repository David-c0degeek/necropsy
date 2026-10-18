"""Source-attributed absorption is not a shield cast or healing-quality score."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.analysis.context import ParticipantFight, participant_fights
from necropsy.analysis.generic.healing import absorption_by_ability
from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import build_document
from necropsy.report.render import build_view, render_playbook, render_report
from tests.class_fixture import snapshot


@pytest.fixture
def context(tmp_path: Path) -> Iterator[tuple[duckdb.DuckDBPyConnection, ParticipantFight]]:
    ingest(
        snapshot(tmp_path, 7, "Holy", "Flash Heal", "healer", include_reference=False),
        tmp_path / "analysis.duckdb",
    )
    with duckdb.connect(str(tmp_path / "analysis.duckdb")) as con:
        con.execute("UPDATE snapshot_meta SET zone_id=2000,partition_id=1")
        con.execute(
            "UPDATE fights SET encounter_id=50663,friendly_players='[1,3]',friendly_pets='[]'"
        )
        con.execute("UPDATE benchmark_participants SET encounter_id=50663")
        con.execute("UPDATE actors SET game_id=12118 WHERE actor_id=50")
        con.execute(
            "INSERT INTO actors(report_code,actor_id,type,sub_type,name) "
            "VALUES ('REPORT1',3,'Player','Warrior','Patient')"
        )
        con.execute(
            "INSERT INTO abilities(report_code,game_id,name) VALUES "
            "('REPORT1',10901,'Power Word: Shield'),('REPORT1',26470,'Persistent Shield')"
        )
        con.execute(
            "INSERT INTO stream_coverage(report_code,fight_id,actor_id,role,direction,"
            "status,boundary_ambiguities,multiplicity_mismatches,raw_events) "
            "SELECT 'REPORT1',7,NULL,'encounter','all','complete',0,0,count(*) FROM events"
        )
        add(con, "shield", 10901, 100, 3)
        add(con, "persistent", 26470, 20, 1)
        yield con, next(p for p in participant_fights(con) if p.kind == "you")


def add(
    con: duckdb.DuckDBPyConnection,
    uid: str,
    spell: int,
    stored_amount: int,
    target: int = 1,
    copy: int = 0,
    **changes: Any,
) -> None:
    raw = (
        dict(
            type="absorbed",
            timestamp=10000,
            sourceID=1,
            targetID=target,
            abilityGameID=spell,
            amount=stored_amount,
            fight=7,
        )
        | changes
    )
    con.execute(
        "INSERT INTO events(report_code,fight_id,event_uid,copy_index,timestamp,type,"
        "source_id,target_id,ability_game_id,amount,raw) "
        "VALUES ('REPORT1',7,?,?,10000,'absorbed',1,?,?,?,?)",
        [uid, copy, target, spell, stored_amount, json.dumps(raw)],
    )
    con.execute("UPDATE stream_coverage SET raw_events=raw_events+1 WHERE role='encounter'")


def finding(context: tuple[Any, ...]) -> dict[str, Any]:
    con, pf = context
    return absorption_by_ability(con, pf, frozenset({12118}))


def test_absorption_abilities_recipients_and_review_reach_both_pages(
    context: tuple[Any, ...],
) -> None:
    con, _ = context
    result = finding(context)
    assert result["absorption"].value == 120
    assert [
        (a["ability_id"], a["absorption"].value, a["effects"].value) for a in result["abilities"]
    ] == [(10901, 100, 1), (26470, 20, 1)]
    assert result["abilities"][0]["recipients"][0]["actor_id"] == 3
    assert result["abilities"][1]["recipients"][0]["actor_id"] == 1
    assert {(c.actor_id, c.direction) for c in result["absorption"].coverage} == {
        (1, "source"),
        (None, "all"),
    }
    assert con.execute(
        "SELECT count(*) FROM events WHERE type='cast' AND ability_game_id=10901"
    ).fetchone() == (0,)
    doc = build_document(con)
    assert doc["bosses"][0]["subject"]["combat"]["metrics"]["effective_absorption"]["value"] == 120
    examples = doc["bosses"][0]["playbook"]["healing_context"]["absorption_examples"]
    assert len(examples) == 1
    for renderer in [render_report, render_playbook]:
        html = renderer(build_view(doc, "0" * 64))
        assert (
            "Power Word: Shield (10901): 100 credited absorption; 1 absorption effects, not casts."
            in html
        )
        assert "Persistent Shield (26470): 20 credited absorption;" in html
        assert "Patient (3): 100 credited absorption" in html
        assert "Agree shield priorities with your tanks and healers" in html
        assert "not prevented-damage, mana-efficiency or WCL ranking estimates" in html
    del doc["bosses"][0]["playbook"]["healing_context"]["absorption_examples"]
    for renderer in [render_report, render_playbook]:
        assert "Agree shield priorities" not in renderer(build_view(doc, "0" * 64))


@pytest.mark.parametrize(
    "mutation",
    [
        "partial-source",
        "missing-source",
        "wrong-source-role",
        "foreign-source-owner",
        "duplicate-source",
        "partial-all",
        "missing-all",
        "extra-row",
        "missing-count",
        "duplicate-player",
        "float-player",
        "missing-owner",
        "player-class",
        "owner-type",
        "duplicate-actor",
        "wrong-bounds",
        "duplicate-fight",
        "unknown-recipient",
        "outside-scope",
    ],
)
def test_uncertain_metadata_or_coverage_never_becomes_zero(
    context: tuple[Any, ...], mutation: str
) -> None:
    con, _ = context
    queries = {
        "partial-source": "UPDATE stream_coverage SET status='partial' WHERE direction='source'",
        "missing-source": "DELETE FROM stream_coverage WHERE direction='source'",
        "wrong-source-role": "UPDATE stream_coverage SET role='pet' WHERE direction='source'",
        "foreign-source-owner": (
            "UPDATE stream_coverage SET owner_actor_id=3 WHERE direction='source'"
        ),
        "duplicate-source": (
            "INSERT INTO stream_coverage SELECT * FROM stream_coverage WHERE direction='source'"
        ),
        "partial-all": "UPDATE stream_coverage SET status='partial' WHERE role='encounter'",
        "missing-all": "DELETE FROM stream_coverage WHERE role='encounter'",
        "extra-row": "UPDATE stream_coverage SET raw_events=raw_events-1 WHERE role='encounter'",
        "missing-count": "UPDATE stream_coverage SET raw_events=NULL WHERE role='encounter'",
        "duplicate-player": "UPDATE fights SET friendly_players='[1,3,3]'",
        "float-player": "UPDATE fights SET friendly_players='[1,3.0]'",
        "missing-owner": "UPDATE fights SET friendly_players='[3]'",
        "player-class": "UPDATE actors SET type='NPC' WHERE actor_id=3",
        "owner-type": "UPDATE actors SET sub_type='Shaman' WHERE actor_id=1",
        "duplicate-actor": "INSERT INTO actors SELECT * FROM actors WHERE actor_id=1",
        "wrong-bounds": "UPDATE fights SET end_time=1",
        "duplicate-fight": "INSERT INTO fights SELECT * FROM fights",
        "unknown-recipient": "UPDATE fights SET friendly_players='[1]'",
        "outside-scope": "UPDATE snapshot_meta SET partition_id=3",
    }
    con.execute(queries[mutation])
    result = finding(context)
    assert result["absorption"].value is None
    if mutation in [
        "partial-source",
        "missing-source",
        "wrong-source-role",
        "foreign-source-owner",
        "duplicate-source",
        "partial-all",
        "missing-all",
        "extra-row",
        "missing-count",
    ]:
        assert result["abilities"][0]["observations"].value == [[10000, 3, 100]]


@pytest.mark.parametrize(
    "changes",
    [
        {"type": None},
        {"type": "heal"},
        {"sourceID": None},
        {"sourceID": 1.0},
        {"sourceID": True},
        {"targetID": None},
        {"targetID": 3.0},
        {"targetID": 999},
        {"abilityGameID": True},
        {"abilityGameID": 10901.0},
        {"timestamp": 10000.0},
        {"timestamp": -1},
        {"timestamp": 999999},
        {"fight": True},
        {"amount": True},
        {"amount": -1},
        {"amount": 101},
    ],
)
def test_bad_candidate_withholds_totals_without_erasing_good_observations(
    context: tuple[Any, ...],
    changes: dict[str, Any],
) -> None:
    con, _ = context
    add(con, "bad", 10901, 100, 3, **changes)
    result = finding(context)
    assert result["absorption"].value is None
    shield = next(a for a in result["abilities"] if a["ability_id"] == 10901)
    assert shield["observations"].value == [[10000, 3, 100]]
    assert result["absorption"].refs[0].actor_id is None
    assert result["absorption"].refs[0].event_count == 1


@pytest.mark.parametrize(
    "field,rawkey",
    [
        ("type", "type"),
        ("source_id", "sourceID"),
        ("target_id", "targetID"),
        ("timestamp", "timestamp"),
        ("ability_game_id", "abilityGameID"),
        ("amount", "amount"),
    ],
)
def test_missing_both_representations_stays_unknown(
    context: tuple[Any, ...], field: str, rawkey: str
) -> None:
    con, _ = context
    payload = json.loads(
        con.execute("SELECT raw FROM events WHERE event_uid='shield'").fetchone()[0]
    )
    payload.pop(rawkey)
    con.execute(
        f"UPDATE events SET {field}=NULL,raw=? WHERE event_uid='shield'", [json.dumps(payload)]
    )
    assert finding(context)["absorption"].value is None


def test_direct_occurrences_do_not_join_duplicate_ability_names(context: tuple[Any, ...]) -> None:
    con, _ = context
    con.execute("INSERT INTO abilities SELECT * FROM abilities WHERE game_id=10901")
    result = finding(context)
    assert result["absorption"].value == 120
    assert result["abilities"][0]["name"] is None


def test_legitimate_identical_copies_remain_individual_effects(context: tuple[Any, ...]) -> None:
    con, _ = context
    add(con, "shield", 10901, 100, 3, copy=1)
    result = finding(context)
    assert result["absorption"].value == 220
    assert result["abilities"][0]["effects"].value == 2


def test_no_absorption_and_no_shield_prompt_is_a_qualified_zero(context: tuple[Any, ...]) -> None:
    con, _ = context
    con.execute("DELETE FROM events WHERE type='absorbed'")
    con.execute(
        "UPDATE stream_coverage SET raw_events=(SELECT count(*) FROM events) WHERE role='encounter'"
    )
    result = finding(context)
    assert (
        result["absorption"].value == 0 and result["abilities"] == [] and result["review"] is None
    )


def test_boss_recipient_is_separate_from_friendly_absorption(context: tuple[Any, ...]) -> None:
    con, _ = context
    add(con, "hostile", 10901, 500, 50)
    assert finding(context)["absorption"].value == 120
