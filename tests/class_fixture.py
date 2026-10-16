"""Small synthetic class snapshots; these are not public-log validation receipts."""

from pathlib import Path
from typing import Any

from necropsy.analysis.class_catalog import CLASS_NAMES
from tests.snapshot_builder import BOSS, ENCOUNTER, SnapshotSpec, build, ev, page

CASES = [
    (4, "Fire", "Fireball", "dps"),
    (4, "Frost", "Frostbolt", "dps"),
    (6, "Holy", "Flash of Light", "healer"),
    (6, "Protection", "Holy Shield", "tank"),
    (6, "Retribution", "Judgement", "dps"),
    (7, "Holy", "Flash Heal", "healer"),
    (7, "Shadow", "Mind Flay", "dps"),
    (8, "Assassination", "Sinister Strike", "dps"),
    (9, "Elemental", "Lightning Bolt", "dps"),
    (9, "Enhancement", "Stormstrike", "dps"),
    (9, "Restoration", "Chain Heal", "healer"),
    (10, "Destruction", "Shadow Bolt", "dps"),
    (11, "Fury", "Bloodthirst", "dps"),
    (11, "Protection", "Shield Slam", "tank"),
]


def snapshot(
    out: Path,
    class_id: int,
    category: str,
    ability: str,
    role: str,
    *,
    partial: bool = False,
    secondary_healing: bool = False,
    subject_tank_hits: bool = True,
    tree_totals: tuple[int, ...] = (0, 51, 0),
) -> Path:
    class_name = CLASS_NAMES[class_id]
    participants = []
    streams: dict[str, list[dict[str, Any] | None]] = {}
    for aid, name in ((1, "Subject"), (2, "Leader")):
        participants.append(
            {
                "kind": "you" if aid == 1 else "top",
                "boss": BOSS,
                "encounterID": ENCOUNTER,
                "leaderboardPosition": None if aid == 1 else 1,
                "player": name,
                "server": "Realm",
                "total": 1000.0,
                "duration": 100000,
                "spec": category,
            }
        )
        info = {
            "timestamp": 0,
            "type": "combatantinfo",
            "sourceID": aid,
            "faction": 0,
            "talents": [{"id": n} for n in tree_totals],
            "auras": [],
            "gear": [],
        }
        casts = [
            ev(
                1000 + i * 2000,
                "cast",
                source=aid,
                abilityGameID=1000,
                target=aid if role == "healer" else 50,
            )
            for i in range(3 + aid)
        ]
        amounts = [
            ev(
                1500 + i * 2000,
                "heal" if role == "healer" else "damage",
                source=aid,
                target=aid if role == "healer" else 50,
                amount=100,
                overheal=20,
                abilityGameID=1000,
            )
            for i in range(3 + aid)
        ]
        hits = (
            [
                ev(
                    2000 + i * 2000,
                    source=50,
                    target=aid,
                    abilityGameID=6603,
                    amount=200,
                    melee=True,
                )
                for i in range(4)
            ]
            if role == "tank" and (aid != 1 or subject_tank_hits)
            else []
        )
        secondary_casts = (
            [
                ev(12000 + i * 2000, "cast", source=aid, target=aid, abilityGameID=2000)
                for i in range(4)
            ]
            if secondary_healing and aid == 1
            else []
        )
        secondary_heals = (
            [
                ev(
                    12500 + i * 2000,
                    "heal",
                    source=aid,
                    target=aid,
                    abilityGameID=2000,
                    amount=100,
                    overheal=20,
                )
                for i in range(4)
            ]
            if secondary_healing and aid == 1
            else []
        )
        streams[f"player_{aid}_{name}/source"] = [
            page(
                [info, *casts, *amounts, *secondary_casts, *secondary_heals],
                90000 if partial and aid == 1 else None,
            )
        ]
        streams[f"player_{aid}_{name}/target"] = [
            page(hits + (amounts if role == "healer" else []) + secondary_heals)
        ]
    return build(
        out / "class.zip",
        SnapshotSpec(
            players={1: "Subject", 2: "Leader"},
            pets={},
            class_id=class_id,
            class_name=class_name,
            participants=participants,
            streams=streams,
            enemy_npcs=[50],
            extra_actors=[
                {"id": 50, "name": BOSS, "type": "NPC", "subType": "Boss", "gameID": 16028}
            ],
            extra_abilities=[
                {"gameID": 1000, "name": ability},
                {"gameID": 6603, "name": "Melee"},
                {"gameID": 2000, "name": "Flash Heal"},
            ],
        ),
    )
