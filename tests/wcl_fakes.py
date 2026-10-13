"""Test doubles for Warcraft Logs access.

Every response built here is a SYNTHETIC shape written to match the queries
Necropsy sends; none is a recorded WCL response. Field names follow the
exporter's working queries and the public API documentation, but they are not
proof that the live server accepts our queries (that is checked by the manual
live test).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx


def rate(spent: float = 10.0, limit: int = 3600, reset: int = 1200) -> dict[str, Any]:
    return {"limitPerHour": limit, "pointsSpentThisHour": spent, "pointsResetIn": reset}


def ok(data: dict[str, Any] | None = None, **extra: Any) -> httpx.Response:
    body = {"data": {**(data or {}), "rateLimitData": rate()}, **extra}
    return httpx.Response(200, json=body)


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps: list[float] = []
        self.start = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds

    def now(self) -> datetime:
        return self.start + timedelta(seconds=self.t)


class Script:
    """An httpx transport answering requests from a list of responses or callables."""

    def __init__(
        self, *answers: httpx.Response | Callable[[httpx.Request], httpx.Response]
    ) -> None:
        self.answers = list(answers)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self.answers:
            raise AssertionError(f"unexpected request {request.url}")
        answer = self.answers.pop(0)
        return answer(request) if callable(answer) else answer

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)

    def bodies(self) -> list[dict[str, Any]]:
        return [json.loads(r.content) for r in self.requests if r.content.startswith(b"{")]
