"""Independent DPS freeze preserves scope, ownership and event multiplicity."""

from __future__ import annotations

import copy
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from scripts import freeze_dps_ranking as dps


def case(tmp_path: Path, mutation: str = "") -> dict[str, Any]:
    def actor(identity: int, kind: str, game_id: int, **fields: Any) -> dict[str, Any]:
        return {"id": identity, "type": kind, "gameID": game_id, **fields}

    realm = "Pyrewood Village" if mutation in {"spaced_realm", "other_catalog_realm"} else "Realm"
    catalog_realm = {"spaced_realm": "PyrewoodVillage", "other_catalog_realm": "Pyrewood"}.get(
        mutation, realm
    )
    me = actor(1, "Player", 101, name="Example", server=catalog_realm, subType="Druid")
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

    hps = mutation.startswith("hps")
    effect = "heal" if hps else "damage"

    def event(
        source: int, target: int, amount: Any, stamp: int = 200, kind: str = ""
    ) -> dict[str, Any]:
        return {
            "type": kind or effect,
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
    pet_rows = [event(6, 3, 40)]
    if hps:
        # Self-heal twice, an absorb on the pet, a heal on an enemy NPC, the pet healing
        # its owner: 250 healing to friendly units over 10 s.
        repeated = event(1, 1, 100)
        source_rows = [repeated, repeated, event(1, 6, 10, 300, "absorbed"), event(1, 3, 30, 400)]
        target_rows = [repeated, event(6, 1, 40)]
        pet_rows = [event(6, 1, 40)]
        if mutation == "hps_damage_only":
            source_rows.append(event(1, 3, 5000, 500, "damage"))
        if mutation in {"hps_mind_control", "hps_bad_flag"}:
            # A heal on an NPC the event marks friendly (mind-controlled) counts.
            controlled = event(1, 4, 20, 450) | {"targetIsFriendly": True}
            if mutation == "hps_bad_flag":
                controlled["targetIsFriendly"] = "yes"
            source_rows.append(controlled)
            source_rows[3] = source_rows[3] | {"targetIsFriendly": False}
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
        (6, "pet", pet_rows, pet_rows),
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
            "spec": "Restoration" if hps else "Balance",
            "role": "restoration" if hps else "balance-dps",
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
                        "server": realm,
                        "spec": "Restoration" if hps else "Balance",
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
        "server": {"name": realm},
        "class": "Druid",
        "spec": "Restoration" if hps else "Balance",
        "duration": 10000,
        "amount": 25.0 if hps else 24.0,
    }
    if mutation == "published_identity":
        row["name"] = "SomeoneElse"
    if mutation == "published_duration":
        row["duration"] = 10001
    if mutation == "published_amount":
        row["amount"] = 25.0
    if mutation in {"hps_mind_control", "hps_bad_flag"}:
        row["amount"] = 27.0
    if mutation == "hps_wrong_amount":
        row["amount"] = 28.0  # the enemy heal counted
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
        "realm": realm,
        "class": "Druid",
        "category": "Restoration" if hps else "Balance",
        "role": "restoration" if hps else "balance-dps",
        "encounter": 51118,
        "excluded_game_ids": [] if hps else [999],
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


def test_a_catalog_realm_without_spaces_is_the_same_realm(tmp_path: Path) -> None:
    spec = case(tmp_path, "spaced_realm")
    assert spec["realm"] == "Pyrewood Village"
    assert dps.compute(spec, tmp_path)["totals"]["ranked"] == 240


def test_a_different_catalog_realm_is_still_refused(tmp_path: Path) -> None:
    spec = case(tmp_path, "other_catalog_realm")
    with pytest.raises(ValueError, match="wrong owner identity"):
        dps.compute(spec, tmp_path)


def test_hps_counts_heals_and_absorbs_on_friendly_units_only(tmp_path: Path) -> None:
    spec = case(tmp_path, "hps")
    result = dps.compute(spec, tmp_path, metric="hps")
    assert result["totals"] == {"raw": 280, "self": 0, "excluded": 30, "ranked": 250}
    assert result["source_damage"] == {"1": 240, "6": 40}
    assert result["published"] == "25.0" and result["residual"] == "0"
    assert dps.compute_hps(spec, tmp_path)["totals"] == result["totals"]
    kinds = {e["raw"]["type"] for e in result["events"]}
    assert kinds == {"heal", "absorbed"}


def test_hps_counts_a_recipient_the_event_marks_friendly(tmp_path: Path) -> None:
    spec = case(tmp_path, "hps_mind_control")
    result = dps.compute(spec, tmp_path, metric="hps")
    assert result["totals"] == {"raw": 300, "self": 0, "excluded": 30, "ranked": 270}
    (tmp_path / "bad").mkdir()
    bad = case(tmp_path / "bad", "hps_bad_flag")
    with pytest.raises(ValueError, match="targetIsFriendly not boolean"):
        dps.compute(bad, tmp_path / "bad", metric="hps")


def test_hps_ignores_damage_events(tmp_path: Path) -> None:
    spec = case(tmp_path, "hps_damage_only")
    assert dps.compute(spec, tmp_path, metric="hps")["totals"]["ranked"] == 250


def test_hps_refuses_contradictions_exclusions_and_dps_roles(tmp_path: Path) -> None:
    spec = case(tmp_path, "hps_wrong_amount")
    with pytest.raises(ValueError, match="published HPS contradicts raw"):
        dps.compute(spec, tmp_path, metric="hps")
    (tmp_path / "good").mkdir()
    good = case(tmp_path / "good", "hps")
    with pytest.raises(ValueError, match="HPS takes no target exclusions"):
        dps.compute(good | {"excluded_game_ids": [999]}, tmp_path / "good", metric="hps")
    with pytest.raises(ValueError):
        dps.compute(good | {"role": "balance-dps"}, tmp_path / "good", metric="hps")
    with pytest.raises(ValueError):
        dps.compute(good, tmp_path / "good")  # a healer row is not a DPS row


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


def derived_case(tmp_path: Path, mutation: str = "") -> dict[str, Any]:
    """The same capture as v3: both target streams copied from one encounter-All stream."""
    spec = case(tmp_path)
    path = tmp_path / spec["archive"]
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}
    marker = json.loads(files["necropsy-snapshot.json"])
    target = json.loads(files["events/ABC/fight_7/player_1_Example/target_001.json"])
    pet_rows = json.loads(files["events/ABC/fight_7/pet_6_Example/target_001.json"])["data"]
    whole = json.dumps({"data": target["data"] + pet_rows, "nextPageTimestamp": None}).encode()
    files["events/ABC/fight_7/encounter/all_001.json"] = whole
    digest = hashlib.sha256(whole).hexdigest()
    parent = {
        **next(p for p in marker["streams"] if p["direction"] == "target")["identity"],
        "actor_id": None,
        "role": "encounter",
        "direction": "all",
    }
    if mutation == "cross_revision":
        parent["revision"] = 2
    if mutation == "endpoint":
        parent["endpoint"] = "client"
    if mutation == "filtered_parent":
        parent["filter_expression"] = "sourceID = 999"
    marker["zone"] = {"id": 2000 if mutation == "zone" else 2006, "partition": 1}
    marker["encounter_streams"] = [
        {
            "report": "ABC",
            "fight": 8 if mutation == "cross_fight" else 7,
            "role": "encounter",
            "actor_id": 999 if mutation == "parent_envelope" else None,
            "direction": "target" if mutation == "parent_envelope" else "all",
            "identity": parent,
            "pages": [digest],
        }
    ]
    if mutation == "extra_parent_page":
        files["events/ABC/fight_7/encounter/all_002.json"] = whole
    if mutation == "missing_parent_page":
        del files["events/ABC/fight_7/encounter/all_001.json"]
    for proof in marker["streams"]:
        name = f"events/ABC/fight_7/{proof['role']}_{proof['actor_id']}_Example/target_001.json"
        if proof["direction"] != "target":
            if mutation == "derived_source" and proof["role"] == "player":
                proof["derivation"] = {"rule": "x", "parent": parent, "parent_pages": [digest]}
            continue
        files[name] = whole
        proof["identity"], proof["pages"] = None, [digest]
        proof["derivation"] = {
            "rule": "wrong" if mutation == "rule" else "target-equals-encounter-all-v1",
            "parent": parent,
            "parent_pages": [digest],
        }
    if mutation == "missing_parent":
        marker["encounter_streams"] = []
    if mutation == "corrupt":
        name = "events/ABC/fight_7/player_1_Example/target_001.json"
        files[name] = json.dumps({"data": target["data"], "nextPageTimestamp": None}).encode()
        changed = hashlib.sha256(files[name]).hexdigest()
        player = next(
            p for p in marker["streams"] if (p["role"], p["direction"]) == ("player", "target")
        )
        player["pages"] = [changed]
    marker["formatVersion"] = 3
    files["necropsy-snapshot.json"] = json.dumps(marker).encode()
    with zipfile.ZipFile(path, "w") as z:
        for name, raw in files.items():
            z.writestr(name, raw)
    return spec | {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def test_a_derived_target_stream_gives_the_same_independent_totals(tmp_path: Path) -> None:
    (tmp_path / "fetched").mkdir()
    (tmp_path / "derived").mkdir()
    expected = dps.compute(case(tmp_path / "fetched"), tmp_path / "fetched")
    derived = dps.compute(derived_case(tmp_path / "derived"), tmp_path / "derived")
    assert derived["totals"] == expected["totals"]
    assert derived["source_damage"] == expected["source_damage"]
    assert derived["residual"] == expected["residual"]


def v4_case(tmp_path: Path, mutation: str = "") -> dict[str, Any]:
    spec = case(tmp_path)
    path = tmp_path / spec["archive"]
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}
    marker = json.loads(files["necropsy-snapshot.json"])
    report = json.loads(files["reports/ABC/bundle.json"])["reportData"]["report"]
    counts: Counter[str] = Counter()
    for name, body in files.items():
        if name.startswith("events/") and ("/source_" in name or "/target_" in name):
            counts |= Counter(json.dumps(e, sort_keys=True) for e in json.loads(body)["data"])
    events = [json.loads(e) for e, n in counts.items() for _ in range(n)]
    events.sort(key=lambda e: e["timestamp"])
    whole = json.dumps({"data": events, "nextPageTimestamp": None}).encode()
    parent = dict(
        marker["streams"][0]["identity"], role="encounter", actor_id=None, direction="all"
    )
    parent_proof = {
        "report": "ABC",
        "fight": 7,
        "role": "encounter",
        "actor_id": None,
        "direction": "all",
        "identity": parent,
        "pages": [hashlib.sha256(whole).hexdigest()],
    }
    files["events/ABC/fight_7/encounter/all_001.json"] = whole
    original = json.dumps({"endpoint": "user", "report": report}).encode()
    files["reports/ABC/fight_7.json"] = original
    marker["bosses"][0]["subject"] = {
        "report": "ABC",
        "fight": 7,
        "player": "Example",
        "status": "complete",
        "pets": [6],
        "bundle_generation": {
            "report": "ABC",
            "fight": 7,
            "revision": 1,
            "sha256": hashlib.sha256(original).hexdigest(),
        },
    }
    marker.update(
        formatVersion=4, zone={"id": 2006, "partition": 1}, encounter_streams=[parent_proof]
    )
    for proof in marker["streams"]:
        source = proof["direction"] == "source"
        ids = [1, 6] if proof["actor_id"] == 1 else [6]
        body = whole
        if source:
            rows = [e for e in events if e["sourceID"] in ids or e["targetID"] in ids]
            body = json.dumps(
                {"data": rows, "nextPageTimestamp": None},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        proof.update(
            identity=None,
            meta={},
            pages=[hashlib.sha256(body).hexdigest()],
            derivation={
                "rule": "source-owned-encounter-all-v1"
                if source
                else "target-equals-encounter-all-v1",
                "parent": parent,
                "parent_pages": parent_proof["pages"],
                **({"actor_ids": ids} if source else {}),
            },
        )
        if mutation == "owner" and source and proof["actor_id"] == 1:
            proof["derivation"]["actor_ids"] = [1]
        if mutation == "bytes" and source and proof["actor_id"] == 1:
            payload = json.loads(body)
            payload["data"].pop()
            body = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
            proof["pages"] = [hashlib.sha256(body).hexdigest()]
        files[
            f"events/ABC/fight_7/{proof['role']}_{proof['actor_id']}_Example/{proof['direction']}_001.json"
        ] = body
    files["necropsy-snapshot.json"] = json.dumps(marker).encode()
    with zipfile.ZipFile(path, "w") as z:
        for name, body in files.items():
            z.writestr(name, body)
    return spec | {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def test_v4_sources_and_targets_preserve_independent_freezer_arithmetic(tmp_path: Path) -> None:
    (tmp_path / "old").mkdir()
    (tmp_path / "new").mkdir()
    before = dps.compute(case(tmp_path / "old"), tmp_path / "old")
    after = dps.compute(v4_case(tmp_path / "new"), tmp_path / "new")
    assert before["totals"] == after["totals"]
    assert before["source_damage"] == after["source_damage"]
    assert before["residual"] == after["residual"]


@pytest.mark.parametrize("mutation", ["owner", "bytes"])
def test_v4_freezer_refuses_forged_projection_even_with_matching_child_hash(
    tmp_path: Path, mutation: str
) -> None:
    with pytest.raises(ValueError, match=r"ownership|projection"):
        dps.compute(v4_case(tmp_path, mutation), tmp_path)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_parent",
        "corrupt",
        "cross_fight",
        "cross_revision",
        "endpoint",
        "rule",
        "derived_source",
        "filtered_parent",
        "parent_envelope",
        "extra_parent_page",
        "missing_parent_page",
        "zone",
    ],
)
def test_a_wrong_derived_target_parent_is_refused(tmp_path: Path, mutation: str) -> None:
    spec = derived_case(tmp_path, mutation)
    with pytest.raises((ValueError, KeyError)):
        dps.compute(spec, tmp_path)


def catalog_case(tmp_path: Path, mutation: str = "") -> dict[str, Any]:
    """The same capture with an extra report-catalog pet of the actor (id 9).

    The selected fight does not list it, and the fight's certified encounter-All
    pages never name it, so only that fight's admission may leave it out (D022).
    """
    spec = case(tmp_path)
    path = tmp_path / spec["archive"]
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}
    marker = json.loads(files["necropsy-snapshot.json"])
    report = json.loads(files["reports/ABC/bundle.json"])["reportData"]["report"]
    actors = report["masterData"]["actors"]
    actors.append(
        {"id": 9, "type": "NPC" if mutation == "not_a_pet" else "Pet", "gameID": 510, "petOwner": 1}
    )
    fight = report["fights"][0]
    if mutation == "listed_owned":
        fight["friendlyPets"].append({"id": 9, "type": "Pet", "gameID": 510, "petOwner": 1})
    if mutation == "listed_other_owner":
        fight["friendlyPets"].append({"id": 9, "type": "Pet", "gameID": 510, "petOwner": 2})
    if mutation == "ownerless_guardian":
        guardian = {"id": 10, "type": "Pet", "gameID": 8836, "petOwner": None}
        actors.append(guardian)
        fight["friendlyPets"].append(guardian)
    rows: list[dict[str, Any]] = []
    for name in sorted(files):
        if name.startswith("events/ABC/fight_7/") and name.rsplit("/", 1)[1].startswith("source_"):
            rows += json.loads(files[name])["data"]
    if mutation == "as_source":
        rows.append({"type": "cast", "sourceID": 9, "targetID": 3, "timestamp": 500, "fight": 7})
    if mutation == "as_target":
        rows.append({"type": "heal", "sourceID": 1, "targetID": 9, "timestamp": 500, "fight": 7})
    if mutation in {"deals_damage", "deals_damage_unpublished", "not_a_pet"}:
        ranked = next(
            r
            for r in rows
            if r.get("type") == "damage" and r.get("sourceID") == 1 and r.get("targetID") == 3
        )
        rows.append(ranked | {"sourceID": 9, "amount": 50, "timestamp": 600})
    if mutation == "deals_damage":
        # 50 more ranked damage over the 10 s fight: published 24.0 -> 29.0.
        board = json.loads(files["leaderboards/51118_Patchwerk.json"])
        board["pages"][0]["characterRankings"]["rankings"][0]["amount"] = 29.0
        files["leaderboards/51118_Patchwerk.json"] = json.dumps(board).encode()
    page: dict[str, Any] = {"data": rows, "nextPageTimestamp": None}
    if mutation == "unterminated":
        page["nextPageTimestamp"] = 600
    whole = json.dumps(page).encode()
    files["events/ABC/fight_7/encounter/all_001.json"] = whole
    identity = {
        **next(p for p in marker["streams"] if p["direction"] == "source")["identity"],
        "actor_id": None,
        "role": "encounter",
        "direction": "all",
    }
    if mutation == "wrong_identity":
        identity["revision"] = 2
    if mutation == "filtered":
        identity["filter_expression"] = "sourceID = 1"
    proof = {
        "report": "ABC",
        "fight": 7,
        "role": "encounter",
        "actor_id": None,
        "direction": "all",
        "identity": identity,
        "pages": ["0" * 64 if mutation == "page_digest" else hashlib.sha256(whole).hexdigest()],
    }
    marker["encounter_streams"] = [] if mutation == "missing_scope" else [proof]
    files["reports/ABC/bundle.json"] = json.dumps({"reportData": {"report": report}}).encode()
    marker["report_sets"][0]["sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    files["necropsy-snapshot.json"] = json.dumps(marker).encode()
    with zipfile.ZipFile(path, "w") as z:
        for name, raw in files.items():
            z.writestr(name, raw)
    return spec | {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def test_agreeing_listings_keep_the_old_output_without_a_scope_record(tmp_path: Path) -> None:
    result = dps.compute(case(tmp_path), tmp_path)
    assert "catalog_pets_out_of_scope" not in result
    assert "fight_active_catalog_units" not in result


@pytest.mark.parametrize("mutation", ["as_source", "as_target"])
def test_a_catalog_unit_named_in_the_fight_is_owned_there(tmp_path: Path, mutation: str) -> None:
    """D028: e.g. a Shaman totem, catalog-owned but absent from friendlyPets."""
    (tmp_path / "plain").mkdir()
    (tmp_path / "unit").mkdir()
    plain = dps.compute(case(tmp_path / "plain"), tmp_path / "plain")
    seen = dps.compute(catalog_case(tmp_path / "unit", mutation), tmp_path / "unit")
    assert seen["totals"] == plain["totals"]
    assert seen["fight_active_catalog_units"] == [
        {"unit": 9, "rule": "catalog-unit-active-in-fight-v1"}
    ]
    assert "catalog_pets_out_of_scope" not in seen


def test_a_fight_active_catalog_units_damage_is_ranked_from_the_encounter_pages(
    tmp_path: Path,
) -> None:
    result = dps.compute(catalog_case(tmp_path, "deals_damage"), tmp_path)
    assert result["totals"]["ranked"] == 290 and result["source_damage"]["9"] == 50
    [event] = [e for e in result["events"] if e["raw"]["sourceID"] == 9]
    assert event["multiplicity"] == 1
    assert event["locators"][0]["member"] == "events/ABC/fight_7/encounter/all_001.json"


def test_dropping_a_fight_active_units_damage_contradicts_the_published_amount(
    tmp_path: Path,
) -> None:
    with pytest.raises(dps.ArithmeticMismatch):
        dps.compute(catalog_case(tmp_path, "deals_damage_unpublished"), tmp_path)


def test_a_catalog_pet_absent_from_the_fight_is_out_of_that_fights_scope(tmp_path: Path) -> None:
    (tmp_path / "plain").mkdir()
    (tmp_path / "extra").mkdir()
    plain = dps.compute(case(tmp_path / "plain"), tmp_path / "plain")
    extra = dps.compute(catalog_case(tmp_path / "extra"), tmp_path / "extra")
    assert extra["totals"] == plain["totals"] and extra["owned_actor_ids"] == [6]
    [record] = extra["catalog_pets_out_of_scope"]
    assert record["pet"] == 9 and record["rule"] == "catalog-pet-absent-from-fight-v1"
    assert len(record["pages"]) == 1


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("not_a_pet", "pet listings disagree"),
        ("listed_owned", "pet listings disagree"),
        ("listed_other_owner", "pet listings disagree"),
        ("ownerless_guardian", "unresolved fight pet ownership"),
        ("missing_scope", "encounter scope not unique"),
        ("unterminated", "unterminated"),
        ("wrong_identity", "encounter scope identity mismatch"),
        ("filtered", "not an exact encounter-All request"),
        ("page_digest", "encounter scope pages differ"),
    ],
)
def test_a_catalog_pet_seen_in_the_fight_or_an_unproven_scope_is_refused(
    tmp_path: Path, mutation: str, reason: str
) -> None:
    spec = catalog_case(tmp_path, mutation)
    with pytest.raises(ValueError, match=reason):
        dps.compute(spec, tmp_path)
