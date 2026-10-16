"""Recover pre-window combatant evidence without extending the ranked fight.

Some encounter rankings start after the combatant snapshot. Buff changes between
that snapshot and the ranked window must be replayed from the report timeline,
without a fight filter (the prelude can be assigned to a different WCL fight).
Raw pages and exact request scope are retained; no context damage enters totals.
"""

from __future__ import annotations

import math
from typing import Any

from necropsy.wcl.client import RATE_FIELDS, InvalidResponse, WclClient
from necropsy.wcl.fetch import Bundle, RevisionChanged, report_query

SNAPSHOT_QUERY = """
query NecropsyCombatantContext($code: String!, $fightIDs: [Int], $sourceID: Int,
                              $startTime: Float) {
  reportData { report(code: $code) {
    revision
    events(fightIDs: $fightIDs, dataType: CombatantInfo, sourceID: $sourceID,
           startTime: $startTime, limit: 10000) { data nextPageTimestamp }
  } }
  RATE
}
""".replace("RATE", RATE_FIELDS)

PRELUDE_QUERY = """
query NecropsyCombatantPrelude($code: String!, $targetID: Int,
                             $startTime: Float, $endTime: Float, $filterExpression: String!) {
  reportData { report(code: $code) {
    revision
    events(dataType: All, targetID: $targetID, filterExpression: $filterExpression,
           startTime: $startTime, endTime: $endTime, limit: 10000) { data nextPageTimestamp }
  } }
  RATE
}
""".replace("RATE", RATE_FIELDS)


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _pages(
    client: WclClient, bundle: Bundle, query: str, variables: dict[str, Any], end: float
) -> list[dict[str, Any]]:
    pages = []
    variables = dict(variables)
    for _ in range(300):
        client.ensure_budget(None)
        result = report_query(client, query, variables, bundle.endpoint)
        report = (result.data.get("reportData") or {}).get("report") or {}
        if type(report.get("revision")) is not int or report["revision"] != bundle.key.revision:
            raise RevisionChanged("combatant context report revision changed", result.rate)
        page = report.get("events")
        if not isinstance(page, dict) or not isinstance(page.get("data"), list):
            raise InvalidResponse("combatant context has no event page", result.rate)
        pages.append(page)
        cursor = page.get("nextPageTimestamp")
        if "nextPageTimestamp" not in page:
            raise InvalidResponse("combatant context has no continuation flag", result.rate)
        if cursor is None:
            return pages
        if not _number(cursor) or not (variables.get("startTime") or 0) < cursor <= end:
            raise InvalidResponse("combatant context continuation did not advance", result.rate)
        variables["startTime"] = cursor
    raise InvalidResponse("combatant context exceeded its page budget")


def snapshot(context: dict[str, Any]) -> dict[str, Any] | None:
    matches = [
        e
        for page in context["snapshots"]
        for e in page["data"]
        if isinstance(e, dict)
        and e.get("type") == "combatantinfo"
        and type(e.get("sourceID")) is int
        and e["sourceID"] == context["actor"]
        and type(e.get("fight")) is int
        and e["fight"] == context["fight"]
        and _number(e.get("timestamp"))
        and 0 <= e["timestamp"] <= context["ranked_start"]
    ]
    if not matches:
        return None
    latest = max(e["timestamp"] for e in matches)
    found = [e for e in matches if e["timestamp"] == latest]
    return found[0] if all(e == found[0] for e in found) else None


def validate_context(
    context: dict[str, Any],
    code: str,
    fight: int,
    actor: int,
    revision: int,
    endpoint: str,
    ranked_start: float,
) -> None:
    expected = {
        "version": 2,
        "report": code,
        "fight": fight,
        "actor": actor,
        "revision": revision,
        "endpoint": endpoint,
        "ranked_start": ranked_start,
    }
    for key, value in expected.items():
        if (
            (key != "ranked_start" and type(context.get(key)) is not type(value))
            or context.get(key) != value
            or (isinstance(context.get(key), bool) and type(value) is not bool)
        ):
            raise ValueError(f"combatant context {key} differs from its fight")
    if type(context.get("target_game_id")) is not int or context["target_game_id"] <= 0:
        raise ValueError("combatant context has no verified game actor identity")
    for kind in ("snapshots", "prelude"):
        pages = context.get(kind)
        if not isinstance(pages, list) or (kind == "snapshots" and not pages):
            raise ValueError("combatant context pages missing")
        previous = -1.0
        previous_last: float | None = None
        for i, page in enumerate(pages):
            if not isinstance(page, dict) or not isinstance(page.get("data"), list):
                raise ValueError("combatant context page malformed")
            if not all(isinstance(e, dict) for e in page["data"]):
                raise ValueError("combatant context event malformed")
            timestamps = [e.get("timestamp") for e in page["data"]]
            if any(not _number(t) for t in timestamps) or timestamps != sorted(timestamps):
                raise ValueError("combatant context event order is malformed")
            if timestamps:
                if previous_last is not None and timestamps[0] <= previous_last:
                    raise ValueError("combatant context has an ambiguous page boundary")
                previous_last = timestamps[-1]
            if "nextPageTimestamp" not in page:
                raise ValueError("combatant context page incomplete")
            cursor = page["nextPageTimestamp"]
            if i == len(pages) - 1:
                if cursor is not None:
                    raise ValueError("combatant context final page incomplete")
            elif not _number(cursor) or cursor <= previous:
                raise ValueError("combatant context pagination malformed")
            else:
                previous = cursor
    event = snapshot(context)
    if event is None or not isinstance(event.get("auras"), list):
        raise ValueError("combatant context has no unique starting snapshot")
    if event["timestamp"] < ranked_start and not context["prelude"]:
        raise ValueError("combatant context prelude is missing")
    for page in context["prelude"]:
        for e in page["data"]:
            if (
                type(e.get("targetID")) is not int
                or e["targetID"] != actor
                or not _number(e.get("timestamp"))
                or not event["timestamp"] <= e["timestamp"] <= ranked_start
                or e.get("type")
                not in {
                    "applybuff",
                    "removebuff",
                    "refreshbuff",
                    "applybuffstack",
                    "removebuffstack",
                }
                or type(e.get("abilityGameID")) is not int
            ):
                raise ValueError("combatant context prelude event is outside its scope")


def fetch_context(client: WclClient, bundle: Bundle, actor: int) -> dict[str, Any] | None:
    actors = [
        a
        for a in (bundle.report.get("masterData") or {}).get("actors") or []
        if a.get("id") == actor
    ]
    game_id = actors[0].get("gameID") if len(actors) == 1 else None
    if game_id is None or not _number(game_id) or game_id <= 0 or int(game_id) != game_id:
        return None  # A name or report-local ID cannot safely stand in for game ID.
    context: dict[str, Any] = {
        "version": 2,
        "target_game_id": int(game_id),
        "report": bundle.key.code,
        "fight": bundle.key.fight,
        "actor": actor,
        "revision": bundle.key.revision,
        "endpoint": bundle.endpoint,
        "ranked_start": bundle.start,
        "snapshots": _pages(
            client,
            bundle,
            SNAPSHOT_QUERY,
            {
                "code": bundle.key.code,
                "fightIDs": [bundle.key.fight],
                "sourceID": actor,
                "startTime": None,
            },
            bundle.end,
        ),
        "prelude": [],
    }
    event = snapshot(context)
    if event is None or not isinstance(event.get("auras"), list):
        return None
    if event["timestamp"] < bundle.start:
        context["prelude"] = _pages(
            client,
            bundle,
            PRELUDE_QUERY,
            {
                "code": bundle.key.code,
                "targetID": actor,
                # WCL expression actor IDs are game IDs, not report-local IDs.
                # Buffs view parameters can select the caster; All + an explicit
                # recipient expression was verified against actual prelude events.
                "filterExpression": f"target.id = {int(game_id)} AND type IN "
                '("applybuff", "removebuff", "refreshbuff", "applybuffstack", "removebuffstack")',
                "startTime": event["timestamp"],
                "endTime": bundle.start,
            },
            bundle.start,
        )
    try:
        validate_context(
            context,
            bundle.key.code,
            bundle.key.fight,
            actor,
            bundle.key.revision,
            bundle.endpoint,
            bundle.start,
        )
    except ValueError as error:
        raise InvalidResponse(str(error)) from error
    return context


def auras_at_start(context: dict[str, Any]) -> tuple[tuple[int, str | None], ...] | None:
    """Replay recipient buff changes by ability and source up to the ranked start."""
    event = snapshot(context)
    if event is None:
        return None
    active: dict[tuple[int, int | None], str | None] = {}
    for aura in event.get("auras") or []:
        if (
            not isinstance(aura, dict)
            or type(aura.get("ability")) is not int
            or (aura.get("source") is not None and type(aura["source"]) is not int)
        ):
            return None
        active[(aura["ability"], aura.get("source"))] = aura.get("name")
    events = [e for p in context["prelude"] for e in p["data"]]
    # Request order at equal timestamps is significant; sorting is stable.
    for e in sorted(events, key=lambda e: e["timestamp"]):
        if e["timestamp"] >= context["ranked_start"]:
            continue  # The ordinary target stream handles the boundary itself.
        key = (e["abilityGameID"], e.get("sourceID"))
        if key[1] is not None and type(key[1]) is not int:
            return None
        kind = e["type"]
        if kind == "removebuff":
            if any(
                ability == key[0] and (source is None or key[1] is None)
                for ability, source in active
                if (ability, source) != key
            ):
                return None  # An unidentified caster makes removal attribution ambiguous.
            active.pop(key, None)
        elif kind == "applybuff":
            active[key] = None
        elif key not in active:
            # A refresh can follow a snapshot with incomplete non-world buffs.
            # Its active state is positively established at this timestamp.
            active[key] = None
    by_id = {ability: name for (ability, _), name in active.items()}
    return tuple(sorted(by_id.items()))
