"""Exact aura endpoints alongside owned effects cannot become reaction grades."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.analysis.context import ParticipantFight, participant_fights
from necropsy.analysis.encounters.effects import actor_effects, mechanic_removals
from necropsy.analysis.encounters.removal_exposure import correlations
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
        con.execute("UPDATE snapshot_meta SET zone_id=2000, partition_id=1")
        con.execute("UPDATE fights SET encounter_id=50668")
        con.execute("UPDATE benchmark_participants SET encounter_id=50668")
        con.execute(
            "INSERT INTO stream_coverage (report_code,fight_id,actor_id,role,direction,status,"
            "boundary_ambiguities,multiplicity_mismatches,raw_events) "
            "SELECT 'REPORT1',7,NULL,'encounter','all','complete',0,0,count(*) FROM events"
        )
        for kind, timestamp, ability in [
            ("applydebuff", 3000, 19659),
            ("removedebuff", 4608, 19659),
            ("dispel", 4608, 988),
        ]:
            add(con, kind, timestamp, ability)
        yield con, next(p for p in participant_fights(con) if p.kind == "you")


def add(
    con: duckdb.DuckDBPyConnection, kind: str, timestamp: int, ability: int, **raw: Any
) -> None:
    row = con.execute("SELECT count(*) FROM events").fetchone()
    assert row is not None
    count = row[0]
    payload = dict(
        type=kind, timestamp=timestamp, sourceID=1, targetID=1, abilityGameID=ability, fight=7
    )
    if kind == "dispel":
        payload.update(extraAbilityGameID=19659, isBuff=False)
    payload.update(raw)
    con.execute(
        "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,type,"
        "source_id,target_id,ability_game_id,raw) VALUES ('REPORT1',7,?,0,?,?,1,1,?,?)",
        [f"pair-{count}", timestamp, kind, ability, json.dumps(payload)],
    )
    con.execute("UPDATE stream_coverage SET raw_events=raw_events+1 WHERE role='encounter'")


def findings(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> tuple[Any, ...]:
    return correlations(con, pf, actor_effects(con, pf), mechanic_removals(con, pf))


def test_exact_pair_retains_integer_boundaries_and_both_shared_pages(
    context: tuple[Any, ...],
) -> None:
    con, pf = context
    [pair] = findings(con, pf)
    assert pair.intervals_ms.value == ((3000, 4608, 1608, 988),)
    assert {(c.actor_id, c.direction) for c in pair.intervals_ms.coverage} == {
        (1, "source"),
        (1, "target"),
        (None, "all"),
    }
    assert pair.intervals_ms.refs[0].event_count == 3
    doc = build_document(con)
    for render in (render_report, render_playbook):
        html = render(build_view(doc, "0" * 64))
        assert "recorded exposure from 3.000s to 4.608s (1.608s)" in html
        assert "Agree self-clear priorities" in html
        assert "reaction quality" in html


@pytest.mark.parametrize(
    "mutation",
    [
        "other-owner",
        "other-recipient",
        "wrong-mechanic",
        "cast",
        "offset",
        "duplicate",
        "missing-apply",
        "same-time",
        "reapply-end",
        "refresh",
        "stack",
        "death",
        "resurrect",
        "raw-target",
        "raw-time",
        "raw-fight",
        "hidden-raw-recipient",
        "partial-source",
        "partial-target",
        "partial-all",
        "extra-event",
    ],
)
def test_ambiguous_or_incomplete_pair_is_withheld(context: tuple[Any, ...], mutation: str) -> None:
    con, pf = context
    if mutation in {"partial-source", "partial-target", "partial-all"}:
        direction = mutation.removeprefix("partial-")
        con.execute("UPDATE stream_coverage SET status='partial' WHERE direction=?", [direction])
    elif mutation == "extra-event":
        con.execute("UPDATE stream_coverage SET raw_events=raw_events-1 WHERE role='encounter'")
    elif mutation in {"duplicate", "reapply-end", "refresh", "stack", "death", "resurrect"}:
        kind = {
            "duplicate": "dispel",
            "reapply-end": "applydebuff",
            "refresh": "refreshdebuff",
            "stack": "applydebuffstack",
            "death": "death",
            "resurrect": "resurrect",
        }[mutation]
        add(
            con,
            kind,
            4608 if mutation in {"duplicate", "reapply-end"} else 4000,
            988 if kind == "dispel" else 19659,
        )
    elif mutation == "missing-apply":
        con.execute("DELETE FROM events WHERE type='applydebuff'")
        con.execute("UPDATE stream_coverage SET raw_events=raw_events-1 WHERE role='encounter'")
    elif mutation == "same-time":
        con.execute(
            "UPDATE events SET timestamp=4608,raw=json_merge_patch(raw,'{\"timestamp\":4608}') "
            "WHERE type='applydebuff'"
        )
    else:
        where = "type='dispel'"
        column, value = {
            "other-owner": ("source_id", 2),
            "other-recipient": ("target_id", 2),
            "wrong-mechanic": ("raw", None),
            "cast": ("type", "cast"),
            "offset": ("timestamp", 4609),
            "raw-target": ("raw", None),
            "raw-time": ("raw", None),
            "raw-fight": ("raw", None),
            "hidden-raw-recipient": ("target_id", 2),
        }[mutation]
        if mutation.startswith("raw-") or mutation == "hidden-raw-recipient":
            where = "type='removedebuff'"
        if column == "raw":
            patch = {
                "wrong-mechanic": {"extraAbilityGameID": 19635},
                "raw-target": {"targetID": 2},
                "raw-time": {"timestamp": 4608.0},
                "raw-fight": {"fight": 8},
            }[mutation]
            con.execute(
                f"UPDATE events SET raw=json_merge_patch(raw,?) WHERE {where}", [json.dumps(patch)]
            )
        else:
            con.execute(f"UPDATE events SET {column}=? WHERE {where}", [value])
            if mutation != "hidden-raw-recipient":
                key = {
                    "source_id": "sourceID",
                    "target_id": "targetID",
                    "type": "type",
                    "timestamp": "timestamp",
                }[column]
                con.execute(
                    f"UPDATE events SET raw=json_merge_patch(raw,?) WHERE {column}=? "
                    "AND event_uid LIKE 'pair-%'",
                    [json.dumps({key: value}), value],
                )
    assert findings(con, pf) == ()
    if mutation in {
        "refresh",
        "stack",
        "death",
        "resurrect",
        "raw-target",
        "raw-time",
        "raw-fight",
        "hidden-raw-recipient",
        "partial-target",
    }:
        assert mechanic_removals(con, pf)[0].removals.value == 1


def test_feign_death_does_not_reset_explicit_exposure_pair(context: tuple[Any, ...]) -> None:
    con, pf = context
    add(con, "death", 4000, 19659, feign=True)
    assert findings(con, pf)[0].intervals_ms.value == ((3000, 4608, 1608, 988),)


def paladin(con: duckdb.DuckDBPyConnection, ability: int = 4987, recipient: int = 1) -> None:
    con.execute("UPDATE snapshot_meta SET subject_class_id=6")
    con.execute("UPDATE actors SET sub_type='Paladin' WHERE actor_id=1")
    con.execute(
        "UPDATE events SET ability_game_id=?,target_id=?,raw=json_merge_patch(raw,?) "
        "WHERE type='dispel'",
        [ability, recipient, json.dumps({"abilityGameID": ability, "targetID": recipient})],
    )


def test_paladin_cleanse_reuses_exact_pair_and_priest_keeps_its_own_spell_set(
    context: tuple[Any, ...],
) -> None:
    con, pf = context
    paladin(con)
    [removal] = mechanic_removals(con, pf)
    assert removal.removals.value == 1
    assert removal.removing_ability_ids == (4987,)
    assert findings(con, pf)[0].intervals_ms.value == ((3000, 4608, 1608, 4987),)
    con.execute("UPDATE snapshot_meta SET subject_class_id=7")
    [priest] = mechanic_removals(con, pf)
    assert priest.removals.value == 0 and priest.removing_ability_ids == (527, 988)
    assert findings(con, pf) == ()


@pytest.mark.parametrize("ability", [527, 988, 1152, 475])
def test_paladin_magic_removal_does_not_credit_priest_ranks_purify_or_decurse(
    context: tuple[Any, ...],
    ability: int,
) -> None:
    con, pf = context
    paladin(con, ability)
    assert mechanic_removals(con, pf)[0].removals.value == 0
    assert findings(con, pf) == ()


def test_paladin_removal_on_another_player_is_not_a_self_exposure_endpoint(
    context: tuple[Any, ...],
) -> None:
    con, pf = context
    paladin(con, recipient=2)
    assert mechanic_removals(con, pf)[0].removals.value == 1
    assert findings(con, pf) == ()


def _lucifron(con: duckdb.DuckDBPyConnection) -> ParticipantFight:
    """The same exact pair, on Lucifron with Impending Doom (19702)."""
    con.execute("UPDATE fights SET encounter_id=50663")
    con.execute("UPDATE benchmark_participants SET encounter_id=50663")
    con.execute(
        "UPDATE events SET ability_game_id=19702,raw=json_merge_patch(raw,?) "
        "WHERE ability_game_id=19659",
        [json.dumps({"abilityGameID": 19702})],
    )
    con.execute(
        "UPDATE events SET raw=json_merge_patch(raw,?) WHERE type='dispel'",
        [json.dumps({"extraAbilityGameID": 19702})],
    )
    return next(p for p in participant_fights(con) if p.kind == "you")


def test_lucifron_paladin_doom_policy_is_class_scoped_not_duty_scoped(
    context: tuple[Any, ...],
) -> None:
    # Removal policies select by the subject's class only, so a Protection or
    # Retribution Paladin gets the same Cleanse policy as a Holy one.
    con, _ = context
    pf = _lucifron(con)
    paladin(con)
    removals = {r.rule: r for r in mechanic_removals(con, pf)}
    assert set(removals) == {
        "lucifron-curse-removals-v1",
        "lucifron-paladin-impending-doom-removal-v1",
        "lucifron-control-removals-v1",
    }
    doom = removals["lucifron-paladin-impending-doom-removal-v1"]
    assert (doom.removals.value, doom.removing_ability_ids) == (1, (4987,))
    assert removals["lucifron-curse-removals-v1"].removals.value == 0
    assert findings(con, pf)[0].intervals_ms.value == ((3000, 4608, 1608, 4987),)


def test_lucifron_priest_keeps_the_generic_doom_policy(context: tuple[Any, ...]) -> None:
    con, _ = context
    pf = _lucifron(con)
    removals = {r.rule: r for r in mechanic_removals(con, pf)}
    assert "lucifron-paladin-impending-doom-removal-v1" not in removals
    assert removals["lucifron-doom-removals-v1"].removals.value == 1
    assert findings(con, pf) == ()  # the generic rule has no correlation
