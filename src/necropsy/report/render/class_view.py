"""Present class evidence through the same playbook components as Hunter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from necropsy.analysis.class_catalog import category_label
from necropsy.report.abilities import comparison
from necropsy.report.render.execution_view import execution as execution_plan
from necropsy.report.render.playbook_view import gear, line, number, source, with_strategy
from necropsy.report.render.view import CONTROLLABILITY, Value, evidence_view, value_of

METRIC_LABELS = {
    "damage_per_second": "Damage per second",
    "effective_healing_per_second": "Effective healing per second",
    "incoming_damage_per_second": "Incoming damage per second",
}


def _comparison_rows(play: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Format the saved primary comparison without deriving new analysis."""
    comparisons = play.get("comparisons") or []
    if not comparisons:
        return ()
    reference = comparisons[0]
    rows = []
    for name in play.get("primary_metrics") or []:
        values = reference.get("metrics", {}).get(name)
        if not values:
            continue
        difference = values.get("difference")
        percent = values.get("difference_pct")
        rows.append(
            {
                "label": METRIC_LABELS.get(name, name.replace("_", " ").capitalize()),
                "yours": number(values.get("yours"), 2),
                "reference": number(values.get("reference"), 2),
                "player": reference["player"],
                "difference": "Unknown" if difference is None else f"{difference:+.2f}",
                "percent": None if percent is None else f"{percent:+.1f}%",
            }
        )
    return tuple(rows)


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
        personal = subject or play.get("excluded_subject")
        personal_role = ((personal or {}).get(key, {}).get("role") or {}).get("value")
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
            (
                "WCL comparison category",
                category_label(document["subject"]["class_id"], play.get("selected_category")),
            ),
            ("Faction", play.get("selected_faction") or "Unknown"),
            ("Build", value_of((personal or {}).get(key, {}).get("build")).text),
            ("Encounter duty", personal_role or "Unknown"),
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
        limits = list(play.get("limitations") or [])
        result[boss["encounter_id"]] = {
            "review_key": f"necropsy:boss:{sha}:{boss['encounter_id']}",
            "metrics": (
                ("Your " + METRIC_LABELS[metric].lower(), measurement(subject)),
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
            "actions": tuple(
                {
                    **r,
                    "control_label": CONTROLLABILITY.get(
                        r.get("controllability", ""), r.get("controllability") or "Unknown"
                    ),
                    "evidence_views": tuple(evidence_view(boss, p) for p in r.get("evidence", [])),
                }
                for r in sorted(
                    recs, key=lambda r: {"high": 0, "medium": 1, "low": 2}.get(r["severity"], 9)
                )
            ),
            "comparison_rows": _comparison_rows(play),
            "quick_plan": quick,
            "pull_before": (
                line("Check your weapons, trinkets, enchants and consumables for your assignment."),
            ),
            "pull_during": (
                line(
                    "Practice this recorded opening: " + _opener(leader, key)
                    if leader
                    else "Opening unknown: no eligible recorded example is available.",
                    f"Example from {leader['player']} · leaderboard "
                    f"#{leader['leaderboard_position']}. "
                    "Not proof of an optimal opener or assigned duty."
                    if leader
                    else "Confirm your opening with the raid leader; no rotation is prescribed.",
                ),
                *encounter_lines,
                *quick[2]["lines"],
            ),
            "pull_asks": (
                line(
                    "Confirm your encounter duties before copying a reference player's decisions."
                ),
            ),
            "pull_limits": (*tuple(play.get("assessment_limits") or ()), *limits[:3]),
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
        result[boss["encounter_id"]] = with_strategy(result[boss["encounter_id"]], play)
    return result
