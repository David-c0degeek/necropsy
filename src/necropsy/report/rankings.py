"""Verified saved ranking references, independent of class and event throughput."""

from __future__ import annotations

import json
import math
from typing import Any

import duckdb

from necropsy.analysis.benchmark import BossData
from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.analysis.evidence import EvidenceRef, observed
from necropsy.analysis.roles import ranking_policy
from necropsy.report.serialize import to_data
from necropsy.wcl.cohort import guild_faction


def top_metadata(
    con: duckdb.DuckDBPyConnection,
    boss: BossData,
    partition: int | None,
    category: str | None,
    metric: str | None,
    acquisition: dict[str, Any] | None,
    faction: str | None = None,
    class_id: int = 2,
) -> dict[str, Any] | None:
    """A saved first leaderboard row is a category score, never a proven duty."""
    if category is None or acquisition is None:
        return None
    policy = ranking_policy(class_id, category, metric)
    key = acquisition.get("key") or {}
    for name, value in {
        "class_name": CLASS_NAMES[class_id],
        "spec": category,
        "partition": partition,
        "encounter": boss.encounter_id,
        "role": policy.role,
    }.items():
        dimension = key.get(name) or {}
        if (
            dimension.get("value") != value
            or type(dimension.get("value")) is not type(value)
            or dimension.get("status") != "enforced"
        ):
            return None
    if "metric" in key and key["metric"].get("value") != policy.metric:
        return None
    rows = con.execute(
        "SELECT source, raw, row_index FROM rankings WHERE kind = 'leaderboard' "
        "AND encounter_id = ? AND page = 1 AND starts_with(source, 'leaderboards/') "
        "ORDER BY row_index",
        [boss.encounter_id],
    ).fetchall()
    if not rows or rows[0][2] != 0 or len({r[0] for r in rows}) != 1:
        return None
    selected = None
    faction_evidence = None
    for source, raw, index in rows:
        row = json.loads(raw) if isinstance(raw, str) else raw
        proof = guild_faction(row)
        report = row.get("report") or {}
        observed_entry = next(
            (
                e
                for e in boss.cohort
                if e.participant.report_code == report.get("code")
                and e.participant.fight_id == report.get("fightID")
                and e.participant.player == row.get("name")
            ),
            None,
        )
        recorded_faction = (
            observed_entry.profile.faction.value.value
            if observed_entry is not None and observed_entry.profile.faction.value is not None
            else proof.value
        )
        if faction is None or recorded_faction == faction:
            selected = source, raw, index
            faction_evidence = (
                observed_entry.profile.faction.level.value
                if observed_entry is not None
                else proof.level
            )
            break
    if selected is None:
        return None
    source, raw, index = selected
    row = json.loads(raw) if isinstance(raw, str) else raw
    amount = row.get("amount")
    if (
        row.get("class") not in (class_id, CLASS_NAMES[class_id])
        or row.get("spec") != category
        or type(amount) not in (int, float)
        or not math.isfinite(amount)
        or amount < 0
        or type(row.get("hardModeLevel")) is not int
        or row["hardModeLevel"] != 0
        or not isinstance(row.get("name"), str)
        or not row["name"].strip()
        or any(
            name in row and (type(row[name]) is not int or row[name] != index + 1)
            for name in ("rank", "position")
        )
    ):
        return None
    report = row.get("report") or {}
    code, fight = report.get("code"), report.get("fightID")
    ref = EvidenceRef(
        code if isinstance(code, str) else "",
        fight if type(fight) is int else None,
        None,
        "leaderboard",
        detail=f"{source}: page 1 row {index}; {category} {policy.metric}",
    )
    return {
        "player": row["name"],
        "leaderboard_position": index + 1,
        "scope": "overall" if faction is None else "same-faction-recorded",
        "faction": faction,
        "player_faction": recorded_faction,
        "faction_evidence": faction_evidence,
        "category": category,
        "metric": policy.metric,
        "category_score": to_data(observed(float(amount), ref)),
        "report_code": code,
        "fight_id": fight,
        "basis": "saved-ranking-metadata",
        "note": "Rank-one category metadata does not prove encounter duty or an optimal strategy.",
    }
