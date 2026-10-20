"""Holy Priest and Restoration Shaman class notes: sourced cooldowns stay
observations, spells match by numeric ID whatever the report names them, and an
unlisted rank stays unknown instead of absent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import build_document
from tests.class_fixture import snapshot


def _healer(
    tmp_path: Path, class_id: int, category: str, ability: str, names: dict[int, str]
) -> duckdb.DuckDBPyConnection:
    archive = snapshot(tmp_path, class_id, category, ability, "healer")
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    con = duckdb.connect(str(db))
    con.execute("UPDATE snapshot_meta SET zone_id=2000, zone_name='Molten Core', partition_id=1")
    con.execute("UPDATE fights SET encounter_id=50668, name='Baron Geddon'")
    con.execute("UPDATE benchmark_participants SET encounter_id=50668, boss='Baron Geddon'")
    con.execute("UPDATE actors SET game_id=12056 WHERE actor_id=50")
    for game_id, name in names.items():
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


def test_priest_cooldowns_match_by_id_under_the_reports_own_names(tmp_path: Path) -> None:
    names = {14751: "Chakra", 10060: "Power Infusion", 19243: "Desperate Prayer"}
    with _healer(tmp_path, 7, "Holy", "Flash Heal", names) as con:
        _cast(con, 4000, 14751)
        _cast(con, 9000, 19243)
        notes = _notes(con)
    focus = notes["cooldown:Inner Focus"]
    assert focus["recorded_s"]["value"] == [4.0]
    assert focus["source"] == "https://www.wowhead.com/classic/spell=14751"
    assert "confirm its planned timing" in focus["text"]
    assert notes["cooldown:Power Infusion"]["text"] == (
        "No Power Infusion cast is recorded in this fight."
    )
    assert notes["emergency:Desperate Prayer"]["text"] == (
        "Recorded Desperate Prayer once. Emergency cooldowns have no expected-use target."
    )


def test_an_unlisted_desperate_prayer_rank_is_unknown_not_absent(tmp_path: Path) -> None:
    with _healer(tmp_path, 7, "Holy", "Flash Heal", {19242: "Desperate Prayer"}) as con:
        _cast(con, 5000, 19242)
        notes = _notes(con)
    prayer = notes["emergency:Desperate Prayer"]
    assert prayer["recorded_s"]["value"] is None and prayer["unresolved_s"] == [5.0]


def test_shaman_cooldowns_cover_every_mana_tide_rank_and_the_renamed_swiftness(
    tmp_path: Path,
) -> None:
    names = {16188: "Ancestral Swiftness", 16190: "Mana Tide Totem"}
    with _healer(tmp_path, 9, "Restoration", "Chain Heal", names) as con:
        _cast(con, 3000, 16188)
        _cast(con, 7000, 16190)
        notes = _notes(con)
    assert notes["cooldown:Nature's Swiftness"]["recorded_s"]["value"] == [3.0]
    tide = notes["cooldown:Mana Tide Totem"]
    assert tide["recorded_s"]["value"] == [7.0]
    assert "shorter than its normal cooldown" in tide["text"]
    assert not [key for key in notes if key.startswith("emergency:")]


def test_without_casts_the_notes_record_absence_only_under_complete_coverage(
    tmp_path: Path,
) -> None:
    with _healer(tmp_path, 9, "Restoration", "Chain Heal", {}) as con:
        notes = _notes(con)
    swiftness = notes["cooldown:Nature's Swiftness"]
    assert swiftness["recorded_s"]["value"] == [] and swiftness["recorded_s"]["claim"] == "complete"
    assert swiftness["text"] == "No Nature's Swiftness cast is recorded in this fight."
