"""Warcraft Logs GraphQL client: bounded retries, rate-limit pacing, typed errors.

Every query asks for `rateLimitData`, and the client keeps the latest reading
even when a call fails. Retries are finite and bounded by a deadline; permanent
errors (authentication, permission, missing data, invalid queries) are never
retried. A response with both data and errors is an error unless the caller
accepts partial data, and then it stays marked partial. Pagination refuses
missing or malformed page flags, repeated pages and runaway page counts.
"""

from __future__ import annotations

import email.utils
import random
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

import httpx

from necropsy.wcl.sites import Site, require_supported

Endpoint = Literal["client", "user"]
RATE_FIELDS = "rateLimitData { limitPerHour pointsSpentThisHour pointsResetIn }"


class WclError(Exception):
    """A Warcraft Logs request failed."""

    def __init__(self, message: str, rate: RateLimit | None = None) -> None:
        super().__init__(message)
        self.rate = rate


class AuthenticationError(WclError):
    """Credentials missing, expired or rejected."""


class PermissionDenied(WclError):
    """The data is private, archived for this account, or otherwise not allowed."""


class NotFound(WclError):
    """The requested character, report or fight does not exist."""


class InvalidRequest(WclError):
    """WCL rejected the query itself (schema or variables); retrying cannot help."""


class RateLimited(WclError):
    """The hourly points budget is exhausted or the server throttled us."""


class ServerError(WclError):
    """Transient server or network failure that outlived the retry budget."""


class InvalidResponse(WclError):
    """The response does not have the shape the query promises."""


class PageBudgetExhausted(InvalidResponse):
    """More pages remain than the caller's page budget allows (not a malformed page)."""


class PartialResponse(WclError):
    """Data came back together with errors."""

    def __init__(self, message: str, data: Any, errors: list[Any], rate: RateLimit | None) -> None:
        super().__init__(message, rate)
        self.data = data
        self.errors = errors


class BudgetExceeded(WclError):
    """A planned request would exceed the allowed points budget."""


@dataclass(frozen=True, slots=True)
class RateLimit:
    limit_per_hour: int
    points_spent: float
    reset_in_s: int

    @property
    def remaining(self) -> float:
        return max(0.0, self.limit_per_hour - self.points_spent)


@dataclass(frozen=True, slots=True)
class Result:
    data: Mapping[str, Any]
    rate: RateLimit
    partial: bool = False
    errors: tuple[Any, ...] = ()


class Clock(Protocol):
    def monotonic(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...
    def now(self) -> datetime: ...


class SystemClock:
    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def now(self) -> datetime:
        return datetime.now(UTC)


TokenProvider = Callable[[Endpoint], str]


@dataclass
class Policy:
    max_attempts: int = 5
    call_deadline_s: float = 120.0
    max_backoff_s: float = 60.0
    budget_share: float = 0.9
    """Share of the hourly limit a run may use."""
    wait_for_reset: bool = False
    """Allow one bounded wait for the hourly reset when the budget is short."""
    max_reset_wait_s: float = 3600.0


_RETRY_STATUS = frozenset({429, 502, 503, 504})
REQUEST_TIMEOUT_S = 30.0


def _rate(data: Any) -> RateLimit | None:
    raw = data.get("rateLimitData") if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        return None
    try:
        return RateLimit(
            int(raw["limitPerHour"]), float(raw["pointsSpentThisHour"]), int(raw["pointsResetIn"])
        )
    except KeyError, TypeError, ValueError:
        return None


def _retry_after(value: str | None, now: datetime) -> float | None:
    if not value:
        return None
    if value.strip().isdigit():
        return float(value.strip())
    try:
        when = email.utils.parsedate_to_datetime(value)
    except TypeError, ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - now).total_seconds())


def _classify(errors: list[Any]) -> type[WclError]:
    text = " ".join(
        str(e.get("message", "")) if isinstance(e, dict) else str(e) for e in errors
    ).lower()
    if "unauthorized" in text or "unauthenticated" in text or "invalid token" in text:
        return AuthenticationError
    if "permission" in text or "private" in text or "not allowed" in text or "archived" in text:
        return PermissionDenied
    if "not found" in text or "does not exist" in text:
        return NotFound
    if "rate limit" in text or "too many" in text:
        return RateLimited
    return InvalidRequest


def _error_summary(errors: list[Any]) -> str:
    messages = [str(e.get("message", "?")) if isinstance(e, dict) else str(e) for e in errors]
    return "; ".join(m[:200] for m in messages[:3])


@dataclass
class WclClient:
    site: Site
    tokens: TokenProvider
    transport: httpx.BaseTransport | None = None
    clock: Clock = field(default_factory=SystemClock)
    rng: random.Random = field(default_factory=random.Random)
    policy: Policy = field(default_factory=Policy)
    last_rate: RateLimit | None = None
    last_rate_at: float | None = None
    """Monotonic time `last_rate` was read from a response; None when not observed."""

    def __post_init__(self) -> None:
        require_supported(self.site)
        self._http = httpx.Client(transport=self.transport, timeout=30.0, follow_redirects=False)

    def close(self) -> None:
        self._http.close()

    def _backoff(self, attempt: int) -> float:
        return float(min(self.policy.max_backoff_s, 2.0**attempt + self.rng.uniform(0, 1)))

    def query(
        self,
        query: str,
        variables: Mapping[str, Any] | None = None,
        *,
        endpoint: Endpoint = "client",
        allow_partial: bool = False,
    ) -> Result:
        """Run one GraphQL query; the query must select `rateLimitData`."""
        if "rateLimitData" not in query:
            raise InvalidRequest("queries must select rateLimitData")
        url = self.site.client_api if endpoint == "client" else self.site.user_api
        deadline = self.clock.monotonic() + self.policy.call_deadline_s
        attempt = 0
        failure: WclError | None = None
        while True:
            remaining = deadline - self.clock.monotonic()
            if remaining <= 0:
                raise failure or ServerError("the request deadline passed", self.last_rate)
            attempt += 1
            wait: float | None = None
            try:
                response = self._http.post(
                    url,
                    json={"query": query, "variables": dict(variables or {})},
                    headers={"Authorization": f"Bearer {self.tokens(endpoint)}"},
                    timeout=min(REQUEST_TIMEOUT_S, remaining),
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                failure = ServerError(f"network error: {type(exc).__name__}", self.last_rate)
            else:
                status = response.status_code
                if status in (401, 403):
                    raise (AuthenticationError if status == 401 else PermissionDenied)(
                        f"WCL answered HTTP {status}", self.last_rate
                    ) from None
                if status == 404:
                    raise NotFound("WCL answered HTTP 404", self.last_rate) from None
                if 300 <= status < 400:
                    raise InvalidResponse(
                        f"unexpected redirect (HTTP {status}); redirects are not followed",
                        self.last_rate,
                    ) from None
                if status in _RETRY_STATUS or status >= 500:
                    failure = (RateLimited if status == 429 else ServerError)(
                        f"WCL answered HTTP {status}", self.last_rate
                    )
                    wait = _retry_after(response.headers.get("Retry-After"), self.clock.now())
                elif status != 200:
                    raise InvalidRequest(f"WCL answered HTTP {status}", self.last_rate) from None
                else:
                    return self._result(response, allow_partial)
            if attempt >= self.policy.max_attempts:
                raise failure
            pause = self._backoff(attempt) if wait is None else wait
            if self.clock.monotonic() + pause > deadline:
                raise failure
            self.clock.sleep(pause)

    def _result(self, response: httpx.Response, allow_partial: bool) -> Result:
        try:
            body = response.json()
        except ValueError:
            raise InvalidResponse("response is not JSON", self.last_rate) from None
        if not isinstance(body, dict):
            raise InvalidResponse("response is not a JSON object", self.last_rate)
        data = body.get("data")
        errors = body.get("errors") or []
        rate = _rate(data)
        if rate is not None:
            self.last_rate = rate
            self.last_rate_at = self.clock.monotonic()
        if errors and not isinstance(errors, list):
            raise InvalidResponse("errors is not a list", self.last_rate)
        if errors and not data:
            raise _classify(errors)(_error_summary(errors), self.last_rate)
        if not isinstance(data, dict):
            raise InvalidResponse("response has no data object", self.last_rate)
        if rate is None:
            raise InvalidResponse("response has no rateLimitData", self.last_rate)
        if errors:
            if not allow_partial:
                raise PartialResponse(
                    "WCL returned partial data: " + _error_summary(errors), data, errors, rate
                )
            return Result(data, rate, partial=True, errors=tuple(errors))
        return Result(data, rate)

    def ensure_budget(self, estimate: float | None) -> None:
        """Refuse work whose estimated points would exceed the allowed share.

        An unknown estimate is treated conservatively: it needs a fresh rate
        reading with at least a tenth of the allowed budget left.
        """
        rate = self.last_rate
        if rate is None:
            raise BudgetExceeded("no rate-limit reading yet; query rateLimitData first")
        cap = rate.limit_per_hour * self.policy.budget_share
        if estimate is not None and estimate > cap:
            raise BudgetExceeded(
                f"estimated {estimate:.0f} points exceeds the allowed {cap:.0f} per hour", rate
            )
        need = cap * 0.1 if estimate is None else estimate
        left = cap - rate.points_spent
        if need <= left:
            return
        if not self.policy.wait_for_reset or rate.reset_in_s + 1 > self.policy.max_reset_wait_s:
            raise BudgetExceeded(
                f"{left:.0f} of {cap:.0f} allowed points left this hour; need about "
                f"{need:.0f}" + (" (estimate unknown)" if estimate is None else ""),
                rate,
            )
        self.clock.sleep(float(rate.reset_in_s) + 1.0)
        self.last_rate = RateLimit(rate.limit_per_hour, 0.0, 3600)
        self.last_rate_at = None  # assumed after the reset, not observed


def pages(
    fetch: Callable[[int], tuple[list[Any], Any, Any]],
    *,
    max_pages: int,
    first_page: int = 1,
) -> Iterator[Any]:
    """Iterate items over numbered pages, refusing anything that would hide gaps.

    `fetch(page)` returns (items, has_more, page_identity). `has_more` must be a
    bool; a repeated page identity or more than `max_pages` pages is an error.
    """
    seen: set[Any] = set()
    page = first_page
    for _ in range(max_pages):
        items, has_more, identity = fetch(page)
        if not isinstance(has_more, bool):
            raise InvalidResponse(f"page {page} has no valid hasMorePages flag")
        if identity in seen:
            raise InvalidResponse(f"page {page} repeats an earlier page")
        seen.add(identity)
        yield from items
        if not has_more:
            return
        page += 1
    raise PageBudgetExhausted(f"more than {max_pages} pages; stopping instead of guessing")


__all__ = [
    "RATE_FIELDS",
    "AuthenticationError",
    "BudgetExceeded",
    "InvalidRequest",
    "InvalidResponse",
    "NotFound",
    "PageBudgetExhausted",
    "PartialResponse",
    "PermissionDenied",
    "Policy",
    "RateLimit",
    "RateLimited",
    "Result",
    "ServerError",
    "SystemClock",
    "WclClient",
    "WclError",
    "pages",
]
