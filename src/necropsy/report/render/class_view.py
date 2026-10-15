"""Present class evidence through the same playbook components as Hunter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from necropsy.report.abilities import comparison
from necropsy.report.render.execution_view import execution as execution_plan
from necropsy.report.render.playbook_view import gear, line, number, source
from necropsy.report.render.view import Value, value_of


def _opener(entry: Any, key: str) -> str:
    if not entry:
        return "Unknown — no eligible recorded encounter."
    return (
        " → ".join(
            f"{number(e['t_s'], 2, 's')} {e.get('name') or e['ability_id']}"
            for e in entry[key].get("opener", [])
        )
        or "No opening casts recorded."
    )


def _buffs(entry: Any) -> str:
    raw = (entry or {}).get("environment", {}).get("world_buffs") or {}
    if raw.get("value") is None:
        return "Unknown — starting world-buff evidence is unavailable."
    return ", ".join(raw["value"]) or "No starting world buffs recorded."


def _loadout(entry: Any, slots: tuple[int, ...]) -> str:
    raw = (entry or {}).get("environment", {}).get("gear") or {}
    if raw.get("value") is None:
        return "Unknown — pull gear was not recorded."
    selected = [g for g in raw["value"] if g["slot"] in slots and g["item_id"]]
    return (
        "; ".join(str(g.get("name") or f"Item {g['item_id']} (name unknown)") for g in selected)
        or "No items recorded for these slots."
    )


def _gear(entry: Any, relic: bool) -> tuple[dict[str, Any], ...]:
    return tuple(
        {**row, "label": "Relic" if relic and row["label"] == "Ranged" else row["label"]}
        for row in gear(entry)
    )


def bosses(document: Mapping[str, Any], sha: str, key: str = "druid") -> dict[int, dict[str, Any]]:
    result = {}
    relic = document["subject"]["class_id"] in (2, 6, 9)
    for boss in document["bosses"]:
        play = boss.get("playbook") or {}
        subject = boss.get("subject")
        leader = play.get("reference")
        basis = subject or leader
        role = ((basis or {}).get(key, {}).get("role") or {}).get("value")
        metric = (
            "effective_healing_per_second"
            if role in ("restoration", "healer") or play.get("selected_metric") == "hps"
            else "damage_per_second"
        )
        if role in ("feral-tank", "tank") or play.get("selected_category") in (
            "Guardian",
            "Protection",
        ):
            metric = "incoming_damage_per_second"

        def measurement(entry: Any, metric_name: str = metric) -> Value:
            raw = (entry or {}).get(key, {}).get("metrics", {}).get(metric_name)
            return value_of(raw, lambda v: number(v, 1)) if raw else Value("Unknown", "unknown")

        n = play.get(
            "n_event_sources", max(len(play.get("comparisons") or []), int(leader is not None))
        )
        same = [
            e
            for e in boss.get("overall_cohort", [])
            if (e["environment"]["faction"] or {}).get("value") == play.get("selected_faction")
        ]
        recs = boss.get("recommendations") or []
        context = [
            ("Selected spec", play.get("selected_category") or "Unknown"),
            ("Faction", play.get("selected_faction") or "Unknown"),
            ("Build", value_of((basis or {}).get(key, {}).get("build")).text),
            ("Encounter duty", role or "Unknown"),
        ]
        quick = [
            {"label": "Your recorded opener", "lines": (line(_opener(subject, key)),)},
            {
                "label": "Faction leader opener",
                "lines": (
                    line(
                        _opener(leader, key),
                        "Recorded example; not proof of an optimal opener or assigned duty.",
                    ),
                ),
            },
            {
                "label": "Practice focus",
                "lines": (
                    line(
                        play.get("guidance")
                        or "Not measured for this role: no supported practice guidance is recorded."
                    ),
                ),
            },
        ]
        encounter = play.get("encounter_facts") or {}
        encounter_lines = tuple(
            line(
                t["text"],
                t.get("note") or "Pinned encounter facts, not an observed event or class rotation.",
                (source(encounter.get("source"), "Encounter source"),),
            )
            for t in encounter.get("timings", [])
        )
        if encounter_lines:
            quick.append({"label": "Encounter notes", "lines": encounter_lines})
        loadout = [
            {
                "label": label,
                "lines": (
                    line("You: " + _loadout(subject, slots)),
                    line(
                        "Faction leader: " + _loadout(leader, slots),
                        "Recorded pull equipment; review the full gear and enchants below.",
                    ),
                ),
            }
            for label, slots in (
                ("Weapons", (15, 16)),
                ("Trinkets", (12, 13)),
                ("Relic" if relic else "Ranged", (17,)),
            )
        ]
        loadout.append(
            {
                "label": "World buffs",
                "lines": (
                    line("You: " + _buffs(subject)),
                    line("Faction leader: " + _buffs(leader)),
                ),
            }
        )
        if key == "combat" and (
            document["subject"]["class_id"] == 10
            or any(((e or {}).get(key) or {}).get("pets") for e in (subject, leader))
        ):
            pet_lines = []
            for label, entry in (("You", subject), ("Faction leader", leader)):
                data = (entry or {}).get(key) or {}
                if not data.get("pets_known"):
                    text = "Unknown — owned-pet listing is incomplete."
                else:
                    text = (
                        "; ".join(
                            f"{p['name']}: {number(p['dps'].get('value'), 1)} DPS"
                            for p in data.get("pets", [])
                        )
                        or "No owned pet/summon participation recorded."
                    )
                pet_lines.append(
                    line(
                        label + ": " + text,
                        "Pet and summon actions are separate from actor ability use.",
                    )
                )
            loadout.append({"label": "Pet / summons", "lines": tuple(pet_lines)})
        core = {
            "Balance": ("Starfire", "Wrath", "Moonfire", "Insect Swarm", "Hurricane"),
            "Restoration": (
                "Healing Touch",
                "Rejuvenation",
                "Regrowth",
                "Tranquility",
                "Swiftmend",
            ),
            "Feral": ("Shred", "Claw", "Rake", "Rip", "Ferocious Bite", "Ravage", "Pounce"),
            "Guardian": ("Maul", "Swipe", "Swipe (Bear)", "Growl", "Challenging Roar"),
        }.get(str(play.get("selected_category") or ""), ())
        core = tuple(((basis or {}).get(key) or {}).get("core_abilities") or core)
        execution = execution_plan(subject, leader, key, core)
        execution.extend(
            {
                "label": r["finding"],
                "lines": (line(r["recommendation"], "Confidence " + r["confidence"]),),
            }
            for r in recs
        )
        limits = list(play.get("limitations") or [])
        result[boss["encounter_id"]] = {
            "review_key": f"necropsy:boss:{sha}:{boss['encounter_id']}",
            "metrics": (
                ("Your " + metric.replace("_", " "), measurement(subject)),
                ("Faction leader", measurement(leader)),
                (
                    "Your kill",
                    Value(
                        "Unknown"
                        if subject is None
                        else number(subject["kill_duration_s"], 1, "s"),
                        "observed" if subject else "unknown",
                    ),
                ),
                ("Event sources", Value(str(n), "inferred", "Limited sample" if n < 3 else None)),
            ),
            "context": context,
            "quick_plan": quick,
            "loadout": loadout,
            "execution": execution,
            "encounter_facts": encounter_lines,
            "gear": _gear(subject, relic),
            "leader_gear": _gear(leader, relic),
            "abilities": comparison(subject, leader),
            "cohort": [
                {
                    "entry": e,
                    "gear": _gear(e, relic),
                    "row_class": "alliance-row"
                    if e["environment"]["faction"].get("value") == "Alliance"
                    else "horde-row"
                    if e["environment"]["faction"].get("value") == "Horde"
                    else "unknown-row",
                }
                for e in same
            ],
            "dont": tuple(line(x) for x in limits[:3])
            or (line("Not measured for this role: no supported warnings recorded."),),
            "asks": tuple(
                line(r["recommendation"])
                for r in recs
                if r.get("controllability") == "raid-assignment"
            )
            or (
                line(
                    "Assigned encounter duties remain unknown; check assignments "
                    "before copying a leader's decisions."
                ),
            ),
        }
    return result
