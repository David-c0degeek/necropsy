"""Builds small synthetic v0 snapshot archives for tests."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPORT = "REPORT1"
FIGHT = 7
BOSS = "Patchwerk"
ENCOUNTER = 51118


def ev(
    ts: int, kind: str = "damage", source: int = 1, target: int = 50, **extra: Any
) -> dict[str, Any]:
    return {
        "timestamp": ts,
        "type": kind,
        "sourceID": source,
        "targetID": target,
        "abilityGameID": 75,
        "fight": FIGHT,
        "amount": 100,
        **extra,
    }


@dataclass
class SnapshotSpec:
    """Members of a synthetic export. Streams map member-dir/direction to pages."""

    players: dict[int, str] = field(default_factory=lambda: {1: "Hunter"})
    pets: dict[int, dict[int, str]] = field(default_factory=lambda: {1: {2: "Cat"}})
    streams: dict[str, list[dict[str, Any] | None]] = field(default_factory=dict)
    with_pets_json: bool = True
    errors: list[dict[str, Any]] = field(default_factory=list)
    participants: list[dict[str, Any]] | None = None
    subset: dict[str, Any] | None = None
    extra_members: dict[str, bytes] = field(default_factory=dict)


def page(events: list[dict[str, Any]], next_ts: float | None = None) -> dict[str, Any]:
    return {"data": events, "nextPageTimestamp": next_ts}


def _participants(spec: SnapshotSpec) -> list[dict[str, Any]]:
    if spec.participants is not None:
        return spec.participants
    return [
        {
            "kind": "top",
            "boss": BOSS,
            "encounterID": ENCOUNTER,
            "leaderboardPosition": i + 1,
            "player": name,
            "server": {"id": 1, "name": "Realm", "region": "EU"},
            "total": 1000.0,
            "duration": 100000,
            "spec": "Marksmanship",
        }
        for i, name in enumerate(spec.players.values())
    ]


def build(path: Path, spec: SnapshotSpec) -> Path:
    participants = _participants(spec)
    members: dict[str, Any] = {
        "profile.json": {
            "characterData": {
                "character": {
                    "id": 99,
                    "canonicalID": 99,
                    "name": "Subject",
                    "classID": 3,
                    "level": 60,
                    "hidden": False,
                    "server": {
                        "id": 1,
                        "name": "Realm",
                        "slug": "realm",
                        "region": {"id": 1, "name": "Europe", "slug": "EU"},
                    },
                }
            },
            "worldData": {
                "zone": {
                    "id": 2006,
                    "name": "Naxxramas",
                    "frozen": False,
                    "partitions": [],
                    "encounters": [{"id": ENCOUNTER, "name": BOSS}],
                }
            },
        },
        "manifest.json": {
            "partition": 1,
            "topNPerBoss": 5,
            "errors": spec.errors,
            "clientSecretIncludedInExport": False,
            "userAccessTokenIncludedInExport": False,
        },
        "selection.json": [{"reportID": REPORT, "fightID": FIGHT, "participants": participants}],
        f"reports/{REPORT}/bundle.json": {
            "reportData": {
                "report": {
                    "code": REPORT,
                    "title": "t",
                    "startTime": 0,
                    "endTime": 1,
                    "revision": 1,
                    "visibility": "public",
                    "archiveStatus": {"isArchived": False},
                    "zone": {"id": 2006, "name": "Naxxramas"},
                    "fights": [
                        {
                            "id": FIGHT,
                            "encounterID": ENCOUNTER,
                            "name": BOSS,
                            "startTime": 0,
                            "endTime": 100000,
                            "kill": True,
                            "difficulty": 3,
                            "size": 40,
                            "averageItemLevel": 80.0,
                            "friendlyPlayers": [1],
                            "enemyNPCs": [],
                            "friendlyPets": [],
                        }
                    ],
                    "masterData": {
                        "logVersion": 1,
                        "gameVersion": 2,
                        "actors": [
                            {
                                "id": aid,
                                "name": n,
                                "type": "Hunter",
                                "subType": "Hunter",
                                "server": "Realm",
                                "gameID": aid,
                                "petOwner": None,
                                "icon": "x",
                            }
                            for aid, n in spec.players.items()
                        ],
                        "abilities": [
                            {"gameID": 75, "name": "Auto Shot", "type": "1", "icon": "y"}
                        ],
                    },
                    "playerDetails": {"data": {"playerDetails": {"dps": []}}},
                    "rankings": {"data": []},
                }
            }
        },
        f"leaderboards/{ENCOUNTER}_{BOSS}.json": {
            "encounter": {"id": ENCOUNTER, "name": BOSS},
            "partition": 1,
            "pages": [
                {
                    "page": 1,
                    "characterRankings": {
                        "rankings": [
                            {
                                "name": "Hunter",
                                "amount": 1000.0,
                                "report": {"code": REPORT, "fightID": FIGHT},
                            }
                        ]
                    },
                }
            ],
        },
    }
    base = f"events/{REPORT}/fight_{FIGHT}/"
    for actor_id, name in spec.players.items():
        reasons = [p for p in participants if p["player"] == name]
        members[f"{base}player_{actor_id}_{name}/selection.json"] = {
            "actor": {
                "id": actor_id,
                "name": name,
                "type": "Hunter",
                "subType": "Hunter",
                "server": "Realm",
                "gameID": actor_id,
                "petOwner": None,
                "icon": "x",
            },
            "player": name,
            "reasons": reasons,
        }
        if spec.with_pets_json:
            members[f"{base}player_{actor_id}_{name}/pets.json"] = [
                {"id": pid, "name": pname, "type": "Pet", "petOwner": actor_id}
                for pid, pname in spec.pets.get(actor_id, {}).items()
            ]
    for stream, pages in spec.streams.items():
        for i, content in enumerate(pages, start=1):
            members[f"{base}{stream}_{i:03d}.json"] = content
    if spec.subset is not None:
        members["subset.json"] = spec.subset
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, json.dumps(content))
        for name, data in spec.extra_members.items():
            zf.writestr(name, data)
    return path
