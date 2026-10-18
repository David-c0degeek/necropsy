"""Frozen absorption splits distinguish credited effects from spell casts."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.check_raid_facts import check_register
from tests.unit.test_raid_facts import BUNDLE, PREFIX, REPORT, _encounter_members, _write_context

ALL = f"events/{REPORT}/fight_1/encounter/all_001.json"


def members() -> dict[str, Any]:
    raw = _encounter_members()
    raw["necropsy-snapshot.json"]["zone"] = dict(id=2000, partition=1)
    report = raw[BUNDLE]["reportData"]["report"]
    report["fights"][0].update(friendlyPlayers=[1, 3], enemyNPCs=[dict(id=2, gameID=12118)])
    actors = report["masterData"]["actors"]
    actors[0].update(type="Player")
    actors[1].update(type="NPC")
    actors[2].update(type="Pet")
    report["masterData"]["abilities"].extend(
        [
            dict(gameID=10901, name="Power Word: Shield"),
            dict(gameID=26470, name="Persistent Shield"),
        ]
    )
    raw[PREFIX + "source_001.json"]["data"][4]["abilityGameID"] = 10901
    event = dict(
        type="absorbed", timestamp=1800, sourceID=1, targetID=3, abilityGameID=26470, amount=7
    )
    raw[PREFIX + "source_001.json"]["data"].append(event)
    raw[ALL]["data"].append(event)
    return raw


def observation(ms: int, target: int, spell: int, amount: int, index: int) -> dict[str, Any]:
    return dict(
        ms=ms,
        target=target,
        ability=spell,
        amount=amount,
        member=PREFIX + "source_001.json",
        index=index,
    )


EXPECTED: dict[str, Any] = {
    "zone_id": 2000,
    "partition": 1,
    "encounter_id": 50663,
    "revision": 4,
    "duration_ms": 2000,
    "actor_class": "Priest",
    "source_pages": [PREFIX + "source_001.json"],
    "friendly_players": [1, 3],
    "friendly_pets": [dict(id=99, gameID=123, petOwner=1)],
    "friendly_absorption": 10,
    "ability_absorption": [
        dict(
            ability_id=10901,
            ability_names=["Power Word: Shield"],
            amount=3,
            events=1,
            recipients=[dict(actor_id=1, amount=3, events=1)],
            observations=[observation(500, 1, 10901, 3, 4)],
        ),
        dict(
            ability_id=26470,
            ability_names=["Persistent Shield"],
            amount=7,
            events=1,
            recipients=[dict(actor_id=3, amount=7, events=1)],
            observations=[observation(800, 3, 26470, 7, 5)],
        ),
    ],
    "excluded_source_absorption": [],
}


def register(root: Path, raw: dict[str, Any], expected: dict[str, Any] = EXPECTED) -> Path:
    path = _write_context(root, raw)
    data = json.loads(path.read_bytes())
    data["kind"] = "absorption-abilities"
    data["cases"][0].update(boss_game_ids=[12118], expected=copy.deepcopy(expected))
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_hand_counted_absorption_ability_and_recipient_splits(tmp_path: Path) -> None:
    assert check_register(register(tmp_path, members())) == []


@pytest.mark.parametrize(
    "mutation",
    [
        "amount",
        "ability",
        "recipient",
        "source",
        "time",
        "float-ability",
        "float-target",
        "float-source",
        "boolean-amount",
        "negative-amount",
        "missing-type",
        "unknown-source",
        "fight-alias",
        "class",
        "owner-roster",
        "duplicate-player",
        "float-player",
        "player-catalog",
        "pet-catalog",
        "pet-game",
        "pet-catalog-game-alias",
        "pet-owner-alias",
        "pet-owner-bool",
        "duplicate-pet",
        "duplicate-catalog",
        "zone-alias",
        "partition-alias",
        "encounter-alias",
        "revision-alias",
        "ability-name",
        "duplicate-ability-name",
        "missing-all",
        "extra-source-copy",
        "all-only-spell",
        "all-only-zero-copy",
    ],
)
def test_rehashed_absorption_split_mutations_fail(tmp_path: Path, mutation: str) -> None:
    raw = members()
    report = raw[BUNDLE]["reportData"]["report"]
    fight = report["fights"][0]
    actors = report["masterData"]["actors"]
    event = raw[PREFIX + "source_001.json"]["data"][4]
    changes = {
        "amount": ("amount", 4),
        "ability": ("abilityGameID", 26470),
        "recipient": ("targetID", 3),
        "source": ("sourceID", 3),
        "time": ("timestamp", 1501),
        "float-ability": ("abilityGameID", 10901.0),
        "float-target": ("targetID", 1.0),
        "float-source": ("sourceID", 1.0),
        "boolean-amount": ("amount", True),
        "negative-amount": ("amount", -1),
        "missing-type": ("type", None),
        "unknown-source": ("sourceID", None),
        "fight-alias": ("fight", True),
    }
    if mutation in changes:
        key, value = changes[mutation]
        event[key] = value
    elif mutation == "class":
        actors[0]["subType"] = "Mage"
    elif mutation == "owner-roster":
        fight["friendlyPlayers"] = [3]
    elif mutation == "duplicate-player":
        fight["friendlyPlayers"] = [1, 3, 3]
    elif mutation == "float-player":
        fight["friendlyPlayers"] = [1, 3.0]
    elif mutation == "player-catalog":
        actors[3]["type"] = "NPC"
    elif mutation == "pet-catalog":
        actors[2]["type"] = "NPC"
    elif mutation == "pet-game":
        fight["friendlyPets"][0]["gameID"] = 124
    elif mutation == "pet-catalog-game-alias":
        actors[2]["gameID"] = 123.0
    elif mutation == "pet-owner-alias":
        fight["friendlyPets"][0]["petOwner"] = 1.0
    elif mutation == "pet-owner-bool":
        fight["friendlyPets"][0]["petOwner"] = True
    elif mutation == "duplicate-pet":
        fight["friendlyPets"].append(fight["friendlyPets"][0].copy())
    elif mutation == "duplicate-catalog":
        actors.append(actors[0].copy())
    elif mutation == "zone-alias":
        raw["necropsy-snapshot.json"]["zone"]["id"] = 2000.0
    elif mutation == "partition-alias":
        raw["necropsy-snapshot.json"]["zone"]["partition"] = True
    elif mutation == "encounter-alias":
        fight["encounterID"] = 50663.0
    elif mutation == "revision-alias":
        report["revision"] = 4.0
        for proof in raw["necropsy-snapshot.json"]["encounter_streams"]:
            proof["identity"]["revision"] = 4.0
    elif mutation == "ability-name":
        report["masterData"]["abilities"][1]["name"] = "Other shield"
    elif mutation == "duplicate-ability-name":
        report["masterData"]["abilities"].append(report["masterData"]["abilities"][1].copy())
    elif mutation == "missing-all":
        raw[ALL]["data"].clear()
    elif mutation == "extra-source-copy":
        raw[PREFIX + "source_001.json"]["data"].append(event.copy())
    elif mutation == "all-only-spell":
        raw[ALL]["data"] = copy.deepcopy(raw[ALL]["data"])
        next(e for e in raw[ALL]["data"] if e.get("type") == "absorbed")["abilityGameID"] = 26470
    elif mutation == "all-only-zero-copy":
        raw[ALL]["data"].append({**event, "amount": 0})
    path = register(tmp_path, raw)
    try:
        problems = check_register(path)
    except ValueError, KeyError:
        return
    assert problems


def test_complete_zero_retains_an_empty_ability_split(tmp_path: Path) -> None:
    raw = members()
    for name in (PREFIX + "source_001.json", ALL):
        raw[name]["data"] = [e for e in raw[name]["data"] if e.get("type") != "absorbed"]
    expected = copy.deepcopy(EXPECTED)
    expected.update(friendly_absorption=0, ability_absorption=[])
    assert check_register(register(tmp_path, raw, expected)) == []


def test_identical_effect_occurrences_keep_their_multiplicity(tmp_path: Path) -> None:
    raw = members()
    effect = raw[PREFIX + "source_001.json"]["data"][4].copy()
    raw[PREFIX + "source_001.json"]["data"].append(effect)
    raw[ALL]["data"].append(effect)
    expected = copy.deepcopy(EXPECTED)
    expected["friendly_absorption"] = 13
    shield = expected["ability_absorption"][0]
    shield.update(amount=6, events=2, recipients=[dict(actor_id=1, amount=6, events=2)])
    shield["observations"].append(observation(500, 1, 10901, 3, 6))
    assert check_register(register(tmp_path, raw, expected)) == []
