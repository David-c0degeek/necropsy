"""Shared execution rows: compare actions, without prescribing a rotation."""

from __future__ import annotations

from typing import Any

from necropsy.report.abilities import rows
from necropsy.report.render.playbook_view import line, number, source


def _data(entry: Any, key: str) -> dict[str, Any]:
    return (entry or {}).get(key) or {}


def _counts(entry: Any, key: str) -> dict[str, int] | None:
    evidence = (entry or {}).get("ability_use") or _data(entry, key).get("casts") or {}
    return evidence.get("value")


def _link(entry: Any) -> tuple[Any, ...]:
    if not entry:
        return ()
    return (
        source(
            f"https://vanilla.warcraftlogs.com/reports/{entry['report_code']}"
            f"#fight={entry['fight_id']}",
            entry["player"] + " · recorded fight",
        ),
    )


def _sequence(entry: Any, key: str) -> str:
    if _counts(entry, key) is None:
        return "Unknown — no complete actor cast stream."
    events = _data(entry, key).get("opener") or []
    return (
        " → ".join(f"{number(e['t_s'], 2, 's')} {e.get('name') or e['ability_id']}" for e in events)
        or "No casts recorded in the opening window."
    )


def _first(entry: Any, key: str, name: str) -> str:
    counts = _counts(entry, key)
    if counts is None:
        return "Unknown"
    if not counts.get(name, 0):
        return "not used"
    events = _data(entry, key).get("timeline") or []
    evidence = (entry or {}).get("ability_use") or _data(entry, key).get("casts") or {}
    actors = {ref["actor"] for ref in evidence.get("refs", []) if ref.get("actor") is not None}
    times = [
        e["t_s"]
        for e in events
        if e["kind"] == "cast" and e.get("name") == name and e.get("source_id") in actors
    ]
    return number(min(times), 2, "s") if times else "Unknown"


def execution(
    subject: Any, leader: Any, key: str, core_abilities: tuple[str, ...] = ()
) -> list[dict[str, Any]]:
    """Use the same labelled plan rows as Hunter, with class-specific action names."""
    result = [
        {
            "label": "Opener",
            "lines": (
                line("You: " + _sequence(subject, key), links=_link(subject)),
                line(
                    "Faction leader: " + _sequence(leader, key),
                    "Compare this recorded opening with your first casts; confirm assignments.",
                    _link(leader),
                ),
            ),
        }
    ]
    mine, theirs = _counts(subject, key), _counts(leader, key)
    cooldown_names = {
        e.get("name")
        for entry in (subject, leader)
        for e in _data(entry, key).get("cooldowns") or []
    }
    comparisons = rows(
        mine,
        theirs,
        (subject or {}).get("kill_duration_s", 1),
        (leader or {}).get("kill_duration_s", 1),
    )
    # Frequent actions first, then each recorded cooldown/utility action separately.
    comparisons.sort(
        key=lambda r: (
            r["spell"] in cooldown_names,
            -(r["counts"]["reference"] or r["counts"]["yours"] or 0),
            r["spell"],
        )
    )
    for row in comparisons:
        name = row["spell"]
        if core_abilities and name not in core_abilities and name not in cooldown_names:
            continue
        kind = "Cooldown / utility" if name in cooldown_names else "Ability cadence"
        lines = []
        for label, side, entry in (
            ("You", "yours", subject),
            ("Faction leader", "reference", leader),
        ):
            lines.append(
                line(
                    f"{label}: {number(row['counts'][side])} uses · "
                    f"{number(row['per_minute'][side], 2)} uses/min · "
                    f"first use {_first(entry, key, name)}.",
                    f"{kind}. "
                    + (
                        f"{number(entry['kill_duration_s'], 1, 's')} fight."
                        if entry
                        else "No personal encounter in this spec."
                    ),
                    _link(entry),
                )
            )
        result.append({"label": name, "lines": tuple(lines)})
    if not comparisons:
        result.append(
            {
                "label": "Ability cadence",
                "lines": (line("Unknown — no complete actor cast stream was acquired."),),
            }
        )
    for label, field in (
        ("Damage targets", "damage_targets"),
        ("Healing targets", "healing_targets"),
    ):
        lines = []
        for who, entry in (("You", subject), ("Faction leader", leader)):
            data = _data(entry, key)
            values = (data.get(field) or {}).get("value")
            catalog = (data.get("actor_catalog") or {}).get("value") or {}
            text = (
                "Unknown"
                if values is None
                else "; ".join(
                    f"{(catalog.get(str(actor)) or {}).get('name') or 'Actor ' + str(actor)}: "
                    f"{number(amount)}"
                    for actor, amount in sorted(values.items(), key=lambda item: -item[1])[:3]
                )
                or "No recorded amounts"
            )
            lines.append(
                line(
                    f"{who}: {text}.",
                    "Recorded target amounts; priorities depend on assignments.",
                    _link(entry),
                )
            )
        result.append({"label": label, "lines": tuple(lines)})
    result.append(
        {
            "label": "Resources / movement",
            "lines": (
                line(
                    "Review resource readings and the full timeline before changing your cadence.",
                    "Cast gaps cannot identify movement, mana starvation or an optimal rotation.",
                ),
            ),
        }
    )
    return result
