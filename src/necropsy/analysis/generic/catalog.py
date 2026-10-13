"""Facts read from the snapshot's ranking rows: item names and parse percentiles.

WCL ranking rows carry each player's gear with display names, and the
subject's own ranking rows carry the parse percentile. Both are read from the
recorded rows only; nothing is guessed across reports or fights.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import duckdb

from necropsy.analysis import gamedata
from necropsy.analysis.context import ParticipantFight
from necropsy.analysis.evidence import Evidenced, EvidenceRef, observed, unknown
from necropsy.rules import load_rules

RANKINGS_SOURCE = "wcl-rankings-gear"
RULES_SOURCE = "rules-items"
GAME_SOURCE = "game-client-data"
_PLACEHOLDERS = frozenset({"Unknown Item"})
"""Names WCL uses when it could not resolve an item; never treated as a real name."""


@dataclass(frozen=True, slots=True)
class ItemName:
    item_id: int
    name: str | None
    source: str
    """`wcl-rankings-gear`, `rules-items`, `conflict` or `none`."""
    note: str | None = None


def _rows(con: duckdb.DuckDBPyConnection, kind: str | None = None) -> list[dict[str, Any]]:
    if kind is None:
        result = con.execute("SELECT raw FROM rankings ORDER BY source, row_index")
    else:
        result = con.execute(
            "SELECT raw FROM rankings WHERE kind = ? ORDER BY source, row_index", [kind]
        )
    out = []
    for (raw,) in result.fetchall():
        data = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(data, dict):
            out.append(data)
    return out


def item_catalog(con: duckdb.DuckDBPyConnection) -> dict[int, ItemName]:
    """Display names by item id: ranking rows first, the rules file as fallback.

    An id that ranking rows name in two different ways is reported as a conflict
    with no name, rather than picking one.
    """
    seen: dict[int, set[str]] = defaultdict(set)
    for row in _rows(con):
        for item in row.get("gear") or []:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(item.get("id"), int) and name and name not in _PLACEHOLDERS:
                seen[int(item["id"])].add(str(name))
    catalog: dict[int, ItemName] = {}
    for item_id, names in seen.items():
        if len(names) == 1:
            catalog[item_id] = ItemName(item_id, next(iter(names)), RANKINGS_SOURCE)
        else:
            catalog[item_id] = ItemName(
                item_id,
                None,
                "conflict",
                "ranking rows name this item differently: " + ", ".join(sorted(names)),
            )
    for item_id, game in gamedata.items().items():
        if item_id not in catalog:
            catalog[item_id] = ItemName(item_id, game.name, GAME_SOURCE)
    for entry in load_rules("classic_era", "items")["items"]:
        item_id = int(entry["id"])
        if item_id not in catalog:
            catalog[item_id] = ItemName(item_id, str(entry["name"]), RULES_SOURCE)
    return catalog


@dataclass(frozen=True, slots=True)
class ParsePercentile:
    percent: float
    """WCL `rankPercent`: the historical percentile of this parse."""
    today_percent: float | None
    """WCL `todayPercent`: the percentile against today's parses when exported."""
    total_parses: int | None
    bracket: int | None


def rank_percent(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> Evidenced[ParsePercentile]:
    """The subject's recorded percentile for exactly this report and fight."""
    if pf.kind != "you":
        return unknown("percentiles are recorded for the subject's own rankings only")
    matches = []
    for row in _rows(con, "subject"):
        raw_report = row.get("report")
        report: dict[str, Any] = raw_report if isinstance(raw_report, dict) else {}
        if report.get("code") == pf.report_code and report.get("fightID") == pf.fight_id:
            matches.append(row)
    ref = EvidenceRef(
        pf.report_code,
        pf.fight_id,
        pf.actor_id,
        "rankings",
        event_count=len(matches),
        detail="subject ranking rows for this fight",
    )
    if not matches:
        return unknown("no ranking row recorded for this report and fight", ref)
    tuples = {_percentile_fields(m) for m in matches}
    if len(tuples) != 1:
        return unknown("ranking rows for this fight disagree", ref)
    percent, today, total, bracket = next(iter(tuples))
    if percent is None:
        return unknown("the ranking row has no valid percentile", ref)
    return observed(ParsePercentile(percent, today, total, bracket), ref)


def _percent(value: Any) -> float | None:
    """A valid percentile: a finite number from 0 to 100 (booleans are not numbers here)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and 0.0 <= number <= 100.0 else None


def _count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _percentile_fields(
    row: dict[str, Any],
) -> tuple[float | None, float | None, int | None, int | None]:
    return (
        _percent(row.get("rankPercent")),
        _percent(row.get("todayPercent")),
        _count(row.get("rankTotalParses")),
        _count(row.get("bracketData")),
    )


__all__ = ["ItemName", "ParsePercentile", "item_catalog", "rank_percent"]
