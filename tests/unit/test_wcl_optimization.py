"""Cost reductions must preserve selection, raw ranking evidence and old checkpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from necropsy.wcl.acquire import Run, acquire, finalize_reports
from necropsy.wcl.cache import Cache
from necropsy.wcl.checkpoint import Journal
from necropsy.wcl.client import RATE_FIELDS, BudgetExceeded, RateLimit, RateLimited, WclClient
from necropsy.wcl.fetch import (
    REPORT_METADATA_QUERY,
    REPORT_QUERY,
    REPORT_SCREEN_QUERY,
    fetch_bundle,
)
from necropsy.wcl.sites import VANILLA
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _cohort, _context
from tests.wcl_fakes import FakeClock, Script


def _rate(*, database: float = 100, cost: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "limitPerHour": 3000,
        "pointsSpentThisHour": 1700,
        "pointsResetIn": 900,
        "databaseLimitPerHour": 1050,
        "databasePointsSpentThisHour": database,
        "currentRequest": cost or {"application": 0, "user": 4.01, "total": 4.01},
    }


def _reply(data: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, content=json.dumps({"data": data}).encode())


def test_telemetry_keeps_legacy_journal_keys_and_does_not_bill_replays(tmp_path: Path) -> None:
    query = "query Example { x " + RATE_FIELDS + " }"
    script = Script(_reply({"x": 1, "rateLimitData": _rate()}))
    journal = Journal(tmp_path / "requests")
    client = WclClient(
        VANILLA,
        lambda _: "secret-token",
        transport=script.transport,
        clock=FakeClock(),
        journal=journal,
    )
    result = client.query(query)
    assert result.rate.database_remaining == 950
    assert result.rate.current_request == {"application": 0, "user": 4.01, "total": 4.01}
    wire_query = json.loads(script.requests[0].content)["query"]
    assert "databaseLimitPerHour" in wire_query and "currentRequest" in wire_query
    assert journal.read(journal.identity(VANILLA.host, "client", query, None)) is not None
    exhausted = RateLimit(3000, 2800, 600, 1050, 1144)
    client.last_rate = exhausted
    client.query(query)
    assert client.last_rate is exhausted and len(script.requests) == 1
    ledger = (tmp_path / "usage.jsonl").read_text()
    assert "secret-token" not in ledger and len(ledger.splitlines()) == 1
    assert json.loads(ledger)["current_request"]["user"] == 4.01


def test_structured_database_exhaustion_on_429_stops_without_retry(tmp_path: Path) -> None:
    body = {
        "data": {"rateLimitData": _rate(database=1144)},
        "errors": [{"message": "no database points remaining"}],
    }
    script = Script(httpx.Response(429, json=body))
    client = WclClient(
        VANILLA,
        lambda _: "secret",
        transport=script.transport,
        clock=FakeClock(),
        journal=Journal(tmp_path / "requests"),
    )
    with pytest.raises(RateLimited, match="database points"):
        client.query("query Ranking { x " + RATE_FIELDS + " }")
    assert len(script.requests) == 1
    assert client.last_rate is not None and client.last_rate.database_remaining == 0
    assert not list((tmp_path / "requests").glob("*.json"))
    assert json.loads((tmp_path / "usage.jsonl").read_text())["http_status"] == 429


def test_exhausted_database_does_not_block_metadata_or_replay(tmp_path: Path) -> None:
    query = "query Ranking { rankings(fightIDs: [1]) " + RATE_FIELDS + " }"
    script = Script(_reply({"reportData": {"report": {}}, "rateLimitData": _rate(database=1144)}))
    client = WclClient(VANILLA, lambda _: "secret", transport=script.transport, clock=FakeClock())
    client.last_rate = RateLimit(3000, 1700, 900, 1050, 1144)
    with pytest.raises(BudgetExceeded, match="database points"):
        client.query(query)
    assert not script.requests
    client.query(REPORT_METADATA_QUERY, {"code": "AbC", "fightIDs": [1]})
    assert len(script.requests) == 1


def test_candidate_screen_reuses_exact_legacy_full_answer_without_http(tmp_path: Path) -> None:
    from tests.unit.test_wcl_fetch import CODE, ENCOUNTER, FIGHT, _report

    journal = Journal(tmp_path / "requests")
    variables = {"code": CODE, "fightIDs": [FIGHT]}
    data = {"reportData": {"report": _report()}, "rateLimitData": _rate()}
    journal.write(journal.identity(VANILLA.host, "user", REPORT_QUERY, variables), data)
    client = WclClient(
        VANILLA,
        lambda _: pytest.fail("legacy replay asked for credentials"),
        transport=Script().transport,
        journal=journal,
        replay_only=True,
    )
    (tmp_path / "cache").mkdir()
    live_reading = RateLimit(3000, 1700, 900, 1050, 1144)
    client.last_rate = live_reading
    bundle = fetch_bundle(
        client,
        Cache(tmp_path / "cache"),
        VANILLA,
        CODE,
        FIGHT,
        ENCOUNTER,
        endpoint="user",
        metadata_only=True,
    )
    assert bundle.report == data["reportData"]["report"]
    assert client.last_rate is live_reading
    assert not (tmp_path / "usage.jsonl").exists()
    # Never cross the acquisition/finalization boundary to find a superset.
    journal.scope = "finalization"
    with pytest.raises(BudgetExceeded):
        client.query(
            REPORT_SCREEN_QUERY, variables, endpoint="user", saved_supersets=(REPORT_QUERY,)
        )


def test_rejected_candidates_never_fetch_rankings_and_singletons_finalize_without_db(
    tmp_path: Path,
) -> None:
    players = _cohort(6)
    players[0].faction_code = 0  # guild claims Alliance; observed Horde
    fake = FakeWcl(players, Player("Haplina"))
    finalizing = False

    def handler(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        if finalizing:
            assert "rankings(" not in query, "finalization re-billed acquired rankings"
        response = fake(request)
        payload = response.json()
        report = (payload["data"].get("reportData") or {}).get("report")
        if report is not None and "NecropsyReport" in query:
            if "rankings(" in query:
                report["rankings"] = {"data": [{"fightID": 3, "evidence": "original"}]}
            else:
                report.pop("rankings", None)
        return httpx.Response(200, json=payload)

    journal = Journal(tmp_path / "requests")
    # Existing captures already paid for these ranking-bearing acquisition answers.
    for player in [fake.subject, *players[1:]]:
        variables = {"code": fake.code(player), "fightIDs": [player.fight]}
        response = handler(
            httpx.Request(
                "POST", VANILLA.client_api, json={"query": REPORT_QUERY, "variables": variables}
            )
        )
        journal.write(
            journal.identity(VANILLA.host, "client", REPORT_QUERY, variables),
            response.json()["data"],
        )
    fake.requests.clear()
    client = WclClient(
        VANILLA,
        lambda _: "secret",
        transport=httpx.MockTransport(handler),
        clock=FakeClock(),
        journal=journal,
    )
    client.last_rate = RateLimit(36000, 10, 1800)
    store = Cache(tmp_path)
    acquisition = acquire(client, store, VANILLA, _context(), encounters=(PATCHWERK,))
    assert not any(
        r["variables"].get("code") == "RAlly1" and "rankings(" in r["query"] for r in fake.requests
    )
    original_requests = len(fake.requests)
    finalizing = True
    client.last_rate = RateLimit(3000, 1700, 900, 1050, 1144)
    reports = finalize_reports(Run(client, store, VANILLA), acquisition)
    assert len(fake.requests) - original_requests == len(reports)
    assert all(r.report["rankings"]["data"][0]["evidence"] == "original" for r in reports.values())
    from necropsy.snapshot.archive import VerifiedArchive, load_entries_manifest
    from necropsy.snapshot.v1 import open_snapshot
    from necropsy.snapshot.v1_writer import write_snapshot

    output = tmp_path / "archive"
    output.mkdir()
    written = write_snapshot(acquisition, store, output, "optimized")
    with VerifiedArchive(
        written.archive,
        expected_sha256=written.sha256,
        entries=load_entries_manifest(written.entries),
    ) as archive:
        reader = open_snapshot(archive)
        assert all(
            report["rankings"]["data"][0]["evidence"] == "original" for report in reader.reports()
        )


def test_twenty_five_candidate_checks_only_bill_rankings_for_selected_entries(
    tmp_path: Path,
) -> None:
    fake = FakeWcl(_cohort(30, guild=None), Player("Haplina"))
    client = WclClient(
        VANILLA,
        lambda _: "secret",
        transport=httpx.MockTransport(fake),
        clock=FakeClock(),
        journal=Journal(tmp_path / "requests"),
    )
    client.last_rate = RateLimit(36000, 10, 1800)
    store = Cache(tmp_path)
    result = acquire(client, store, VANILLA, _context(), encounters=(PATCHWERK,))
    assert len(result.bosses[0].metadata) == 25
    assert len(result.bosses[0].cohort) == 3
    full = sum("query NecropsyReport(" in r["query"] for r in fake.requests)
    assert full == 0  # screening and event acquisition do not need ranking-bearing reports
    assert sum("NecropsyReportScreen" in r["query"] for r in fake.requests) == 25
    before = len(fake.requests)
    finalize_reports(Run(client, store, VANILLA), result)
    assert len(fake.requests) - before == 4
    assert sum("query NecropsyReport(" in r["query"] for r in fake.requests) == 4
    assert client.journal is not None and client.journal.scope == "acquisition"
    finalized = [
        json.loads(line)
        for line in (tmp_path / "usage.jsonl").read_text().splitlines()
        if json.loads(line)["scope"] == "finalization"
    ]
    assert len(finalized) == 4
    assert all(row["operation"] == "NecropsyReport" for row in finalized)


def test_transient_structured_throttling_still_honors_retry_after() -> None:
    script = Script(
        httpx.Response(
            429, headers={"Retry-After": "2"}, json={"errors": [{"message": "Too many requests"}]}
        ),
        _reply({"x": 1, "rateLimitData": _rate()}),
    )
    clock = FakeClock()
    client = WclClient(VANILLA, lambda _: "secret", transport=script.transport, clock=clock)
    assert client.query("query Example { x " + RATE_FIELDS + " }").data["x"] == 1
    assert clock.sleeps == [2.0]


@pytest.mark.parametrize("value", [True, -1, float("nan"), "1050", None])
def test_malformed_optional_database_fields_stay_unknown(value: Any) -> None:
    rate = _rate()
    rate["databaseLimitPerHour"] = value
    script = Script(_reply({"x": 1, "rateLimitData": rate}))
    client = WclClient(VANILLA, lambda _: "secret", transport=script.transport)
    result = client.query("query Example { x " + RATE_FIELDS + " }")
    assert result.rate.database_limit_per_hour is None
    assert result.rate.database_remaining is None
