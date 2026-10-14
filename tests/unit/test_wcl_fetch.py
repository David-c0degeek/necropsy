"""Fetching report bundles and event streams into the cache.

Every response here is SYNTHETIC, shaped like the recorded exporter's queries.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import httpx
import pytest

from necropsy.wcl import client as c
from necropsy.wcl.cache import Cache
from necropsy.wcl.fetch import (
    ReportInaccessible,
    RevisionChanged,
    fetch_bundle,
    fetch_stream,
)
from necropsy.wcl.sites import VANILLA
from tests.wcl_fakes import FakeClock, Script, ok

CODE, FIGHT, ENCOUNTER = "AbC123", 7, 51118


def _client(script: Script) -> c.WclClient:
    client = c.WclClient(
        VANILLA,
        lambda e: "secret-token",
        transport=script.transport,
        clock=FakeClock(),
        rng=random.Random(0),
    )
    client.last_rate = c.RateLimit(3600, 10.0, 1200)
    return client


def _report(**over: Any) -> dict[str, Any]:
    report: dict[str, Any] = {
        "code": CODE,
        "revision": 4,
        "fights": [{"id": FIGHT, "encounterID": ENCOUNTER, "startTime": 1000, "endTime": 9000}],
        "masterData": {"actors": [{"id": 3, "name": "Haplina", "type": "Hunter"}]},
        "playerDetails": {"data": {}},
    }
    report.update(over)
    return report


def _bundle_response(report: dict[str, Any] | None) -> httpx.Response:
    return ok({"reportData": {"report": report}})


def _events(
    data: Any, cursor: Any, revision: Any = 4, *, drop_cursor: bool = False
) -> httpx.Response:
    events: dict[str, Any] = {"data": data}
    if not drop_cursor:
        events["nextPageTimestamp"] = cursor
    return ok({"reportData": {"report": {"revision": revision, "events": events}}})


def _ev(n: int) -> list[dict[str, Any]]:
    return [{"timestamp": 1000 + i, "type": "cast"} for i in range(n)]


def _bundle(tmp_path: Path, script: Script) -> Any:
    store = Cache(tmp_path)
    client = _client(script)
    return client, store, fetch_bundle(client, store, VANILLA, CODE, FIGHT, ENCOUNTER)


def test_bundle_is_validated_then_published_under_its_revision(tmp_path: Path) -> None:
    _, store, bundle = _bundle(tmp_path, Script(_bundle_response(_report())))
    assert bundle.key.revision == 4 and (bundle.start, bundle.end) == (1000.0, 9000.0)
    assert store.get_bundle(bundle.key, bundle.endpoint, bundle.sha256) is not None
    assert (
        tmp_path
        / "vanilla"
        / CODE
        / "r4"
        / f"fight_{FIGHT}"
        / f"report_client_{bundle.sha256}.json"
    ).exists()


@pytest.mark.parametrize(
    ("report", "error"),
    [
        (None, ReportInaccessible),
        (_report(code="Other1"), c.InvalidResponse),
        (_report(revision=None), c.InvalidResponse),
        (_report(revision=True), c.InvalidResponse),
        (_report(fights=[]), c.InvalidResponse),
        (
            _report(fights=[{"id": FIGHT, "encounterID": 1, "startTime": 1, "endTime": 2}]),
            c.InvalidResponse,
        ),
        (
            _report(fights=[{"id": FIGHT, "encounterID": ENCOUNTER, "startTime": 5, "endTime": 5}]),
            c.InvalidResponse,
        ),
    ],
)
def test_bad_bundles_are_refused_before_writing(
    tmp_path: Path, report: Any, error: type[Exception]
) -> None:
    with pytest.raises(error):
        _bundle(tmp_path, Script(_bundle_response(report)))
    assert not (tmp_path / "vanilla").exists() or not list(
        (tmp_path / "vanilla").rglob("report_*.json")
    )


def test_stream_pages_until_an_explicit_null_cursor(tmp_path: Path) -> None:
    script = Script(_bundle_response(_report()), _events(_ev(2), 2000), _events(_ev(1), None))
    client, store, bundle = _bundle(tmp_path, script)
    stream = fetch_stream(client, store, bundle, "player", 3, "source")
    assert [len(p["data"]) for p in stream.pages] == [2, 1]
    sent = script.bodies()[1:]
    assert [b["variables"]["startTime"] for b in sent] == [1000.0, 2000]
    assert all(b["variables"]["sourceID"] == 3 and b["variables"]["targetID"] is None for b in sent)
    # A second call is served from the cache without any request.
    assert fetch_stream(client, store, bundle, "player", 3, "source").pages == stream.pages


def test_empty_terminal_page_completes(tmp_path: Path) -> None:
    client, store, bundle = _bundle(
        tmp_path, Script(_bundle_response(_report()), _events([], None))
    )
    assert fetch_stream(client, store, bundle, "pet", 9, "target").pages[0]["data"] == []


def test_revision_drift_leaves_the_stream_incomplete(tmp_path: Path) -> None:
    script = Script(
        _bundle_response(_report()), _events(_ev(1), 2000), _events(_ev(1), None, revision=5)
    )
    client, store, bundle = _bundle(tmp_path, script)
    with pytest.raises(RevisionChanged):
        fetch_stream(client, store, bundle, "player", 3, "source")
    folder = tmp_path / "vanilla" / CODE / "r4" / f"fight_{FIGHT}" / "client_player_3_source"
    assert not (folder / "stream.json").exists()


@pytest.mark.parametrize(
    "page",
    [
        _events(_ev(1), None, drop_cursor=True),
        _events(_ev(1), True),
        httpx.Response(
            200,
            content=b'{"data": {"reportData": {"report": {"revision": 4, "events": '
            b'{"data": [], "nextPageTimestamp": NaN}}}, "rateLimitData": '
            b'{"limitPerHour": 3600, "pointsSpentThisHour": 1, "pointsResetIn": 60}}}',
        ),
        _events(_ev(1), 1000),
        _events(_ev(1), 999),
        _events(_ev(1), 9001),
        _events(_ev(1), "2000"),
        _events("nope", None),
        _events([1, 2], None),
        _events(_ev(1), None, revision=None),
    ],
)
def test_bad_pages_never_complete(tmp_path: Path, page: httpx.Response) -> None:
    client, store, bundle = _bundle(tmp_path, Script(_bundle_response(_report()), page))
    with pytest.raises(c.WclError):
        fetch_stream(client, store, bundle, "player", 3, "source")
    folder = tmp_path / "vanilla" / CODE / "r4" / f"fight_{FIGHT}" / "client_player_3_source"
    assert not (folder / "stream.json").exists()


def test_page_budget_leaves_the_stream_incomplete(tmp_path: Path) -> None:
    script = Script(_bundle_response(_report()), _events(_ev(1), 2000), _events(_ev(1), 3000))
    client, store, bundle = _bundle(tmp_path, script)
    with pytest.raises(c.PageBudgetExhausted):
        fetch_stream(client, store, bundle, "player", 3, "source", max_pages=2)


def test_permission_and_inaccessible_reports_stop_without_fallback(tmp_path: Path) -> None:
    script = Script(_bundle_response(_report()), httpx.Response(403))
    client, store, bundle = _bundle(tmp_path, script)
    with pytest.raises(c.PermissionDenied):
        fetch_stream(client, store, bundle, "player", 3, "target")
    assert len(script.requests) == 2
    assert all("/api/v2/client" in str(r.url) for r in script.requests)
    (tmp_path / "second").mkdir()
    gone = Script(_bundle_response(_report()), ok({"reportData": {"report": None}}))
    client, store, bundle = _bundle(tmp_path / "second", gone)
    with pytest.raises(ReportInaccessible):
        fetch_stream(client, store, bundle, "player", 3, "source")


def test_tokens_never_reach_the_cache(tmp_path: Path) -> None:
    script = Script(_bundle_response(_report()), _events(_ev(1), None))
    client, store, bundle = _bundle(tmp_path, script)
    fetch_stream(client, store, bundle, "player", 3, "source")
    blob = b"".join(p.read_bytes() for p in tmp_path.rglob("*") if p.is_file())
    assert b"secret-token" not in blob and b"Bearer" not in blob


def test_completed_streams_record_fetch_provenance_and_hits_say_so(tmp_path: Path) -> None:
    script = Script(_bundle_response(_report()), _events(_ev(1), None))
    client, store, bundle = _bundle(tmp_path, script)
    fresh = fetch_stream(client, store, bundle, "player", 3, "source")
    assert not fresh.reused
    assert fresh.meta["fetched_at"].startswith("2026-10-13")
    assert fresh.meta["rate_before"]["points_spent"] == 10.0
    assert fresh.meta["rate_after"] is not None
    hit = fetch_stream(client, store, bundle, "player", 3, "source")
    assert hit.reused and hit.meta == fresh.meta
    assert len(script.requests) == 2


def test_points_need_two_observed_readings_in_one_period() -> None:
    from necropsy.wcl.fetch import Reading, fetch_meta

    client = _client(Script())
    same = fetch_meta(
        client,
        Reading(c.RateLimit(3600, 10, 1200), 0.0),
        Reading(c.RateLimit(3600, 25.5, 1100), 100.0),
    )
    assert same["account_points_between_readings"] == 15.5
    assert "not an exact stream cost" in same["points_note"]
    # Countdown and counter look plausible, but 3700 s later is the next period.
    later = fetch_meta(
        client,
        Reading(c.RateLimit(3600, 10, 1200), 0.0),
        Reading(c.RateLimit(3600, 20, 1100), 3700.0),
    )
    assert later["account_points_between_readings"] is None
    unobserved = fetch_meta(
        client,
        Reading(c.RateLimit(3600, 10, 1200), None),
        Reading(c.RateLimit(3600, 20, 1100), 5.0),
    )
    assert unobserved["account_points_between_readings"] is None
    missing = fetch_meta(client, Reading(None, None), Reading(c.RateLimit(3600, 5, 3590), 1.0))
    assert missing["account_points_between_readings"] is None
    dropped = fetch_meta(
        client,
        Reading(c.RateLimit(3600, 50, 1200), 0.0),
        Reading(c.RateLimit(3600, 40, 1190), 10.0),
    )
    assert dropped["account_points_between_readings"] is None


def test_a_long_fetch_crossing_the_hour_records_no_cost(tmp_path: Path) -> None:
    clock = FakeClock()

    def late(request: httpx.Request) -> httpx.Response:
        clock.t += 3700
        body = {
            "data": {
                "reportData": {
                    "report": {"revision": 4, "events": {"data": [], "nextPageTimestamp": None}}
                },
                "rateLimitData": {
                    "limitPerHour": 3600,
                    "pointsSpentThisHour": 20,
                    "pointsResetIn": 1100,
                },
            }
        }
        return httpx.Response(200, json=body)

    early_body = {
        "data": {
            "reportData": {"report": _report()},
            "rateLimitData": {
                "limitPerHour": 3600,
                "pointsSpentThisHour": 10,
                "pointsResetIn": 1200,
            },
        }
    }
    script = Script(httpx.Response(200, json=early_body), late)
    client = c.WclClient(
        VANILLA, lambda e: "t", transport=script.transport, clock=clock, rng=random.Random(0)
    )
    client.last_rate = c.RateLimit(3600, 0.0, 3600)
    store = Cache(tmp_path)
    bundle = fetch_bundle(client, store, VANILLA, CODE, FIGHT, ENCOUNTER)
    stream = fetch_stream(client, store, bundle, "player", 3, "source")
    assert stream.meta["account_points_between_readings"] is None
    assert stream.meta["rate_before"]["points_spent"] == 10
    assert stream.meta["rate_after"]["points_spent"] == 20


def test_a_reading_assumed_after_a_reset_wait_is_not_an_observation() -> None:
    clock = FakeClock()
    client = c.WclClient(
        VANILLA,
        lambda e: "t",
        transport=Script().transport,
        clock=clock,
        rng=random.Random(0),
        policy=c.Policy(wait_for_reset=True),
    )
    client.last_rate = c.RateLimit(3600, 3590.0, 10)
    client.last_rate_at = 0.0
    client.ensure_budget(500.0)
    assert client.last_rate is not None and client.last_rate.points_spent == 0.0
    assert client.last_rate_at is None


def _archived(data: dict[str, Any]) -> httpx.Response:
    message = (
        "This report has been archived. Subscribing users can access the report content "
        "via the /user API endpoint."
    )
    body = {"data": {**data, "rateLimitData": rate_dict()}, "errors": [{"message": message}]}
    return httpx.Response(200, json=body)


def rate_dict() -> dict[str, Any]:
    return {"limitPerHour": 1800, "pointsSpentThisHour": 10, "pointsResetIn": 3000}


def test_archived_event_pages_are_an_unreachable_report(tmp_path: Path) -> None:
    archived = _archived({"reportData": {"report": {"revision": 4, "events": None}}})
    client, store, bundle = _bundle(tmp_path, Script(_bundle_response(_report()), archived))
    with pytest.raises(ReportInaccessible, match="user endpoint"):
        fetch_stream(client, store, bundle, "player", 3, "source")
    folder = tmp_path / "vanilla" / CODE / "r4" / f"fight_{FIGHT}" / "client_player_3_source"
    assert not (folder / "stream.json").exists()


def test_other_partial_answers_are_invalid_not_crashes(tmp_path: Path) -> None:
    other = httpx.Response(
        200,
        json={
            "data": {"reportData": {"report": None}, "rateLimitData": rate_dict()},
            "errors": [{"message": "Something odd"}],
        },
    )
    with pytest.raises(c.InvalidResponse, match="partial answer"):
        _bundle(tmp_path, Script(other))


def test_mixed_archive_and_other_errors_are_invalid(tmp_path: Path) -> None:
    response = _archived({"reportData": {"report": None}})
    body = response.json()
    body["errors"].append({"message": "Unknown field"})
    with pytest.raises(c.InvalidResponse, match="partial answer"):
        _bundle(tmp_path, Script(httpx.Response(200, json=body)))


def test_anonymized_report_reference_is_inaccessible_before_any_request(tmp_path: Path) -> None:
    script = Script()
    client = _client(script)
    with pytest.raises(ReportInaccessible, match="anonymized"):
        fetch_bundle(client, Cache(tmp_path), VANILLA, "a:AnonymizedId", FIGHT, ENCOUNTER)
    assert not script.requests
    assert not (tmp_path / "vanilla").exists()


def test_metadata_rerun_preserves_generation_and_reuses_event_evidence(tmp_path: Path) -> None:
    script = Script(
        _bundle_response(_report(title="first")),
        _events(_ev(1), None),
        _bundle_response(_report(title="changed at the same revision")),
    )
    client, store, first = _bundle(tmp_path, script)
    original_stream = fetch_stream(client, store, first, "player", 3, "source")
    second = fetch_bundle(client, store, VANILLA, CODE, FIGHT, ENCOUNTER)
    assert first.key == second.key and first.sha256 != second.sha256
    assert store.get_bundle(first.key, first.endpoint, first.sha256)["report"]["title"] == "first"
    reused = fetch_stream(client, store, second, "player", 3, "source")
    assert reused.reused and reused.pages == original_stream.pages
