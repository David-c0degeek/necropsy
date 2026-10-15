"""Shared descriptive ability-use comparisons for every supported class."""

from __future__ import annotations

from typing import Any


def difference(yours: float | None, reference: float | None) -> dict[str, Any]:
    """Descriptive arithmetic only; a difference never proves an execution error."""
    return {
        "yours": yours,
        "reference": reference,
        "difference": None if yours is None or reference is None else yours - reference,
        "difference_pct": None
        if yours is None or reference is None or reference == 0
        else 100 * (yours - reference) / reference,
    }


def rows(
    yours: dict[str, int] | None,
    theirs: dict[str, int] | None,
    your_seconds: float,
    their_seconds: float,
) -> list[dict[str, Any]]:
    result = []
    for name in sorted(set(yours or {}) | set(theirs or {})):
        mine = None if yours is None else yours.get(name, 0)
        other = None if theirs is None else theirs.get(name, 0)
        result.append(
            {
                "spell": name,
                "counts": difference(mine, other),
                "per_minute": difference(
                    None if mine is None else mine * 60 / your_seconds,
                    None if other is None else other * 60 / their_seconds,
                ),
            }
        )
    return result


def comparison(subject: Any, reference: Any) -> dict[str, Any] | None:
    if not reference:
        return None
    mine = (
        (subject or {}).get("ability_use")
        or ((subject or {}).get("druid") or {}).get("casts")
        or {}
    )
    theirs = reference.get("ability_use") or (reference.get("druid") or {}).get("casts")
    if theirs is None:
        return None
    return {
        "player": reference["player"],
        "rank": reference["leaderboard_position"],
        "report": reference["report_code"],
        "fight": reference["fight_id"],
        "personal": subject is not None,
        "rows": rows(
            mine.get("value"),
            theirs.get("value"),
            (subject or {}).get("kill_duration_s", 1),
            reference["kill_duration_s"],
        ),
        "known": theirs.get("value") is not None,
        "note": theirs.get("note")
        or "Recorded actor cast events, excluding passive damage and pets.",
    }
