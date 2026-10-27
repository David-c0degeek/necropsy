"""Acquisition orchestration against a fake Warcraft Logs server.

Every response is SYNTHETIC, shaped like the recorded exporter's queries (subject
encounterRankings, characterRankings pages, report bundles with masterData and
playerDetails, events pages). No credentials and no network are involved.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pytest

from necropsy.analysis.evidence import Faction
from necropsy.wcl import client as c
from necropsy.wcl.acquire import Run, acquire, fight_pets, finalize_reports, pick_subject
from necropsy.wcl.cache import Cache
from necropsy.wcl.context import SUPPORTED_ZONE_ID, CharacterContext, Field, Partition
from necropsy.wcl.fetch import ReportInaccessible
from necropsy.wcl.sites import VANILLA
from tests.wcl_fakes import FakeClock

PATCHWERK = 51118
ALLIANCE_CODE, HORDE_CODE = 1, 0  # externals.yaml factions (combatant codes)


def _rate() -> dict[str, Any]:
    return {"limitPerHour": 36000, "pointsSpentThisHour": 10, "pointsResetIn": 1800}


@dataclass
class Player:
    name: str
    faction_code: int | None = ALLIANCE_CODE
    guild: int | None = 0
    server: str = "Whitemane"
    actor_id: int = 5
    pets: list[int] = field(default_factory=list)
    pet_list: bool = True
    extra_same_name: bool = False
    subtype: str = "Hunter"
    report: str | None = None
    """Shared report code (default: one report per player)."""
    fight: int = 3


@dataclass
class FakeWcl:
    """Routes queries by operation name; records every request."""

    players: list[Player]
    subject: Player
    forbidden: set[str] = field(default_factory=set)
    stream_forbidden: set[str] = field(default_factory=set)
    revisions: dict[str, list[int]] = field(default_factory=dict)
    requests: list[dict[str, Any]] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    stop_after: int | None = None
    drift_after_events: dict[str, int] = field(default_factory=dict)
    """After this many event requests for a code, the report becomes revision 5 and its
    Hunter and pet actors get new ids."""
    event_counts: dict[str, int] = field(default_factory=dict)

    def code(self, p: Player) -> str:
        return p.report or f"R{p.name}"

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append(body)
        self.urls.append(str(request.url))
        query, var = body["query"], body["variables"]
        if self.stop_after is not None and len(self.requests) > self.stop_after:
            data = {"rateLimitData": {**_rate(), "pointsSpentThisHour": 36000}}
            return httpx.Response(200, json={"data": {"x": 1, **data}})
        if "NecropsySubject" in query:
            ranks = [self._rank(self.subject, 1500.0)]
            return self._ok(
                {"characterData": {"character": {"encounterRankings": {"ranks": ranks}}}}
            )
        if "NecropsyLeaderboard" in query:
            rows = [self._rank(p, 2000.0 - i) for i, p in enumerate(self.players)]
            rankings = {"rankings": rows, "hasMorePages": False}
            return self._ok(
                {
                    "worldData": {
                        "encounter": {"id": var["encounter"], "characterRankings": rankings}
                    }
                }
            )
        player = next(p for p in [*self.players, self.subject] if self.code(p) == var["code"])
        wanted = var.get("fightIDs") or [player.fight]
        if "NecropsyReport" in query:
            if var["code"] in self.forbidden:
                return httpx.Response(403)
            return self._ok({"reportData": {"report": self._report(player, wanted)}})
        if "NecropsyEvents" in query:
            if var["code"] in self.stream_forbidden:
                return httpx.Response(403)
            self.event_counts[var["code"]] = self.event_counts.get(var["code"], 0) + 1
            revision = self._revision(var["code"], peek=True)
            limit = self.drift_after_events.get(var["code"])
            if limit is not None and self.event_counts[var["code"]] > limit:
                revision = 5
            events = {"data": [{"timestamp": 1500, "type": "cast"}], "nextPageTimestamp": None}
            return self._ok({"reportData": {"report": {"revision": revision, "events": events}}})
        raise AssertionError(query)

    def _revision(self, code: str, peek: bool = False) -> int:
        seq = self.revisions.get(code)
        if not seq:
            return 4
        return seq[0] if peek or len(seq) == 1 else seq.pop(0)

    def _ok(self, data: dict[str, Any]) -> httpx.Response:
        return httpx.Response(200, json={"data": {**data, "rateLimitData": _rate()}})

    def _rank(self, p: Player, amount: float) -> dict[str, Any]:
        row: dict[str, Any] = {
            "name": p.name,
            "class": "Hunter",
            "spec": "Marksmanship",
            "amount": amount,
            "hardModeLevel": 0,
            "size": 40,
            "report": {"code": self.code(p), "fightID": p.fight},
            "server": {"name": p.server, "region": "US"},
        }
        if p is self.subject:
            row.update(**{"class": 3, "rankPercent": 95.0, "startTime": 1})
        if p.guild is not None:
            row["guild"] = {"id": 1, "name": "g", "faction": p.guild}
        return row

    def _report(self, p: Player, wanted: list[int] | None = None) -> dict[str, Any]:
        code = self.code(p)
        limit = self.drift_after_events.get(code)
        if limit is not None and self.event_counts.get(code, 0) > limit:
            return _drifted_report(self, p)
        group = [q for q in [*self.players, self.subject] if self.code(q) == code]
        fight_ids = sorted({q.fight for q in group} & set(wanted or [p.fight]))
        actors: list[dict[str, Any]] = []
        dps: list[dict[str, Any]] = []
        for q in group:
            actors.append(
                {
                    "id": q.actor_id,
                    "name": q.name,
                    "type": "Player",
                    "subType": q.subtype,
                    "server": q.server,
                }
            )
            actors += [
                {"id": pid, "name": "Pet", "type": "Pet", "petOwner": q.actor_id} for pid in q.pets
            ]
            if q.extra_same_name:
                actors.append(
                    {
                        "id": 99,
                        "name": q.name,
                        "type": "Player",
                        "subType": "Hunter",
                        "server": q.server,
                    }
                )
            info = {} if q.faction_code is None else {"factionID": q.faction_code}
            dps.append({"id": q.actor_id, "name": q.name, "type": "Hunter", "combatantInfo": info})
        fights = []
        for fid in fight_ids:
            fight: dict[str, Any] = {
                "id": fid,
                "encounterID": PATCHWERK,
                "startTime": 1000,
                "endTime": 9000,
            }
            members = [q for q in group if q.fight == fid]
            if all(q.pet_list for q in members):
                fight["friendlyPets"] = [
                    {"id": pid, "petOwner": q.actor_id} for q in members for pid in q.pets
                ]
            fights.append(fight)
        details = {"dps": dps}
        # The report bundle's revision consumes the code's revision sequence.
        return {
            "code": self.code(p),
            "revision": self._revision(self.code(p)),
            "fights": fights,
            "masterData": {"actors": actors},
            "playerDetails": {"data": {"playerDetails": details}},
        }


def _drifted_report(fake: FakeWcl, p: Player) -> dict[str, Any]:
    new_id, new_pets = p.actor_id + 10, [pid + 10 for pid in p.pets]
    fight = {
        "id": 3,
        "encounterID": PATCHWERK,
        "startTime": 1000,
        "endTime": 9000,
        "friendlyPets": [{"id": pid, "petOwner": new_id} for pid in new_pets],
    }
    actors = [
        {"id": new_id, "name": p.name, "type": "Player", "subType": "Hunter", "server": p.server}
    ] + [{"id": pid, "name": "Pet", "type": "Pet", "petOwner": new_id} for pid in new_pets]
    details = {
        "dps": [
            {
                "id": new_id,
                "name": p.name,
                "type": "Hunter",
                "combatantInfo": {"factionID": p.faction_code},
            }
        ]
    }
    return {
        "code": fake.code(p),
        "revision": 5,
        "fights": [fight],
        "masterData": {"actors": actors},
        "playerDetails": {"data": {"playerDetails": details}},
    }


def _context(faction: Faction = Faction.ALLIANCE) -> CharacterContext:
    part = Partition(3, "Phase 6", True, True)
    return CharacterContext(
        character_id=Field(86583560, "observed", "t"),
        canonical_id=Field(86583560, "observed", "t"),
        name=Field("Haplina", "observed", "t"),
        server=Field("Whitemane", "observed", "t"),
        region=Field("US", "observed", "t"),
        class_id=Field(3, "observed", "t"),
        faction=Field(faction, "observed", "t"),
        raw_faction={"name": faction.value},
        zone_id=SUPPORTED_ZONE_ID,
        zone_name=Field("Naxxramas", "observed", "t"),
        partitions=(part,),
        partition=part,
    )


def _run(tmp_path: Path, fake: FakeWcl, **kw: Any) -> Any:
    client = c.WclClient(
        VANILLA,
        lambda e: "secret-token",
        transport=httpx.MockTransport(fake),
        clock=FakeClock(),
        rng=random.Random(0),
    )
    client.last_rate = c.RateLimit(36000, 10.0, 1800)
    return acquire(client, Cache(tmp_path), VANILLA, _context(), encounters=(PATCHWERK,), **kw)


def _run_with(tmp_path: Path, handler: Any, **kw: Any) -> Any:
    client = c.WclClient(
        VANILLA,
        lambda e: "secret-token",
        transport=httpx.MockTransport(handler),
        clock=FakeClock(),
        rng=random.Random(0),
    )
    client.last_rate = c.RateLimit(36000, 10.0, 1800)
    return acquire(client, Cache(tmp_path), VANILLA, _context(), encounters=(PATCHWERK,), **kw)


def _cohort(n: int, **over: Any) -> list[Player]:
    return [Player(f"Ally{i}", **over) for i in range(1, n + 1)]


def _archive_answer() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "data": {"reportData": {"report": None}, "rateLimitData": _rate()},
            "errors": [{"message": "This report has been archived. Subscriber access required."}],
        },
    )


@pytest.mark.usefixtures("historical_cohort_depth")
def test_archived_stream_entry_is_replaced_from_later_candidates(tmp_path: Path) -> None:
    fake = FakeWcl(_cohort(30), Player("Haplina"))

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "NecropsyEvents" in body["query"] and body["variables"]["code"] == "RAlly1":
            return _archive_answer()
        return fake(request)

    result = _run_with(tmp_path, handler)
    boss = result.bosses[0]
    complete = [e.name for e in boss.cohort if e.status == "complete"]
    assert complete == [f"Ally{i}" for i in range(2, 7)]
    assert any(d.candidate.name == "Ally1" and "archived" in d.reason for d in boss.dropped)


def test_combined_reports_finalize_fresh_and_archive_errors_are_typed(tmp_path: Path) -> None:
    fake = FakeWcl(_cohort(5), Player("Haplina"))
    state = {"title": "first", "archived": False}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "NecropsyReport" in body["query"]:
            if state["archived"]:
                return _archive_answer()
            response = fake(request)
            payload = response.json()
            payload["data"]["reportData"]["report"]["title"] = state["title"]
            return httpx.Response(200, json=payload)
        return fake(request)

    client = c.WclClient(
        VANILLA,
        lambda e: "synthetic-token",
        transport=httpx.MockTransport(handler),
        clock=FakeClock(),
        rng=random.Random(0),
    )
    client.last_rate = c.RateLimit(36000, 10.0, 1800)
    store = Cache(tmp_path)
    acquisition = acquire(client, store, VANILLA, _context(), encounters=(PATCHWERK,))
    first = finalize_reports(Run(client, store, VANILLA), acquisition)
    state["title"] = "later metadata, same revision"
    second = finalize_reports(Run(client, store, VANILLA), acquisition)
    assert set(first) == set(second)
    for code, old in first.items():
        new = second[code]
        assert old.sha256 != new.sha256
        assert store.get_report_set(old.key, old.fight_ids, old.endpoint, old.sha256) is not None
    state["archived"] = True
    with pytest.raises(ReportInaccessible, match="archived"):
        finalize_reports(Run(client, store, VANILLA), acquisition)


def _ops(fake: FakeWcl, name: str) -> int:
    return sum(1 for r in fake.requests if name in r["query"])


@pytest.mark.usefixtures("historical_cohort_depth")
def test_full_boss_acquisition_with_pets(tmp_path: Path) -> None:
    fake = FakeWcl(_cohort(30, pets=[7]), Player("Haplina", pets=[8]))
    result = _run(tmp_path, fake)
    boss = result.bosses[0]
    assert boss.subject.status == "complete" and boss.subject.pets == [8]
    assert [e.name for e in boss.cohort if e.status == "complete"] == [
        f"Ally{i}" for i in range(1, 6)
    ]
    assert boss.coverage["complete"], boss.coverage["reasons"]
    assert boss.coverage["usable_deep"] == 5 and boss.coverage["metadata"] == 25
    assert boss.coverage["metadata_observed"] == 5 and boss.coverage["metadata_inferred"] == 20
    assert {(s.role, s.direction) for s in boss.cohort[0].streams} == {
        ("player", "source"),
        ("player", "target"),
        ("pet", "source"),
        ("pet", "target"),
    }
    assert boss.selection.raw_pages and boss.subject_raw == {
        "ranks": [fake._rank(fake.subject, 1500.0)]
    }
    assert all("/api/v2/client" in u for u in fake.urls)


def test_rerun_reuses_every_completed_stream(tmp_path: Path) -> None:
    _run(tmp_path, FakeWcl(_cohort(6), Player("Haplina")))
    again = FakeWcl(_cohort(6), Player("Haplina"))
    result = _run(tmp_path, again)
    assert _ops(again, "NecropsyEvents") == 0
    assert all(s.reused for e in result.bosses[0].cohort for s in e.streams)


def test_user_endpoint_is_used_for_every_request(tmp_path: Path) -> None:
    fake = FakeWcl(_cohort(6), Player("Haplina"), stream_forbidden={"RAlly1"})
    result = _run(tmp_path, fake, endpoint="user")
    assert fake.urls and all("/api/v2/user" in u for u in fake.urls)
    streams = [s for e in result.bosses[0].cohort for s in e.streams]
    assert streams and all(s.identity["endpoint"] == "user" for s in streams)


@pytest.mark.usefixtures("historical_cohort_depth")
def test_inaccessible_and_contradicted_rows_are_replaced(tmp_path: Path) -> None:
    players = _cohort(8)
    players[0].faction_code = HORDE_CODE  # guild says Alliance, report says Horde
    fake = FakeWcl(players, Player("Haplina"), forbidden={"RAlly2"}, stream_forbidden={"RAlly3"})
    boss = _run(tmp_path, fake).bosses[0]
    usable = [e.name for e in boss.cohort if e.status == "complete"]
    assert usable == ["Ally4", "Ally5", "Ally6", "Ally7", "Ally8"]
    assert [x.name for x in boss.selection.contradicted] == ["Ally1"]
    assert "Ally2" in [x.name for x in boss.selection.inaccessible]
    failed = {e.name: e.status for e in boss.cohort if e.status != "complete"}
    assert failed == {"Ally3": "inaccessible"}
    assert "Ally3" not in [m.name for m in boss.metadata]


def test_unknown_identity_never_counts(tmp_path: Path) -> None:
    players = _cohort(3)
    players[0].extra_same_name = True
    players[1].faction_code = None
    players[2].subtype = "Warrior"
    boss = _run(tmp_path, FakeWcl(players, Player("Haplina"))).bosses[0]
    assert not [e for e in boss.cohort if e.status == "complete"]
    reasons = {
        x.name: boss.selection.verdicts[x.position].reason for x in boss.selection.unresolved
    }
    assert set(reasons) == {"Ally1", "Ally2", "Ally3"}
    assert boss.coverage["below_minimum"] and not boss.coverage["complete"]


def test_unknown_pet_list_is_explicit(tmp_path: Path) -> None:
    fake = FakeWcl(_cohort(6), Player("Haplina", pet_list=False))
    boss = _run(tmp_path, fake).bosses[0]
    assert boss.subject.pets is None
    assert any("pets unknown for Haplina" in r for r in boss.coverage["reasons"])


def test_subject_of_the_wrong_faction_is_rejected(tmp_path: Path) -> None:
    boss = _run(tmp_path, FakeWcl(_cohort(6), Player("Haplina", faction_code=HORDE_CODE))).bosses[0]
    assert boss.subject.status == "rejected" and not boss.subject.streams
    assert any("subject fight not acquired" in r for r in boss.coverage["reasons"])


def test_a_revision_change_restarts_the_whole_entry(tmp_path: Path) -> None:
    # Bundle r4 (verify), entry reuses it; events answer r5 -> restart: bundle r5.
    fake = FakeWcl(_cohort(6), Player("Haplina"), revisions={"RAlly1": [4, 5]})
    boss = _run(tmp_path, fake).bosses[0]
    first = boss.cohort[0]
    assert first.status == "complete" and first.generations == 2
    assert first.bundle_key.revision == 5
    assert all(s.identity["revision"] == 5 for s in first.streams)


@pytest.mark.usefixtures("historical_cohort_depth")
def test_two_revision_changes_fail_the_entry(tmp_path: Path) -> None:
    fake = FakeWcl(_cohort(7), Player("Haplina"), revisions={"RAlly1": [4, 5, 6]})
    boss = _run(tmp_path, fake).bosses[0]
    first = boss.cohort[0]
    assert first.status == "failed" and "twice" in (first.reason or "") and not first.streams
    assert len([e for e in boss.cohort if e.status == "complete"]) == 5


def test_cross_faction_ceiling_is_opt_in_and_needs_an_observed_faction(tmp_path: Path) -> None:
    horde = Player("Orcy", faction_code=HORDE_CODE, guild=1)
    players = [horde, *_cohort(5)]
    boss = _run(tmp_path, FakeWcl(players, Player("Haplina"))).bosses[0]
    assert boss.cross_faction is None
    (tmp_path / "x").mkdir()
    boss = _run(
        tmp_path / "x",
        FakeWcl(players, Player("Haplina")),
        cross_faction=True,
    ).bosses[0]
    assert boss.cross_faction is not None and boss.cross_faction.status == "complete"
    unknown = Player("Mystery", faction_code=None, guild=None)
    (tmp_path / "y").mkdir()
    boss = _run(
        tmp_path / "y", FakeWcl([unknown, *_cohort(5)], Player("Haplina")), cross_faction=True
    ).bosses[0]
    assert boss.cross_faction is None


def test_running_out_of_points_stops_with_a_partial_result(tmp_path: Path) -> None:
    fake = FakeWcl(_cohort(6), Player("Haplina"), stop_after=3)
    result = _run(tmp_path, fake)
    assert result.stopped is not None and "51118" in result.stopped
    assert not result.bosses[-1].coverage["complete"]


def test_subject_pick_order_and_conflicts() -> None:
    def row(
        code: str, amount: Any, percent: Any = None, start: Any = None, cls: Any = 3
    ) -> dict[str, Any]:
        r: dict[str, Any] = {"class": cls, "amount": amount, "report": {"code": code, "fightID": 1}}
        if percent is not None:
            r["rankPercent"] = percent
        if start is not None:
            r["startTime"] = start
        return r

    pick = pick_subject([row("A", 900), row("B", 1000, 50), row("C", 1000, 60)])
    assert pick.report_code == "C"
    pick = pick_subject([row("A", 1000), row("B", 1000, 10)])
    assert pick.report_code == "B"
    pick = pick_subject([row("A", 1000, 10, 5), row("B", 1000, 10, 3)])
    assert pick.report_code == "B"
    pick = pick_subject([row("A", 1000), row("A", 1200), row("B", 900)])
    assert pick.report_code == "B" and any("conflicting" in n for n in pick.notes)
    pick = pick_subject([row("A", 1000, cls=4), row("B", True), row("", 5)])
    assert pick.report_code is None and pick.row is None
    assert pick_subject([row("A", 1000), dict(row("A", 1000))]).report_code == "A"


def test_fight_pets_need_consistent_ownership() -> None:
    master = {
        "masterData": {
            "actors": [
                {"id": 7, "type": "Pet", "petOwner": 5},
                {"id": 8, "type": "Pet", "petOwner": 6},
                {"id": 9, "type": "NPC"},
            ]
        }
    }

    def pets(listed: Any, report: dict[str, Any] = master) -> list[int] | None:
        fight = {} if listed is None else {"friendlyPets": listed}
        return fight_pets(report, fight, 5)[0]

    assert pets(None) is None
    assert pets([]) == []
    assert pets([{"id": 7, "petOwner": 5}, {"id": 8, "petOwner": 6}]) == [7]
    assert pets([{"id": 8, "petOwner": 6}]) == []  # confirmed other owner
    for owner in (None, True, 0, -1, "5"):
        assert pets([{"id": 7, "petOwner": owner}]) is None
    assert pets([{"id": 7}]) is None
    assert pets([{"id": True, "petOwner": 5}]) is None
    assert pets([{"id": 7, "petOwner": 5}, {"id": 7, "petOwner": 6}]) is None
    assert pets([{"id": 9, "petOwner": 5}]) is None  # not a pet actor
    assert pets([{"id": 8, "petOwner": 5}]) is None  # masterData names another owner
    assert pets([{"id": 10, "petOwner": 5}]) is None  # absent from masterData


@pytest.mark.usefixtures("historical_cohort_depth")
def test_metadata_shortfall_is_reported_apart_from_deep(tmp_path: Path) -> None:
    boss = _run(tmp_path, FakeWcl(_cohort(6), Player("Haplina"))).bosses[0]
    assert boss.coverage["usable_deep"] == 5 and not boss.coverage["complete"]
    assert boss.coverage["reasons"] == ["6 of 25 same-faction metadata rows"]


def test_points_stop_keeps_completed_entries(tmp_path: Path) -> None:
    fake = FakeWcl(_cohort(8), Player("Haplina"), stop_after=None)
    calls = {"n": 0}
    real = fake.__call__

    def stop_on_third_cohort_events(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "NecropsyEvents" in body["query"] and body["variables"]["code"] == "RAlly3":
            calls["n"] += 1
            return httpx.Response(429, headers={"Retry-After": "1"})
        return real(request)

    result = _run_with(tmp_path, stop_on_third_cohort_events)
    boss = result.bosses[0]
    assert result.stopped is not None and "RAlly3" in result.stopped
    assert boss.subject is not None and boss.subject.status == "complete"
    assert [e.status for e in boss.cohort] == ["complete", "complete", "stopped"]
    assert boss.coverage["usable_deep"] == 2 and not boss.coverage["complete"]
    assert boss.selection is not None and boss.key is not None


@pytest.mark.usefixtures("historical_cohort_depth")
def test_points_stop_during_a_replacement_check(tmp_path: Path) -> None:
    players = _cohort(8)
    fake = FakeWcl(players, Player("Haplina"), stream_forbidden={"RAlly1"})
    real = fake.__call__

    def stop_on_ally6_bundle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "NecropsyReport" in body["query"] and body["variables"]["code"] == "RAlly6":
            return httpx.Response(429, headers={"Retry-After": "1"})
        return real(request)

    result = _run_with(tmp_path, stop_on_ally6_bundle)
    boss = result.bosses[0]
    assert result.stopped is not None and "Ally6" in result.stopped
    assert [e.name for e in boss.cohort if e.status == "complete"] == [
        "Ally2",
        "Ally3",
        "Ally4",
        "Ally5",
    ]
    assert [d.candidate.name for d in boss.dropped] == ["Ally1"]


def test_the_legacy_selector_verifier_still_works() -> None:
    from necropsy.wcl.cohort import cohort_key, select

    ctx = _context()
    key = cohort_key(VANILLA, ctx, PATCHWERK)
    fake = FakeWcl(_cohort(3, guild=None), Player("Haplina"))
    rows = [(1, 3, fake._rank(p, 100.0)) for p in fake.players]
    sel = select(iter(rows), key, ctx, lambda cand: Faction.ALLIANCE)
    assert len(sel.deep) == 3 and all(d.faction.level == "observed" for d in sel.deep)


def test_drift_after_completed_streams_discards_the_old_generation(tmp_path: Path) -> None:
    players = _cohort(6, pets=[7])
    fake = FakeWcl(players, Player("Haplina"), drift_after_events={"RAlly1": 2})
    boss = _run(tmp_path, fake).bosses[0]
    first = boss.cohort[0]
    assert first.status == "complete" and first.generations == 2
    assert first.actor_id == 15 and first.pets == [17]
    assert {(s.actor_id, s.identity["revision"]) for s in first.streams} == {(15, 5), (17, 5)}
    old = tmp_path / "vanilla" / "RAlly1" / "r4" / "fight_3"
    assert (old / "client_player_5_source" / "stream.json").exists()
    assert (old / "client_player_5_target" / "stream.json").exists()


@pytest.mark.golden
def test_subject_rule_reproduces_the_recorded_export_choice() -> None:
    from tests.analysis_db import connect, full_db

    with connect(full_db()) as con:
        chosen = {
            e: (code, fight)
            for code, fight, e in con.execute(
                "SELECT report_code, fight_id, encounter_id FROM benchmark_participants "
                "WHERE kind = 'you'"
            ).fetchall()
        }
        rows: dict[int, list[Any]] = {}
        for e, raw in con.execute(
            "SELECT encounter_id, raw FROM rankings WHERE kind = 'subject'"
        ).fetchall():
            rows.setdefault(e, []).append(json.loads(raw))
    assert len(rows) == 15
    for encounter, ranks in rows.items():
        pick = pick_subject(ranks)
        assert (pick.report_code, pick.fight_id) == chosen[encounter], encounter


@pytest.mark.usefixtures("historical_cohort_depth")
def test_observed_rows_still_get_deep_slots_after_metadata_is_full() -> None:
    from necropsy.wcl.cohort import Verdict, cohort_key, select

    ctx = _context()
    key = cohort_key(VANILLA, ctx, PATCHWERK)
    fake = FakeWcl(
        [*_cohort(25), *[Player(f"Late{i}", guild=None) for i in range(5)]], Player("Haplina")
    )
    rows = [(1, 30, fake._rank(p, 100.0)) for p in fake.players]

    def verify(cand: Any) -> Verdict | None:
        if cand.name.startswith("Late"):
            return Verdict("observed", Faction.ALLIANCE)
        return Verdict("unknown", None, "no factionID") if cand.faction.level == "unknown" else None

    sel = select(iter(rows), key, ctx, verify, deep_needs_observed=True)
    assert [d.name for d in sel.deep] == [f"Late{i}" for i in range(5)]
    assert len(sel.metadata) == 25 and all(d in sel.metadata for d in sel.deep)
    assert [d.name for d in sel.displaced] == [f"Ally{i}" for i in range(25, 20, -1)]


@pytest.mark.parametrize(
    "bad",
    [
        {"class": 3.0},
        {"class": True},
        {"report": {"code": "../x", "fightID": 1}},
        {"report": {"code": "R1", "fightID": 1.0}},
        {"amount": -5},
        {"amount": float("inf")},
    ],
)
def test_subject_rows_are_validated_before_any_query(bad: dict[str, Any]) -> None:
    row = {"class": 3, "amount": 100.0, "report": {"code": "R1", "fightID": 1}, **bad}
    pick = pick_subject([row])
    assert pick.report_code is None and any("excluded" in n for n in pick.notes)


def test_unusable_tie_fields_count_as_missing() -> None:
    rows = [
        {"class": 3, "amount": 100.0, "rankPercent": 150, "report": {"code": "A", "fightID": 1}},
        {"class": 3, "amount": 100.0, "rankPercent": 40, "report": {"code": "B", "fightID": 1}},
    ]
    pick = pick_subject(rows)
    assert pick.report_code == "B"


@pytest.mark.parametrize(
    ("document", "note"),
    [(None, "no rankings"), ({"other": []}, "no ranks list"), ("[]", "no ranks list")],
)
def test_missing_subject_rankings_carry_a_reason(document: Any, note: str) -> None:
    from necropsy.wcl.acquire import subject_rankings
    from necropsy.wcl.cohort import cohort_key

    def handler(request: httpx.Request) -> httpx.Response:
        data = {
            "characterData": {"character": {"encounterRankings": document}},
            "rateLimitData": _rate(),
        }
        return httpx.Response(200, json={"data": data})

    client = c.WclClient(
        VANILLA,
        lambda e: "t",
        transport=httpx.MockTransport(handler),
        clock=FakeClock(),
        rng=random.Random(0),
    )
    client.last_rate = c.RateLimit(36000, 10.0, 1800)
    key = cohort_key(VANILLA, _context(), PATCHWERK)
    _, rows, notes = subject_rankings(client, _context(), key, "client")
    assert rows == [] and any(note in n for n in notes)


def test_every_listed_pet_must_agree_with_masterdata() -> None:
    def report(*actors: dict[str, Any]) -> dict[str, Any]:
        return {"masterData": {"actors": list(actors)}}

    pet7_mine = {"id": 7, "type": "Pet", "petOwner": 5}
    # Fight says another owner, masterData says it is ours: contradiction, not absence.
    ids, why = fight_pets(report(pet7_mine), {"friendlyPets": [{"id": 7, "petOwner": 6}]}, 5)
    assert ids is None and "masterData says 5" in why
    dup = report(pet7_mine, {"id": 7, "type": "Pet", "petOwner": 6})
    assert fight_pets(dup, {"friendlyPets": [{"id": 7, "petOwner": 5}]}, 5)[0] is None
    bad_master = report({"id": 7, "type": "Pet", "petOwner": True})
    assert fight_pets(bad_master, {"friendlyPets": [{"id": 7, "petOwner": 5}]}, 5)[0] is None
    fight_only = report({"id": 7, "type": "Pet"})
    ids, why = fight_pets(fight_only, {"friendlyPets": [{"id": 7, "petOwner": 5}]}, 5)
    assert ids == [7] and "fight list only" in why
    ids, why = fight_pets(report(pet7_mine), {"friendlyPets": [{"id": 7, "petOwner": 5}]}, 5)
    assert ids == [7] and why == "fight pet list and masterData agree"


def test_a_cached_bundle_is_never_reused_for_another_boss(tmp_path: Path) -> None:
    from necropsy.wcl.acquire import Run

    fake = FakeWcl(_cohort(1), Player("Haplina"))
    client = c.WclClient(
        VANILLA,
        lambda e: "t",
        transport=httpx.MockTransport(fake),
        clock=FakeClock(),
        rng=random.Random(0),
    )
    client.last_rate = c.RateLimit(36000, 10.0, 1800)
    run = Run(client, Cache(tmp_path), VANILLA)
    run.bundle("RAlly1", 3, PATCHWERK)
    with pytest.raises(c.InvalidResponse):
        run.bundle("RAlly1", 3, 51120)
    assert _ops(fake, "NecropsyReport") == 1
    verdict = run.verify(51120)(
        type(
            "C",
            (),
            {"report_code": "RAlly1", "fight_id": 3, "name": "Ally1", "server": "Whitemane"},
        )()
    )
    assert verdict.status == "unknown" and "invalid report data" in (verdict.reason or "")


@pytest.mark.usefixtures("historical_cohort_depth")
def test_cross_faction_is_not_applicable_when_number_one_is_own_faction(tmp_path: Path) -> None:
    fake = FakeWcl(_cohort(30), Player("Haplina"))
    boss = _run(tmp_path, fake, cross_faction=True).bosses[0]
    assert boss.cross_faction is None and boss.cross_faction_applicable is False
    assert boss.coverage["complete"], boss.coverage["reasons"]
    assert _ops(fake, "NecropsyReport") == 6  # subject + 5 deep; no extra ceiling fetch


def test_cross_faction_unknown_or_unreachable_number_one_is_partial(tmp_path: Path) -> None:
    unknown = Player("Mystery", faction_code=None, guild=None)
    (tmp_path / "a").mkdir()
    boss = _run(
        tmp_path / "a", FakeWcl([unknown, *_cohort(30)], Player("Haplina")), cross_faction=True
    ).bosses[0]
    assert boss.cross_faction_applicable is None
    assert any("cross-faction ceiling not acquired" in r for r in boss.coverage["reasons"])
    horde = Player("Orcy", faction_code=HORDE_CODE, guild=1)
    (tmp_path / "b").mkdir()
    fake = FakeWcl([horde, *_cohort(30)], Player("Haplina"), stream_forbidden={"ROrcy"})
    boss = _run(tmp_path / "b", fake, cross_faction=True).bosses[0]
    assert boss.cross_faction is not None and boss.cross_faction.status == "inaccessible"
    assert any("cross-faction ceiling not acquired" in r for r in boss.coverage["reasons"])


@pytest.mark.usefixtures("historical_cohort_depth")
def test_rows_pointing_at_another_boss_never_count(tmp_path: Path) -> None:
    fake = FakeWcl(_cohort(6), Player("Haplina"))
    client = c.WclClient(
        VANILLA,
        lambda e: "t",
        transport=httpx.MockTransport(fake),
        clock=FakeClock(),
        rng=random.Random(0),
    )
    client.last_rate = c.RateLimit(36000, 10.0, 1800)
    result = acquire(client, Cache(tmp_path), VANILLA, _context(), encounters=(PATCHWERK, 51120))
    first, second = result.bosses
    assert first.coverage["usable_deep"] == 5
    # Every report fight in the fake is Patchwerk: nothing may count for Thaddius.
    assert second.coverage["usable_deep"] == 0
    assert second.subject is not None and second.subject.status == "failed"
    assert second.selection is not None
    assert all(v.status != "observed" for v in second.selection.verdicts.values())


def test_the_current_depth_takes_three_top_ranked_comparisons(tmp_path: Path) -> None:
    fake = FakeWcl(_cohort(30, pets=[7]), Player("Haplina", pets=[8]))
    boss = _run(tmp_path, fake).bosses[0]
    assert [e.name for e in boss.cohort if e.status == "complete"] == ["Ally1", "Ally2", "Ally3"]
    assert boss.coverage["complete"], boss.coverage["reasons"]
    assert boss.coverage["usable_deep"] == 3 and boss.coverage["metadata"] == 25
    assert boss.selection.rule_set == "live-cohort-v2"


def test_a_depth_three_resume_selects_the_prefix_of_a_depth_five_run(tmp_path: Path) -> None:
    from tests.conftest import cohort_depth

    with cohort_depth(5):
        first = _run(tmp_path, FakeWcl(_cohort(30, pets=[7]), Player("Haplina", pets=[8])))
    earlier = [e.name for e in first.bosses[0].cohort if e.status == "complete"]
    assert earlier == [f"Ally{i}" for i in range(1, 6)]
    again = FakeWcl(_cohort(30, pets=[7]), Player("Haplina", pets=[8]))
    boss = _run(tmp_path, again).bosses[0]
    # The same ordering selects the first three, entirely from verified cached streams;
    # the two later comparisons stay in the cache and are not selected.
    chosen = [e for e in boss.cohort if e.status == "complete"]
    assert [e.name for e in chosen] == earlier[:3]
    assert _ops(again, "NecropsyEvents") == 0
    assert all(s.reused for e in chosen for s in e.streams)
    assert boss.subject.status == "complete" and boss.subject.pets == [8]
    assert [e.actor_id for e in chosen] == [
        e.actor_id for e in first.bosses[0].cohort if e.status == "complete"
    ][:3]
    assert boss.coverage["usable_deep"] == 3 and boss.coverage["complete"]
