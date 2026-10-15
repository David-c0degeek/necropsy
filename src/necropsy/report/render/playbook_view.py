"""Word the structured playbook without querying or recalculating analysis.

This is presentation: decisions, statistics and game knowledge arrive in the
document. Each displayed comparison keeps its uncertainty and sample visible.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from necropsy.report.render.view import Value, value_of

SLOTS = (
    (0, "Head"),
    (1, "Neck"),
    (2, "Shoulders"),
    (4, "Chest"),
    (5, "Waist"),
    (6, "Legs"),
    (7, "Feet"),
    (8, "Wrist"),
    (9, "Hands"),
    (10, "Ring 1"),
    (11, "Ring 2"),
    (12, "Trinket 1"),
    (13, "Trinket 2"),
    (14, "Back"),
    (15, "Main hand"),
    (16, "Off hand"),
    (17, "Ranged"),
)


def number(value: Any, digits: int = 0, suffix: str = "") -> str:
    return "Unknown" if value is None else f"{value:.{digits}f}{suffix}"


def source(url: Any, label: str = "Source") -> dict[str, str] | None:
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme != "https" or not parsed.netloc or parsed.username is not None:
        return None
    return {"url": url, "label": label}


def line(text: str, note: str = "", links: Any = ()) -> dict[str, Any]:
    return {"text": text, "note": note, "sources": tuple(x for x in links if x)}


def aggregate(raw: Any, suffix: str = "") -> str:
    if not isinstance(raw, dict):
        return "Unknown — this statistic was not recorded"
    sample = f"n={raw['n_values']}"
    if raw["n_without"]:
        sample += f"; {raw['n_without']} known without a value"
    if raw["n_unknown"]:
        sample += f"; {raw['n_unknown']} unknown"
    if raw.get("value") is None:
        return f"Unknown — {raw.get('reason') or 'insufficient evidence'} ({sample})"
    qualifier = " · inferred comparison" if raw.get("level") == "inferred" else ""
    return f"{number(raw['value'], 1, suffix)}{qualifier} ({sample})"


def who(raw: Any) -> str:
    if not isinstance(raw, dict):
        return "Unknown comparator"
    rank = raw.get("leaderboard_position")
    return (
        (f"#{rank} " if rank is not None else "")
        + str(raw["player"])
        + " · "
        + number(raw.get("ranked_dps"))
        + " DPS"
    )


def _item(item_id: Any, names: Mapping[str, str]) -> str:
    if item_id == 0:
        return "Empty (recorded)"
    if item_id is None:
        return "Unknown / empty in this recorded set"
    return names.get(str(item_id), f"Unknown item (ID {item_id})")


def _items(items: Any, names: Mapping[str, str]) -> str:
    return (
        "Unknown"
        if items is None
        else " + ".join(_item(i, names) for i in items if i is not None) or "None recorded"
    )


def _count(ev: Any) -> Value:
    if not isinstance(ev, dict) or ev.get("value") is None or ev.get("claim") != "complete":
        return Value("Unknown", "unknown", "complete cast coverage is unavailable")
    return Value(str(len(ev["value"])), str(ev["level"]), ev.get("note"))


def gear(entry: Any) -> tuple[dict[str, Any], ...]:
    ev = {} if not entry else entry["environment"]["gear"]
    recorded = ev.get("value")
    by = {} if recorded is None else {i["slot"]: i for i in recorded}
    rows = []
    for slot, label in SLOTS:
        item = by.get(slot)
        if item is None:
            value = Value("Unknown", "unknown", "slot not recorded")
            detail = ""
        elif item["item_id"] == 0:
            value = Value("Empty (recorded)", str(ev["level"]))
            detail = ""
        else:
            name = item.get("name")
            value = Value(
                str(name) if name else f"Unknown item (ID {item['item_id']})",
                str(ev["level"]) if name else "unknown",
                item.get("name_note")
                or (f"Item ID {item['item_id']}; display name unavailable" if not name else None),
            )
            extras = [
                str(item.get("enchant_name") or f"enchant {item['permanent_enchant']}")
                if item.get("permanent_enchant")
                else "",
                str(
                    item.get("temporary_enchant_name")
                    or f"temporary enchant {item['temporary_enchant']}"
                )
                if item.get("temporary_enchant")
                else "",
            ]
            detail = " · ".join(x for x in extras if x)
        rows.append({"label": label, "value": value, "detail": detail})
    return tuple(rows)


def _pets(entry: Mapping[str, Any]) -> dict[str, Any]:
    hunter = entry["hunter"]
    pets = hunter["hunter_pets"]
    if not pets:
        listed = entry.get("pets_listed")
        unclassified = any(p["category"].get("value") is None for p in hunter["pets"])
        text = (
            "No Hunter pet listed" if listed is True and not unclassified else "Unknown pet listing"
        )
        return {"name": text, "family": (), "abilities": "", "dps": Value("Unknown", "unknown")}
    # Per-actor DPS remains explicit: multiple pets are not silently merged.
    return {
        "name": ", ".join(str(p["name"]) for p in pets),
        "family": tuple(value_of(p["family"]) for p in pets),
        "abilities": "; ".join(
            ", ".join(str(a[1]) for a in p["abilities"].get("value") or [])
            if p["abilities"].get("value") is not None
            else "Abilities unknown"
            for p in pets
        ),
        "dps": value_of(pets[0]["dps"], lambda v: number(v))
        if len(pets) == 1
        else Value("Multiple pets — see each actor in the report", "unknown"),
    }


def cohort(entry: Mapping[str, Any], names: Mapping[str, str]) -> dict[str, Any]:
    env, hunter = entry["environment"], entry["hunter"]
    faction = value_of(env["faction"])
    race = value_of(env["race"]["race"])
    labels = {"Alliance": "alliance-row", "Horde": "horde-row"}
    weapons = []
    for key in ("ranged", "main_hand", "off_hand"):
        ev = hunter["gear"][key]
        weapons.append(value_of(ev, lambda v: _item(v["item_id"], names)))
    return {
        "player": str(entry["player"]),
        "rank": entry.get("leaderboard_position"),
        "faction": faction,
        "class": labels.get(faction.text, "unknown-row"),
        "race": race,
        "race_note": "; ".join(
            str(r["detail"]) for r in env["race"]["race"].get("refs") or [] if r.get("detail")
        ),
        "wf": value_of(env["windfury"]["procs"]),
        "wf_status": str(env["windfury"]["status"]),
        "dps": number(entry["ranking"].get("ranked_dps")),
        "dps_note": (
            str(
                (entry["ranking"].get("external") or {}).get("note")
                or "Event-derived ranked DPS is unavailable."
            )
            if entry["ranking"].get("ranked_dps") is None
            else ""
        ),
        "spec": value_of(env["talents"]),
        "trinkets": value_of(
            hunter["gear"]["trinkets"], lambda v: _items([i["item_id"] for i in v], names)
        ),
        "weapons": tuple(weapons),
        "raptor": _count(hunter["shots"]["raptor_strike"]["casts"]),
        "white": value_of(hunter["white_melee_swings"]),
        "pet": _pets(entry),
        "gear": gear(entry),
        "kill": number(entry["kill_duration_s"], 1, "s"),
    }


def _sequence(raw: Any) -> str:
    if raw is None:
        return "Unknown — cast sequence unavailable"
    return (
        " → ".join(f"{str(kind).replace('_', ' ').title()} {number(t, 2, 's')}" for t, kind in raw)
        or "No casts recorded"
    )


def _quick_plan(
    plan: Mapping[str, Any] | None,
    static: Mapping[str, Any],
    game: Mapping[str, Any],
    pet_facts: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    if not plan:
        return (
            {
                "label": "Recommended opener",
                "lines": (line("Unknown: opening evidence unavailable."),),
            },
            {"label": "Rapid Fire", "lines": (line("Unknown: cooldown evidence unavailable."),)},
            {
                "label": "Notes",
                "lines": (line("Review the evidence limits before choosing an opening."),),
            },
        )
    sequence = plan["opener"].get("comparator_sequence")
    ranged_names = {
        "auto_shot": "Auto Shot",
        "aimed_shot": "Aimed Shot",
        "multi_shot": "Multi-Shot",
    }
    shots = (
        []
        if sequence is None
        else [
            ranged_names[str(kind)]
            for _time, kind in sequence
            if kind in {"auto_shot", "aimed_shot", "multi_shot"}
        ][:5]
    )
    pattern = " → ".join(shots) if shots else "Unknown: no comparator ranged opening recorded."
    member = str(plan["context"].get("membership_level", "unknown"))
    basis = "Practice pattern from the same-faction comparator; detailed timestamps remain below."
    if member == "inferred":
        basis += " Comparator membership is inferred."
    rapid = plan["rapid_fire"]["same_faction_first_s"]
    usage = (
        f"{rapid['n_values']} cast RF / {rapid['n_values'] + rapid['n_without']} known; "
        f"{rapid['n_without']} had no RF cast recorded; {rapid['n_unknown']} unknown."
    )
    timing = (
        f"First-use median: {number(rapid['value'], 1, 's')} after fight start."
        if rapid.get("value") is not None
        else "First-use timing unknown: insufficient recorded evidence."
    )
    encounter_static = {
        **static,
        "guidance": {
            "items": [
                item
                for item in (static.get("guidance") or {}).get("items") or []
                if item.get("scope") == "encounter"
            ]
        },
    }
    notes = tuple(
        advice for _destination, advice in _guidance_lines(encounter_static, game, pet_facts)
    )
    return (
        {"label": "Recommended opener", "lines": (line(pattern, basis),)},
        {
            "label": "Rapid Fire",
            "lines": (
                line(
                    timing,
                    usage
                    + " Observed cast timing, not a mandatory pull timing."
                    + (
                        " Comparison membership is inferred."
                        if rapid.get("level") == "inferred"
                        else ""
                    ),
                ),
            ),
        },
        {
            "label": "Notes",
            "lines": notes
            or (line("Review your cooldown window against the detailed execution plan below."),),
        },
    )


def _overall_reason(boss: Mapping[str, Any], document: Mapping[str, Any] | None, live: bool) -> str:
    if boss["benchmarks"].get("overall_top_unavailable_reason"):
        return str(boss["benchmarks"]["overall_top_unavailable_reason"])
    if boss["benchmarks"].get("overall_top"):
        return "Overall #1 was acquired, but its ranked DPS is unavailable."
    if not live:
        return "Overall #1 is absent from this recorded export."
    acquisition = (document or {}).get("acquisition") or {}
    if acquisition.get("cross_faction"):
        record: Mapping[str, Any] = next(
            (
                b
                for b in acquisition.get("bosses") or []
                if b.get("encounter_id") == boss["encounter_id"]
            ),
            {},
        )
        entry = record.get("cross_faction") or {}
        reason = entry.get("reason") or record.get("cross_faction_reason")
        return "Overall #1 was not acquired: " + str(reason or "see recorded acquisition coverage")
    return (
        "Overall #1 was not acquired in this same-faction run. "
        "Add --cross-faction and use a fresh output directory to request separate context."
    )


def _cooldown(raw: Mapping[str, Any], label: str, live: bool = False) -> tuple[dict[str, Any], ...]:
    comparison = "acquired-cohort" if live else "overall-top-five"
    used = raw.get("subject_used")
    mine = (
        "Unknown"
        if used is None
        else (number(raw.get("subject_first_s"), 2, "s") if used else "not cast")
    )
    rank = raw.get("rank_one")
    rank_timing = "Unknown"
    if rank:
        if rank.get("used") is False:
            rank_timing = "not cast"
        elif rank.get("used") is True or "used" not in rank:
            rank_timing = number(rank.get("first_s"), 2, "s")
    ranked = "Unknown" if not rank else f"{who(rank['entry'])}: {rank_timing}"
    return (
        line(
            (
                "Your first "
                f"{label}"
                ": "
                f"{mine}"
                ". Same-faction median: "
                f"{aggregate(raw.get('same_faction_first_s'), 's')}"
                "."
            ),
            f"Rank 1 timing (context): {ranked}.",
        ),
        line(
            "Your logged "
            f"{label}"
            ": "
            f"{mine}"
            f" · {comparison} median: "
            f"{aggregate(raw.get('overall_first_s'), 's')}"
            " (context only)."
        ),
    )


def _weave(raw: Mapping[str, Any], membership: str) -> str:
    verdict = raw.get("boss_verdict") or "unknown"
    others = raw.get("non_boss_verdict") or "unknown"
    entries = "; ".join(
        f"{e['entry']['player']}: {number(e.get('raptors_total'))} Raptor, "
        f"{number(e.get('raptors_on_boss'))} boss / {number(e.get('raptors_on_others'))} other NPCs"
        for e in raw.get("same_faction") or []
    )
    qualifier = " Comparison membership is inferred." if membership == "inferred" else ""
    return (
        "On the boss: "
        f"{verdict.upper()}"
        ". On other hostile NPCs: "
        f"{others.upper()}"
        ". "
        f"{entries or 'No same-faction entries recorded.'}"
        f"{qualifier}"
    )


def _client_sources(game: Mapping[str, Any], tables: tuple[str, ...]) -> tuple[Any, ...]:
    template = game.get("url_template")
    if not isinstance(template, str):
        return ()
    return tuple(
        source(template.format(table=t, build=game.get("build", "")), f"{t} client data")
        for t in tables
    )


def _guidance_lines(
    static: Mapping[str, Any], game: Mapping[str, Any], pet_facts: Mapping[str, Any]
) -> tuple[tuple[str, dict[str, Any]], ...]:
    guidance = static.get("guidance") or {}
    encounter = static.get("encounter") or {}
    rows = []
    for item in guidance.get("items") or []:
        status = item["status"]
        condition = item.get("condition")
        if status == "otherwise":
            text = str(item["otherwise"])
        elif status == "conditional":
            text = "Conditional advice: " + str(item["text"])
            if item.get("otherwise"):
                text += " Alternative: " + str(item["otherwise"])
        elif status == "inapplicable":
            text = "Not applicable to the recorded setup: " + str(item["text"])
        else:
            text = str(item["text"])
        note = "General game advice · rule " + str(item["rule"])
        if condition:
            note += f" · {condition['level']}: {condition['detail']}"
        links: list[Any] = []
        based_on = set(item["based_on"])
        if based_on - {"rapid_fire", "refocus", "pet"}:
            links.append(source(encounter.get("source"), "Encounter source"))
        if based_on & {"rapid_fire", "refocus"}:
            links.extend(_client_sources(game, ("SpellEffect", "SpellCooldowns", "ItemSetSpell")))
        if "pet" in based_on:
            links.extend(_pet_sources(pet_facts, ("passive_ranks",)))
        destination = (
            "Pet"
            if item["scope"] == "pet"
            else "Refocus"
            if str(item["key"]).startswith("refocus")
            else "Rapid Fire"
        )
        rows.append((destination, line(text, note, links)))
    return tuple(rows)


def _pet_sources(facts: Mapping[str, Any], keys: tuple[str, ...]) -> tuple[Any, ...]:
    sources = facts.get("sources") or {}
    labels = {
        "training_points": "Training points",
        "passive_ranks": "Passive ranks",
        "active_ranks": "Active ranks",
    }
    return tuple(source(url, labels[key]) for key in keys for url in sources.get(key) or [])


def _profile_lines(
    facts: Mapping[str, Any], limit: int | None = None
) -> tuple[dict[str, Any], ...]:
    profiles = (facts.get("profiles") or [])[:limit]
    rows = tuple(
        line(
            f"{p['label']}: {p['total_tp']}/{p['budget_tp']} TP — "
            + ("fits the budget" if p["fits"] else "over budget"),
            "Example for a pet that can learn these abilities; guide-based training costs "
            "are not client-verified. "
            "Your pet's training is not recorded in the export.",
        )
        for p in profiles
    )
    if not rows:
        return rows
    return (
        *rows,
        line(
            "Profile sources:",
            links=_pet_sources(facts, ("training_points", "passive_ranks", "active_ranks")),
        ),
    )


def boss_view(
    boss: Mapping[str, Any],
    names: Mapping[str, str],
    sha: str,
    document: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    live = (document or {}).get("mode") == "live"
    subject = boss.get("subject")
    acquisition = (document or {}).get("acquisition") or {}
    leader_practice = None
    if subject is None and acquisition.get("selected_category"):
        leader_practice = next(
            (
                e
                for e in boss.get("overall_cohort", [])
                if e["environment"]["faction"]["value"] == acquisition.get("subject_faction")
            ),
            None,
        )
    plan = boss.get("playbook")
    overall = boss.get("overall_cohort")
    rows = tuple(cohort(e, names) for e in (overall if overall is not None else boss["cohort"]))
    base = boss["benchmarks"].get("baseline")
    member = "unknown" if not base else str(base["membership"]["level"])
    target = (
        "Unknown"
        if not base
        else " / ".join(
            value_of(base["shot_targets"].get(k), lambda v: f"{v[0]}-{v[1]}").text
            for k in ("auto", "aimed", "multi")
        )
    )
    ceiling = boss["benchmarks"].get("ceiling")
    comparator = who(ceiling)
    faction = "Unknown" if not subject else value_of(subject["environment"]["faction"]).text
    mix = boss["benchmarks"].get("faction_mix") or {}
    mix_text = " / ".join(f"{n} {f}" for f, n in mix.get("by_faction", {}).items()) or "Unknown"
    if mix.get("inferred_faction_entries"):
        mix_text += f" · {mix['inferred_faction_entries']} inferred"
    percent = Value("Unknown", "unknown", "percentile not recorded in this analysis")
    if subject:
        raw = subject["ranking"].get("rank_percent")
        if raw and raw.get("value") and raw["value"].get("today_percent") is not None:
            percent = Value(
                number(raw["value"]["today_percent"], 2),
                str(raw["level"]),
                "Today's percentile at export time; no live update",
            )
    shots = (
        "Unknown"
        if not subject
        else " / ".join(
            _count(subject["hunter"]["shots"][k]["casts"]).text
            for k in ("auto_shot", "aimed_shot", "multi_shot")
        )
    )
    top = boss["benchmarks"].get("overall_top")
    top_level = str(((top or {}).get("ranked_dps_evidence") or {}).get("level", "derived"))
    top_note = None
    metadata_top = (top or {}).get("basis") == "leaderboard-metadata"
    if metadata_top:
        captured = top.get("captured_at")
        top_note = "Saved WCL leaderboard DPS; metadata-only context. " + (
            f"Captured {captured}." if captured else "Capture time not recorded in this archive."
        )
    metrics = (
        (
            "Your DPS",
            Value(
                "Unknown" if not subject else number(subject["ranking"].get("ranked_dps")),
                "derived"
                if subject and subject["ranking"].get("ranked_dps") is not None
                else "unknown",
            ),
        ),
        ("Current %", percent),
        (
            "Your kill",
            Value(
                "Unknown" if not subject else number(subject["kill_duration_s"], 1, "s"),
                "observed" if subject else "unknown",
            ),
        ),
        (
            "Overall #1 DPS",
            Value(
                number(None if not top else top.get("ranked_dps")),
                top_level if top and top.get("ranked_dps") is not None else "unknown",
                top_note
                if top and top.get("ranked_dps") is not None
                else _overall_reason(boss, document, live),
                metadata_top,
            ),
        ),
        (
            f"{faction} comparator in " + ("acquired cohort" if live else "overall top five"),
            Value(comparator, member if ceiling else "unknown"),
        ),
    )
    pet_context = "Unknown"
    loadout: list[dict[str, Any]] = []
    execution: list[dict[str, Any]] = []
    dont: list[dict[str, Any]] = []
    asks: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    document = document or {}
    game = document.get("game_data") or {}
    pet_facts = ((document.get("overview") or {}).get("setup") or {}).get("pet_facts") or {}
    static: Mapping[str, Any] = {}
    if plan:
        context = plan["context"]
        member = context["membership_level"]
        weak = " Comparison group is inferred." if member == "inferred" else ""
        weapon_lines = [
            line(
                _items([w["main_hand"], w["off_hand"], w["ranged"]], names),
                "; ".join(who(e) for e in w["entries"])
                + f" · {w['raptor_users']} recorded Raptor users.{weak}",
            )
            for w in plan["weapons"]
        ]
        loadout.append(
            {
                "label": "Weapons",
                "lines": tuple(weapon_lines)
                or (line("Unknown — no complete same-faction weapon sets recorded."),),
            }
        )
        pair_lines = [
            line(_items(p["items"], names), "; ".join(who(e) for e in p["entries"]) + weak)
            for p in plan["trinket_pairs"]
        ]
        static = plan.get("static") or {}
        encounter = static.get("encounter") or {}
        for bonus in static.get("type_bonuses") or []:
            applies = bonus["applies_to_boss"]
            text = (
                "Boss eligibility unknown"
                if applies is None
                else ("Applies to this boss" if applies else "Does not apply to this boss")
            )
            pair_lines.append(
                line(
                    f"{bonus['name']}: {text}. {bonus['effect']}.",
                    "Creature-type rule; adds may differ.",
                    (source(bonus["source"], "Item source"),),
                )
            )
        loadout.append(
            {
                "label": "Trinkets",
                "lines": tuple(pair_lines)
                or (line("Unknown — no complete same-faction trinket pairs recorded."),),
            }
        )
        pet = plan["pet"]
        median = aggregate(pet["same_faction_median_dps"])
        pet_median = pet["same_faction_median_dps"]
        pet_context = (
            f"{number(pet['subject_dps'])} → {number(pet_median.get('value'))} "
            f"{faction} med · {pet_median['level']}"
        )
        missing = pet["no_hunter_pet"]
        pet_text = (
            "No Hunter pet took part (listing recorded)."
            if missing is True
            else (
                "Pet participation unknown; the listing/classification is incomplete."
                if missing is None
                else (
                    f"{pet['subject_pet'] or 'Multiple Hunter pets'}"
                    " · family "
                    f"{pet['subject_family'] or 'unknown'}"
                )
                + (" (inferred)" if pet["subject_family_level"] == "inferred" else "")
                + "."
            )
        )
        pet_lines = [
            line(
                pet_text,
                f"Your pet DPS: {number(pet['subject_dps'])}; same-faction median {median}.",
            ),
            line(
                "Recorded same-faction pet range: "
                f"{aggregate(pet['same_faction_dps_min'])}"
                " to "
                f"{aggregate(pet['same_faction_dps_max'])}"
                "."
            ),
        ]
        if pet["subject_died_at_s"] is not None:
            pet_lines.append(
                line(
                    "Your pet died at "
                    f"{number(pet['subject_died_at_s'], 1, 's')}"
                    ". Review its survival and positioning."
                )
            )
        if pet["subject_stopped_early_s"] is not None:
            pet_lines.append(
                line(
                    "Last pet damage was "
                    f"{number(pet['subject_stopped_early_s'], 1, 's')}"
                    " before the kill; this alone does not establish why."
                )
            )
        loadout.append({"label": "Pet", "lines": tuple(pet_lines)})
        weave = _weave(plan["weaving"], member)
        loadout.append(
            {
                "label": "Weaving",
                "lines": (
                    line(
                        weave,
                        "Protect ranged cycles; prevalence alone does not prove weaving helps.",
                    ),
                ),
            }
        )
        opener = plan["opener"]
        execution.append(
            {
                "label": "Opener",
                "lines": (
                    line("Recorded opening: " + _sequence(opener["subject_sequence"])),
                    line("Same-faction comparator: " + _sequence(opener["comparator_sequence"])),
                    line(
                        (
                            "First Aimed: you "
                            f"{number(opener['subject_first_aimed_s'], 2, 's')}"
                            "; comparator "
                            f"{number(opener['comparator_first_aimed_s'], 2, 's')}"
                            "; faction median "
                            f"{aggregate(opener['same_faction_first_aimed_s'], 's')}"
                            "."
                        ),
                        (
                            "Use the recorded sequence to review your first ranged cycle; "
                            "timings are not a guaranteed opening script."
                        ),
                    ),
                ),
            }
        )
        execution.append(
            {"label": "Rapid Fire", "lines": _cooldown(plan["rapid_fire"], "RF", live)}
        )
        execution.append(
            {
                "label": "Refocus",
                "lines": (
                    line(
                        (
                            "Renataki at the pull: "
                            f"{opener['renataki_users']}"
                            "/"
                            f"{opener['renataki_known']}"
                            " known same-faction entries."
                        ),
                        (
                            "Refocus is gear-dependent; recorded usage does not make the "
                            "trinket mandatory."
                        ),
                    ),
                    *_cooldown(plan["refocus"], "Refocus", live),
                ),
            }
        )
        for destination, advice in _guidance_lines(static, game, pet_facts):
            for row in (*loadout, *execution):
                if row["label"] == destination:
                    row["lines"] = (*row["lines"], advice)
        guidance = static.get("guidance") or {}
        rapid = guidance.get("rapid_fire")
        if rapid:
            execution[1]["lines"] += (
                line(
                    f"Rapid Fire: {number(rapid['duration_s'], 0, 's')} duration, "
                    f"{number(rapid['cooldown_s'], 0, 's')} cooldown, "
                    f"+{number(rapid['ranged_haste_pct'])}% ranged haste.",
                    "; ".join(rapid.get("applied") or ())
                    + (
                        " · worn-set check complete"
                        if rapid["known"]
                        else " · gear unknown; base values"
                    ),
                    _client_sources(game, ("SpellEffect", "SpellCooldowns", "ItemSetSpell")),
                ),
            )
        if any(i["key"] == "frost-resistance" for i in guidance.get("items") or []):
            for row in loadout:
                if row["label"] == "Pet":
                    profiles = _profile_lines(pet_facts, limit=1)
                    row["lines"] = (*row["lines"], *profiles)
        destinations = {
            "trinket": "Trinkets",
            "pet-absent": "Pet",
            "pet-dps": "Pet",
            "pet-death": "Pet",
            "pet-stopped-early": "Pet",
            "weave-adoption": "Weaving",
            "rapid-fire-unused": "Rapid Fire",
            "aimed-cadence": "Opener",
        }
        for recommendation in boss["recommendations"]:
            rec_destination = destinations.get(recommendation["rule"])
            for row in (*loadout, *execution):
                if row["label"] == rec_destination:
                    row["lines"] += (
                        line(
                            str(recommendation["recommendation"]),
                            f"Rule {recommendation['rule']} · "
                            f"{recommendation['confidence']} confidence. "
                            "Read the finding and its evidence below.",
                        ),
                    )
        for item in plan["do_not"]:
            kind, detail = item["kind"], item["details"]
            if kind == "other-faction-melee-package":
                p = detail["package"]
                text = (
                    "Do not use "
                    f"{who(p['entry'])}"
                    "'s other-faction melee package as your direct "
                    "target: "
                    f"{number(p['white_swings'])}"
                    " white swings, "
                    f"{number(p['white_dps'])}"
                    " white DPS, WF "
                    f"{p['windfury_status']}"
                    " ("
                    f"{number(p['windfury_procs'])}"
                    " procs)."
                )
                note = ""
                if p.get("windfury_matched_damage") is not None:
                    note = (
                        f"{number(p['windfury_matched_damage'])}"
                        " damage matched to WF candidates (inferred); not "
                        "proven caused damage or a bound."
                    )
                dont.append(line(text, note))
            elif kind == "idle-pet":
                text = (
                    f"Pet died at {number(detail.get('at_s'), 1, 's')}"
                    if detail["reason"] == "died"
                    else (
                        "Pet stopped dealing damage "
                        f"{number(detail.get('seconds'), 1, 's')}"
                        " before the kill"
                    )
                )
                dont.append(
                    line(text + ". Review pet control and the encounter's survival demands.")
                )
            elif kind == "long-auto-gaps":
                dont.append(
                    line(
                        "Review "
                        f"{detail['count']}"
                        " long Auto Shot gaps. Do not assume they are "
                        "clipping; this is an advisory signal."
                    )
                )
            elif kind == "padded-comparison":
                dont.append(
                    line(
                        "Do not compare displayed DPS without checking "
                        "targets: recorded cohort foreign-target median "
                        f"{number(detail['cohort_median_foreign_share_pct'], 1, '%')}"
                        " ("
                        f"{detail.get('level', 'unknown')}"
                        ")."
                    )
                )
        for item in plan["raid_asks"]:
            kind, detail = item["kind"], item["details"]
            if kind == "raid-speed":
                asks.append(
                    line(
                        (
                            "Review the raid's kill length: your "
                            f"{number(detail['your_kill_s'], 1, 's')}"
                            " versus "
                            f"{number(detail['reference_s'], 1, 's')}"
                            " ("
                            f"{detail['basis']}"
                            ", "
                            f"{number(detail['ratio'], 2, 'x')}"
                            "; "
                            f"{detail.get('level', 'unknown')}"
                            ")."
                        ),
                        "This comparison does not identify the cause or guarantee a DPS gain.",
                    )
                )
            elif kind == "already-faster-than-rank-one":
                asks.append(
                    line(
                        (
                            "Your kill ("
                            f"{number(detail['your_kill_s'], 1, 's')}"
                            ") is no longer than rank 1's ("
                            f"{number(detail['rank_one_kill_s'], 1, 's')}"
                            ")."
                        ),
                        "That comparison alone establishes no required raid-speed change.",
                    )
                )
            elif kind == "raid-utility":
                asks.append(
                    line(
                        "Review your assignment: "
                        f"{detail['friendly_crowd_control_casts']}"
                        " friendly crowd-control casts were recorded. "
                        "Coordinate duties before changing your shot plan."
                    )
                )
            elif kind == "padding-strategy":
                asks.append(
                    line(
                        (
                            "Discuss the target/side assignment and ranking "
                            "scope: foreign share "
                            f"{number(detail['your_foreign_share_pct'], 1, '%')}"
                            " versus cohort "
                            f"{number(detail['cohort_median_foreign_share_pct'], 1, '%')}"
                            " ("
                            f"{detail.get('level', 'unknown')}"
                            ")."
                        ),
                        (
                            "Extra-trash overlap is context, not a default recommendation to "
                            "pad damage."
                        ),
                    )
                )
        if encounter:
            links = (source(encounter.get("source"), "Encounter source"),)
            facts.append(
                line(
                    f"Creature type: {encounter.get('creature_type') or 'unknown'}.",
                    encounter.get("note") or "Static game knowledge; not observed in this log.",
                    (*links, source(encounter.get("type_source"), "Creature-type source")),
                )
            )
            for timing in encounter.get("timings") or []:
                facts.append(line(str(timing["text"]), timing.get("note") or "", links))
        scope_text = "in the acquired cohort" if live else "inside the recorded overall top five"
        context_text = f"{mix_text} {scope_text}. Primary {faction} comparator: {comparator}.{weak}"
    else:
        weave = "Unknown — structured playbook not recorded in this analysis"
        context_text = (
            f"{mix_text}"
            ". Comparator: "
            f"{comparator}"
            ". Rebuild from the archive to include the detailed "
            "playbook rules."
        )
        for label in ("Weapons", "Trinkets", "Pet", "Weaving"):
            loadout.append(
                {
                    "label": label,
                    "lines": (
                        line(
                            "Detailed decision unavailable in this older analysis; recorded "
                            "facts remain below."
                        ),
                    ),
                }
            )
        for label in ("Opener", "Rapid Fire", "Refocus"):
            execution.append(
                {
                    "label": label,
                    "lines": (
                        line(
                            "Detailed decision unavailable in this older analysis; recorded "
                            "facts remain below."
                        ),
                    ),
                }
            )
    return {
        "metrics": metrics,
        "leader_practice": leader_practice,
        "percent": percent,
        "comparator": comparator,
        "target": target,
        "mix": mix_text,
        "weave": weave,
        "context_text": context_text,
        "context": (
            ("Faction mix", mix_text),
            ("Current Auto / Aimed / Multi", shots),
            (
                f"{faction}-normalized target",
                target + (" · inferred comparison" if member == "inferred" else ""),
            ),
            ("Pet DPS", pet_context),
        ),
        "loadout": tuple(loadout),
        "execution": tuple(execution),
        "quick_plan": _quick_plan(plan, static, game, pet_facts),
        "dont": tuple(dont)
        or (
            line(
                "No additional warning was established by these rules. Review the "
                "evidence limits and encounter context."
            ),
        ),
        "asks": tuple(asks)
        or (
            line(
                "No additional raid ask was established by these rules; that does "
                "not prove assignments or positioning are optimal."
            ),
        ),
        "facts": tuple(facts),
        "gear": gear(subject),
        "cohort": rows,
        "cohort_complete": overall is not None,
        "cohort_title": "Acquired comparison cohort" if live else "Current overall top five",
        "gear_title": "Full 17-slot gear for each acquired Hunter"
        if live
        else "Full 17-slot gear for each top-five Hunter",
        "review_key": f"necropsy:boss:{sha}:{boss['encounter_id']}",
        "limits": tuple(plan.get("limitations") or ()) if plan else (),
    }


def _tally(raw: Mapping[str, Any]) -> str:
    rows = raw.get("counts") or []
    text = "; ".join(f"{r['key']} ({r['count']}/{raw['known']} known)" for r in rows[:3])
    return (text or "Unknown") + f" · {raw['unknown']} unknown"


def acquisition_view(document: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Show the recorded outcome of every requested boss, including unavailable fights."""
    raw = document.get("acquisition") or {}
    rows = []
    analysed = {b["encounter_id"] for b in document["bosses"]}
    for boss in raw.get("bosses") or []:
        coverage = boss.get("coverage") or {}
        status = (
            "Not attempted"
            if boss.get("attempted") is False
            else "Complete"
            if coverage.get("complete") is True
            else "Partial"
            if coverage.get("complete") is False
            else "Unknown"
        )
        rows.append(
            {
                "boss": str(boss.get("boss") or "Unknown boss"),
                "status": status,
                "anchor": f"boss-{boss['encounter_id']}"
                if boss.get("encounter_id") in analysed
                else None,
                "deep": f"{number(coverage.get('usable_deep'))}/{number(coverage.get('target'))}",
                "metadata": (
                    f"{number(coverage.get('metadata'))}/{number(coverage.get('metadata_target'))}"
                ),
                "reasons": tuple(str(r) for r in coverage.get("reasons") or []),
            }
        )
    return tuple(rows)


def overview_view(document: Mapping[str, Any]) -> dict[str, Any]:
    live = document.get("mode") == "live"
    acquisition = acquisition_view(document) if live else ()
    raw = document.get("overview")
    if not raw:
        return {
            "badges": ("Offline / self-contained",),
            "setup": tuple(
                {
                    "label": label,
                    "lines": (
                        line("Not recorded in this older analysis; rebuild from the archive."),
                    ),
                }
                for label in (
                    "Spec",
                    "World buff",
                    "Core ranged gear",
                    "Armor pattern",
                    "Pet",
                    "Ammo",
                    "Engineering",
                    "Renataki",
                    "Faction rule",
                )
            ),
            "corrections": (line("Faction corrections were not recorded in this older analysis."),),
            "sources": (),
            "pet_profiles": (),
            "pet_facts": {},
            "pet_family_sources": (),
            "acquisition": acquisition,
            "faction_label": "Faction-aware",
        }
    setup = raw["setup"]
    faction = setup["faction"] or "Unknown faction"
    weak = (
        " Comparison membership includes inferred factions."
        if raw["inferred_faction_entries"]
        else ""
    )
    badges = (
        f"{raw['recorded_entries']} "
        + ("acquired comparator rows" if live else "recorded top-five rows"),
        " / ".join(f"{r['count']} {r['key']}" for r in raw["by_faction"]),
        f"{raw['inferred_faction_entries']} inferred faction entries",
        "Faction-normalized shot targets",
        "Faction-aware weaving",
        "Detected WF events",
        "Offline / self-contained",
    )
    rows = []
    for label, key in (("Spec", "talents"), ("World buff", "darkmoon")):
        rows.append(
            {
                "label": label,
                "lines": (
                    line(
                        _tally(setup[key]),
                        "Recorded prevalence is a comparison, not an unconditional prescription."
                        + weak,
                    ),
                ),
            }
        )
    rows.append(
        {
            "label": "Core ranged gear",
            "lines": (
                line(_tally(setup["ranged_weapon"]), _tally(setup["ranged_enchant"]) + weak),
            ),
        }
    )
    rows.append(
        {
            "label": "Armor pattern",
            "lines": (
                line(
                    _tally(setup["armor_pattern"]),
                    "Hands: "
                    + _tally(setup["hands"])
                    + weak
                    + (
                        " Other set pieces: " + _tally(setup["set_extras"])
                        if setup.get("set_extras")
                        else ""
                    ),
                ),
            ),
        }
    )
    families = setup["pet_families"]
    profile = (
        "; ".join(
            f"{f['family']}: {f['observed']} observed / {f['inferred']} inferred"
            for f in families["families"]
        )
        or "No uniquely identified family"
    )
    rows.append(
        {
            "label": "Pet",
            "lines": (
                line(
                    profile,
                    (
                        f"{families['unknown_family']}"
                        " family unknown; "
                        f"{families['no_hunter_pet']}"
                        " no Hunter pet; "
                        f"{families['listing_missing']}"
                        " listing missing; "
                        f"{families['unclassified']}"
                        " unclassified; "
                        f"{families['multiple_hunter_pets']}"
                        " multiple pets."
                    )
                    + weak,
                ),
            ),
        }
    )
    ammo = setup["subject_ammo"]
    ammo_text = (
        "Advice unknown: " + str(ammo.get("reason"))
        if not ammo.get("recommended_name")
        else (
            f"{ammo['recommended_name']}"
            " for a "
            f"{ammo['ranged_type']}"
            " using "
            f"{ammo['uses_ammo']}"
            "s: +"
            f"{number(ammo['dps_bonus'], 1)}"
            " ammunition DPS."
        )
    )
    rows.append(
        {
            "label": "Ammo",
            "lines": (
                line(
                    ammo_text,
                    "General game advice. Ammunition actually used is not recorded in this export.",
                    (source(ammo.get("source"), "Ammunition source"),),
                ),
            ),
        }
    )
    rows.append(
        {
            "label": "Engineering",
            "lines": (
                line(
                    (
                        f"{setup['engineering_pet_users']}"
                        " recorded engineering-pet users; explosives: "
                        f"{_tally(setup['explosive_users'])}"
                        "."
                    ),
                    "Engineering guardians stay separate from your Hunter pet." + weak,
                ),
            ),
        }
    )
    renataki = "; ".join(
        f"{r['boss']}: {r['users']}/{r['known']} known" for r in setup["renataki_by_boss"]
    )
    rows.append(
        {
            "label": "Renataki",
            "lines": (
                line(
                    renataki,
                    "Choose boss-specific context; usage does not make it a universal requirement."
                    + weak,
                ),
            ),
        }
    )
    rows.append(
        {
            "label": "Faction rule",
            "lines": (
                line(
                    "Subject faction: "
                    f"{faction}"
                    " ("
                    f"{setup['faction_level']}"
                    "). Same-faction entries drive execution advice; "
                    "other-faction rows remain context."
                ),
            ),
        }
    )
    corrections = []
    for c in raw["corrections"]:
        weavers = (
            ", ".join(f"{name}: {count} Raptor" for name, count in c["same_faction_weavers"])
            or "none recorded"
        )
        racial = (
            f"; race {c['rank_one_race']} (racial-cast evidence)"
            if c["rank_one_race_proven"]
            else "; race unknown"
        )
        text = (
            f"{c['boss']}"
            ": rank 1 "
            f"{c['rank_one_player'] or 'unknown'}"
            " ("
            f"{c['rank_one_faction'] or 'faction unknown'}"
            f"{racial}"
            "; WF "
            f"{c['rank_one_windfury'] or 'unknown'}"
            "). Same-faction Raptor users: "
            f"{weavers}"
            "."
        )
        note = (
            "Boss weave verdict: same faction "
            f"{c['verdict_same_faction'] or 'unknown'}"
            "; all recorded entries "
            f"{c['verdict_all_entries'] or 'unknown'}"
            " (context)."
        )
        if c["pure_ranged_reference"]:
            name, dps = c["pure_ranged_reference"]
            note += f" Best-ranked zero-Raptor reference: {name}, {number(dps)} DPS."
        corrections.append(line(text, note + weak))
    game = document.get("game_data") or {}
    sources = tuple(
        source(
            str(game.get("url_template", "")).format(table=t, build=game.get("build", "")),
            f"{t} · build {game.get('build', 'unknown')}",
        )
        for t in game.get("tables") or ()
    )
    return {
        "badges": badges,
        "acquisition": acquisition,
        "faction_label": f"{faction}-normalized"
        + (" (inferred)" if setup["faction_level"] == "inferred" else ""),
        "setup": tuple(rows),
        "corrections": tuple(corrections),
        "sources": tuple(s for s in sources if s),
        "pet_profiles": _profile_lines(setup.get("pet_facts") or {}),
        "pet_facts": setup.get("pet_facts") or {},
        "pet_family_sources": tuple(
            s
            for url in ((setup.get("pet_facts") or {}).get("sources") or {}).get(
                "family_modifiers", ()
            )
            if (s := source(url, "Family modifier guide"))
        ),
    }
