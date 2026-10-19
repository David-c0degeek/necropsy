"""Sourced, observation-only notes for combat-class healing views.

Recorded casts come from the actor's own cast events under the same coverage as
the saved cast counts, matched by numeric ability ID. No note infers an
opportunity, a missed use, an assignment or a resource loss: cooldown
availability and pre-pull state are outside the recorded fight window.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from necropsy.analysis.classes.classic_era.combat import CombatAnalysis
from necropsy.analysis.evidence import Evidenced, complete_or_unknown, unknown
from necropsy.analysis.generic.combat import CombatEvent
from necropsy.rules import load_rules

RULE = "healer-class-notes-v1"


@dataclass(frozen=True, slots=True)
class HealerNote:
    key: str
    kind: str
    text: str
    recorded_s: Evidenced[tuple[float, ...]]
    source: str | None = None
    retrieved: str | None = None
    # Casts that may belong to this group but whose identity is unresolved.
    unresolved_s: tuple[float, ...] = ()


def _rules(class_id: int) -> dict[str, Any] | None:
    classes: dict[int, dict[str, Any]] = load_rules("classic_era", "healer_notes")["classes"]
    return classes.get(class_id)


def _count(n: int) -> str:
    return {1: "once", 2: "twice"}.get(n, f"{n} times")


def notes(
    data: CombatAnalysis, class_id: int, actor_id: int, duration_s: float
) -> tuple[HealerNote, ...]:
    rules = _rules(class_id)
    if rules is None:
        return ()
    buffs = rules.get("pre_pull_buffs")
    groups = [*rules.get("planned_cooldowns", ()), *rules.get("emergency_cooldowns", ())]
    groups += buffs["spells"] if buffs else []
    known = {int(i) for group in groups for i in group["ability_ids"]}
    # One occurrence per recorded event, however many ability-name rows join to it.
    casts: dict[tuple[str, int], CombatEvent] = {
        (e.uid, e.copy): e for e in data.timeline if e.kind == "cast" and e.source_id == actor_id
    }

    def unresolved(group: list[dict[str, Any]], contains: str | None = None) -> tuple[float, ...]:
        if all(g.get("complete_ids") is True for g in group):
            return ()
        names = {g["name"] for g in group}
        return tuple(
            sorted(
                e.t_s
                for e in casts.values()
                if e.ability_id not in known
                and (
                    e.name is None
                    or e.name in names
                    or (contains is not None and contains in e.name)
                )
            )
        )

    def times(
        group: list[dict[str, Any]], detail: str, contains: str | None = None
    ) -> Evidenced[tuple[float, ...]]:
        counts = data.casts
        if counts.value is None:
            return unknown(
                counts.note or "actor cast coverage is incomplete",
                *counts.refs,
                coverage=counts.coverage,
            )
        if unresolved(group, contains):
            return unknown(
                "some cast identities are unresolved", *counts.refs, coverage=counts.coverage
            )
        ids = {int(i) for g in group for i in g["ability_ids"]}
        return complete_or_unknown(
            tuple(sorted(e.t_s for e in casts.values() if e.ability_id in ids)),
            counts.coverage,
            *counts.refs,
            rule_id=RULE,
            note=detail,
        )

    result = []
    for cooldown in rules.get("planned_cooldowns", ()):
        name = cooldown["name"]
        recorded = times([cooldown], f"recorded {name} casts")
        if recorded.value is None:
            text = f"{name} casts are unknown: {recorded.note}."
        elif not recorded.value:
            text = f"No {name} cast is recorded in this fight."
        elif duration_s < cooldown["cooldown_s"]:
            text = (
                f"Recorded {name} {_count(len(recorded.value))}. This fight is shorter than its "
                f"normal cooldown; confirm its planned timing with your healing team."
            )
        else:
            text = (
                f"Recorded {name} {_count(len(recorded.value))}. Availability before and during "
                f"the fight is unmeasured; confirm its planned timing with your healing team."
            )
        result.append(
            HealerNote(
                f"cooldown:{name}",
                "planned-cooldown",
                text,
                recorded,
                cooldown["source"],
                cooldown["retrieved"],
            )
        )
    for cooldown in rules.get("emergency_cooldowns", ()):
        name = cooldown["name"]
        recorded = times([cooldown], f"recorded {name} casts")
        if recorded.value == ():
            continue
        result.append(
            HealerNote(
                f"emergency:{name}",
                "emergency-cooldown",
                f"{name} casts are unknown: {recorded.note}."
                if recorded.value is None
                else f"Recorded {name} {_count(len(recorded.value))}. "
                "Emergency cooldowns have no expected-use target.",
                recorded,
                unresolved_s=unresolved([cooldown]),
            )
        )
    if buffs is not None:
        label = buffs["label"]
        contains = buffs.get("unresolved_name_contains")
        recorded = times(buffs["spells"], f"recorded in-fight {label} casts", contains)
        limit = f"Fight-window events cannot establish pre-pull {label} coverage or assignment."
        if recorded.value is None:
            text = f"In-fight {label} casts are unknown. {limit}"
        elif recorded.value:
            n = len(recorded.value)
            text = f"Recorded {n} in-fight {label} cast{'' if n == 1 else 's'}. {limit}"
        else:
            text = f"No cast of a listed {label} rank is recorded in the fight window. {limit}"
        result.append(
            HealerNote(
                f"pre-pull:{label}",
                "unmeasured",
                text,
                recorded,
                unresolved_s=unresolved(buffs["spells"], contains),
            )
        )
    readings = [r for r in data.resources if r["reading"].get("type") == 0]
    if readings and all(r["evidence"].value is None for r in readings):
        result.append(
            HealerNote(
                "resource:mana-capacity",
                "unmeasured",
                "Mana capacity is missing from this log, so mana timing and mana lost to "
                "encounter effects cannot be assessed.",
                unknown("every mana reading lacks capacity", *readings[0]["evidence"].refs),
            )
        )
    return tuple(result)
