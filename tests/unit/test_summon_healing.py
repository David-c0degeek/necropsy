"""Owned healing units remain separate and contradictions cannot certify zero."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.analysis.context import ParticipantFight, Pet, participant_fights
from necropsy.analysis.generic.summon_healing import support
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
            "UPDATE fights SET encounter_id=50663, friendly_players='[1]', "
            'friendly_pets=\'[{"id":3,"gameID":3909,"petOwner":1}]\''
        )
        con.execute("UPDATE benchmark_participants SET encounter_id=50663")
        con.execute("UPDATE actors SET game_id=12118 WHERE actor_id=50")
        con.execute(
            "INSERT INTO actors (report_code,actor_id,name,type,game_id,pet_owner) "
            "VALUES ('REPORT1',3,'zzOLDHealing Stream Totem V','Pet',3909,1)"
        )
        con.execute(
            "INSERT INTO stream_coverage (report_code,fight_id,actor_id,actor_name,"
            "owner_actor_id,role,direction,status,boundary_ambiguities,multiplicity_mismatches) "
            "VALUES ('REPORT1',7,3,'Totem',1,'pet','source','complete',0,0)"
        )
        con.execute(
            "INSERT INTO stream_coverage (report_code,fight_id,actor_id,role,direction,"
            "status,boundary_ambiguities,multiplicity_mismatches,raw_events) "
            "SELECT 'REPORT1',7,NULL,'encounter','all','complete',0,0,count(*) FROM events"
        )
        add(con, "heal", 100)
        add(con, "absorbed", 20)
        yield con, next(p for p in participant_fights(con) if p.kind == "you")


def add(con: duckdb.DuckDBPyConnection, kind: str, amount: int, target: int = 1) -> None:
    raw = dict(
        type=kind,
        timestamp=10000,
        sourceID=3,
        targetID=target,
        abilityGameID=10461,
        amount=amount,
        fight=7,
    )
    con.execute(
        "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,type,"
        "source_id,target_id,ability_game_id,amount,raw) "
        "VALUES ('REPORT1',7,?,0,10000,?,3,?,10461,?,?)",
        [f"summon-{kind}-{target}", kind, target, amount, json.dumps(raw)],
    )
    con.execute("UPDATE stream_coverage SET raw_events=raw_events+1 WHERE role='encounter'")


def finding(context: tuple[Any, ...]) -> dict[str, Any]:
    con, pf = context
    return support(con, pf, Pet(3, "zzOLDHealing Stream Totem V", 3909), frozenset({12118}))


def test_positive_support_separate_from_owner_and_damage_on_both_pages(
    context: tuple[Any, ...],
) -> None:
    con, _ = context
    result = finding(context)
    assert result["healing"].value == 100
    assert result["absorption"].value == 20
    assert result["combined_per_second"].value == 1.2
    assert {(c.actor_id, c.direction) for c in result["healing"].coverage} == {
        (3, "source"),
        (None, "all"),
    }
    before = build_document(con)
    subject = before["bosses"][0]["subject"]
    assert subject["combat"]["metrics"]["effective_healing"]["value"] == 400
    assert subject["combat"]["pets"][0]["damage"]["value"] == 0
    for render in [render_report, render_playbook]:
        html = render(build_view(before, "0" * 64))
        assert (
            "100 friendly healing; 20 credited absorption; 1.20/s separate summon support." in html
        )
        assert "not added to actor support or WCL scores" in html
    del before["bosses"][0]["playbook"]["healing_context"]["owned_summon_examples"]
    for render in [render_report, render_playbook]:
        assert "separate summon support." not in render(build_view(before, "0" * 64))


@pytest.mark.parametrize(
    "mutation",
    [
        "master-owner",
        "fight-owner",
        "game",
        "owner-type",
        "pet-type",
        "duplicate-pet",
        "duplicate-actor",
        "source-owner",
        "source-role",
        "partial-source",
        "missing-source",
        "partial-all",
        "extra-event",
        "raw-source",
        "hidden-source",
        "raw-target",
        "raw-time",
        "hidden-time",
        "raw-type",
        "hidden-type",
        "raw-fight",
        "raw-spell",
        "raw-amount",
        "negative",
        "missing-target",
        "aliased-owner",
        "aliased-roster",
        "unknown-recipient",
        "lost-source",
        "lost-type",
        "malformed-other-source",
        "malformed-type",
        "duplicate-ability",
        "negative-source",
    ],
)
def test_uncertain_support_never_becomes_complete_zero(
    context: tuple[Any, ...], mutation: str
) -> None:
    con, _ = context
    if mutation == "master-owner":
        con.execute("UPDATE actors SET pet_owner=2 WHERE actor_id=3")
    elif mutation == "fight-owner":
        con.execute('UPDATE fights SET friendly_pets=\'[{"id":3,"gameID":3909,"petOwner":2}]\'')
    elif mutation == "game":
        con.execute("UPDATE actors SET game_id=3908 WHERE actor_id=3")
    elif mutation == "owner-type":
        con.execute("UPDATE actors SET type='NPC' WHERE actor_id=1")
    elif mutation == "pet-type":
        con.execute("UPDATE actors SET type='NPC' WHERE actor_id=3")
    elif mutation == "duplicate-pet":
        con.execute(
            'UPDATE fights SET friendly_pets=\'[{"id":3,"gameID":3909,"petOwner":1},'
            '{"id":3,"gameID":3909,"petOwner":1}]\''
        )
    elif mutation == "duplicate-actor":
        con.execute("INSERT INTO actors SELECT * FROM actors WHERE actor_id=3")
    elif mutation == "duplicate-ability":
        con.execute(
            "INSERT INTO abilities (report_code,game_id,name) VALUES "
            "('REPORT1',10461,'Healing Stream'),('REPORT1',10461,'Duplicate')"
        )
    elif mutation == "source-owner":
        con.execute("UPDATE stream_coverage SET owner_actor_id=2 WHERE actor_id=3")
    elif mutation == "source-role":
        con.execute("UPDATE stream_coverage SET role='player' WHERE actor_id=3")
    elif mutation == "partial-source":
        con.execute("UPDATE stream_coverage SET status='partial' WHERE actor_id=3")
    elif mutation == "missing-source":
        con.execute("DELETE FROM stream_coverage WHERE actor_id=3")
    elif mutation == "partial-all":
        con.execute("UPDATE stream_coverage SET status='partial' WHERE role='encounter'")
    elif mutation == "extra-event":
        con.execute("UPDATE stream_coverage SET raw_events=raw_events-1 WHERE role='encounter'")
    elif mutation == "hidden-source":
        con.execute("UPDATE events SET source_id=2 WHERE event_uid='summon-heal-1'")
    elif mutation == "negative-source":
        con.execute(
            "UPDATE events SET source_id=-2,raw=json_merge_patch(raw,'{\"sourceID\":-2}') "
            "WHERE event_uid='summon-heal-1'"
        )
    elif mutation == "hidden-time":
        con.execute("UPDATE events SET timestamp=100001 WHERE event_uid='summon-heal-1'")
    elif mutation == "hidden-type":
        con.execute("UPDATE events SET type='cast' WHERE event_uid='summon-heal-1'")
    elif mutation == "lost-source":
        con.execute(
            "UPDATE events SET source_id=NULL,raw=json_merge_patch(raw,'{\"sourceID\":null}') "
            "WHERE event_uid='summon-heal-1'"
        )
    elif mutation == "lost-type":
        con.execute(
            "UPDATE events SET type=NULL,raw=json_merge_patch(raw,'{\"type\":null}') "
            "WHERE event_uid='summon-heal-1'"
        )
    elif mutation == "malformed-other-source":
        con.execute(
            'UPDATE events SET source_id=2,raw=json_merge_patch(raw,\'{"sourceID":"3"}\') '
            "WHERE event_uid='summon-heal-1'"
        )
    elif mutation == "malformed-type":
        con.execute(
            "UPDATE events SET type=NULL,raw=json_merge_patch(raw,'{\"type\":{}}') "
            "WHERE event_uid='summon-heal-1'"
        )
    elif mutation == "aliased-owner":
        con.execute('UPDATE fights SET friendly_pets=\'[{"id":3,"gameID":3909,"petOwner":1.0}]\'')
    elif mutation == "aliased-roster":
        con.execute("UPDATE fights SET friendly_players='[1.0]'")
    elif mutation == "unknown-recipient":
        add(con, "heal", 5, target=99)
    else:
        row = con.execute("SELECT raw FROM events WHERE event_uid='summon-heal-1'").fetchone()
        assert row
        raw = json.loads(row[0])
        key, value = {
            "raw-source": ("sourceID", 3.0),
            "raw-target": ("targetID", True),
            "raw-time": ("timestamp", 10000.0),
            "raw-type": ("type", "damage"),
            "raw-fight": ("fight", 8),
            "raw-spell": ("abilityGameID", 10461.0),
            "raw-amount": ("amount", None),
            "negative": ("amount", -1),
            "missing-target": ("targetID", None),
        }[mutation]
        raw[key] = value
        con.execute("UPDATE events SET raw=? WHERE event_uid='summon-heal-1'", [json.dumps(raw)])
    result = finding(context)
    assert result["healing"].value is None
    assert result["combined_per_second"].value is None


def test_boss_healing_excluded_and_other_owners_do_not_inflate_support(
    context: tuple[Any, ...],
) -> None:
    con, _ = context
    add(con, "heal", 500, target=50)
    assert finding(context)["healing"].value == 100
    con.execute(
        "UPDATE events SET source_id=1,raw=json_merge_patch(raw,'{\"sourceID\":1}') "
        "WHERE event_uid LIKE 'summon-%'"
    )
    assert finding(context)["healing"].value == 0


def test_known_unit_survives_incomplete_overall_listing_and_no_target_stream(
    context: tuple[Any, ...],
) -> None:
    con, _ = context
    con.execute(
        "INSERT INTO stream_coverage (report_code,fight_id,owner_actor_id,role,direction,status) "
        "VALUES ('REPORT1',7,1,'pet-discovery','all','missing')"
    )
    assert finding(context)["healing"].value == 100
    con.execute("UPDATE actors SET game_id=3908 WHERE actor_id=3")
    con.execute('UPDATE fights SET friendly_pets=\'[{"id":3,"gameID":3908,"petOwner":1}]\'')
    result = support(con, context[1], Pet(3, "Totem IV", 3908), frozenset({12118}))
    assert result["healing"].value == 100
