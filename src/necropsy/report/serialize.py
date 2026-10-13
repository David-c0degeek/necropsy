"""Turn analysis objects into deterministic JSON-ready data."""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any

from necropsy.analysis.evidence import CoverageRef, Evidenced, EvidenceRef

FLOAT_DIGITS = 6
JSON_EVENT_REFS = 10
"""Event occurrences listed per reference in analysis.json; the full count is kept."""


def to_data(value: Any) -> Any:
    """Recursively convert dataclasses, enums, tuples and sets to JSON data.

    Lists keep their order (chronology matters); sets are sorted; floats are
    rounded so repeated runs produce identical bytes.
    """
    if isinstance(value, Evidenced):
        return evidence(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, float):
        return round(value, FLOAT_DIGITS)
    if isinstance(value, bool | int | str) or value is None:
        return value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_data(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(to_data(k)): to_data(v) for k, v in value.items()}
    if isinstance(value, frozenset | set):
        return sorted((to_data(v) for v in value), key=repr)
    if isinstance(value, list | tuple):
        return [to_data(v) for v in value]
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _ref(ref: EvidenceRef) -> dict[str, Any]:
    out: dict[str, Any] = {"source": ref.source, "report": ref.report_code}
    if ref.fight_id is not None:
        out["fight"] = ref.fight_id
    if ref.actor_id is not None:
        out["actor"] = ref.actor_id
    if ref.event_ids or ref.event_count:
        out["events"] = [
            {"uid": uid, "copy": copy} for uid, copy in ref.event_ids[:JSON_EVENT_REFS]
        ]
        out["event_count"] = ref.event_count
    if ref.detail:
        out["detail"] = ref.detail
    return out


def _coverage(c: CoverageRef) -> dict[str, Any]:
    return {
        "report": c.report_code,
        "fight": c.fight_id,
        "actor": c.actor_id,
        "direction": c.direction,
        "trusted": c.trusted,
    }


def evidence(value: Evidenced[Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "value": to_data(value.value),
        "level": value.level.value,
        "claim": value.claim.value,
    }
    if value.rule_id:
        out["rule"] = value.rule_id
    if value.params:
        out["params"] = {k: to_data(v) for k, v in value.params}
    if value.note:
        out["note"] = value.note
    if value.refs:
        out["refs"] = [_ref(r) for r in value.refs]
    if value.coverage:
        out["coverage"] = [_coverage(c) for c in value.coverage]
    return out
