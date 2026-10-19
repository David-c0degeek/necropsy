"""Control application evidence keeps casts, coverage and NPC instances distinct."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.analysis.context import ParticipantFight, participant_fights
from necropsy.analysis.encounters.control import applications, curse_applications
from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import build_document
from necropsy.report.render import build_view, render_playbook, render_report
from tests.class_fixture import snapshot

ROSTER = [{"id": 50, "gameID": 12099, "instanceCount": 8}]


@pytest.fixture
def context(tmp_path: Path) -> Iterator[tuple[duckdb.DuckDBPyConnection, ParticipantFight]]:
    ingest(
        snapshot(tmp_path, 10, "Destruction", "Shadow Bolt", "dps"),
        tmp_path / "analysis.duckdb",
    )
    with duckdb.connect(str(tmp_path / "analysis.duckdb")) as con:
        con.execute("UPDATE snapshot_meta SET zone_id=2000, partition_id=1")
        con.execute("UPDATE fights SET encounter_id=50666, enemy_npcs=?", [json.dumps(ROSTER)])
        con.execute("UPDATE benchmark_participants SET encounter_id=50666")
        con.execute("UPDATE actors SET game_id=12099, name='Firesworn' WHERE actor_id=50")
        con.execute(
            "INSERT INTO abilities(report_code,game_id,name) VALUES "
            "('REPORT1',710,'Banish'),('REPORT1',18647,'Banish')"
        )
        con.execute(
            "INSERT INTO stream_coverage(report_code,fight_id,actor_id,role,direction,"
            "status,boundary_ambiguities,multiplicity_mismatches,raw_events) "
            "SELECT 'REPORT1',7,NULL,'encounter','all','complete',0,0,count(*) FROM events"
        )
        yield con, next(p for p in participant_fights(con) if p.kind == "you")


def add(
    con: duckdb.DuckDBPyConnection,
    uid: str,
    timestamp: int,
    spell: int,
    instance: int | None,
    *,
    copy: int = 0,
    kind: str = "applydebuff",
    source: int = 1,
    target: int = 50,
    stored: dict[str, Any] | None = None,
    counted: bool = True,
    **changes: Any,
) -> None:
    raw = (
        dict(
            type=kind,
            timestamp=timestamp,
            sourceID=source,
            targetID=target,
            abilityGameID=spell,
            fight=7,
        )
        | ({} if instance is None else {"targetInstance": instance})
        | changes
    )
    row = dict(
        timestamp=timestamp,
        type=kind,
        source_id=source,
        target_id=target,
        target_instance=instance,
        ability_game_id=spell,
    ) | (stored or {})
    con.execute(
        "INSERT INTO events(report_code,fight_id,event_uid,copy_index,timestamp,type,source_id,"
        "target_id,target_instance,ability_game_id,raw) VALUES ('REPORT1',7,?,?,?,?,?,?,?,?,?)",
        [uid, copy, *row.values(), raw if isinstance(raw, str) else json.dumps(raw)],
    )
    if counted:
        con.execute("UPDATE stream_coverage SET raw_events=raw_events+1 WHERE role='encounter'")


def pair(con: duckdb.DuckDBPyConnection, **changes: Any) -> None:
    add(con, "banish-1", 5000, 710, 1, **changes)
    add(con, "banish-2", 6000, 18647, 2)


def result(context: tuple[Any, ...]) -> Any:
    con, pf = context
    (control,) = applications(con, pf)
    return control


def test_owned_applications_count_with_event_set_proof_and_review(
    context: tuple[Any, ...],
) -> None:
    con, _ = context
    pair(con)
    control = result(context)
    assert control.applications.value == 2
    assert control.observations.value == ((5, 50, 1, 710), (6, 50, 2, 18647))
    assert {(c.actor_id, c.direction) for c in control.applications.coverage} == {
        (1, "source"),
        (None, "all"),
    }
    assert [r["text"] for r in control.review] == [
        "Recorded Banish on Firesworn 50, instance 1, at 5.00s. Confirm whether you should "
        "maintain control on this add and who provides backup when it ends before copying a "
        "damage reference opener.",
        "Recorded Banish on Firesworn 50, instance 2, at 6.00s. Confirm whether you should "
        "maintain control on this add and who provides backup when it ends before copying a "
        "damage reference opener.",
    ]
    assert "uptime" in control.limitation and "not a failed duty" in control.limitation
    (saved,) = build_document(con)["bosses"][0]["playbook"]["control_applications"]
    assert saved["applications"]["value"] == 2
    assert [r["target_instance"] for r in saved["review"]] == [1, 2]


@pytest.mark.parametrize(
    "case",
    ["cast", "other-source", "other-spell", "other-npc", "player-recipient"],
)
def test_typed_unrelated_rows_are_excluded_to_a_known_zero(
    context: tuple[Any, ...], case: str
) -> None:
    con, _ = context
    if case == "other-npc":
        con.execute(
            "UPDATE fights SET enemy_npcs=?",
            [json.dumps([*ROSTER, {"id": 51, "gameID": 12057, "instanceCount": 1}])],
        )
        con.execute(
            "INSERT INTO actors(report_code,actor_id,type,game_id,name) "
            "VALUES ('REPORT1',51,'NPC',12057,'Flamewaker')"
        )
    add(
        con,
        "row",
        5000,
        8994 if case == "other-spell" else 710,
        1,
        kind="cast" if case == "cast" else "applydebuff",
        source=2 if case == "other-source" else 1,
        target={"other-npc": 51, "player-recipient": 1}.get(case, 50),
    )
    control = result(context)
    assert control.applications.value == 0
    assert control.observations.value == ()
    assert control.review == ()


@pytest.mark.parametrize(
    "case",
    [
        "no-all-scope",
        "extra-identity-outside-all",
        "foreign-source-binding",
        "raw-not-object",
        "missing-raw-type",
        "source-contradiction",
        "time-contradiction",
        "out-of-fight",
        "instance-present-vs-missing",
        "instance-out-of-range",
        "firesworn-outside-roster",
        "duplicate-identity",
    ],
)
def test_unresolved_or_unproven_rows_keep_positives_but_withhold_count(
    context: tuple[Any, ...], case: str
) -> None:
    con, _ = context
    if case == "no-all-scope":
        con.execute("DELETE FROM stream_coverage WHERE role='encounter'")
        pair(con)
    elif case == "extra-identity-outside-all":
        pair(con)
        # A disjoint owned identity absent from All has no overlapping key to mismatch.
        add(con, "banish-3", 7000, 710, 3, counted=False)
    elif case == "foreign-source-binding":
        con.execute(
            "UPDATE stream_coverage SET owner_actor_id=2 WHERE actor_id=1 AND direction='source'"
        )
        pair(con)
    elif case == "raw-not-object":
        pair(con)
        add(con, "broken", 7000, 710, 3, type="x")
        con.execute("UPDATE events SET raw='[]' WHERE event_uid='broken'")
    elif case == "missing-raw-type":
        pair(con, type=None)
    elif case == "source-contradiction":
        pair(con, stored={"source_id": 9})
    elif case == "time-contradiction":
        pair(con, stored={"timestamp": 5001})
    elif case == "out-of-fight":
        pair(con)
        add(con, "late", 10**12, 710, 3)
    elif case == "instance-present-vs-missing":
        pair(con, stored={"target_instance": None})
    elif case == "instance-out-of-range":
        pair(con)
        add(con, "nine", 7000, 710, 9)
    elif case == "firesworn-outside-roster":
        con.execute(
            "INSERT INTO actors(report_code,actor_id,type,game_id,name) "
            "VALUES ('REPORT1',52,'NPC',12099,'Firesworn')"
        )
        pair(con)
        add(con, "outside", 7000, 710, 1, target=52)
    elif case == "duplicate-identity":
        pair(con)
        add(con, "banish-2", 6000, 18647, 2)
    control = result(context)
    assert control.applications.value is None
    both = ((5, 50, 1, 710), (6, 50, 2, 18647))
    expected = {
        "missing-raw-type": both[1:],
        "source-contradiction": both[1:],
        "time-contradiction": both[1:],
        "instance-present-vs-missing": both[1:],
        "extra-identity-outside-all": (*both, (7, 50, 3, 710)),
    }.get(case, both)
    assert control.observations.value == expected
    assert [r["target_instance"] for r in control.review] == [o[2] for o in expected]


def test_absent_instance_keeps_observation_without_instance_prompt(
    context: tuple[Any, ...],
) -> None:
    con, _ = context
    add(con, "plain", 5000, 710, None)
    control = result(context)
    assert control.applications.value == 1
    assert control.observations.value == ((5, 50, None, 710),)
    assert control.review == ()


def test_legitimate_copies_count_separately(context: tuple[Any, ...]) -> None:
    con, _ = context
    pair(con)
    add(con, "banish-2", 6000, 18647, 2, copy=1)
    assert result(context).applications.value == 3


def test_missing_control_roster_withholds_zero(context: tuple[Any, ...]) -> None:
    con, _ = context
    con.execute("UPDATE fights SET enemy_npcs='[]'")
    control = result(context)
    assert control.applications.value is None
    assert control.observations.value is None
    assert control.review == ()


def test_policy_scope_is_class_partition_and_zone(context: tuple[Any, ...]) -> None:
    con, pf = context
    con.execute("UPDATE snapshot_meta SET subject_class_id=7")
    assert applications(con, pf) == ()
    con.execute("UPDATE snapshot_meta SET subject_class_id=10,partition_id=3")
    assert applications(con, pf) == ()
    con.execute("UPDATE snapshot_meta SET partition_id=1,zone_id=2006")
    assert applications(con, pf) == ()


@pytest.mark.parametrize("positive", [True, False])
def test_unbound_relevant_npc_withholds_count_even_with_bound_target(
    context: tuple[Any, ...], positive: bool
) -> None:
    con, _ = context
    con.execute(
        "INSERT INTO actors(report_code,actor_id,type,game_id,name) "
        "VALUES ('REPORT1',52,'NPC',12099,'Firesworn')"
    )
    if positive:
        pair(con)
    control = result(context)
    assert control.applications.value is None
    assert "roster binding" in control.applications.note
    if positive:
        assert control.observations.value == ((5, 50, 1, 710), (6, 50, 2, 18647))
        assert len(control.review) == 2
    else:
        assert control.observations.value is None
        assert control.review == ()


def test_reapplication_on_one_add_instance_prompts_once(context: tuple[Any, ...]) -> None:
    con, _ = context
    add(con, "first", 5000, 710, 3)
    add(con, "again", 9000, 18647, 3)
    control = result(context)
    assert control.applications.value == 2
    assert control.observations.value == ((5, 50, 3, 710), (9, 50, 3, 18647))
    assert [(r["target_instance"], r["elapsed_s"]) for r in control.review] == [(3, 5)]


@pytest.mark.parametrize("trusted", [True, False])
def test_saved_review_reaches_both_pages_without_reconstruction(
    context: tuple[Any, ...], trusted: bool
) -> None:
    con, _ = context
    pair(con)
    if not trusted:
        con.execute("UPDATE stream_coverage SET status='partial' WHERE role='encounter'")
    doc = build_document(con)
    (saved,) = doc["bosses"][0]["playbook"]["control_applications"]
    assert saved["applications"]["value"] == (2 if trusted else None)
    prompts = saved["review"]
    assert len(prompts) == 2
    for renderer in (render_report, render_playbook):
        html = renderer(build_view(doc, "0" * 64))
        for prompt in prompts:
            assert prompt["text"] in html
            assert prompt["limitation"] in html
        if not trusted:
            assert "Recorded Firesworn Banish applications: Unknown." in html
    # Rendering an older saved document must not reconstruct advice from observations.
    del saved["review"]
    for renderer in (render_report, render_playbook):
        html = renderer(build_view(doc, "0" * 64))
        assert "Confirm whether you should maintain control on this add" not in html
        assert "Firesworn Banish applied; target instance 1." in html


@pytest.mark.parametrize("trusted", [True, False])
def test_no_positive_control_does_not_render_maintenance_advice(
    context: tuple[Any, ...], trusted: bool
) -> None:
    con, _ = context
    if not trusted:
        con.execute("DELETE FROM stream_coverage WHERE role='encounter'")
    doc = build_document(con)
    (saved,) = doc["bosses"][0]["playbook"]["control_applications"]
    assert saved["applications"]["value"] == (0 if trusted else None)
    assert saved["review"] == []
    for renderer in (render_report, render_playbook):
        html = renderer(build_view(doc, "0" * 64))
        assert "Confirm whether you should maintain control on this add" not in html


def curse(con: duckdb.DuckDBPyConnection, uid: str, timestamp: int, spell: int, **kw: Any) -> None:
    add(con, uid, timestamp, spell, kw.pop("instance", None), **kw)


@pytest.fixture
def garr(context: tuple[Any, ...]) -> tuple[Any, ...]:
    con, _ = context
    con.execute(
        "UPDATE fights SET enemy_npcs=?",
        [json.dumps([*ROSTER, {"id": 51, "gameID": 12057, "instanceCount": 1}])],
    )
    con.execute(
        "INSERT INTO actors(report_code,actor_id,type,game_id,name) "
        "VALUES ('REPORT1',51,'NPC',12057,'Garr')"
    )
    con.execute(
        "INSERT INTO abilities(report_code,game_id,name) VALUES "
        "('REPORT1',17937,'Curse of Shadow'),('REPORT1',11717,'Curse of Recklessness')"
    )
    return context


def curses_of(context: tuple[Any, ...]) -> Any:
    con, pf = context
    (found,) = curse_applications(con, pf)
    return found


def test_owned_curses_count_observe_and_prompt_once_per_spell_and_target(
    garr: tuple[Any, ...],
) -> None:
    con, _ = garr
    curse(con, "shadow", 2000, 17937, target=51)
    curse(con, "again", 9000, 17937, target=51)
    curse(con, "reckless", 4000, 11717, target=51)
    curse(con, "add", 5000, 17937, target=50, instance=3)
    found = curses_of(garr)
    assert found.applications.value == 4
    assert found.observations.value == (
        (2, 51, None, 17937),
        (4, 51, None, 11717),
        (5, 50, 3, 17937),
        (9, 51, None, 17937),
    )
    assert [r["text"] for r in found.review] == [
        "Recorded Curse of Shadow on Garr 51, instance unrecorded, at 2.00s. Confirm which "
        "curse your raid assigned you before copying a reference curse choice.",
        "Recorded Curse of Recklessness on Garr 51, instance unrecorded, at 4.00s. Confirm "
        "which curse your raid assigned you before copying a reference curse choice.",
        "Recorded Curse of Shadow on Firesworn 50, instance 3, at 5.00s. Confirm which curse "
        "your raid assigned you before copying a reference curse choice.",
    ]
    assert "another Warlock's curse is not yours" in found.limitation
    assert "not an assignment" in found.review[0]["limitation"]
    # Curses are not control: the control policy excludes them to a known zero.
    (controls,) = applications(con, garr[1])
    assert controls.applications.value == 0 and controls.review == ()
    playbook = build_document(con)["bosses"][0]["playbook"]
    assert playbook["curse_applications"][0]["applications"]["value"] == 4
    assert playbook["control_applications"][0]["applications"]["value"] == 0


def test_curse_zero_and_unproven_totals(garr: tuple[Any, ...]) -> None:
    con, _ = garr
    found = curses_of(garr)
    assert found.applications.value == 0 and found.review == ()
    con.execute("DELETE FROM stream_coverage WHERE role='encounter'")
    assert curses_of(garr).applications.value is None
    curse(con, "shadow", 2000, 17937, target=51)
    found = curses_of(garr)
    assert found.applications.value is None
    assert found.observations.value == ((2, 51, None, 17937),)
    assert len(found.review) == 1


def test_other_warlock_curse_is_not_owned(garr: tuple[Any, ...]) -> None:
    con, _ = garr
    curse(con, "theirs", 2000, 17937, target=51, source=2)
    found = curses_of(garr)
    assert found.applications.value == 0 and found.review == ()


def test_curse_policy_requires_warlock_and_garr(garr: tuple[Any, ...]) -> None:
    con, pf = garr
    con.execute("UPDATE snapshot_meta SET subject_class_id=7")
    assert curse_applications(con, pf) == ()


@pytest.mark.parametrize("trusted", [True, False])
def test_saved_curse_review_and_identity_reach_both_pages(
    garr: tuple[Any, ...], trusted: bool
) -> None:
    con, _ = garr
    curse(con, "shadow", 2000, 17937, target=51)
    curse(con, "add", 5000, 17937, target=50, instance=3)
    curse(con, "again", 9000, 17937, target=50, instance=3)
    if not trusted:
        con.execute("DELETE FROM stream_coverage WHERE role='encounter'")
    doc = build_document(con)
    playbook = doc["bosses"][0]["playbook"]
    (saved,) = playbook["curse_applications"]
    assert saved["applications"]["value"] == (3 if trusted else None)
    assert len(saved["review"]) == 2
    for renderer in (render_report, render_playbook):
        html = renderer(build_view(doc, "0" * 64))
        assert (
            "Recorded Garr Recklessness/Elements/Shadow curse applications: "
            f"{3 if trusted else 'Unknown'}." in html
        )
        assert "2.00s · Curse ability 17937 applied; target actor 51, instance unrecorded." in html
        assert "5.00s · Curse ability 17937 applied; target actor 50, instance 3." in html
        assert "9.00s · Curse ability 17937 applied; target actor 50, instance 3." in html
        for prompt in saved["review"]:
            assert html.count(prompt["text"]) == 1
            assert prompt["limitation"] in html
    # Old documents and missing saved review never acquire inferred advice.
    del saved["review"]
    for renderer in (render_report, render_playbook):
        html = renderer(build_view(doc, "0" * 64))
        assert "Confirm which curse your raid assigned you" not in html
        assert "target actor 50, instance 3." in html
    del playbook["curse_applications"]
    for renderer in (render_report, render_playbook):
        html = renderer(build_view(doc, "0" * 64))
        assert "Recorded Garr Recklessness/Elements/Shadow curse applications" not in html
        assert "Curse ability 17937 applied" not in html
        assert "Recorded Firesworn Banish applications" in html


@pytest.mark.parametrize("trusted", [True, False])
def test_no_owned_curse_observation_supplies_no_assignment_prompt(
    garr: tuple[Any, ...], trusted: bool
) -> None:
    con, _ = garr
    curse(con, "theirs", 2000, 17937, target=51, source=2)
    if not trusted:
        con.execute("DELETE FROM stream_coverage WHERE role='encounter'")
    doc = build_document(con)
    (saved,) = doc["bosses"][0]["playbook"]["curse_applications"]
    assert saved["applications"]["value"] == (0 if trusted else None)
    for renderer in (render_report, render_playbook):
        html = renderer(build_view(doc, "0" * 64))
        assert (
            "Recorded Garr Recklessness/Elements/Shadow curse applications: "
            f"{0 if trusted else 'Unknown'}." in html
        )
        assert "Curse ability 17937 applied" not in html
        assert "Confirm which curse your raid assigned you" not in html
