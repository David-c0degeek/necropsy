"""Naxx captures take actor target streams from the fight's certified encounter-All pages."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

from necropsy.snapshot.archive import EntryOrigin, VerifiedArchive, load_entries_manifest
from necropsy.snapshot.model import SnapshotError
from necropsy.snapshot.v1 import open_snapshot
from necropsy.snapshot.v1_writer import write_snapshot
from necropsy.wcl.acquire import Run, acquire, finalize_reports
from necropsy.wcl.cache import Cache
from necropsy.wcl.context import Field
from necropsy.wcl.sites import VANILLA
from tests.integration.test_encounter_snapshot import EVENTS, EncounterWcl, NaxxEncounterWcl
from tests.integration.test_live_snapshot import _client, _rewrite
from tests.unit.test_wcl_acquire import PATCHWERK, Player, _context


def _capture(root: Path, naxx: bool) -> tuple[Any, list[dict[str, Any]]]:
    root.mkdir()
    (root / "cache").mkdir()
    players = [Player(f"Ally{i}") for i in range(5)]
    fake = (NaxxEncounterWcl if naxx else EncounterWcl)(players, Player("Haplina"))
    context = _context()
    assert context.partition is not None
    context = replace(context, partition=replace(context.partition, id=1))
    if naxx:
        context, encounter = replace(context, zone_id=2006), PATCHWERK
    else:
        zone = Field("Molten Core", "observed", "test")
        context, encounter = replace(context, zone_id=2000, zone_name=zone), 50669
    client, store = _client(fake), Cache(root / "cache")
    try:
        result = acquire(
            client, store, VANILLA, context, encounters=(encounter,), encounter_context=True
        )
        assert result.stopped is None
        finalize_reports(Run(client, store, VANILLA), result)
        return write_snapshot(result, store, root, "capture"), fake.requests
    finally:
        client.close()


def _event_requests(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r["variables"] for r in requests if "NecropsyEvents" in r["query"]]


@pytest.fixture(scope="module")
def naxx(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, list[dict[str, Any]]]:
    return _capture(tmp_path_factory.mktemp("derived") / "naxx", True)


def test_naxx_requests_no_actor_target_stream_and_copies_the_encounter_pages(naxx: Any) -> None:
    written, requests = naxx
    events = _event_requests(requests)
    assert events and not any(v.get("targetID") is not None for v in events)
    assert any(v.get("sourceID") is not None for v in events)
    entries = load_entries_manifest(written.entries)
    with VerifiedArchive(written.archive) as archive:
        reader = open_snapshot(archive)
        assert reader.issues() == []
        assert reader.descriptor().format == "necropsy-live-snapshot-v3"
        marker = archive.read_json("necropsy-snapshot.json")
        assert marker["formatVersion"] == 3
        parents = {
            (p["report"], p["fight"]): p
            for p in marker["encounter_streams"]
            if p["role"] == "encounter"
        }
        targets = [s for s in marker["streams"] if s["direction"] == "target"]
        sources = [s for s in marker["streams"] if s["direction"] == "source"]
        assert targets and sources
        assert all(s["identity"] is not None and "derivation" not in s for s in sources)
        for stream in targets:
            parent = parents[(stream["report"], stream["fight"])]
            assert stream["identity"] is None and stream["meta"] == {}
            assert stream["derivation"] == {
                "rule": "target-equals-encounter-all-v1",
                "parent": parent["identity"],
                "parent_pages": parent["pages"],
            }
            assert stream["pages"] == parent["pages"]
        for name, entry in entries.items():
            if "/target_" in name:
                assert entry.origin is EntryOrigin.GENERATED
                fight = name.split("/")[2]
                twin = f"events/{name.split('/')[1]}/{fight}/encounter/all_{name[-8:]}"
                assert archive.read_bytes(name) == archive.read_bytes(twin)
            elif (name.startswith("events/") and "/source_" in name) or "/encounter/" in name:
                assert entry.origin is EntryOrigin.ACQUIRED


def test_other_raids_keep_requesting_actor_target_streams(tmp_path: Path) -> None:
    written, requests = _capture(tmp_path / "mc", False)
    assert any(v.get("targetID") is not None for v in _event_requests(requests))
    with VerifiedArchive(written.archive) as archive:
        assert open_snapshot(archive).descriptor().format == "necropsy-live-snapshot-v2"
        marker = archive.read_json("necropsy-snapshot.json")
        assert marker["formatVersion"] == 2
        assert all("derivation" not in s for s in marker["streams"])


def _target(marker: dict[str, Any]) -> dict[str, Any]:
    return next(s for s in marker["streams"] if s["direction"] == "target")


def _break(case: str, members: dict[str, bytes]) -> None:
    marker = json.loads(members["necropsy-snapshot.json"])
    stream = _target(marker)
    derivation = stream["derivation"]
    if case == "rule":
        derivation["rule"] = "target-equals-encounter-all-v2"
    elif case == "parent-revision":
        derivation["parent"]["revision"] += 1
    elif case == "parent-endpoint":
        derivation["parent"]["endpoint"] = (
            "user" if derivation["parent"]["endpoint"] == "client" else "client"
        )
    elif case == "parent-pages":
        derivation["parent_pages"] = ["0" * 64]
    elif case == "both-provenances":
        source = next(s for s in marker["streams"] if s["direction"] == "source")
        stream["identity"] = dict(source["identity"], direction="target")
    elif case == "no-provenance":
        del stream["derivation"]
    elif case == "derived-source":
        source = next(s for s in marker["streams"] if s["direction"] == "source")
        source["identity"], source["derivation"] = None, derivation
    elif case == "cross-fight":
        stream["fight"] += 1
    elif case == "page-bytes":
        name = next(n for n in members if "/target_" in n)
        page = json.loads(members[name])
        page["data"] = page["data"][:-1]
        members[name] = json.dumps(page).encode()
        digest = hashlib.sha256(members[name]).hexdigest()
        stream["pages"] = derivation["parent_pages"] = [digest]
    elif case == "missing-page":
        del members[next(n for n in members if "/target_" in n)]
    elif case == "no-derived-stream":
        for s in marker["streams"]:
            if "derivation" in s:
                del s["derivation"]
                s["identity"] = dict(s["identity"] or {}, direction="target")
    elif case == "not-naxx":
        marker["zone"]["id"] = 2000
    elif case == "as-v2":
        marker["formatVersion"] = 2
    elif case == "as-v1":
        marker["formatVersion"] = 1
    members["necropsy-snapshot.json"] = json.dumps(marker).encode()


@pytest.mark.parametrize(
    "case",
    [
        "rule",
        "parent-revision",
        "parent-endpoint",
        "parent-pages",
        "both-provenances",
        "no-provenance",
        "derived-source",
        "cross-fight",
        "page-bytes",
        "missing-page",
        "no-derived-stream",
        "not-naxx",
        "as-v2",
        "as-v1",
    ],
)
def test_a_wrong_derivation_is_refused(naxx: Any, tmp_path: Path, case: str) -> None:
    written, _ = naxx
    bad = _rewrite(written, tmp_path / "bad.zip", lambda members: _break(case, members))
    with VerifiedArchive(bad) as archive, pytest.raises(SnapshotError):
        open_snapshot(archive)


class RevisedNaxxWcl(NaxxEncounterWcl):
    """Event pages report the code's current revision, so a bundle can go stale."""

    def __call__(self, request: httpx.Request) -> httpx.Response:
        response = super().__call__(request)
        body = json.loads(request.content)
        if "NecropsyEvents" not in body["query"]:
            return response
        data = response.json()
        code = body["variables"]["code"]
        data["data"]["reportData"]["report"]["revision"] = self._revision(code, peek=True)
        return httpx.Response(200, json=data)


class AllFailsWcl(NaxxEncounterWcl):
    """The whole-fight request hits the points limit."""

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        v = body["variables"]
        whole = "NecropsyEvents" in body["query"] and not any(
            v.get(k) is not None for k in ("sourceID", "targetID", "filterExpression")
        )
        if whole:
            self.requests.append(body)
            data = {
                "rateLimitData": {
                    "limitPerHour": 3000,
                    "pointsSpentThisHour": 36000,
                    "pointsResetIn": 3000,
                }
            }
            return httpx.Response(200, json={"data": {"x": 1, **data}})
        return super().__call__(request)


def _acquire(fake: Any, root: Path, *, zones: Any = None) -> Any:
    (root / "cache").mkdir(parents=True, exist_ok=True)
    context = _context()
    assert context.partition is not None
    context = replace(context, zone_id=2006, partition=replace(context.partition, id=1))
    client, store = _client(fake), Cache(root / "cache")
    try:
        with pytest.MonkeyPatch.context() as patch:
            if zones is not None:
                patch.setattr("necropsy.wcl.acquire.DERIVED_TARGET_ZONES", zones)
            result = acquire(
                client, store, VANILLA, context, encounters=(PATCHWERK,), encounter_context=True
            )
        return result, store, client
    except Exception:
        client.close()
        raise


def test_no_actor_request_or_derivation_follows_a_failed_encounter_all(tmp_path: Path) -> None:
    fake = AllFailsWcl([Player(f"Ally{i}") for i in range(5)], Player("Haplina"))
    result, _, client = _acquire(fake, tmp_path / "run")
    client.close()
    assert result.stopped is not None
    events = _event_requests(fake.requests)
    assert events, "the whole-fight request was attempted"
    whole = next(
        i
        for i, v in enumerate(events)
        if not any(v.get(k) is not None for k in ("sourceID", "targetID", "filterExpression"))
    )
    assert all(v.get("sourceID") is None and v.get("targetID") is None for v in events[whole:])
    entries = [b.subject for b in result.bosses if b.subject is not None]
    assert all(not e.streams for e in entries)


def test_a_legacy_target_cache_entry_never_feeds_a_derived_stream(tmp_path: Path) -> None:
    players = [Player(f"Ally{i}") for i in range(5)]
    legacy = NaxxEncounterWcl(players, Player("Haplina"))
    _, store, client = _acquire(legacy, tmp_path / "run", zones=frozenset())
    client.close()
    assert any(v.get("targetID") is not None for v in _event_requests(legacy.requests))
    cached = [p for p in (tmp_path / "run" / "cache").rglob("*") if "_target" in p.name]
    assert cached, "the legacy run left actor-target cache entries behind"
    fresh = NaxxEncounterWcl(players, Player("Haplina"))
    result, store, client = _acquire(fresh, tmp_path / "run")
    try:
        finalize_reports(Run(client, store, VANILLA), result)
        written = write_snapshot(result, store, tmp_path / "run", "capture")
    finally:
        client.close()
    with VerifiedArchive(written.archive) as archive:
        reader = open_snapshot(archive)
        assert reader.issues() == []
        names = archive.names()
        targets = [n for n in names if "/target_" in n]
        assert targets
        for name in targets:
            fight = "/".join(name.split("/")[:3])
            assert archive.read_bytes(name) == archive.read_bytes(
                f"{fight}/encounter/all_{name[-8:]}"
            )
    # The cached legacy target pages hold only the actor's incoming rows, not the fight.
    legacy_rows = [e for e in EVENTS if e.get("targetID") == 5]
    assert len(legacy_rows) < len(EVENTS)


def test_a_revision_change_derives_from_the_new_parent_only(tmp_path: Path) -> None:
    fake = RevisedNaxxWcl(
        [Player(f"Ally{i}") for i in range(5)],
        Player("Haplina"),
        revisions={"RHaplina": [4, 5]},
    )
    result, store, client = _acquire(fake, tmp_path / "run")
    try:
        assert result.stopped is None
        assert result.bosses[0].subject is not None
        assert result.bosses[0].subject.generations == 2  # the stale bundle was refetched
        finalize_reports(Run(client, store, VANILLA), result)
        written = write_snapshot(result, store, tmp_path / "run", "capture")
    finally:
        client.close()
    with VerifiedArchive(written.archive) as archive:
        assert open_snapshot(archive).issues() == []
        marker = archive.read_json("necropsy-snapshot.json")
    revisions = {s["report"]: s["revision"] for s in marker["report_sets"]}
    for stream in marker["streams"]:
        identity = stream["identity"] or stream["derivation"]["parent"]
        assert identity["revision"] == revisions[stream["report"]]
    assert revisions["RHaplina"] == 5
