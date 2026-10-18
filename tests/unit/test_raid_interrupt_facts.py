"""Fully rehashed raw changes must still fail frozen raid interruption facts."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.check_raid_facts import check_register
from tests.unit.test_raid_facts import BUNDLE, REPORT, _encounter_members, _write_context

ALL = f"events/{REPORT}/fight_1/encounter/all_001.json"


def members() -> dict[str, Any]:
    result = _encounter_members()
    result["necropsy-snapshot.json"]["zone"] = dict(id=2000, partition=1)
    report = result[BUNDLE]["reportData"]["report"]
    report["fights"][0].update(
        encounterID=50669,
        friendlyPlayers=[1, 3],
        enemyNPCs=[dict(id=2, gameID=11662, instanceCount=4)],
    )
    report["masterData"]["actors"][0].update(type="Player", subType="Shaman", name="Caster")
    report["masterData"]["actors"][1].update(type="NPC", gameID=11662)
    report["masterData"]["actors"][3].update(name="Other Mage")
    result[ALL]["data"].append(
        dict(
            type="interrupt",
            timestamp=1900,
            sourceID=1,
            targetID=2,
            targetInstance=3,
            abilityGameID=8042,
            extraAbilityGameID=19775,
            fight=1,
        )
    )
    return result


ROW = dict(
    ms=900,
    source=1,
    source_name="Caster",
    source_type="Player",
    source_class="Shaman",
    friendly=True,
    target=2,
    target_type="NPC",
    target_game_id=11662,
    target_instance=3,
    ability=8042,
    stopped=19775,
    member=ALL,
    index=10,
)
EXPECTED = {
    "zone_id": 2000,
    "partition": 1,
    "encounter_id": 50669,
    "revision": 4,
    "duration_ms": 2000,
    "friendly_players": [
        dict(id=1, type="Player", name="Caster", **{"class": "Shaman"}),
        dict(id=3, type="Player", name="Other Mage", **{"class": "Mage"}),
    ],
    "targets": [dict(id=2, game_id=11662, instances=4)],
    "all_pages": [ALL],
    "interrupt_rows": [ROW],
    "qualified_interrupts": [ROW],
}


def register(root: Path, raw: dict[str, Any]) -> Path:
    path = _write_context(root, raw)  # Rehash ZIP, all members and All/critical proofs.
    data = json.loads(path.read_bytes())
    data["kind"] = "raid-interrupts"
    data["cases"][0].update(
        source_class="Shaman",
        target_game_ids=[11662],
        stopped_ability_ids=[19775],
        expected=copy.deepcopy(EXPECTED),
    )
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_hand_counted_raid_interrupt_facts(tmp_path: Path) -> None:
    assert check_register(register(tmp_path, members())) == []


@pytest.mark.parametrize(
    "mutation",
    [
        "zone-alias",
        "partition-alias",
        "encounter-alias",
        "revision-alias",
        "class",
        "missing-class",
        "source-alias",
        "target-alias",
        "source-missing",
        "timestamp-alias",
        "fight-alias",
        "stopped-alias",
        "spell",
        "type",
        "instance-alias",
        "instance-outside",
        "roster-alias",
        "duplicate-roster",
        "missing-enemy",
        "wrong-npc",
        "duplicate-catalog",
        "npc-alias",
        "instance-count-alias",
        "other-class",
    ],
)
def test_valid_rehash_cannot_hide_eligibility_or_measurement_changes(
    tmp_path: Path,
    mutation: str,
) -> None:
    raw = members()
    report = raw[BUNDLE]["reportData"]["report"]
    fight = report["fights"][0]
    actors = report["masterData"]["actors"]
    event = raw[ALL]["data"][-1]
    if mutation == "zone-alias":
        raw["necropsy-snapshot.json"]["zone"]["id"] = 2000.0
    elif mutation == "partition-alias":
        raw["necropsy-snapshot.json"]["zone"]["partition"] = True
    elif mutation == "encounter-alias":
        fight["encounterID"] = 50669.0
    elif mutation == "revision-alias":
        report["revision"] = 4.0
        for proof in raw["necropsy-snapshot.json"]["encounter_streams"]:
            proof["identity"]["revision"] = 4.0
    elif mutation == "class":
        actors[0]["subType"] = "Priest"
    elif mutation == "missing-class":
        actors[0].pop("subType")
    elif mutation == "other-class":
        actors[3]["subType"] = "Shaman"
    elif mutation == "roster-alias":
        fight["friendlyPlayers"] = [1.0, 3]
    elif mutation == "duplicate-roster":
        fight["friendlyPlayers"] = [1, 3, 3]
    elif mutation == "missing-enemy":
        fight["enemyNPCs"] = []
    elif mutation == "wrong-npc":
        actors[1]["gameID"] = 123
    elif mutation == "duplicate-catalog":
        actors.append(actors[0].copy())
    elif mutation == "npc-alias":
        fight["enemyNPCs"][0]["gameID"] = 11662.0
    elif mutation == "instance-count-alias":
        fight["enemyNPCs"][0]["instanceCount"] = 4.0
    else:
        key, value = {
            "source-alias": ("sourceID", 1.0),
            "target-alias": ("targetID", 2.0),
            "source-missing": ("sourceID", None),
            "timestamp-alias": ("timestamp", 1900.0),
            "fight-alias": ("fight", True),
            "stopped-alias": ("extraAbilityGameID", 19775.0),
            "spell": ("abilityGameID", 10414),
            "type": ("type", "cast"),
            "instance-alias": ("targetInstance", 3.0),
            "instance-outside": ("targetInstance", 5),
        }[mutation]
        event[key] = value
    path = register(tmp_path, raw)
    try:
        problems = check_register(path)
    except ValueError, KeyError:
        return
    assert problems
