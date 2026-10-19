"""Paladin healer notes through ingest and the analysis document.

The raid remapping is deliberately synthetic and never a real-evidence receipt.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import build_document
from tests.class_fixture import snapshot

ABILITIES = {
    20216: "Divine Favor",
    1020: "Divine Shield",
    19742: "Blessing of Wisdom",
    1022: "Blessing of Protection",
}


def _paladin(
    tmp_path: Path, category: str = "Holy", role: str = "healer", **options: Any
) -> duckdb.DuckDBPyConnection:
    ability = "Flash of Light" if role == "healer" else "Judgement"
    archive = snapshot(tmp_path, 6, category, ability, role, **options)
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    con = duckdb.connect(str(db))
    con.execute("UPDATE snapshot_meta SET zone_id=2000, zone_name='Molten Core', partition_id=1")
    con.execute("UPDATE fights SET encounter_id=50668, name='Baron Geddon'")
    con.execute("UPDATE benchmark_participants SET encounter_id=50668, boss='Baron Geddon'")
    con.execute("UPDATE actors SET game_id=12056 WHERE actor_id=50")
    for game_id, name in ABILITIES.items():
        con.execute(
            "INSERT INTO abilities (report_code,game_id,name) VALUES ('REPORT1',?,?)",
            [game_id, name],
        )
    return con


def _cast(con: duckdb.DuckDBPyConnection, at_ms: int, ability: int, **raw: Any) -> None:
    start = con.execute("SELECT min(start_time) FROM fights").fetchone()
    assert start is not None
    payload = {"type": "cast", "sourceID": 1, "targetID": 1, "abilityGameID": ability, **raw}
    con.execute(
        "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,type,"
        "source_id,target_id,ability_game_id,raw) VALUES ('REPORT1',7,?,0,?,'cast',1,1,?,?)",
        [f"note-{ability}-{at_ms}", start[0] + at_ms, ability, json.dumps(payload)],
    )


def _notes(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, Any]]:
    play = build_document(con)["bosses"][0]["playbook"]
    return {note["key"]: note for note in play["class_notes"]}


def test_recorded_cooldowns_stay_observations_with_sourced_duration(tmp_path: Path) -> None:
    with _paladin(tmp_path) as con:
        _cast(con, 5000, 20216)
        _cast(con, 6000, 1020)
        notes = _notes(con)
    favor = notes["cooldown:Divine Favor"]
    assert favor["recorded_s"]["value"] == [5.0]
    assert favor["text"] == (
        "Recorded Divine Favor once. This fight is shorter than its normal cooldown; "
        "confirm its planned timing with your healing team."
    )
    assert favor["source"] == "https://www.wowhead.com/classic/spell=20216/divine-favor"
    assert notes["emergency:Divine Shield"]["text"] == (
        "Recorded Divine Shield once. Emergency cooldowns have no expected-use target."
    )


def test_long_fight_never_turns_cooldown_into_an_expected_use_count(tmp_path: Path) -> None:
    with _paladin(tmp_path) as con:
        con.execute("UPDATE fights SET end_time=start_time+300000")
        _cast(con, 5000, 20216)
        text = _notes(con)["cooldown:Divine Favor"]["text"]
    assert "Availability before and during the fight is unmeasured" in text
    assert "missed" not in text and "should" not in text


def test_zero_is_recorded_only_under_complete_cast_coverage(tmp_path: Path) -> None:
    with _paladin(tmp_path) as con:
        notes = _notes(con)
    favor = notes["cooldown:Divine Favor"]
    assert favor["recorded_s"] == {**favor["recorded_s"], "value": [], "claim": "complete"}
    assert favor["text"] == "No Divine Favor cast is recorded in this fight."
    # Unused emergency cooldowns produce no note at all.
    assert not [key for key in notes if key.startswith("emergency:")]


def test_incomplete_cast_coverage_gives_no_personal_notes(tmp_path: Path) -> None:
    # A partial source stream leaves duty unknown, so the fight is excluded from
    # the healing view instead of producing zero or unknown cooldown notes.
    with _paladin(tmp_path, partial=True) as con:
        _cast(con, 5000, 20216)
        play = build_document(con)["bosses"][0]["playbook"]
    assert play["class_notes"] == []
    assert play["excluded_subject"] is not None


def test_blessings_stay_unmeasured_and_protection_is_not_a_blessing_buff(tmp_path: Path) -> None:
    with _paladin(tmp_path) as con:
        _cast(con, 3000, 19742)
        _cast(con, 4000, 1022)
        notes = _notes(con)
    blessing = notes["pre-pull:blessing"]
    assert blessing["kind"] == "unmeasured"
    assert blessing["recorded_s"]["value"] == [3.0]
    assert blessing["text"] == (
        "Recorded 1 in-fight blessing cast. Fight-window events cannot establish pre-pull "
        "blessing coverage or assignment."
    )
    assert "emergency:Blessing of Protection" in notes


@pytest.mark.parametrize(("capacity", "expected"), [(0, True), (5000, False)])
def test_missing_mana_capacity_is_named_and_never_treated_as_zero(
    tmp_path: Path, capacity: int, expected: bool
) -> None:
    with _paladin(tmp_path) as con:
        _cast(
            con,
            5000,
            20216,
            resourceActor=1,
            classResources=[{"amount": 0 if capacity == 0 else 4000, "max": capacity, "type": 0}],
        )
        notes = _notes(con)
    assert ("resource:mana-capacity" in notes) is expected
    if expected:
        assert notes["resource:mana-capacity"]["recorded_s"]["level"] == "unknown"


@pytest.mark.parametrize(("category", "role"), [("Retribution", "dps"), ("Protection", "tank")])
def test_wrong_duty_views_have_no_healer_notes(tmp_path: Path, category: str, role: str) -> None:
    with _paladin(tmp_path, category, role) as con:
        _cast(con, 5000, 20216)
        assert build_document(con)["bosses"][0]["playbook"]["class_notes"] == []


def test_spells_are_matched_by_id_not_by_a_missing_or_duplicated_name(tmp_path: Path) -> None:
    with _paladin(tmp_path) as con:
        con.execute("DELETE FROM abilities WHERE game_id=20216")
        _cast(con, 5000, 20216)
        assert _notes(con)["cooldown:Divine Favor"]["recorded_s"]["value"] == [5.0]
        con.execute(
            "INSERT INTO abilities (report_code,game_id,name) VALUES "
            "('REPORT1',20216,'Divine Favor'),('REPORT1',20216,'Divine Favour')"
        )
        # Two conflicting name rows join to one recorded cast, which still counts once.
        assert _notes(con)["cooldown:Divine Favor"]["recorded_s"]["value"] == [5.0]


def test_a_same_named_spell_under_another_id_is_not_counted(tmp_path: Path) -> None:
    with _paladin(tmp_path) as con:
        con.execute(
            "INSERT INTO abilities (report_code,game_id,name) VALUES "
            "('REPORT1',99901,'Divine Favor'),('REPORT1',99902,'Divine Shield')"
        )
        _cast(con, 5000, 99901)
        _cast(con, 6000, 99902)
        notes = _notes(con)
    # Divine Favor has a single listed rank, so its zero stays known.
    assert notes["cooldown:Divine Favor"]["recorded_s"]["value"] == []
    # An unlisted Divine Shield rank leaves that group unresolved, never absent.
    shield = notes["emergency:Divine Shield"]
    assert shield["recorded_s"]["value"] is None
    assert shield["text"] == "Divine Shield casts are unknown: some cast identities are unresolved."


def test_an_unnamed_unlisted_cast_withholds_blessing_absence(tmp_path: Path) -> None:
    with _paladin(tmp_path) as con:
        _cast(con, 5000, 99903)
        blessing = _notes(con)["pre-pull:blessing"]
    assert blessing["recorded_s"]["value"] is None
    assert blessing["unresolved_s"] == [5.0]
    assert blessing["text"].startswith("In-fight blessing casts are unknown.")


@pytest.mark.parametrize(
    ("ability", "name"),
    [
        (1038, "Blessing of Salvation"),
        (19741, "Blessing of Might"),
        (25782, "Greater Blessing of Might"),
    ],
)
def test_an_unlisted_blessing_rank_is_kept_and_never_certified_absent(
    tmp_path: Path, ability: int, name: str
) -> None:
    with _paladin(tmp_path) as con:
        con.execute(
            "INSERT INTO abilities (report_code,game_id,name) VALUES ('REPORT1',?,?)",
            [ability, name],
        )
        _cast(con, 5000, ability)
        blessing = _notes(con)["pre-pull:blessing"]
    if ability == 25782:
        # A listed rank is counted as a recorded blessing.
        assert blessing["recorded_s"]["value"] == [5.0] and blessing["unresolved_s"] == []
        return
    assert blessing["recorded_s"]["value"] is None
    assert blessing["unresolved_s"] == [5.0]
    assert "No cast" not in blessing["text"]


@pytest.mark.parametrize(("ability", "name"), [(633, "Lay on Hands"), (5599, None)])
def test_an_unlisted_emergency_rank_is_unknown_not_absent(
    tmp_path: Path, ability: int, name: str | None
) -> None:
    with _paladin(tmp_path) as con:
        if name is not None:
            con.execute(
                "INSERT INTO abilities (report_code,game_id,name) VALUES ('REPORT1',?,?)",
                [ability, name],
            )
        _cast(con, 5000, ability)
        notes = _notes(con)
    key = "emergency:Lay on Hands"
    assert notes[key]["recorded_s"]["value"] is None and notes[key]["unresolved_s"] == [5.0]
