"""Synthetic normal acquisition and versioned encounter-context integrity checks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import duckdb
import httpx
import pytest

from necropsy.normalize.coverage import has_complete_coverage
from necropsy.report.offline import run_offline
from necropsy.snapshot.archive import VerifiedArchive
from necropsy.snapshot.model import ActorRole, Direction, SnapshotError
from necropsy.snapshot.v1 import open_snapshot
from necropsy.snapshot.v1_writer import write_snapshot
from necropsy.wcl.acceptance import check_run
from necropsy.wcl.acquire import Run, acquire, finalize_reports
from necropsy.wcl.cache import Cache
from necropsy.wcl.context import Field
from necropsy.wcl.sites import VANILLA
from tests.integration.test_live_snapshot import _client, _rewrite
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _context

EVENTS = [
    {"timestamp": 1000, "type": "combatantinfo", "sourceID": 5, "faction": 1},
    {"timestamp": 1500, "type": "cast", "sourceID": 5, "targetID": 50, "abilityGameID": 75},
    {
        "timestamp": 1600,
        "type": "damage",
        "sourceID": 5,
        "targetID": 50,
        "abilityGameID": 75,
        "amount": 60,
        "hitType": 1,
    },
    {
        "timestamp": 1700,
        "type": "damage",
        "sourceID": 50,
        "targetID": 5,
        "abilityGameID": 1,
        "amount": 10,
        "hitType": 1,
    },
    {
        "timestamp": 1800,
        "type": "damage",
        "sourceID": 17,
        "targetID": 50,
        "abilityGameID": 10151,
        "amount": 100,
        "hitType": 17,
    },
    {
        "timestamp": 1900,
        "type": "begincast",
        "sourceID": 51,
        "targetID": 50,
        "abilityGameID": 19775,
    },
]


class EncounterWcl(FakeWcl):
    def _report(self, p: Player, wanted: list[int] | None = None) -> dict[str, Any]:
        report = super()._report(p, wanted)
        for fight in report["fights"]:
            fight["encounterID"] = 50669
        report["masterData"]["actors"] += [
            {"id": 50, "name": "Sulfuron", "type": "NPC", "gameID": 12098},
            {"id": 51, "name": "Priest", "type": "NPC", "gameID": 11662},
            {"id": 17, "name": "OtherMage", "type": "Player", "subType": "Mage"},
        ]
        return report

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "NecropsyEvents" not in body["query"]:
            return super().__call__(request)
        self.requests.append(body)
        variables = body["variables"]
        events = EVENTS
        if variables.get("filterExpression"):
            events = [EVENTS[4]]
        elif variables.get("sourceID") is not None:
            events = [e for e in EVENTS if e.get("sourceID") == variables["sourceID"]]
        elif variables.get("targetID") is not None:
            events = [e for e in EVENTS if e.get("targetID") == variables["targetID"]]
        return self._ok(
            {
                "reportData": {
                    "report": {
                        "revision": 4,
                        "events": {"data": events, "nextPageTimestamp": None},
                    }
                }
            }
        )


def _capture(root: Path, enabled: bool) -> Any:
    root.mkdir()
    (root / "cache").mkdir()
    fake = EncounterWcl([Player(f"Ally{i}") for i in range(5)], Player("Haplina"))
    context = _context()
    assert context.partition is not None
    context = replace(
        context,
        zone_id=2000,
        zone_name=Field("Molten Core", "observed", "test"),
        partition=replace(context.partition, id=1),
    )
    client, store = _client(fake), Cache(root / "cache")
    try:
        result = acquire(
            client, store, VANILLA, context, encounters=(50669,), encounter_context=enabled
        )
        assert result.stopped is None
        finalize_reports(Run(client, store, VANILLA), result)
        return write_snapshot(result, store, root, "capture")
    finally:
        client.close()


class NaxxEncounterWcl(EncounterWcl):
    """The same encounter events on a Patchwerk kill in Naxxramas."""

    def _report(self, p: Player, wanted: list[int] | None = None) -> dict[str, Any]:
        report = FakeWcl._report(self, p, wanted)
        report["masterData"]["actors"] += [
            {"id": 50, "name": "Patchwerk", "type": "NPC", "gameID": 16028},
            {"id": 51, "name": "Priest", "type": "NPC", "gameID": 11662},
            {"id": 17, "name": "OtherMage", "type": "Player", "subType": "Mage"},
        ]
        return report


def _naxx_capture(root: Path, enabled: bool) -> Any:
    root.mkdir()
    (root / "cache").mkdir()
    fake = NaxxEncounterWcl([Player(f"Ally{i}") for i in range(5)], Player("Haplina"))
    context = _context()
    assert context.partition is not None
    context = replace(context, zone_id=2006, partition=replace(context.partition, id=1))
    client, store = _client(fake), Cache(root / "cache")
    try:
        result = acquire(
            client, store, VANILLA, context, encounters=(PATCHWERK,), encounter_context=enabled
        )
        assert result.stopped is None
        finalize_reports(Run(client, store, VANILLA), result)
        return write_snapshot(result, store, root, "capture")
    finally:
        client.close()


@pytest.mark.parametrize("enabled", [True, False])
def test_naxx_encounter_context_needs_a_v2_capture(tmp_path: Path, enabled: bool) -> None:
    """Naxxramas gains encounter context only from a capture that carries its streams."""
    written = _naxx_capture(tmp_path / "capture", enabled)
    with VerifiedArchive(written.archive) as archive:
        reader = open_snapshot(archive)
        assert reader.issues() == []
        assert reader.descriptor().format == (
            "necropsy-live-snapshot-v2" if enabled else "necropsy-live-snapshot-v1"
        )
        scopes = {r.role for r in reader.expected_streams() if r.direction is Direction.ALL}
        assert scopes == ({ActorRole.ENCOUNTER, ActorRole.CRITICAL} if enabled else set())
    out = tmp_path / "report"
    run_offline(written.archive, out, db=tmp_path / "analysis.duckdb")
    doc = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    [boss] = doc["bosses"]
    assert boss["encounter_id"] == PATCHWERK
    assert ("duty_context" in boss["playbook"]) is enabled


@pytest.fixture(scope="module")
def encounter_capture(tmp_path_factory: pytest.TempPathFactory) -> Any:
    return _capture(tmp_path_factory.mktemp("encounter") / "capture", True)


def test_encounter_context_reaches_normalized_events_both_pages_and_package(
    encounter_capture: Any, tmp_path: Path
) -> None:
    written = encounter_capture
    with VerifiedArchive(written.archive) as archive:
        reader = open_snapshot(archive)
        assert reader.descriptor().format == "necropsy-live-snapshot-v2"
        assert reader.issues() == []
        scopes = [r for r in reader.expected_streams() if r.direction is Direction.ALL]
        assert len(scopes) == 12
        assert all(r.actor_id is None for r in scopes)
        assert {r.role for r in scopes} == {ActorRole.ENCOUNTER, ActorRole.CRITICAL}
    db = tmp_path / "analysis.duckdb"
    out = tmp_path / "report"
    run_offline(written.archive, out, db=db)
    with duckdb.connect(str(db), read_only=True) as con:
        assert con.execute("SELECT count(*) FROM events").fetchone() == (36,)
        assert con.execute(
            "SELECT sum(amount) FROM events WHERE source_id=5 AND type='damage'"
        ).fetchone() == (360,)
        assert con.execute("SELECT count(*) FROM events WHERE source_id=17").fetchone() == (6,)
        assert has_complete_coverage(con, "RHaplina", 3, 5, Direction.SOURCE)
        assert not has_complete_coverage(con, "RHaplina", 3, 17, Direction.SOURCE)
        assert con.execute("SELECT count(*) FROM event_anomalies").fetchone() == (0,)
    doc = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    assert doc["bosses"][0]["subject"]["ranking"]["ranked"]["value"] is None
    assert (out / "report.html").is_file() and (out / "playbook.html").is_file()
    assert list(out.glob("necropsy-*.zip"))
    assert check_run(out, written.archive, written.entries, written.sha256, requested=(50669,))[
        "package_sha256"
    ]


def test_default_acquisition_still_writes_only_v1_actor_streams(tmp_path: Path) -> None:
    written = _capture(tmp_path / "capture", False)
    with VerifiedArchive(written.archive) as archive:
        marker = archive.read_json("necropsy-snapshot.json")
        assert marker["formatVersion"] == 1 and "encounter_streams" not in marker
        assert not any("/encounter/" in n for n in archive.names())
        assert all(
            r.direction is not Direction.ALL for r in open_snapshot(archive).expected_streams()
        )


@pytest.mark.parametrize("zone,partition", [(2006, 3), (2000, 3), (2002, 7), (2005, 11)])
def test_encounter_collection_refuses_other_rulesets_before_any_request(
    tmp_path: Path, zone: int, partition: int
) -> None:
    context = _context()
    assert context.partition is not None
    context = replace(context, zone_id=zone, partition=replace(context.partition, id=partition))
    fake = EncounterWcl([], Player("Haplina"))
    client, store = _client(fake), Cache(tmp_path)
    try:
        with pytest.raises(ValueError, match="Era raid partition"):
            acquire(client, store, VANILLA, context, encounters=(50669,), encounter_context=True)
        assert fake.requests == []
    finally:
        client.close()


@pytest.mark.parametrize(
    "case",
    [
        "missing-proof",
        "duplicate-proof",
        "filter",
        "bounds",
        "revision",
        "actor",
        "direction",
        "missing-page",
        "extra-page",
        "digest",
        "critical-not-subset",
        "actor-not-subset",
        "global-extra-owned",
        "cursor",
        "fight",
        "v1",
        "unsupported-version",
    ],
)
def test_encounter_context_rejects_wrong_scope_content_and_completion(
    encounter_capture: Any, tmp_path: Path, case: str
) -> None:
    def change(members: dict[str, bytes]) -> None:
        marker = json.loads(members["necropsy-snapshot.json"])
        proof = next(p for p in marker["encounter_streams"] if p["role"] == "critical")
        prefix = f"events/{proof['report']}/fight_{proof['fight']}/encounter/"
        name = prefix + "critical_001.json"
        if case == "missing-proof":
            marker["encounter_streams"].remove(proof)
        elif case == "duplicate-proof":
            marker["encounter_streams"].append(proof)
        elif case == "filter":
            proof["identity"]["filter_expression"] = 'type = "damage"'
        elif case == "bounds":
            proof["identity"]["start_time"] += 1
        elif case == "revision":
            proof["identity"]["revision"] += 1
        elif case == "actor":
            proof["actor_id"] = 0
        elif case == "direction":
            proof["direction"] = "source"
        elif case == "missing-page":
            del members[name]
        elif case == "extra-page":
            members[prefix + "all_002.json"] = members[name]
        elif case in {
            "digest",
            "critical-not-subset",
            "actor-not-subset",
            "global-extra-owned",
            "cursor",
        }:
            if case in {"actor-not-subset", "global-extra-owned"}:
                proof = next(
                    p
                    for p in marker["encounter_streams"]
                    if p["report"] == proof["report"] and p["role"] == "encounter"
                )
                name = prefix + "all_001.json"
            page = json.loads(members[name])
            if case == "cursor":
                page["nextPageTimestamp"] = 2000
            elif case == "actor-not-subset":
                page["data"] = [EVENTS[4]]
            elif case == "global-extra-owned":
                page["data"].append({**EVENTS[2], "amount": 40})
            else:
                page["data"][0]["amount"] += 1
            members[name] = json.dumps(page).encode()
            if case != "digest":
                proof["pages"] = [hashlib.sha256(members[name]).hexdigest()]
        elif case == "fight":
            proof["fight"] += 1
        elif case == "v1":
            marker["formatVersion"] = 1
        elif case == "unsupported-version":
            marker["formatVersion"] = 3
        members["necropsy-snapshot.json"] = json.dumps(marker).encode()

    bad = _rewrite(encounter_capture, tmp_path / "bad.zip", change)
    with VerifiedArchive(bad) as archive, pytest.raises(SnapshotError):
        open_snapshot(archive)
