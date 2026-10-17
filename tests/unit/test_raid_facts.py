"""Frozen independent arithmetic catches semantic mutations after valid rehashing."""

from __future__ import annotations

import copy
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
