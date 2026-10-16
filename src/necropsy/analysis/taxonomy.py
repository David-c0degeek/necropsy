"""Source-specific talent evidence and Classic Era identity constraints."""

from __future__ import annotations

from typing import Any

from necropsy.analysis.class_catalog import RACES, TALENT_TREES, WCL_CATEGORIES, category_label
from necropsy.analysis.evidence import Evidenced, derived, unknown


def talent_points(raw: Any, key: str) -> str | None:
    """Combatant event IDs / playerDetails GUIDs encode three ordered tree totals."""
    if not isinstance(raw, list) or len(raw) != 3:
        return None
    if any(
        not isinstance(t, dict) or type(t.get(key)) is not int or not 0 <= t[key] <= 51 for t in raw
    ):
        return None
    values = [t[key] for t in raw]
    return "/".join(map(str, values)) if sum(values) <= 51 else None


def point_totals(build: str | None) -> tuple[int, ...] | None:
    if not isinstance(build, str):
        return None
    parts = build.split("/")
    if len(parts) != 3 or any(not p.isascii() or not p.isdecimal() for p in parts):
        return None
    values = tuple(map(int, parts))
    return values if max(values) <= 51 and sum(values) <= 51 else None


def primary_tree(class_id: int, build: Evidenced[str]) -> Evidenced[str]:
    """A unique largest tree is a derived label, not full allocation or fight duty."""
    points = point_totals(build.value)
    if class_id not in TALENT_TREES or points is None:
        return unknown("no valid three-tree talent distribution", *build.refs)
    largest = max(points)
    if largest == 0 or points.count(largest) != 1:
        return unknown("talent totals have no unique primary tree", *build.refs)
    return derived(
        TALENT_TREES[class_id][points.index(largest)],
        *build.refs,
        rule_id="unique-largest-talent-tree-v1",
        note="Largest tree total; not full allocation or encounter duty.",
    )


def build_matches(left: str | None, right: str | None) -> bool | None:
    a, b = point_totals(left), point_totals(right)
    return a == b if a is not None and b is not None else None


def race_validity(class_id: int, race: str | None, faction: str | None) -> bool | None:
    """Unknown identity stays unknown; constraints never fabricate a race."""
    if race is None or faction not in ("Alliance", "Horde") or class_id not in TALENT_TREES:
        return None
    record = RACES.get(race)
    return record is not None and record[0] == faction and class_id in record[1]


def category_metadata(class_id: int, slug: str | None) -> dict[str, Any]:
    record = WCL_CATEGORIES.get(class_id, {}).get(slug or "")
    return {
        "namespace": "wcl-vanilla",
        "class_id": class_id,
        "category_id": record[0] if record else None,
        "slug": slug,
        "label": category_label(class_id, slug),
    }
