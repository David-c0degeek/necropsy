"""Conservative product summaries of saved analysis, never new recommendations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from necropsy.report.render.view import CONTROLLABILITY, RULE_HEADINGS

RAIDS = {
    "Naxxramas": "naxxramas",
    "Blackwing Lair": "blackwing-lair",
    "Molten Core": "molten-core",
    "Temple of Ahn'Qiraj": "ahn-qiraj",
    "Ahn'Qiraj": "ahn-qiraj",
}


def experience(document: Mapping[str, Any], class_name: str) -> dict[str, Any]:
    """Order saved findings by severity, keeping their original evidence attached."""
    rows: list[dict[str, Any]] = []
    priorities: list[dict[str, Any]] = []
    factions: set[tuple[str, str]] = set()
    severity_order = {"high": 0, "medium": 1, "low": 2}
    for boss in document["bosses"]:
        subject = boss.get("subject")
        faction = ((subject or {}).get("environment") or {}).get("faction") or {}
        if faction.get("value") in ("Alliance", "Horde"):
            factions.add((faction["value"], faction.get("level", "unknown")))
        anchor = f"boss-{boss['encounter_id']}"
        recs = boss.get("recommendations") or []
        base = (boss.get("benchmarks") or {}).get("baseline") or {}
        entries = base.get("entries")
        count = len(entries) if isinstance(entries, list) else entries
        medians = base.get("medians") or {}
        missing = any(m.get("value", {}).get("value") is None for m in medians.values())
        limited = count is None or count < 4 or missing
        quality = (
            "No reliable comparison"
            if not count
            else "Limited sample"
            if count < 4
            else "Some comparisons unavailable"
            if missing
            else "Comparison available"
        )
        top = min(recs, key=lambda r: severity_order.get(r["severity"], 9), default=None)
        state = (
            "Not assessed"
            if subject is None
            else "High priority"
            if top and top["severity"] == "high"
            else "Worth reviewing"
            if top
            else "Insufficient comparison"
            if not count
            else "No finding flagged"
        )
        row = {
            "anchor": anchor,
            "name": boss["boss"],
            "state": state,
            "attention": bool(recs),
            "limited": limited,
            "quality": quality,
            "sources": "Unknown" if count is None else str(count),
            "membership_label": "Faction membership inferred"
            if (base.get("membership") or {}).get("level") == "inferred"
            else "",
            "finding_count": len(recs),
            "has_subject": subject is not None,
            "summary": top["recommendation"]
            if top
            else (
                "No personal fight in this view."
                if subject is None
                else "No rule produced a recommendation; this is not a clean bill of health."
            ),
            "kill": f"{subject['kill_duration_s']:.0f} s" if subject else "Unknown",
        }
        rows.append(row)
        for index, rec in enumerate(recs):
            priorities.append(
                {
                    **rec,
                    "boss_anchor": anchor,
                    "boss_name": boss["boss"],
                    "heading": RULE_HEADINGS.get(rec["rule"], rec["recommendation"]),
                    "control": CONTROLLABILITY.get(rec["controllability"], rec["controllability"]),
                    "order": (severity_order.get(rec["severity"], 9), len(rows), index),
                }
            )
    priorities.sort(key=lambda r: r["order"])
    # One example per rule avoids a raid-wide issue occupying every priority slot.
    unique: dict[str, dict[str, Any]] = {}
    for priority in priorities:
        rule = priority["rule"]
        if rule not in unique:
            unique[rule] = {**priority, "boss_count": 0}
        unique[rule]["boss_count"] += 1
    coverage = document["coverage"]
    gaps = coverage.get("streams_not_complete")
    issues = coverage.get("snapshot_issues")
    anomalies = coverage.get("event_anomalies")
    incomplete = any(v is None or v > 0 for v in (gaps, issues, anomalies))
    acquisition = document.get("acquisition") or {}
    incomplete = (
        incomplete
        or bool(acquisition.get("stopped"))
        or any(
            not (b.get("coverage") or {}).get("complete", False)
            for b in acquisition.get("bosses", [])
        )
    )
    faction_values = {f[0] for f in factions}
    faction_name = next(iter(faction_values)) if len(faction_values) == 1 else "Unknown"
    faction_level = (
        "inferred"
        if any(f[1] == "inferred" for f in factions)
        else "observed"
        if factions and all(f[1] == "observed" for f in factions)
        else "unknown"
    )
    return {
        "class_key": class_name.lower()
        if class_name
        in (
            "Warrior",
            "Paladin",
            "Hunter",
            "Rogue",
            "Priest",
            "Shaman",
            "Mage",
            "Warlock",
            "Druid",
        )
        else "neutral",
        "raid_key": RAIDS.get(document["zone"]["name"], "neutral"),
        "faction": faction_name,
        "faction_key": faction_name.lower(),
        "faction_level": faction_level,
        "bosses": rows,
        "priorities": list(unique.values())[:3],
        "finding_count": len(priorities),
        "attention_count": sum(r["attention"] for r in rows),
        "personal_count": sum(r["has_subject"] for r in rows),
        "limited_count": sum(r["limited"] for r in rows),
        "coverage": "Data limitations"
        if incomplete
        else (
            "No event streams acquired"
            if coverage.get("streams") == 0
            else "Coverage unavailable"
            if coverage.get("streams") is None
            else "Recorded streams complete"
        ),
        "coverage_note": (
            f"{gaps if gaps is not None else 'Unknown'} incomplete streams · "
            f"{issues if issues is not None else 'Unknown'} snapshot issues · "
            f"{anomalies if anomalies is not None else 'Unknown'} event anomalies. "
            "These describe limits in the available evidence, not sync progress. "
            "See the coverage notes for affected fights and measurements."
        ),
    }
