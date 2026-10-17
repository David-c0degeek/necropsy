"""Frozen independent arithmetic catches semantic mutations after valid rehashing."""

from __future__ import annotations

import copy
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from necropsy.snapshot.archive import (
    EntryDigest,
    EntryOrigin,
    VerifiedArchive,
    format_entries_manifest,
    sha256_file,
)
from scripts.check_raid_facts import check_register, raw_actor_facts

REPORT = "AbCdEfGhIjKlMnOp"
PREFIX = f"events/{REPORT}/fight_1/player_1_Healer/"
BUNDLE = f"reports/{REPORT}/bundle.json"


def _members() -> dict[str, Any]:
    heal = {"type": "heal", "timestamp": 1100, "sourceID": 1, "targetID": 1, "amount": 10}
    return {
        BUNDLE: {
            "reportData": {
                "report": {
                    "revision": 4,
                    "fights": [
                        {
                            "id": 1,
                            "encounterID": 50663,
                            "startTime": 1000,
                            "endTime": 3000,
                            "friendlyPets": [{"id": 99, "gameID": 123, "petOwner": 1}],
                        }
                    ],
                    "masterData": {
                        "actors": [
                            {"id": 1, "gameID": 11, "subType": "Priest"},
                            {"id": 2, "gameID": 12118},
                            {"id": 99, "gameID": 123, "petOwner": 1},
                        ]
                    },
                }
            }
        },
        PREFIX + "source_001.json": {
            "nextPageTimestamp": None,
            "data": [
                heal,
                heal,
                {"type": "cast", "timestamp": 1200, "sourceID": 1, "abilityGameID": 10917},
                {"type": "damage", "timestamp": 1300, "sourceID": 1, "targetID": 2, "amount": 20},
                {"type": "absorbed", "timestamp": 1500, "sourceID": 1, "targetID": 1, "amount": 3},
            ],
        },
        PREFIX + "target_001.json": {
            "nextPageTimestamp": None,
            "data": [
                heal,
                heal,
                {
                    "type": "cast",
                    "timestamp": 1400,
                    "sourceID": 2,
                    "targetID": 1,
                    "abilityGameID": 42,
                },
                {"type": "damage", "timestamp": 1500, "sourceID": 2, "targetID": 1, "amount": 7},
            ],
        },
    }


EXPECTED = {
    "encounter_id": 50663,
    "revision": 4,
    "duration_ms": 2000,
    "actor_class": "Priest",
    "actor_game_id": 11,
    "totals": {"damage": 20, "effective_healing": 20, "absorbed_amount": 3, "incoming_damage": 7},
    "casts_ms": {"10917": [200]},
    "damage_by_actor": {"2": 20},
    "target_game_ids": {"2": 12118},
    "pet_ownership": {"99": {"game_id": 123, "fight_owner": 1, "master_owner": 1}},
}


def _write(root: Path, members: dict[str, Any]) -> Path:
    archive = root / "raw.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for name, value in members.items():
            z.writestr(name, json.dumps(value))
    import hashlib

    entries = root / "raw.entries"
    with zipfile.ZipFile(archive) as z:
        entries.write_text(
            format_entries_manifest(
                EntryDigest(
                    n, len(z.read(n)), hashlib.sha256(z.read(n)).hexdigest(), EntryOrigin.ACQUIRED
                )
                for n in z.namelist()
            ),
            encoding="utf-8",
        )
    register = root / "facts.json"
    register.write_text(
        json.dumps(
            {
                "version": 1,
                "cases": [
                    {
                        "id": "manual-synthetic-arithmetic",
                        "archive": archive.name,
                        "entries": entries.name,
                        "sha256": sha256_file(archive),
                        "report": REPORT,
                        "fight": 1,
                        "actor": 1,
                        "review_basis": "Hand-counted synthetic arithmetic; not real evidence.",
                        "expected": EXPECTED,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return register


def test_union_preserves_multiplicity_and_excludes_incoming_casts(tmp_path: Path) -> None:
    register = _write(tmp_path, _members())
    assert check_register(register) == []
    with VerifiedArchive(tmp_path / "raw.zip") as archive:
        assert raw_actor_facts(archive, REPORT, 1, 1) == EXPECTED


@pytest.mark.parametrize("mutation", ["duration", "target", "owner", "cast-time", "amount"])
def test_rehashed_wrong_raw_facts_fail(tmp_path: Path, mutation: str) -> None:
    members = copy.deepcopy(_members())
    report = members[BUNDLE]["reportData"]["report"]
    if mutation == "duration":
        report["fights"][0]["endTime"] += 1
    elif mutation == "target":
        report["masterData"]["actors"][1]["gameID"] = 1
    elif mutation == "owner":
        report["masterData"]["actors"][2]["petOwner"] = 2
    elif mutation == "cast-time":
        members[PREFIX + "source_001.json"]["data"][2]["timestamp"] += 1
    else:
        members[PREFIX + "source_001.json"]["data"][3]["amount"] += 1
    register = _write(tmp_path, members)
    assert check_register(register), "valid hashes cannot make wrong semantic facts pass"


@pytest.mark.parametrize("mutation", ["missing-target", "unterminated", "missing-cursor"])
def test_partial_raw_streams_cannot_establish_complete_totals(
    tmp_path: Path, mutation: str
) -> None:
    members = _members()
    if mutation == "missing-target":
        del members[PREFIX + "target_001.json"]
    elif mutation == "unterminated":
        members[PREFIX + "source_001.json"]["nextPageTimestamp"] = 1501
    else:
        del members[PREFIX + "source_001.json"]["nextPageTimestamp"]
    register = _write(tmp_path, members)
    with pytest.raises(ValueError, match=r"stream|directions"):
        check_register(register)


def test_missing_raw_amount_is_not_an_independent_zero(tmp_path: Path) -> None:
    members = _members()
    del members[PREFIX + "source_001.json"]["data"][3]["amount"]
    register = _write(tmp_path, members)
    with pytest.raises(ValueError, match="raw amount missing"):
        check_register(register)


def _encounter_members() -> dict[str, Any]:
    members = _members()
    report = members[BUNDLE]["reportData"]["report"]
    report["masterData"]["actors"].append({"id": 3, "type": "Player", "subType": "Mage"})
    report["masterData"]["abilities"] = [{"gameID": 133, "type": "4"}]
    critical = {
        "type": "damage",
        "timestamp": 1600,
        "sourceID": 3,
        "targetID": 2,
        "abilityGameID": 133,
        "amount": 30,
        "hitType": 2,
    }
    all_rows = [
        *members[PREFIX + "source_001.json"]["data"],
        *members[PREFIX + "target_001.json"]["data"][2:],
        critical,
        {
            "type": "damage",
            "timestamp": 1700,
            "sourceID": 3,
            "targetID": 2,
            "abilityGameID": 12654,
            "amount": 9,
        },
        {
            "type": "applydebuff",
            "timestamp": 1500,
            "sourceID": 2,
            "targetID": 1,
            "abilityGameID": 20604,
        },
    ]
    prefix = f"events/{REPORT}/fight_1/encounter/"
    members[prefix + "all_001.json"] = {"data": all_rows, "nextPageTimestamp": None}
    members[prefix + "critical_001.json"] = {"data": [critical], "nextPageTimestamp": None}
    proofs = []
    for role in ("encounter", "critical"):
        identity = dict(
            site="vanilla.warcraftlogs.com",
            code=REPORT,
            revision=4,
            fight=1,
            actor_id=None,
            role=role,
            direction="all",
            start_time=1000.0,
            end_time=3000.0,
            data_type="All",
            limit=10000,
            include_resources=True,
            translate=True,
            query_version=1,
            endpoint="user",
        )
        if role == "critical":
            identity["filter_expression"] = 'type = "damage" AND isCritical = true'
        proofs.append(
            dict(
                report=REPORT,
                fight=1,
                role=role,
                actor_id=None,
                direction="all",
                identity=identity,
                pages=[],
            )
        )
    members["necropsy-snapshot.json"] = dict(
        formatVersion=2, endpoint="user", encounter_streams=proofs
    )
    return members


CONTEXT_EXPECTED = {
    "events": 10,
    "critical_events": 1,
    "critical_hit_types": {"2": 1},
    "fire_critical_mages_by_target": {"2": [3]},
    "unclassified_mage_critical_abilities": [],
    "unclassified_critical_sources": [],
    "ignite_by_source_target": {"3/2": 9},
    "mind_control_transitions": [[500, "applydebuff", 2, 1, None, 20604, None]],
    "deaths": [],
    "interrupts": [],
}


def _write_context(root: Path, members: dict[str, Any]) -> Path:
    for proof in members["necropsy-snapshot.json"]["encounter_streams"]:
        kind = "all" if proof["role"] == "encounter" else "critical"
        name = f"events/{REPORT}/fight_1/encounter/{kind}_001.json"
        proof["pages"] = [hashlib.sha256(json.dumps(members[name]).encode()).hexdigest()]
    register = _write(root, members)
    data = json.loads(register.read_text(encoding="utf-8"))
    data["cases"][0]["encounter_context"] = True
    data["cases"][0]["expected"]["encounter_context"] = CONTEXT_EXPECTED
    register.write_text(json.dumps(data), encoding="utf-8")
    return register


def test_hand_counted_encounter_observations_keep_scope_and_mage_sharing_inputs(
    tmp_path: Path,
) -> None:
    assert check_register(_write_context(tmp_path, _encounter_members())) == []


@pytest.mark.parametrize(
    "mutation", ["ignite", "critical-owner", "control-target", "school", "critical-count"]
)
def test_rehashed_global_semantic_changes_fail_independent_expectations(
    tmp_path: Path, mutation: str
) -> None:
    members = _encounter_members()
    prefix = f"events/{REPORT}/fight_1/encounter/"
    rows = members[prefix + "all_001.json"]["data"]
    if mutation == "ignite":
        rows[-2]["amount"] += 1
    elif mutation == "critical-owner":
        rows[-3]["sourceID"] = 99
    elif mutation == "control-target":
        rows[-1]["targetID"] = 2
    elif mutation == "school":
        members[BUNDLE]["reportData"]["report"]["masterData"]["abilities"][0]["type"] = "16"
    else:
        members[prefix + "critical_001.json"]["data"] = []
    assert check_register(_write_context(tmp_path, members))


@pytest.mark.parametrize("mutation", ["filter", "critical-cursor", "source-after-terminal"])
def test_valid_hashes_cannot_certify_wrong_scope_or_pagination(
    tmp_path: Path, mutation: str
) -> None:
    members = _encounter_members()
    if mutation == "filter":
        members["necropsy-snapshot.json"]["encounter_streams"][1]["identity"][
            "filter_expression"
        ] = ""
    elif mutation == "critical-cursor":
        members[f"events/{REPORT}/fight_1/encounter/critical_001.json"]["nextPageTimestamp"] = True
    else:
        members[PREFIX + "source_002.json"] = {"data": [], "nextPageTimestamp": None}
    with pytest.raises(ValueError, match=r"scope|stream"):
        check_register(_write_context(tmp_path, members))


@pytest.mark.parametrize("mutation", [None, "instance", "ability", "kind"])
def test_independent_aura_facts_bind_recipient_instance_and_transition_kind(
    tmp_path: Path,
    mutation: str | None,
) -> None:
    members = _encounter_members()
    application = {
        "timestamp": 2100,
        "type": "applybuff",
        "sourceID": 2,
        "targetID": 2,
        "targetInstance": 1,
        "abilityGameID": 20619,
    }
    removal = {**application, "timestamp": 2200, "type": "removebuff"}
    if mutation == "instance":
        removal["targetInstance"] = 2
    elif mutation == "ability":
        removal["abilityGameID"] = 20620
    elif mutation == "kind":
        removal["type"] = "cast"
    members[f"events/{REPORT}/fight_1/encounter/all_001.json"]["data"].extend(
        [application, removal]
    )
    register = _write_context(tmp_path, members)
    doc = json.loads(register.read_text(encoding="utf-8"))
    case = doc["cases"][0]
    case["encounter_aura_ids"] = [20619]
    expected = case["expected"]["encounter_context"]
    expected["events"] = 12
    expected["aura_transitions"] = {
        "20619": [
            [1100, "applybuff", 2, 2, 1, 20619, None],
            [1200, "removebuff", 2, 2, 1, 20619, None],
        ]
    }
    register.write_text(json.dumps(doc), encoding="utf-8")
    assert bool(check_register(register)) is (mutation is not None)


@pytest.mark.parametrize("mutation", [None, "owner", "recipient", "amount", "kind"])
def test_independent_absorption_facts_reject_validly_rehashed_semantic_changes(
    tmp_path: Path,
    mutation: str | None,
) -> None:
    members = _members()
    members[BUNDLE]["reportData"]["report"]["masterData"]["actors"][1]["type"] = "NPC"
    event = members[PREFIX + "source_001.json"]["data"][-1]
    if mutation == "owner":
        event["sourceID"] = 2
    elif mutation == "recipient":
        event["targetID"] = 2
    elif mutation == "amount":
        event["amount"] = 4
    elif mutation == "kind":
        event["type"] = "damage"
    register = _write(tmp_path, members)
    data = json.loads(register.read_text(encoding="utf-8"))
    data["kind"] = "healing-recipients"
    data["cases"][0]["boss_game_ids"] = [12118]
    data["cases"][0]["expected"] = {
        "friendly_healing": 20,
        "boss_healing": 0,
        "unclassified_healing": 0,
        "raw_healing": 20,
        "friendly_absorption": 3,
        "boss_absorption": 0,
        "unclassified_absorption": 0,
        "raw_absorption": 3,
        "friendly_healing_and_absorption": 23,
        "duration_ms": 2000,
    }
    register.write_text(json.dumps(data), encoding="utf-8")
    assert bool(check_register(register)) is (mutation is not None)


CONTROL_EXPECTED = {
    "duration_ms": 2000,
    "observations": [
        {
            "ms": 500,
            "kind": "applydebuff",
            "spell": 710,
            "caster": {"id": 4, "type": "Player", "subType": "Warlock", "name": "Lock"},
            "target": {"id": 5, "type": "NPC", "gameID": 12099, "name": "Firesworn"},
            "instance": 2,
        },
        {
            "ms": 1500,
            "kind": "removedebuff",
            "spell": 710,
            "caster": {"id": 4, "type": "Player", "subType": "Warlock", "name": "Lock"},
            "target": {"id": 5, "type": "NPC", "gameID": 12099, "name": "Firesworn"},
            "instance": 2,
        },
    ],
    "lifecycles": [],
}


def _control_members() -> dict[str, Any]:
    members = _encounter_members()
    members[BUNDLE]["reportData"]["report"]["masterData"]["actors"].extend(
        [
            {"id": 4, "type": "Player", "subType": "Warlock", "name": "Lock"},
            {"id": 5, "type": "NPC", "gameID": 12099, "name": "Firesworn"},
        ]
    )
    members[f"events/{REPORT}/fight_1/encounter/all_001.json"]["data"].extend(
        [
            {
                "timestamp": 1500,
                "type": "applydebuff",
                "sourceID": 4,
                "targetID": 5,
                "targetInstance": 2,
                "abilityGameID": 710,
            },
            {
                "timestamp": 2500,
                "type": "removedebuff",
                "sourceID": 4,
                "targetID": 5,
                "targetInstance": 2,
                "abilityGameID": 710,
            },
        ]
    )
    return members


def _write_control(root: Path, members: dict[str, Any]) -> Path:
    register = _write_context(root, members)
    data = json.loads(register.read_text(encoding="utf-8"))
    data["kind"] = "npc-controls"
    case = data["cases"][0]
    case["ability_ids"] = [710]
    case["target_game_ids"] = [12099]
    case["expected"] = CONTROL_EXPECTED
    register.write_text(json.dumps(data), encoding="utf-8")
    return register


def test_independent_control_catalog_instance_and_transition_facts(tmp_path: Path) -> None:
    assert check_register(_write_control(tmp_path, _control_members())) == []


@pytest.mark.parametrize(
    "mutation", ["caster", "class", "target", "instance", "time", "kind", "spell", "lifecycle"]
)
def test_validly_rehashed_control_changes_cannot_match_manual_facts(
    tmp_path: Path, mutation: str
) -> None:
    members = _control_members()
    rows = members[f"events/{REPORT}/fight_1/encounter/all_001.json"]["data"]
    application = rows[-2]
    if mutation == "class":
        members[BUNDLE]["reportData"]["report"]["masterData"]["actors"][-2]["subType"] = "Mage"
    elif mutation == "lifecycle":
        rows.append({"timestamp": 2400, "type": "death", "targetID": 5, "targetInstance": 2})
    else:
        key, value = {
            "caster": ("sourceID", 3),
            "target": ("targetID", 2),
            "instance": ("targetInstance", 3),
            "time": ("timestamp", 1501),
            "kind": ("type", "cast"),
            "spell": ("abilityGameID", 18647),
        }[mutation]
        application[key] = value
    assert check_register(_write_control(tmp_path, members))


def test_control_raw_boolean_owner_is_not_an_integer_identity(tmp_path: Path) -> None:
    members = _control_members()
    members[f"events/{REPORT}/fight_1/encounter/all_001.json"]["data"][-2]["sourceID"] = True
    with pytest.raises(ValueError, match="raw control actor identity"):
        check_register(_write_control(tmp_path, members))
