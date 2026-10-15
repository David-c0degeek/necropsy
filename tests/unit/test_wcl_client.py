"""WCL client: bounded retries, typed errors, pacing and pagination."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import httpx
import pytest

from necropsy.wcl import client as c
from necropsy.wcl.sites import SITES, VANILLA, UnsupportedSite
from tests.wcl_fakes import FakeClock, Script, ok, rate

Q = "query Q { x " + c.RATE_FIELDS + " }"


def _client(script: Script, clock: FakeClock | None = None, **policy: Any) -> c.WclClient:
    return c.WclClient(
        VANILLA,
        lambda endpoint: f"token-for-{endpoint}",
        transport=script.transport,
        clock=clock or FakeClock(),
        rng=random.Random(0),
        policy=c.Policy(**policy),
    )


def test_success_keeps_rate_and_sends_the_right_token() -> None:
    script = Script(ok({"x": 1}))
    client = _client(script)
    result = client.query(Q, {"a": 1}, endpoint="user")
    assert result.data["x"] == 1 and not result.partial
    assert client.last_rate == c.RateLimit(3600, 10.0, 1200)
    request = script.requests[0]
    assert str(request.url) == VANILLA.user_api
    assert request.headers["Authorization"] == "Bearer token-for-user"


def test_queries_must_ask_for_rate_data() -> None:
    with pytest.raises(c.InvalidRequest):
        _client(Script()).query("query Q { x }")


def test_unsupported_sites_cannot_build_a_client() -> None:
    with pytest.raises(UnsupportedSite):
        c.WclClient(SITES["fresh.warcraftlogs.com"], lambda e: "t")


def test_transient_errors_retry_with_capped_backoff() -> None:
    clock = FakeClock()
    script = Script(httpx.Response(503), httpx.Response(502), ok({"x": 2}))
    assert _client(script, clock).query(Q).data["x"] == 2
    assert len(clock.sleeps) == 2 and all(s <= 60 for s in clock.sleeps)


def test_retries_are_finite() -> None:
    clock = FakeClock()
    script = Script(*[httpx.Response(503) for _ in range(3)])
    with pytest.raises(c.ServerError):
        _client(script, clock, max_attempts=3).query(Q)
    assert len(script.requests) == 3


def test_retry_after_is_honoured_but_bounded_by_the_deadline() -> None:
    clock = FakeClock()
    script = Script(httpx.Response(429, headers={"Retry-After": "7"}), ok({"x": 3}))
    assert _client(script, clock).query(Q).data["x"] == 3
    assert clock.sleeps == [7.0]
    long_wait = Script(httpx.Response(429, headers={"Retry-After": "600"}))
    with pytest.raises(c.RateLimited):
        _client(long_wait, FakeClock(), call_deadline_s=120).query(Q)
    assert len(long_wait.requests) == 1


def test_retry_after_http_date() -> None:
    clock = FakeClock()
    date = "Tue, 13 Oct 2026 12:00:30 GMT"
    script = Script(httpx.Response(429, headers={"Retry-After": date}), ok({"x": 4}))
    _client(script, clock).query(Q)
    assert clock.sleeps == [30.0]


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(401), c.AuthenticationError),
        (httpx.Response(403), c.PermissionDenied),
        (httpx.Response(404), c.NotFound),
        (httpx.Response(400), c.InvalidRequest),
        (httpx.Response(302, headers={"Location": "https://evil.example/"}), c.InvalidResponse),
        (
            httpx.Response(200, json={"errors": [{"message": "You do not have permission"}]}),
            c.PermissionDenied,
        ),
        (
            httpx.Response(200, json={"errors": [{"message": "Cannot query field"}]}),
            c.InvalidRequest,
        ),
        (httpx.Response(200, json={"data": {"x": 1}}), c.InvalidResponse),
        (httpx.Response(200, content=b"<html>"), c.InvalidResponse),
    ],
)
def test_permanent_errors_are_typed_and_not_retried(
    response: httpx.Response, error: type[Exception]
) -> None:
    script = Script(response)
    with pytest.raises(error):
        _client(script).query(Q)
    assert len(script.requests) == 1


def test_partial_data_is_an_error_unless_accepted_and_then_marked() -> None:
    body = {
        "data": {"x": 1, "rateLimitData": rate()},
        "errors": [{"message": "some fight missing"}],
    }
    with pytest.raises(c.PartialResponse) as raised:
        _client(Script(httpx.Response(200, json=body))).query(Q)
    assert raised.value.data["x"] == 1 and raised.value.rate is not None
    result = _client(Script(httpx.Response(200, json=body))).query(Q, allow_partial=True)
    assert result.partial and result.errors


def test_rate_is_kept_when_a_call_fails() -> None:
    client = _client(Script(ok({"x": 1}), httpx.Response(403)))
    client.query(Q)
    with pytest.raises(c.PermissionDenied) as raised:
        client.query(Q)
    assert raised.value.rate == client.last_rate


def test_budget_uses_the_allowed_share_and_never_loops() -> None:
    client = _client(Script(ok()), budget_share=0.9)
    client.query(Q)  # 10 of 3600 spent
    client.ensure_budget(100.0)
    with pytest.raises(c.BudgetExceeded, match="exceeds the allowed"):
        client.ensure_budget(3300.0)  # over 3240 = 90% of 3600
    client.last_rate = c.RateLimit(3600, 3200.0, 900)
    with pytest.raises(c.BudgetExceeded, match="points left"):
        client.ensure_budget(100.0)
    with pytest.raises(c.BudgetExceeded, match="estimate unknown"):
        client.ensure_budget(None)


def test_budget_waits_once_for_the_reset_only_when_allowed() -> None:
    clock = FakeClock()
    client = _client(Script(), clock, wait_for_reset=True)
    client.last_rate = c.RateLimit(3600, 3200.0, 900)
    client.last_rate_at = clock.monotonic()
    client.ensure_budget(100.0)
    assert sum(clock.sleeps) == 901.0 and max(clock.sleeps) <= 30
    assert client.last_rate_at is None  # reset is assumed, never observed
    assert client.reset_wait is not None and client.reset_wait["elapsed_wait_s"] == 901
    client.last_rate = c.RateLimit(3600, 3200.0, 900)
    client.last_rate_at = clock.monotonic()
    with pytest.raises(c.BudgetExceeded, match="already used"):
        client.ensure_budget(100.0)


def test_reset_wait_requires_an_observed_reading() -> None:
    clock = FakeClock()
    client = _client(Script(), clock, wait_for_reset=True)
    client.last_rate = c.RateLimit(3600, 3200, 900)
    with pytest.raises(c.BudgetExceeded):
        client.ensure_budget(100)
    assert clock.sleeps == [] and client.reset_wait is None


def test_reset_wait_subtracts_the_readings_age() -> None:
    clock = FakeClock()
    client = _client(Script(), clock, wait_for_reset=True)
    client.last_rate = c.RateLimit(3600, 3200, 90)
    client.last_rate_at = 0
    clock.t = 60
    client.ensure_budget(100)
    assert sum(clock.sleeps) == 31
    assert client.reset_wait is not None and client.reset_wait["reading_age_s"] == 60


def test_cancelling_a_reset_wait_does_not_assume_a_reset() -> None:
    class CancelClock(FakeClock):
        def sleep(self, seconds: float) -> None:
            super().sleep(seconds)
            raise KeyboardInterrupt

    clock = CancelClock()
    client = _client(Script(), clock, wait_for_reset=True)
    original = c.RateLimit(3600, 3200, 90)
    client.last_rate = original
    client.last_rate_at = 0
    with pytest.raises(KeyboardInterrupt):
        client.ensure_budget(100)
    assert client.last_rate == original and client.last_rate_at == 0
    assert client.reset_wait is not None and client.reset_wait["elapsed_wait_s"] == 30


def test_no_budget_without_a_rate_reading() -> None:
    with pytest.raises(c.BudgetExceeded, match="no rate-limit reading"):
        _client(Script()).ensure_budget(1.0)


def _pages(table: dict[int, tuple[list[int], Any, Any]]) -> Any:
    return lambda page: table[page]


def test_pages_follow_has_more_pages() -> None:
    items = list(c.pages(_pages({1: ([1, 2], True, 1), 2: ([3], False, 2)}), max_pages=5))
    assert items == [1, 2, 3]


@pytest.mark.parametrize(
    "table",
    [
        {1: ([1], None, 1)},
        {1: ([1], "yes", 1)},
        {1: ([1], True, 1), 2: ([1], True, 1)},
        {1: ([1], True, 1), 2: ([2], True, 2), 3: ([3], True, 3)},
    ],
)
def test_pages_refuse_anything_that_could_hide_a_gap(table: dict[int, Any]) -> None:
    with pytest.raises(c.InvalidResponse):
        list(c.pages(_pages(table), max_pages=2))


def test_the_deadline_bounds_requests_not_only_sleeps() -> None:
    clock = FakeClock()

    def slow(request: httpx.Request) -> httpx.Response:
        clock.t += 100  # the request itself took 100 s
        return httpx.Response(429, headers={"Retry-After": "0"})

    script = Script(slow, slow, slow)
    with pytest.raises(c.RateLimited):
        _client(script, clock, call_deadline_s=150, max_attempts=5).query(Q)
    assert len(script.requests) == 2  # third attempt refused: deadline passed


def test_each_request_gets_at_most_the_remaining_time() -> None:
    clock = FakeClock()
    seen: list[Any] = []

    def capture(request: httpx.Request) -> httpx.Response:
        seen.append(request.extensions.get("timeout"))
        return ok({"x": 1})

    _client(Script(capture), clock, call_deadline_s=5).query(Q)
    assert seen and all(v is None or v <= 5 for v in seen[0].values())


def test_reset_wait_must_fit_the_cap_including_the_extra_second() -> None:
    clock = FakeClock()
    client = _client(Script(), clock, wait_for_reset=True, max_reset_wait_s=900)
    client.last_rate = c.RateLimit(3600, 3500.0, 900)
    client.last_rate_at = clock.monotonic()
    with pytest.raises(c.BudgetExceeded):
        client.ensure_budget(100.0)
    assert clock.sleeps == []


def test_request_checkpoint_does_not_rewind_the_live_budget(tmp_path: Path) -> None:
    from necropsy.wcl.checkpoint import Journal

    journal = Journal(tmp_path / "requests")
    first = _client(Script(ok({"x": 1})))
    first.journal = journal
    captured = first.query(Q).captured_at
    script = Script()
    second = _client(script)
    second.journal = Journal(journal.root)
    second.last_rate = c.RateLimit(3600, 2000, 300)
    second.last_rate_at = 99.0
    second.clock.sleep(3600)
    replayed = second.query(Q)
    assert replayed.data["x"] == 1
    assert replayed.captured_at == captured
    assert replayed.captured_at != second.clock.now().isoformat()
    assert not script.requests
    assert second.last_rate.points_spent == 2000
    assert second.last_rate_at == 99.0
    first.close()
    second.close()


def test_checkpoint_separates_finalization_and_drops_changed_report(tmp_path: Path) -> None:
    from necropsy.wcl.checkpoint import Journal

    journal = Journal(tmp_path / "requests")
    identity = journal.identity(VANILLA.host, "user", Q, {"code": "Test"})
    journal.write(identity, {"value": 1})
    journal.scope = "finalization"
    final = journal.identity(VANILLA.host, "user", Q, {"code": "Test"})
    assert journal.read(final) is None
    journal.write(final, {"value": 2})
    journal.forget_report("Test")
    assert journal.read(identity) is None and journal.read(final) is None


def test_partial_rate_limit_response_is_not_saved(tmp_path: Path) -> None:
    from necropsy.wcl.checkpoint import Journal

    script = Script(ok({"x": None}, errors=[{"message": "rate limit exceeded"}]))
    client = _client(script)
    client.journal = Journal(tmp_path / "requests")
    with pytest.raises(c.RateLimited):
        client.query(Q)
    assert not list(client.journal.root.glob("*.json"))
    client.close()


def test_corrupt_saved_response_is_refused(tmp_path: Path) -> None:
    from necropsy.wcl.cache import CacheCorrupt
    from necropsy.wcl.checkpoint import Journal

    journal = Journal(tmp_path / "requests")
    identity = journal.identity(VANILLA.host, "user", Q, None)
    journal.write(identity, {"x": 1})
    path = next(journal.root.glob("*.json"))
    path.write_text(path.read_text().replace('"x":1', '"x":2'))
    with pytest.raises(CacheCorrupt, match="digest differs"):
        journal.read(identity)
