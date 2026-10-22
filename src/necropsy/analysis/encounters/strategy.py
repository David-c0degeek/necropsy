"""Sourced static encounter strategy, separate from observed personal findings."""

from dataclasses import dataclass
from typing import Any

from necropsy.analysis.class_catalog import CLASS_NAMES
from necropsy.analysis.roles import ranking_policy
from necropsy.rules import load_rules


@dataclass(frozen=True, slots=True)
class StrategyItem:
    rule: str
    section: str
    text: str
    source: str
    retrieved: str
    kind: str = "general-strategy"
    controllability: str = "assignment-dependent"


@dataclass(frozen=True, slots=True)
class EncounterStrategy:
    items: tuple[StrategyItem, ...]
    limitation: str = (
        "General encounter strategy, not an observed phase, assigned duty or personal finding. "
        "Confirm your raid's plan; available logs may not establish these opportunities."
    )


def encounter_strategy(
    zone: str,
    encounter_id: int,
    partition: int,
    class_id: int,
    metric: str,
    *,
    category: str | None = None,
) -> EncounterStrategy | None:
    """Explicit ruleset/class/metric/category applicability; no inferred assignment."""
    if (
        type(partition) is not int
        or partition not in load_rules("classic_era", "raid_scope")["partitions"]
    ):
        return None
    if class_id not in CLASS_NAMES or metric not in ("dps", "hps"):
        raise ValueError("strategy needs a known class and ranking metric")
    if category is not None:
        category = ranking_policy(class_id, category, metric).category
    data: dict[str, Any] = load_rules("classic_era", f"zones/{zone}_guidance")
    entry = (data.get("strategy") or {}).get(encounter_id)
    if entry is None:
        return None
    items = []
    for row in entry["items"]:
        if "categories" in row:
            allowed = row["categories"]
            if (
                not isinstance(allowed, list)
                or not allowed
                or any(not isinstance(c, str) or not c for c in allowed)
            ):
                raise ValueError("strategy categories must be a nonempty list of names")
            if category is None or category not in allowed:
                continue
        if class_id not in row.get("classes", CLASS_NAMES) or metric not in row.get(
            "metrics", ("dps", "hps")
        ):
            continue
        if row["section"] not in ("before", "during", "raid"):
            raise ValueError("unknown encounter strategy section")
        items.append(
            StrategyItem(
                str(row["rule"]),
                str(row["section"]),
                str(row["text"]),
                str(row.get("source") or entry["source"]),
                str(row.get("retrieved") or entry["retrieved"]),
            )
        )
    return EncounterStrategy(tuple(items)) if items else None
