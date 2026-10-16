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
from necropsy.analysis.context import ParticipantFight, realm_key
from necropsy.analysis.evidence import Evidenced, EvidenceRef, observed, unknown
from necropsy.rules import load_rules

RANKINGS_SOURCE = "wcl-rankings-gear"
RULES_SOURCE = "rules-items"
GAME_SOURCE = "game-client-data"
_PLACEHOLDERS = frozenset({"Unknown Item"})
"""Names WCL uses when it could not resolve an item; never treated as a real name."""


def recorded_hunter_dps(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> Evidenced[float]:
    """Recorded WCL score, independently of whether pet events can be reconstructed.

    Only live Hunter DPS acquisitions qualify. Never turn a score into damage
    totals, pet attribution or event coverage.
    """
    meta = con.execute("SELECT mode, partition_id, acquisition FROM snapshot_meta").fetchone()
    if meta is None or meta[0] != "live":
        return unknown("no live Hunter DPS acquisition")
    acquisition = json.loads(meta[2]) if isinstance(meta[2], str) else meta[2]
    records = [
        r for r in (acquisition or {}).get("bosses", []) if r.get("encounter_id") == pf.encounter_id
    ]
    if len(records) != 1:
        return unknown("no unique acquisition context for this encounter")
    key = records[0].get("key") or {}
    required = {
        "site": "vanilla.warcraftlogs.com",
        "game": "classic_era",
        "zone": 2006,
        "partition": meta[1],
        "encounter": pf.encounter_id,
        "role": "dps",
        "class_name": "Hunter",
        "difficulty": 0,
    }
    for name, value in required.items():
        dim = key.get(name) or {}
        if (
            type(dim.get("value")) is not type(value)
            or dim.get("value") != value
            or dim.get("status") != "enforced"
        ):
            return unknown("acquisition does not establish the Hunter DPS category")
    spec = key.get("spec") or {}
    kind = "subject" if pf.kind == "you" else "leaderboard"
    rows = con.execute(
        """SELECT source, row_index, player, raw FROM rankings
           WHERE kind = ? AND encounter_id = ? AND report_code = ? AND fight_id = ?
             AND player = ?
           ORDER BY source, row_index""",
        [kind, pf.encounter_id, pf.report_code, pf.fight_id, pf.player],
    ).fetchall()
    refs = []
    amounts = set()
    for source, index, player, raw in rows:
        row = json.loads(raw) if isinstance(raw, str) else raw
        report = row.get("report") or {}
        amount = row.get("amount")
        server = row.get("server") or {}
        if (
            player != pf.player
            or report.get("code") != pf.report_code
            or type(report.get("fightID")) is not int
            or report["fightID"] != pf.fight_id
            or not (
                row.get("class") == "Hunter"
                or (type(row.get("class")) is int and row["class"] == 3)
            )
            or (kind == "leaderboard" and row.get("name") != pf.player)
            or (
                kind == "leaderboard"
                and (type(row.get("hardModeLevel")) is not int or row["hardModeLevel"] != 0)
            )
            or (spec.get("status") == "enforced" and row.get("spec") != spec.get("value"))
            or (
                pf.server is not None
                and server.get("name") is not None
                and realm_key(server["name"]) != realm_key(pf.server)
            )
            or type(amount) not in (int, float)
            or not math.isfinite(amount)
            or amount < 0
        ):
            return unknown("ranking identity or DPS amount is invalid")
        amounts.add(float(amount))
        refs.append(
            EvidenceRef(
                pf.report_code,
                pf.fight_id,
                pf.actor_id,
                "rankings",
                detail=f"{source}, row {index}; recorded WCL Hunter DPS",
            )
        )
    if len(amounts) != 1:
        return unknown("no matching ranking score or ranking scores disagree", *refs)
    return observed(
        amounts.pop(), *refs, note="Recorded WCL DPS; event reconstruction unavailable."
    )


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
