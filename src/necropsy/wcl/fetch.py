"""Fetch one fight's report bundle and event streams into the immutable cache.

Acquisition orchestration and the analyze CLI use these query shapes, initially
ported from the recorded exporter and checked by the manual live run.
Every events request also asks for the report's revision, and a page is accepted
only when it equals the bundle's revision, so pages of a revised report are never
filed with an older bundle. A stream is complete only on an explicit `null`
`nextPageTimestamp`; anything else unexpected leaves it incomplete (no marker).
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from necropsy.wcl.cache import Cache, FightKey, StreamKey, StreamPages, valid_report_code
from necropsy.wcl.client import (
    RATE_FIELDS,
    Endpoint,
    InvalidResponse,
    PageBudgetExhausted,
    PartialResponse,
    RateLimit,
    Result,
    WclClient,
    WclError,
)
from necropsy.wcl.sites import Site

QUERY_VERSION = 1
EVENTS_LIMIT = 10000
MAX_STREAM_PAGES = 300

REPORT_QUERY = f"""
query NecropsyReport($code: String!, $fightIDs: [Int]) {{
  reportData {{
    report(code: $code) {{
      code title startTime endTime visibility revision segments exportedSegments
      archiveStatus {{ isArchived archiveDate }}
      zone {{ id name }}
      fights(fightIDs: $fightIDs, translate: true) {{
        id encounterID originalEncounterID name startTime endTime kill fightPercentage
        bossPercentage difficulty size averageItemLevel classicSeasonID friendlyPlayers
        friendlySpecs friendlyItemLevels
        friendlyPets {{ id gameID instanceCount groupCount petOwner }}
        enemyNPCs {{ id gameID instanceCount groupCount petOwner }}
      }}
      masterData(translate: true) {{
        logVersion gameVersion lang
        actors {{ id name type subType server gameID petOwner icon }}
        abilities {{ gameID name type icon }}
      }}
      playerDetails(fightIDs: $fightIDs, includeCombatantInfo: true, translate: true)
      rankings(fightIDs: $fightIDs, playerMetric: dps)
    }}
  }}
  {RATE_FIELDS}
}}
"""
"""Shape ported from the recorded exporter and exercised by authenticated live runs."""


def report_query_for_metric(metric: str = "dps") -> str:
    if metric not in ("dps", "hps"):
        raise ValueError("unsupported report ranking metric")
    return (
        REPORT_QUERY
        if metric == "dps"
        else REPORT_QUERY.replace("playerMetric: dps", "playerMetric: hps")
    )


EVENTS_QUERY = f"""
query NecropsyEvents($code: String!, $fightIDs: [Int], $sourceID: Int, $targetID: Int,
                     $startTime: Float, $endTime: Float) {{
  reportData {{
    report(code: $code) {{
      revision
      events(fightIDs: $fightIDs, dataType: All, sourceID: $sourceID, targetID: $targetID,
             startTime: $startTime, endTime: $endTime, limit: {EVENTS_LIMIT},
             includeResources: true, translate: true) {{
        data
        nextPageTimestamp
      }}
    }}
  }}
  {RATE_FIELDS}
}}
"""


class ReportInaccessible(WclError):
    """WCL returned no report for this code (private, deleted or archived)."""


def report_query(
    client: WclClient, query: str, variables: dict[str, Any], endpoint: Endpoint
) -> Result:
    """One report query; WCL's partial answers become typed errors, never a crash.

    An archived report answers with partial data and an "archived" error: its content
    is readable only through the user endpoint (for subscribers). That is an
    unreachable report for this run, named as such; any other partial answer is an
    invalid response.
    """
    try:
        return client.query(query, variables, endpoint=endpoint)
    except PartialResponse as error:
        text = str(error)
        if error.errors and all(
            isinstance(item, dict)
            and isinstance(item.get("message"), str)
            and item["message"].casefold().startswith("this report has been archived.")
            for item in error.errors
        ):
            where = (
                "it is readable only through the user endpoint (subscribers)"
                if endpoint == "client"
                else "the signed-in account cannot read it"
            )
            raise ReportInaccessible(f"report archived; {where}", error.rate) from None
        raise InvalidResponse(f"partial answer: {text}", error.rate) from None


class RevisionChanged(WclError):
    """The report's revision changed during the fetch; restart with a fresh bundle."""


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


@dataclass(frozen=True, slots=True)
class Bundle:
    key: FightKey
    report: dict[str, Any]
    fight: dict[str, Any]
    start: float
    end: float
    endpoint: Endpoint
    sha256: str
    """The exact cached report generation, including its endpoint wrapper."""


def _report(result_data: Mapping[str, Any], code: str) -> dict[str, Any]:
    report = (result_data.get("reportData") or {}).get("report")
    if report is None:
        raise ReportInaccessible(f"WCL returned no report {code}")
    if not isinstance(report, dict):
        raise InvalidResponse(f"report {code} is not an object")
    return report


def fetch_bundle(
    client: WclClient,
    cache: Cache,
    site: Site,
    code: str,
    fight_id: int,
    encounter_id: int,
    *,
    endpoint: Endpoint = "client",
    metric: str = "dps",
) -> Bundle:
    """Fetch (and publish) the report bundle for one fight, validated before writing."""
    if not valid_report_code(code):
        raise ReportInaccessible(
            "report identifier is unsupported for identity-verified acquisition "
            "(including anonymized reports); candidate skipped"
        )
    client.ensure_budget(None)
    result = report_query(
        client, report_query_for_metric(metric), {"code": code, "fightIDs": [fight_id]}, endpoint
    )
    report = _report(result.data, code)
    if report.get("code") != code:
        raise InvalidResponse(f"asked for report {code}, got {report.get('code')!r}")
    revision = _int(report.get("revision"))
    if revision is None or revision < 0:
        raise InvalidResponse(f"report {code} has no usable revision; not cached")
    key = FightKey(site, code, revision, fight_id)
    fights = report.get("fights")
    fight = next(
        (f for f in fights or () if isinstance(f, dict) and _int(f.get("id")) == fight_id), None
    )
    if fight is None:
        raise InvalidResponse(f"report {code} has no fight {fight_id}")
    if _int(fight.get("encounterID")) != encounter_id:
        raise InvalidResponse(
            f"fight {fight_id} is encounter {fight.get('encounterID')!r}, not {encounter_id}"
        )
    start, end = _number(fight.get("startTime")), _number(fight.get("endTime"))
    if start is None or end is None or start < 0 or end <= start:
        raise InvalidResponse(f"fight {fight_id} has no valid time bounds")
    digest = cache.put_bundle(key, {"endpoint": endpoint, "report": report})
    return Bundle(key, report, fight, start, end, endpoint, digest)


def stream_identity(bundle: Bundle, role: str, actor_id: int, direction: str) -> dict[str, Any]:
    """The canonical request a stream answers (no auth data, no fetch-time metadata)."""
    return {
        "site": bundle.key.site.host,
        "code": bundle.key.code,
        "revision": bundle.key.revision,
        "fight": bundle.key.fight,
        "actor_id": actor_id,
        "role": role,
        "direction": direction,
        "start_time": bundle.start,
        "end_time": bundle.end,
        "data_type": "All",
        "limit": EVENTS_LIMIT,
        "include_resources": True,
        "translate": True,
        "query_version": QUERY_VERSION,
        "endpoint": bundle.endpoint,
    }


def _pages(
    client: WclClient, bundle: Bundle, actor_id: int, direction: str, max_pages: int
) -> Iterator[dict[str, Any]]:
    start = bundle.start
    for n in range(1, max_pages + 1):
        client.ensure_budget(None)
        result = report_query(
            client,
            EVENTS_QUERY,
            {
                "code": bundle.key.code,
                "fightIDs": [bundle.key.fight],
                "sourceID": actor_id if direction == "source" else None,
                "targetID": actor_id if direction == "target" else None,
                "startTime": start,
                "endTime": bundle.end,
            },
            bundle.endpoint,
        )
        report = _report(result.data, bundle.key.code)
        revision = _int(report.get("revision"))
        if revision != bundle.key.revision:
            raise RevisionChanged(
                f"report {bundle.key.code} revision {report.get('revision')!r} on page {n}, "
                f"bundle has {bundle.key.revision}",
                result.rate,
            )
        events = report.get("events")
        if not isinstance(events, dict) or "nextPageTimestamp" not in events:
            raise InvalidResponse(f"page {n} has no nextPageTimestamp", result.rate)
        data = events.get("data")
        if not isinstance(data, list) or not all(isinstance(e, dict) for e in data):
            raise InvalidResponse(f"page {n} data is not a list of events", result.rate)
        cursor = events["nextPageTimestamp"]
        if cursor is None:
            yield {"data": data, "nextPageTimestamp": None}
            return
        following = _number(cursor)
        if following is None or following <= start or following > bundle.end:
            raise InvalidResponse(f"page {n} has an invalid next cursor {cursor!r}", result.rate)
        yield {"data": data, "nextPageTimestamp": cursor}
        start = following
    raise PageBudgetExhausted(f"more than {max_pages} event pages; stream left incomplete")


def fetch_stream(
    client: WclClient,
    cache: Cache,
    bundle: Bundle,
    role: str,
    actor_id: int,
    direction: str,
    *,
    max_pages: int = MAX_STREAM_PAGES,
) -> StreamPages:
    """The verified complete stream: reused from the cache, or fetched and published.

    Any failure (revision change, bad cursor, budget, permission) propagates and
    leaves the stream without a marker, so it is never reported complete.
    """
    key = StreamKey(bundle.key, role, actor_id, direction, bundle.endpoint)
    identity = stream_identity(bundle, role, actor_id, direction)
    cached = cache.read_stream(key, identity)
    if cached is not None:
        return cached
    before = Reading(client.last_rate, client.last_rate_at)
    pages = _pages(client, bundle, actor_id, direction, max_pages)
    return cache.write_stream(
        key,
        identity,
        pages,
        meta=lambda: fetch_meta(client, before, Reading(client.last_rate, client.last_rate_at)),
    )


@dataclass(frozen=True, slots=True)
class Reading:
    """A rate-limit reading and the monotonic time it was observed (None: not observed)."""

    rate: RateLimit | None
    at: float | None


PERIOD_TOLERANCE_S = 2.0
"""Slack when matching period ends: the reset countdown is reported in whole seconds."""


def _rate(rate: RateLimit | None) -> dict[str, Any] | None:
    if rate is None:
        return None
    return {
        "limit_per_hour": rate.limit_per_hour,
        "points_spent": rate.points_spent,
        "reset_in_s": rate.reset_in_s,
    }


def _period_end(reading: Reading) -> float | None:
    if reading.rate is None or reading.at is None:
        return None
    return reading.at + float(reading.rate.reset_in_s)


def fetch_meta(client: WclClient, before: Reading, after: Reading) -> dict[str, Any]:
    """Provenance of one fetch: when, both rate readings, and a points delta if provable.

    The delta is account-wide (any other use of the account in between counts
    too), not an exact per-stream cost, and is given only when both readings were
    observed in responses and provably fall in the same hourly period: their
    period ends (observation time + reset countdown) agree, the later reading was
    taken before that end, and the spent counter did not drop. Otherwise it is
    unknown, never a negative or guessed number.
    """
    delta: float | None = None
    end_before, end_after = _period_end(before), _period_end(after)
    if end_before is None or end_after is None:
        note = "a rate reading was not observed in a response"
    elif (
        before.at is not None
        and after.at is not None
        and before.rate is not None
        and after.rate is not None
        and before.at <= after.at < end_before
        and abs(end_before - end_after) <= PERIOD_TOLERANCE_S
        and after.rate.points_spent >= before.rate.points_spent
    ):
        delta = round(after.rate.points_spent - before.rate.points_spent, 3)
        note = "account-wide points spent between the two readings, not an exact stream cost"
    else:
        note = "the readings are not provably in the same hourly period"
    return {
        "fetched_at": client.clock.now().isoformat(),
        "rate_before": _rate(before.rate),
        "rate_after": _rate(after.rate),
        "account_points_between_readings": delta,
        "points_note": note,
    }


__all__ = [
    "EVENTS_QUERY",
    "REPORT_QUERY",
    "Bundle",
    "Reading",
    "ReportInaccessible",
    "RevisionChanged",
    "fetch_bundle",
    "fetch_meta",
    "fetch_stream",
    "stream_identity",
]
