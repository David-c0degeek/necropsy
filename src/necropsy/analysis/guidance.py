"""Execution guidance: general advice from cited facts, with snapshot conditions.

Guidance items come from rule data (rules/classic_era/zones/<zone>_guidance.yaml)
and always name the facts they rest on. Some apply only under a condition the
snapshot can decide (how long the subject's kill was, where ranked damage went);
an undecidable condition leaves the item visibly conditional, never decided.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from functools import cache
from typing import Any

from necropsy.analysis import gamedata
from necropsy.analysis.benchmark import BossData, Entry, kill_seconds, non_boss_share
from necropsy.rules import load_rules

GAME = "classic_era"
MIN_KNOWN = 3
KIND = "general-advice"


@dataclass(frozen=True, slots=True)
class Condition:
    name: str
    status: str
    """`true`, `false` or `unknown`."""
    detail: str
    """What decided it, with the numbers used (or why it could not be decided)."""
    level: str
    """`derived`, `inferred` (rests on inferred faction membership) or `unknown`."""


@dataclass(frozen=True, slots=True)
class GuidanceItem:
    key: str
    scope: str
    """`general`, `encounter` or `pet`."""
    status: str
    """`applies`, `otherwise` (condition false, alternative text shown), `inapplicable`
    (condition false, nothing to show) or `conditional` (condition unknown)."""
    text: str
    otherwise: str | None
    condition: Condition | None
    based_on: tuple[str, ...]
    kind: str
    rule: str


@dataclass(frozen=True)
class Guidance:
    rule: str
    rapid_fire: gamedata.RapidFire
    items: tuple[GuidanceItem, ...]


@cache
def _data(zone: str) -> dict[str, Any]:
    return dict(load_rules(GAME, f"zones/{zone}_guidance"))


def _worn(e: Entry) -> list[int] | None:
    gear = e.profile.gear.value
    return None if gear is None else [g.item_id for g in gear if g.item_id]


def _kill_within(subject: Entry, rf: gamedata.RapidFire) -> Condition:
    name = "kill_within_rapid_fire_cooldown"
    kill = kill_seconds(subject).value
    if kill is None:
        return Condition(name, "unknown", "kill duration unknown", "unknown")
    if not rf.known:
        return Condition(
            name, "unknown", "gear unknown: Rapid Fire set bonuses unchecked", "unknown"
        )
    return Condition(
        name,
        "true" if kill < rf.cooldown_s else "false",
        f"kill {kill:.1f} s; Rapid Fire cooldown {rf.cooldown_s:.0f} s",
        "derived",
    )


def _non_boss(boss: BossData, same: tuple[Entry, ...], inferred: bool, min_pct: float) -> Condition:
    name = "non_boss_ranked_damage"
    if not boss.rules.boss_game_ids:
        return Condition(name, "unknown", "no boss game ID rule for this encounter", "unknown")
    values = [v for v in (non_boss_share(e, boss.rules) for e in same) if v is not None]
    if len(values) < MIN_KNOWN:
        return Condition(
            name,
            "unknown",
            f"only {len(values)} same-faction entries with known ranked damage",
            "unknown",
        )
    median = float(statistics.median(values))
    return Condition(
        name,
        "true" if median >= min_pct else "false",
        f"same-faction median non-boss share {median:.1f}% over {len(values)} entries "
        f"(threshold {min_pct:g}%)",
        "inferred" if inferred else "derived",
    )


def _lockout(subject: Entry) -> Condition:
    name = "refocus_shares_trinket_lockout"
    worn = _worn(subject)
    if worn is None:
        return Condition(name, "unknown", "gear unknown", "unknown")
    refocus = load_rules(GAME, "hunter")["cooldown_facts"]["refocus"]
    charm, category = int(refocus["item"]), int(refocus["category"])
    if charm not in worn:
        return Condition(name, "false", "Renataki's Charm not worn", "derived")
    items = gamedata.items()
    others = []
    for i in worn:
        use = items[i].on_use if i in items else None
        if i != charm and use is not None and use.category == category:
            others.append(items[i].name)
    if not others:
        return Condition(
            name, "false", "no other worn on-use item shares its cooldown category", "derived"
        )
    return Condition(name, "true", "shares a category with " + ", ".join(sorted(others)), "derived")


def build(
    zone: str, boss: BossData, subject: Entry, same: tuple[Entry, ...], inferred_membership: bool
) -> Guidance:
    data = _data(zone)
    rf = gamedata.rapid_fire(_worn(subject))
    conditions: dict[str, Condition] = {}

    def condition(name: str) -> Condition:
        if name not in conditions:
            if name == "kill_within_rapid_fire_cooldown":
                conditions[name] = _kill_within(subject, rf)
            elif name == "non_boss_ranked_damage":
                min_pct = float(data["non_boss_share_min_pct"])
                conditions[name] = _non_boss(boss, same, inferred_membership, min_pct)
            elif name == "refocus_shares_trinket_lockout":
                conditions[name] = _lockout(subject)
            else:
                raise ValueError(f"unknown guidance condition {name!r}")
        return conditions[name]

    groups = (
        ("general", data.get("general") or ()),
        ("encounter", (data.get("encounters") or {}).get(boss.encounter_id) or ()),
        ("pet", (data.get("pet") or {}).get(boss.encounter_id) or ()),
    )
    items = []
    for scope, rows in groups:
        for row in rows:
            cond = condition(str(row["when"])) if row.get("when") else None
            otherwise = row.get("otherwise")
            if cond is None or cond.status == "true":
                status = "applies"
            elif cond.status == "false":
                status = "otherwise" if otherwise else "inapplicable"
            else:
                status = "conditional"
            items.append(
                GuidanceItem(
                    str(row["key"]),
                    scope,
                    status,
                    str(row["text"]),
                    None if otherwise is None else str(otherwise),
                    cond,
                    tuple(str(b) for b in row["based_on"]),
                    KIND,
                    str(data["rule"]),
                )
            )
    return Guidance(str(data["rule"]), rf, tuple(items))


__all__ = ["Condition", "Guidance", "GuidanceItem", "build"]
