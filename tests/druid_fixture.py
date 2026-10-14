"""Synthetic Druid snapshots for behavior and browser tests; no real-log claims."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import build_document
from tests.snapshot_builder import BOSS, ENCOUNTER, SnapshotSpec, build, ev, page


def snapshot(tmp_path: Path, names: list[str], *, partial: bool = False) -> Path:
    abilities = {1000 + i: name for i, name in enumerate(dict.fromkeys(names))}
    ability_ids = {name: aid for aid, name in abilities.items()}
    combatant = {
        "timestamp": 0,
        "type": "combatantinfo",
        "sourceID": 1,
        "faction": 0,
        "talents": [{"id": 0}, {"id": 0}, {"id": 51}],
        "auras": [],
        "gear": [],
    }
    casts = [
        ev(1000 + i * 1500, "cast", abilityGameID=ability_ids[name]) for i, name in enumerate(names)
    ]
    heals = [
        ev(
            2000 + i * 1500,
            "heal",
            target=1,
            amount=100,
            overheal=50,
            abilityGameID=ability_ids[name],
        )
        for i, name in enumerate(names)
        if name == "Healing Touch"
    ]
    participants = [
        {
            "kind": "you",
            "boss": BOSS,
            "encounterID": ENCOUNTER,
            "leaderboardPosition": None,
            "player": "Druid",
            "server": "Realm",
            "total": 123.0,
            "duration": 100000,
            "spec": "Restoration",
        }
    ]
    return build(
        tmp_path / "druid.zip",
        SnapshotSpec(
            players={1: "Druid"},
            pets={},
            class_id=2,
            class_name="Druid",
            participants=participants,
            extra_abilities=[{"gameID": aid, "name": name} for aid, name in abilities.items()],
            streams={
                "player_1_Druid/source": [
                    page([combatant, *casts, *heals], 90000 if partial else None)
                ],
                "player_1_Druid/target": [page(heals)],
            },
        ),
    )


def document(tmp_path: Path, names: list[str], *, partial: bool = False) -> dict[str, Any]:
    archive = snapshot(tmp_path, names, partial=partial)
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db), read_only=True) as con:
        return build_document(con)
