"""V4 fetches one All scope and proves exact derived views, with safe legacy/fallback paths."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest
from necropsy.snapshot.model import SnapshotError
from necropsy.snapshot.v1 import open_snapshot
from necropsy.snapshot.v1_writer import write_snapshot
from necropsy.wcl.acquire import Run, acquire, finalize_reports
from necropsy.wcl.cache import Cache, CacheCorrupt
from scripts.check_raid_facts import raw_actor_facts
from scripts.raw_projection import verify_projection
from tests.integration.test_encounter_snapshot import EVENTS, NaxxEncounterWcl
from tests.integration.test_live_snapshot import _client, _rewrite
from tests.unit.test_wcl_acquire import PATCHWERK, Player, _context


class ViewWcl(NaxxEncounterWcl):
    encounter_id = PATCHWERK

    def _report(self, player: Player, wanted: list[int] | None = None) -> dict[str, Any]:
        report = super()._report(player, wanted)
        for fight in report["fights"]:
            fight["encounterID"] = self.encounter_id
        return report

    def __init__(self, *, unknown_hit: bool = False, incomplete_pets: bool = False) -> None:
        super().__init__(
            [Player(f"Ally{i}", pets=[7], pet_list=not incomplete_pets) for i in range(5)],
            Player("Haplina", pets=[7], pet_list=not incomplete_pets),
        )
        self.rows: list[dict[str, Any]] = [dict(e) for e in EVENTS]
        self.rows += [
            {
                "timestamp": 1850,
                "type": "damage",
                "sourceID": 7,
                "targetID": 50,
                "abilityGameID": 75,
                "amount": 15,
                "hitType": 2,
            },
            {
                "timestamp": 1850,
                "type": "damage",
                "sourceID": 7,
                "targetID": 50,
                "abilityGameID": 75,
                "amount": 15,
                "hitType": 2,
            },
        ]
        if unknown_hit:
            self.rows.append(
                {
                    "timestamp": 2000,
                    "type": "damage",
                    "sourceID": 5,
                    "targetID": 50,
                    "amount": 9,
                    "hitType": 999,
                }
            )
        self.rows.sort(key=lambda e: e["timestamp"])

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "NecropsyEvents" not in body["query"]:
            return super().__call__(request)
        self.requests.append(body)
        variables = body["variables"]
        floor = variables["startTime"]
        rows = [e for e in self.rows if e["timestamp"] >= floor]
        if variables.get("filterExpression"):
            rows = [e for e in rows if e["type"] == "damage" and e.get("hitType") in {2, 5, 17}]
        elif variables.get("sourceID") is not None:
            ids = {variables["sourceID"]}
            if variables["sourceID"] == 5:
                ids.add(7)
            rows = [e for e in rows if e.get("sourceID") in ids or e.get("targetID") in ids]
        cursor = 1700 if floor < 1700 else None
        if cursor is not None:
            rows = [e for e in rows if e["timestamp"] < cursor]
        return self._ok(
            {
                "reportData": {
                    "report": {"revision": 4, "events": {"data": rows, "nextPageTimestamp": cursor}}
                }
            }
        )


def capture(
    root: Path,
    *,
    enabled: bool = True,
    fake: ViewWcl | None = None,
    cache: Path | None = None,
    partition: int = 1,
    zone: int = 2006,
) -> tuple[Any, ViewWcl]:
    root.mkdir()
    cache = cache or root / "cache"
    cache.mkdir(exist_ok=True)
    fake = fake or ViewWcl()
    fake.encounter_id = {2006: PATCHWERK, 2000: 50669, 2002: 50631, 2005: 50713}[zone]
    context = _context()
    assert context.partition is not None
    context = replace(context, zone_id=zone, partition=replace(context.partition, id=partition))
    client, store = _client(fake), Cache(cache)
    try:
        result = acquire(
            client,
            store,
            context=context,
            site=client.site,
            encounters=(fake.encounter_id,),
            encounter_context=True,
            derive_views=enabled,
        )
        assert result.stopped is None
        finalize_reports(Run(client, store, client.site), result)
        return write_snapshot(result, store, root, "capture"), fake
    finally:
        client.close()


@pytest.fixture(scope="module")
def v4(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, ViewWcl]:
    return capture(tmp_path_factory.mktemp("v4") / "new")


def test_one_all_request_scope_serves_actor_source_target_and_critical(v4: Any) -> None:
    written, fake = v4
    requests = [r["variables"] for r in fake.requests if "NecropsyEvents" in r["query"]]
    assert len(requests) == 8  # four distinct reports, two All pages per fight
    assert all(
        r["sourceID"] is None and r["targetID"] is None and "filterExpression" not in r
        for r in requests
    )
    with VerifiedArchive(
        written.archive,
        expected_sha256=written.sha256,
        entries=load_entries_manifest(written.entries),
    ) as archive:
        reader = open_snapshot(archive)
        assert reader.descriptor().format == "necropsy-live-snapshot-v4"
        marker = archive.read_json("necropsy-snapshot.json")
        assert all(s["identity"] is None and s["meta"] == {} for s in marker["streams"])
        assert all(
            s["identity"] is None for s in marker["encounter_streams"] if s["role"] == "critical"
        )
        reports = {r["code"]: r for r in reader.reports()}
        for proof in [*marker["streams"], *marker["encounter_streams"]]:
            if "derivation" in proof:
                verify_projection(archive, marker, proof, reports[proof["report"]])
        assert any(
            archive.read_json(n)["data"] == []
            for n in archive.names()
            if "/pet_7_" in n and "/source_001" in n
        )


@pytest.mark.parametrize("zone", [2000, 2002, 2005])
@pytest.mark.parametrize("partition", [1, 2])
def test_other_era_raids_reuse_all_with_native_and_independent_proofs(
    tmp_path: Path, zone: int, partition: int
) -> None:
    written, fake = capture(tmp_path / "new", zone=zone, partition=partition)
    requests = [r["variables"] for r in fake.requests if "NecropsyEvents" in r["query"]]
    assert len(requests) == 8
    assert all(r["sourceID"] is None and r["targetID"] is None for r in requests)
    with VerifiedArchive(written.archive) as archive:
        assert open_snapshot(archive).descriptor().format == "necropsy-live-snapshot-v4"
        marker = archive.read_json("necropsy-snapshot.json")
        reports = {r["code"]: r for r in open_snapshot(archive).reports()}
        for proof in (*marker["streams"], *marker["encounter_streams"]):
            if proof.get("derivation"):
                verify_projection(archive, marker, proof, reports[proof["report"]])


@pytest.mark.parametrize("zone", [2000, 2002, 2005])
def test_other_raids_resume_requested_legacy_scopes_with_v4_target_proof(
    tmp_path: Path, zone: int
) -> None:
    old, _ = capture(tmp_path / "old", zone=zone, enabled=False)
    new, fake = capture(tmp_path / "new", zone=zone, cache=tmp_path / "old/cache")
    assert not any("NecropsyEvents" in r["query"] for r in fake.requests)
    with VerifiedArchive(old.archive) as before, VerifiedArchive(new.archive) as after:
        assert open_snapshot(before).descriptor().format == "necropsy-live-snapshot-v2"
        assert open_snapshot(after).descriptor().format == "necropsy-live-snapshot-v4"
        marker = after.read_json("necropsy-snapshot.json")
        assert all(s["identity"] for s in marker["streams"] if s["direction"] == "source")


def test_raw_actor_and_encounter_measurements_equal_requested_scopes(
    v4: Any, tmp_path: Path
) -> None:
    old, fake = capture(tmp_path / "old", enabled=False)
    new = v4[0]
    assert len([r for r in fake.requests if "NecropsyEvents" in r["query"]]) == 32
    with VerifiedArchive(old.archive) as before, VerifiedArchive(new.archive) as after:
        for code in ("RHaplina", "RAlly0", "RAlly1", "RAlly2"):
            for actor in (5,):
                assert raw_actor_facts(
                    before, code, 3, actor, encounter_context=True
                ) == raw_actor_facts(after, code, 3, actor, encounter_context=True)


def test_independent_oracle_accepts_the_other_supported_partition(tmp_path: Path) -> None:
    written, _ = capture(tmp_path / "partition2", partition=2)
    with VerifiedArchive(written.archive) as archive:
        reader = open_snapshot(archive)
        marker = archive.read_json("necropsy-snapshot.json")
        reports = {r["code"]: r for r in reader.reports()}
        for proof in (*marker["streams"], *marker["encounter_streams"]):
            if "derivation" in proof:
                verify_projection(archive, marker, proof, reports[proof["report"]])


def test_unknown_damage_hit_type_falls_back_to_requested_critical(tmp_path: Path) -> None:
    written, fake = capture(tmp_path / "unknown", fake=ViewWcl(unknown_hit=True))
    with VerifiedArchive(written.archive) as archive:
        open_snapshot(archive)
        marker = archive.read_json("necropsy-snapshot.json")
        assert all(
            s["identity"] is not None and "derivation" not in s
            for s in marker["encounter_streams"]
            if s["role"] == "critical"
        )
    assert any(r["variables"].get("filterExpression") for r in fake.requests)


def test_incomplete_pet_ownership_falls_back_to_requested_source(tmp_path: Path) -> None:
    written, fake = capture(tmp_path / "incomplete", fake=ViewWcl(incomplete_pets=True))
    with VerifiedArchive(written.archive) as archive:
        open_snapshot(archive)
        marker = archive.read_json("necropsy-snapshot.json")
        assert all(
            s["identity"] is not None for s in marker["streams"] if s["direction"] == "source"
        )
    assert any(r["variables"].get("sourceID") is not None for r in fake.requests)


def test_resume_prefers_existing_requested_cache_and_never_downloads_events_again(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "cache"
    old, _ = capture(tmp_path / "old", enabled=False, cache=cache)
    new, fake = capture(tmp_path / "new", cache=cache)
    assert not [r for r in fake.requests if "NecropsyEvents" in r["query"]]
    with VerifiedArchive(old.archive) as a, VerifiedArchive(new.archive) as b:
        assert open_snapshot(b).descriptor().format == "necropsy-live-snapshot-v3"
        assert raw_actor_facts(a, "RHaplina", 3, 5, encounter_context=True) == raw_actor_facts(
            b, "RHaplina", 3, 5, encounter_context=True
        )


@pytest.mark.parametrize("scope", ["player_5_source", "encounter"])
def test_corrupt_existing_cache_is_refused_instead_of_hidden_by_derivation(
    tmp_path: Path, scope: str
) -> None:
    cache = tmp_path / "cache"
    capture(tmp_path / "old", enabled=False, cache=cache)
    page = next(
        p for p in cache.rglob("page_001.json") if "RHaplina" in p.parts and scope in p.parent.name
    )
    page.write_bytes(page.read_bytes() + b" ")
    fake = ViewWcl()
    with pytest.raises(CacheCorrupt):
        capture(tmp_path / "new", cache=cache, fake=fake)
    assert not any("NecropsyEvents" in r["query"] for r in fake.requests)


@pytest.mark.parametrize("kind", ["unknown-hit", "unknown-ownership"])
def test_unsupported_requested_scope_cannot_be_relabelled_as_derived(
    tmp_path: Path, kind: str
) -> None:
    written, _ = capture(
        tmp_path / "input",
        fake=ViewWcl(
            unknown_hit=kind == "unknown-hit", incomplete_pets=kind == "unknown-ownership"
        ),
    )

    def edit(members: dict[str, bytes]) -> None:
        marker = json.loads(members["necropsy-snapshot.json"])
        proof = next(
            s
            for s in (marker["encounter_streams"] if kind == "unknown-hit" else marker["streams"])
            if (
                s["role"] == "critical"
                if kind == "unknown-hit"
                else s["role"] == "player" and s["direction"] == "source"
            )
        )
        parent = next(
            p
            for p in marker["encounter_streams"]
            if p["role"] == "encounter"
            and (p["report"], p["fight"]) == (proof["report"], proof["fight"])
        )
        proof["identity"], proof["meta"] = None, {}
        proof["derivation"] = {
            "rule": "critical-hit-type-encounter-all-v1"
            if kind == "unknown-hit"
            else "source-owned-encounter-all-v1",
            "parent": parent["identity"],
            "parent_pages": parent["pages"],
        }
        if kind == "unknown-ownership":
            proof["derivation"]["actor_ids"] = [5, 7]
        members["necropsy-snapshot.json"] = json.dumps(marker).encode()

    bad = _rewrite(written, tmp_path / "bad.zip", edit)
    with VerifiedArchive(bad) as archive:
        with pytest.raises(SnapshotError, match=r"hit type|ownership"):
            open_snapshot(archive)
        marker = archive.read_json("necropsy-snapshot.json")
        proof = next(
            p
            for p in (*marker["streams"], *marker["encounter_streams"])
            if p.get("derivation", {}).get("rule")
            == (
                "critical-hit-type-encounter-all-v1"
                if kind == "unknown-hit"
                else "source-owned-encounter-all-v1"
            )
            and p["identity"] is None
        )
        report = archive.read_json(f"reports/{proof['report']}/bundle.json")["reportData"]["report"]
        with pytest.raises(ValueError, match=r"hit type|ownership"):
            verify_projection(archive, marker, proof, report)


def corrupt(case: str, members: dict[str, bytes]) -> None:
    marker = json.loads(members["necropsy-snapshot.json"])
    source = next(
        s for s in marker["streams"] if s["direction"] == "source" and s["role"] == "player"
    )
    critical = next(s for s in marker["encounter_streams"] if s["role"] == "critical")
    proof = critical if case.startswith("critical") else source
    if case == "actor-ids":
        proof["derivation"]["actor_ids"].append(50)
    elif case == "rule":
        proof["derivation"]["rule"] = "source-owned-encounter-all-v2"
    elif case == "parent-revision":
        proof["derivation"]["parent"]["revision"] += 1
    elif case == "parent-endpoint":
        proof["derivation"]["parent"]["endpoint"] = "user"
    elif case == "parent-digest":
        proof["derivation"]["parent_pages"][0] = "0" * 64
    elif case == "cost":
        proof["meta"] = {"current_request": {"total": 0}}
    elif case == "api-identity":
        proof["identity"] = dict(proof["derivation"]["parent"])
    elif case == "as-v3":
        marker["formatVersion"] = 3
    elif case == "original-missing":
        del members[f"reports/{source['report']}/fight_{source['fight']}.json"]
    elif case == "original-owner-missing-rehashed":
        name = f"reports/{source['report']}/fight_{source['fight']}.json"
        original = json.loads(members[name])
        original["report"]["fights"][0]["friendlyPets"][0].pop("petOwner")
        members[name] = json.dumps(original).encode()
        for boss in marker["bosses"]:
            for entry in [
                boss.get("subject"),
                *(boss.get("cohort") or []),
                boss.get("cross_faction"),
            ]:
                if entry and (entry["report"], entry["fight"]) == (
                    source["report"],
                    source["fight"],
                ):
                    entry["bundle_generation"]["sha256"] = hashlib.sha256(members[name]).hexdigest()
    elif case == "parent-missing":
        del members[f"events/{source['report']}/fight_{source['fight']}/encounter/all_001.json"]
    elif case in {"source-bytes-rehashed", "critical-bytes-rehashed", "source-order-rehashed"}:
        prefix = f"events/{proof['report']}/fight_{proof['fight']}/"
        names = sorted(
            n
            for n in members
            if n.startswith(prefix)
            and (
                "/critical_" in n
                if proof is critical
                else f"/player_{proof['actor_id']}_" in n and "/source_" in n
            )
        )
        name = names[-1]
        page = json.loads(members[name])
        if case == "source-order-rehashed":
            page["data"].reverse()
        else:
            page["data"] = page["data"][:-1]
        members[name] = json.dumps(
            page, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        proof["pages"][-1] = hashlib.sha256(members[name]).hexdigest()
    members["necropsy-snapshot.json"] = json.dumps(marker).encode()


@pytest.mark.parametrize(
    "case",
    [
        "actor-ids",
        "rule",
        "parent-revision",
        "parent-endpoint",
        "parent-digest",
        "cost",
        "api-identity",
        "as-v3",
        "source-bytes-rehashed",
        "critical-bytes-rehashed",
        "source-order-rehashed",
        "original-missing",
        "original-owner-missing-rehashed",
        "parent-missing",
    ],
)
def test_reader_and_independent_oracle_reject_forged_projection(
    v4: Any, tmp_path: Path, case: str
) -> None:
    bad = _rewrite(v4[0], tmp_path / "bad.zip", lambda members: corrupt(case, members))
    with VerifiedArchive(bad) as archive:
        with pytest.raises(SnapshotError):
            open_snapshot(archive)
        marker = archive.read_json("necropsy-snapshot.json")
        proofs = [*marker["streams"], *marker["encounter_streams"]]
        failures = 0
        for proof in proofs:
            if "derivation" not in proof:
                continue
            report = archive.read_json(f"reports/{proof['report']}/bundle.json")["reportData"][
                "report"
            ]
            try:
                verify_projection(archive, marker, proof, report)
            except ValueError, KeyError, TypeError:
                failures += 1
        assert failures > 0
