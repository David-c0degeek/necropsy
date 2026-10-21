"""Independent DPS freeze preserves scope, ownership and event multiplicity."""

from __future__ import annotations

import copy
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from scripts import freeze_dps_ranking as dps


def case(tmp_path: Path, mutation: str = "") -> dict[str, Any]:
    def actor(identity: int, kind: str, game_id: int, **fields: Any) -> dict[str, Any]:
        return {"id": identity, "type": kind, "gameID": game_id, **fields}

    me = actor(1, "Player", 101, name="Example", server="Realm", subType="Druid")
    pet = actor(6, "Pet", 8836, petOwner=1)
    fight = {
        "id": 7,
        "encounterID": 51118,
        "kill": True,
        "startTime": 100,
        "endTime": 10100,
        "friendlyPlayers": [1],
        "friendlyPets": [pet],
    }
    report = {
        "code": "ABC",
        "visibility": "public",
        "revision": 1,
        "fights": [fight],
        "masterData": {"actors": [me, pet, actor(3, "NPC", 16028), actor(4, "NPC", 999)]},
    }
    if mutation == "ownership":
        pet["petOwner"] = 2

    def event(source: int, target: int, amount: Any, stamp: int = 200) -> dict[str, Any]:
        return {
            "type": "damage",
            "sourceID": source,
            "targetID": target,
            "amount": amount,
            "timestamp": stamp,
            "fight": 7,
            "abilityGameID": 1,
        }

    repeated = event(1, 3, 100)
    source_rows = [repeated, repeated, event(1, 1, 10, 300), event(1, 4, 30, 400)]
    target_rows = [repeated, event(1, 1, 10, 300)]
    if mutation == "amount_missing":
        source_rows[0].pop("amount")
    if mutation == "amount_float":
        source_rows[0]["amount"] = 100.0
    if mutation == "target_alias":
        source_rows[0]["targetID"] = True
    if mutation == "timestamp":
        source_rows[0]["timestamp"] = 10101
    files: dict[str, bytes] = {}

    def write(name: str, data: Any) -> None:
        files[name] = json.dumps(data).encode()

    proofs = []
    for identity, role, outgoing, incoming in (
        (1, "player", source_rows, target_rows),
        (6, "pet", [event(6, 3, 40)], [event(6, 3, 40)]),
    ):
        folder = f"events/ABC/fight_7/{role}_{identity}_Example"
        for direction, rows in (("source", outgoing), ("target", incoming)):
            name = f"{folder}/{direction}_001.json"
            write(name, {"data": rows, "nextPageTimestamp": None})
            request = {
                "code": "ABC",
                "fight": 7,
                "actor_id": identity,
                "role": role,
                "direction": direction,
                "revision": 1,
                "data_type": "All",
                "include_resources": True,
                "translate": True,
                "start_time": 100,
                "end_time": 10100,
                "site": "vanilla.warcraftlogs.com",
                "endpoint": "user",
                "query_version": 1,
                "limit": 10000,
            }
            if mutation == "proof_identity":
                request["revision"] = 2
            proofs.append(
                {
                    "report": "ABC",
                    "fight": 7,
                    "actor_id": identity,
                    "role": role,
                    "direction": direction,
                    "identity": request,
                    "pages": [hashlib.sha256(files[name]).hexdigest()],
                }
            )
    if mutation != "missing_pets":
        write("events/ABC/fight_7/player_1_Example/pets.json", [pet])
    if mutation == "unterminated":
        write(
            "events/ABC/fight_7/player_1_Example/source_001.json",
            {"data": source_rows, "nextPageTimestamp": 500},
        )
        proofs[0]["pages"] = [
            hashlib.sha256(files["events/ABC/fight_7/player_1_Example/source_001.json"]).hexdigest()
        ]
    key = {
        k: {"status": "enforced", "value": v}
        for k, v in {
            "class_name": "Druid",
            "spec": "Balance",
            "role": "balance-dps",
            "partition": 1,
        }.items()
    }
    marker = {
        "kind": "necropsy.live-snapshot",
        "endpoint": "user",
        "fights": [
            {
                "reportID": "ABC",
                "fightID": 7,
                "participants": [
                    {
                        "player": "Example",
                        "server": "Realm",
                        "spec": "Balance",
                        "encounterID": 51118,
                    }
                ],
            }
        ],
        "formatVersion": 1,
        "streams": proofs,
        "bosses": [{"encounter_id": 51118, "key": key}],
        "report_sets": [
            {
                "report": "ABC",
                "revision": 1,
                "sha256": hashlib.sha256(
                    json.dumps(
                        report, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                    ).encode()
                ).hexdigest(),
            }
        ],
    }
    write("necropsy-snapshot.json", marker)
    write("reports/ABC/bundle.json", {"reportData": {"report": report}})
    row = {
        "report": {"code": "ABC", "fightID": 7},
        "name": "Example",
        "server": {"name": "Realm"},
        "class": "Druid",
        "spec": "Balance",
        "duration": 10000,
        "amount": 24.0,
    }
    if mutation == "published_identity":
        row["name"] = "SomeoneElse"
    if mutation == "published_duration":
        row["duration"] = 10001
    if mutation == "published_amount":
        row["amount"] = 25.0
    write(
        "leaderboards/51118_Patchwerk.json",
        {
            "encounter": {"id": 51118},
            "partition": 1,
            "pages": [{"page": 1, "characterRankings": {"rankings": [row]}}],
        },
    )
    archive = tmp_path / "capture.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for name, raw in files.items():
            z.writestr(name, raw)
    return {
        "archive": archive.name,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "report": "ABC",
        "fight": 7,
        "actor": 1,
        "player": "Example",
        "realm": "Realm",
        "class": "Druid",
        "category": "Balance",
        "role": "balance-dps",
        "encounter": 51118,
        "excluded_game_ids": [999],
        "leaderboard_member": "leaderboards/51118_Patchwerk.json",
        "page": 1,
        "row": 0,
    }


def test_raw_multiplicity_owned_damage_and_frozen_exclusions(tmp_path: Path) -> None:
    spec = case(tmp_path)
    result = dps.compute(spec, tmp_path)
    assert result["totals"] == {"raw": 280, "self": 10, "excluded": 30, "ranked": 240}
    assert result["source_damage"] == {"1": 240, "6": 40}
    assert result["owned_actor_ids"] == [6]
    repeated = next(e for e in result["events"] if e["raw"]["amount"] == 100)
    assert repeated["multiplicity"] == 2 and len(repeated["locators"]) == 3
    assert result["published"] == "24.0" and result["residual"] == "0"
    assert not dps.consistent(200, 10000, "24.0")  # dropped pet
    assert not dps.consistent(250, 10000, "24.0")  # self damage included
    assert not dps.consistent(270, 10000, "24.0")  # encounter exclusions dropped
    assert not dps.consistent(240, 11000, "24.0")  # wrong duration
    wrong = copy.deepcopy(spec)
    wrong["excluded_game_ids"] = []
    with pytest.raises(ValueError, match="contradicts raw"):
        dps.compute(wrong, tmp_path)


@pytest.mark.parametrize(
    "mutation",
    [
        "ownership",
        "missing_pets",
        "amount_missing",
        "amount_float",
        "target_alias",
        "timestamp",
        "proof_identity",
        "unterminated",
        "published_identity",
        "published_duration",
        "published_amount",
    ],
)
def test_insufficient_or_wrong_evidence_is_refused(tmp_path: Path, mutation: str) -> None:
    spec = case(tmp_path, mutation)
    with pytest.raises((ValueError, KeyError)):
        dps.compute(spec, tmp_path)


def test_hash_aliases_unknown_fields_and_healer_roles_are_refused(tmp_path: Path) -> None:
    spec = case(tmp_path)
    for key, value in (
        ("sha256", "0" * 64),
        ("actor", True),
        ("row", -1),
        ("role", "restoration"),
        ("extra", 1),
    ):
        wrong = spec | {key: value}
        with pytest.raises(ValueError):
            dps.compute(wrong, tmp_path)


def test_strict_json_and_exact_publication_precision() -> None:
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}'):
        with pytest.raises(ValueError):
            dps.read_json(raw)
    assert dps.read_json(b'{"amount":24.000}', decimal_text=True)["amount"] == "24.000"
    assert dps.consistent(240001, 10000, "24000.100")
    assert not dps.consistent(240002, 10000, "24000.100")


def test_cli_relocation_replay_tamper_and_no_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = case(tmp_path)
    source = tmp_path / "spec.json"
    source.write_text(json.dumps(spec), encoding="utf-8")
    output_dir = tmp_path / "drafts"
    output_dir.mkdir()
    output = output_dir / "oracle.json"
    monkeypatch.setattr(
        "sys.argv", ["freeze_dps_ranking", "freeze", str(source), "--out", str(output)]
    )
    assert dps.main() == 0
    original = output.read_bytes()
    assert json.loads(original)["spec"]["archive"] == "../capture.zip"
    assert dps.main() == 2
    assert output.read_bytes() == original
    monkeypatch.setattr("sys.argv", ["freeze_dps_ranking", "check", str(output)])
    assert dps.main() == 0
    changed = json.loads(original)
    changed["totals"]["ranked"] += 1
    output.write_text(json.dumps(changed), encoding="utf-8")
    assert dps.main() == 1
