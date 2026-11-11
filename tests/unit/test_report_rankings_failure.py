"""Rankings-only upstream failures must not discard otherwise usable captures."""

import json
from pathlib import Path

import httpx
import pytest

from necropsy.wcl.acquire import MixedRevision, Run, acquire, finalize_reports
from necropsy.wcl.cache import Cache
from necropsy.wcl.checkpoint import Journal
from necropsy.wcl.client import InvalidResponse, RateLimit, WclClient
from necropsy.wcl.fetch import (
    REPORT_METADATA_QUERY,
    ReportRankingsUnavailable,
    report_query,
    report_query_for_metric,
)
from necropsy.wcl.sites import VANILLA
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _cohort, _context
from tests.wcl_fakes import FakeClock


@pytest.mark.parametrize("fault", ["rankings", "metadata", "mixed", "revision"])
def test_finalization_rankings_failure(tmp_path: Path, fault: str) -> None:
    metric = "dps"
    fake = FakeWcl(_cohort(3), Player("Haplina"))
    finalizing = False
    failed_code = fake.code(fake.subject)
    errors = [{"message": "Internal server error", "path": ["reportData", "report", "rankings"]}]
    if fault == "metadata":
        errors[0]["path"] = ["reportData", "report", "playerDetails"]
    elif fault == "mixed":
        errors.append({"message": "Internal server error", "path": ["reportData", "report"]})

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        payload = fake(request).json()
        report = (payload["data"].get("reportData") or {}).get("report")
        if report is not None and "rankings(" in body["query"]:
            report["rankings"] = {"data": []}
        if finalizing and report is not None and body["variables"].get("code") == failed_code:
            if "rankings(" in body["query"]:
                report["rankings"] = None
                payload["errors"] = errors
                # A poisoned partial answer must never reach the snapshot.
                report["title"] = "REJECT THIS PARTIAL RESPONSE"
            elif fault == "revision":
                report["revision"] = 999
        return httpx.Response(200, json=payload)

    journal = Journal(tmp_path / "requests")
    client = WclClient(
        VANILLA,
        lambda _: "secret",
        transport=httpx.MockTransport(handler),
        clock=FakeClock(),
        journal=journal,
    )
    client.last_rate = RateLimit(36000, 10, 1800)
    (tmp_path / "cache").mkdir()
    store = Cache(tmp_path / "cache")
    collected = acquire(client, store, VANILLA, _context(), encounters=(PATCHWERK,))
    finalizing = True
    run = Run(client, store, VANILLA, metric=metric)
    if fault in ("metadata", "mixed"):
        with pytest.raises(InvalidResponse):
            finalize_reports(run, collected)
        assert not any(r["query"] == REPORT_METADATA_QUERY for r in fake.requests)
        return
    if fault == "revision":
        with pytest.raises(MixedRevision):
            finalize_reports(run, collected)
        return
    finalized = finalize_reports(run, collected)
    report = finalized[failed_code].report
    assert "rankings" not in report and "title" not in report
    boss = collected.bosses[0]
    assert not boss.coverage["complete"]
    assert any("report rankings unavailable" in reason for reason in boss.coverage["reasons"])
    assert all(e.status == "complete" for _, e in collected.complete_entries())
    variables = {"code": failed_code, "fightIDs": [fake.subject.fight]}
    journal.scope = "finalization"
    assert (
        journal.read(
            journal.identity(VANILLA.host, "client", report_query_for_metric(metric), variables)
        )
        is None
    )
    assert (
        journal.read(journal.identity(VANILLA.host, "client", REPORT_METADATA_QUERY, variables))
        is not None
    )
    from necropsy.snapshot.v1_writer import write_snapshot

    output = tmp_path / "archive"
    output.mkdir()
    written = write_snapshot(collected, store, output, "rankings-unavailable")
    assert written.archive.is_file()


@pytest.mark.parametrize("metric", ["dps", "hps"])
def test_rankings_failure_classification(metric: str) -> None:
    from tests.wcl_fakes import Script

    script = Script(
        httpx.Response(
            200,
            json={
                "data": {
                    "reportData": {"report": {"rankings": None}},
                    "rateLimitData": {
                        "limitPerHour": 3000,
                        "pointsSpentThisHour": 10,
                        "pointsResetIn": 300,
                    },
                },
                "errors": [
                    {
                        "message": "Internal server error",
                        "path": ["reportData", "report", "rankings"],
                    }
                ],
            },
        )
    )
    client = WclClient(VANILLA, lambda _: "secret", transport=script.transport)
    with pytest.raises(ReportRankingsUnavailable):
        report_query(
            client, report_query_for_metric(metric), {"code": "AbC", "fightIDs": [29]}, "user"
        )
