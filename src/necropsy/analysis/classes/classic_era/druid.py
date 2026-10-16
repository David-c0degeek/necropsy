"""Classic Era Druid actions, healing, incoming damage and evidenced encounter duties."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

import duckdb

from necropsy.analysis.classes import register
from necropsy.analysis.context import ParticipantFight, coverage
from necropsy.analysis.encounters import encounter_rules
from necropsy.analysis.evidence import (
    Evidenced,
    EvidenceRef,
    complete_or_unknown,
    inferred,
    observed,
    unknown,
)
from necropsy.analysis.generic import combat, metrics
from necropsy.analysis.generic.combat import CombatEvent as DruidEvent
from necropsy.analysis.generic.combat import event_ref as _ref
from necropsy.analysis.generic.combat import event_rows as _events
from necropsy.analysis.generic.combat import event_totals as _totals
from necropsy.analysis.generic.environment import EnvironmentProfile
from necropsy.analysis.generic.metrics import DeathsFinding
from necropsy.analysis.roles import DRUID_CATEGORIES, FightRole, RoleOverride
from necropsy.rules import load_rules
from necropsy.snapshot.model import Direction

LIMITATIONS = (
    "Encounter duties are inferred from repeated actions, not talents or WCL category.",
    "Healing throughput and overheal reflect assignments, damage taken and other healers; "
    "neither is a healing quality score.",
    "Incoming damage, healing support and deaths do not prove avoidability or causality.",
    "Tank category DPS is not survivability or threat. Threat and assigned duties are unknown.",
    "Action spans show recorded activity; they do not prove continuous assignment or form uptime.",
    "Movement, downtime causes and optimal rotations cannot be established "
    "from actor streams alone.",
)


@dataclass(frozen=True)
class DruidAnalysis:
    class_id: Evidenced[int]
    build: Evidenced[str]
    ranking_category: Evidenced[str]
    observed_roles: Evidenced[tuple[FightRole, ...]]
    role: Evidenced[FightRole]
    assignment: Evidenced[str]
    override: RoleOverride | None
    selected_role: FightRole
    metrics: dict[str, Evidenced[float]]
    casts: Evidenced[dict[str, int]]
    timeline: tuple[DruidEvent, ...]
    opener: tuple[DruidEvent, ...]
    cooldowns: tuple[DruidEvent, ...]
    forms: dict[str, Evidenced[tuple[tuple[int, int], ...]]]
    activity_spans: tuple[dict[str, Any], ...]
    healing_targets: Evidenced[dict[int, int]]
    healing_spells: Evidenced[dict[str, int]]
    damage_targets: Evidenced[dict[int, int]]
    defensive_uptime_s: dict[str, Evidenced[float]]
    actor_catalog: Evidenced[dict[int, dict[str, Any]]]
    resources: tuple[dict[str, Any], ...]
    deaths: DeathsFinding
    threat: Evidenced[float]
    limitations: tuple[str, ...] = LIMITATIONS


def _category(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> Evidenced[str]:
    rows = con.execute(
        """SELECT DISTINCT spec FROM benchmark_participants WHERE report_code = ?
           AND fight_id = ? AND player = ?""",
        [pf.report_code, pf.fight_id, pf.player],
    ).fetchall()
    values = {r[0] for r in rows}
    ref = EvidenceRef(pf.report_code, pf.fight_id, pf.actor_id, "benchmark_participants")
    if len(values) != 1 or next(iter(values), None) not in DRUID_CATEGORIES:
        return unknown("missing, conflicting or unsupported WCL Druid ranking category", ref)
    return observed(str(values.pop()), ref)


def _form_windows(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    profile: EnvironmentProfile,
    rules: dict[str, Any],
) -> dict[str, Evidenced[tuple[tuple[int, int], ...]]]:
    ids: dict[str, list[int]] = defaultdict(list)
    for ability, name in con.execute(
        "SELECT game_id, name FROM abilities WHERE report_code = ?", [pf.report_code]
    ).fetchall():
        if name in rules["forms"]:
            ids[rules["forms"][name]].append(int(ability))
    at_start = profile.starting_auras.value
    active = None if at_start is None else frozenset(a.ability_id for a in at_start)
    windows = {
        form: metrics.aura_intervals(con, pf, pf.actor_id, ids[form], active)
        if ids[form]
        else unknown(f"no verified ability ID for {form} form in report catalog")
        for form in ("cat", "bear", "moonkin")
    }
    for form, spells in (("bear", rules["tanking"]), ("cat", rules["feral"])):
        if windows[form].value != ():
            continue
        actions = con.execute(
            """SELECT count(*) FROM events e JOIN abilities a
               ON a.report_code = e.report_code AND a.game_id = e.ability_game_id
               WHERE e.report_code = ? AND e.fight_id = ? AND e.source_id = ?
                 AND e.type = 'cast' AND a.name IN (SELECT unnest(?::VARCHAR[]))""",
            [pf.report_code, pf.fight_id, pf.actor_id, spells],
        ).fetchone()
        if actions and actions[0]:
            windows[form] = unknown(
                "form-specific actions are present but no form aura interval is recorded",
                *windows[form].refs,
            )
    return windows


def _duties(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    events: list[DruidEvent],
    rules: dict[str, Any],
) -> tuple[Evidenced[tuple[FightRole, ...]], Evidenced[FightRole], tuple[dict[str, Any], ...]]:
    candidates: dict[FightRole, list[DruidEvent]] = defaultdict(list)
    mapping = {
        "feral": FightRole.FERAL,
        "balance": FightRole.BALANCE,
        "healing": FightRole.HEALER,
        "tanking": FightRole.TANK,
    }
    for event in events:
        if event.source_id == pf.actor_id and event.kind == "cast":
            for group, role in mapping.items():
                if event.name in rules[group]:
                    candidates[role].append(event)
    encounter = encounter_rules("classic_era", "naxxramas", pf.encounter_id)
    boss_ids = {
        int(actor)
        for actor, game_id in con.execute(
            "SELECT actor_id, game_id FROM actors WHERE report_code = ? AND type = 'NPC'",
            [pf.report_code],
        ).fetchall()
        if game_id is not None
        and (
            encounter.is_boss(int(game_id))
            or (encounter.native_game_ids is not None and encounter.is_native(int(game_id), None))
        )
    }
    tank_hits = [
        e
        for e in events
        if e.kind == "damage"
        and e.target_id == pf.actor_id
        and e.source_id in boss_ids
        and (e.name in rules["direct_tank_hits"] or e.raw.get("melee") is True)
    ]
    minimum = int(rules["minimum_role_actions"])
    # Repeated bear-only actions plus boss hits; form alone cannot establish duty.
    if len(tank_hits) < minimum:
        candidates.pop(FightRole.TANK, None)
    healing_minimum = encounter.healing_role_minimum_actions or minimum
    repeated = {
        r: es
        for r, es in candidates.items()
        if len(es) >= (healing_minimum if r is FightRole.HEALER else minimum)
    }
    refs = [_ref(pf, es, f"repeated {r.value} casts") for r, es in repeated.items()]
    if FightRole.TANK in repeated:
        refs.append(
            _ref(pf, tank_hits, "encounter enemy damage alongside repeated bear-only actions")
        )
    signals = tuple(sorted(repeated, key=lambda r: r.value))
    total_actions = sum(len(es) for es in candidates.values())
    minimum_share = float(rules["minimum_secondary_cast_share"])
    roles = tuple(
        r
        for r in signals
        if r is FightRole.TANK or len(repeated[r]) / total_actions >= minimum_share
    )
    params = {"minimum_casts": minimum, "minimum_secondary_cast_share": minimum_share}
    if encounter.healing_role_minimum_actions is not None:
        params["healing_minimum_casts"] = healing_minimum
    observed_roles: Evidenced[tuple[FightRole, ...]] = (
        inferred(signals, *refs, rule_id="druid-duty-signals-v3", params=params)
        if signals
        else unknown("insufficient repeated actions to distinguish encounter duties")
    )
    cov = [coverage(con, pf, pf.actor_id, d) for d in (Direction.SOURCE, Direction.TARGET)]
    if not roles or not all(c.trusted for c in cov):
        resolved_role: Evidenced[FightRole] = unknown(
            "fight role uncertain: missing duty signals or incomplete actor streams", *refs
        )
    else:
        resolved_role = inferred(
            roles[0] if len(roles) == 1 else FightRole.HYBRID,
            *refs,
            rule_id="druid-duty-signals-v3",
            params=params,
        )
    spans = tuple(
        {
            "role": r.value,
            "first_action_s": es[0].t_s,
            "last_action_s": es[-1].t_s,
            "casts_observed": len(es),
            "cast_share": len(es) / total_actions,
            "qualifies_as_duty": r in roles,
            "evidence": observed(tuple((e.uid, e.copy) for e in es), _ref(pf, es, r.value)),
        }
        for r, es in sorted(repeated.items(), key=lambda item: item[1][0].timestamp)
    )
    return observed_roles, resolved_role, spans


class DruidClassicEra:
    game = "classic_era"
    class_id = 2
    name = "Druid"

    def analyze(
        self,
        con: duckdb.DuckDBPyConnection,
        pf: ParticipantFight,
        profile: EnvironmentProfile,
        override: RoleOverride | None = None,
    ) -> DruidAnalysis:
        rules = load_rules(self.game, "druid")
        events = _events(con, pf)
        actor_catalog = combat.actor_catalog(con, pf, events)
        forms = _form_windows(con, pf, profile, rules)
        signals, role, spans = _duties(con, pf, events, rules)
        totals, heals, damage = _totals(con, pf, events)
        casts = [e for e in events if e.kind == "cast" and e.source_id == pf.actor_id]
        source_coverage = [coverage(con, pf, pf.actor_id, Direction.SOURCE)]
        for group in ("feral", "balance", "healing", "tanking"):
            actions = [e for e in casts if e.name in rules[group]]
            totals[f"{group}_casts_per_minute"] = complete_or_unknown(
                len(actions) * 60000 / pf.duration_ms,
                source_coverage,
                _ref(pf, actions, f"{group} cast cadence"),
            )
        heal_events = [e for e in events if e.kind == "heal" and e.source_id == pf.actor_id]
        spell_totals: dict[str, int] = defaultdict(int)
        for event in heal_events:
            spell_totals[event.name or f"ability {event.ability_id}"] += event.amount or 0
        healing_spells = (
            unknown("healing events have missing amounts", _ref(pf, heal_events, "healing spells"))
            if any(e.amount is None for e in heal_events)
            else complete_or_unknown(
                dict(spell_totals),
                source_coverage,
                _ref(pf, heal_events, "healing by spell"),
            )
        )
        at_start = profile.starting_auras.value
        active = None if at_start is None else frozenset(a.ability_id for a in at_start)
        defensive_uptime = {}
        for name in ("Barkskin", "Frenzied Regeneration", "Enrage"):
            ids = [
                int(r[0])
                for r in con.execute(
                    "SELECT game_id FROM abilities WHERE report_code = ? AND name = ?",
                    [pf.report_code, name],
                ).fetchall()
            ]
            defensive_uptime[name] = (
                metrics.aura_uptime(con, pf, pf.actor_id, ids, active)
                if ids
                else unknown(f"no verified {name} ability in report catalog")
            )
        resources = combat.resource_readings(pf, events)
        ref = EvidenceRef(pf.report_code, None, pf.actor_id, "actors", detail="subType Druid")
        return DruidAnalysis(
            observed(2, ref),
            profile.talents,
            _category(con, pf),
            signals,
            role,
            unknown("encounter assignment was not supplied by the raid"),
            override,
            override.role if override else role.value or FightRole.UNCERTAIN,
            totals,
            complete_or_unknown(
                dict(sorted(Counter(e.name or f"ability {e.ability_id}" for e in casts).items())),
                [coverage(con, pf, pf.actor_id, Direction.SOURCE)],
                _ref(pf, casts, "cast counts"),
            ),
            tuple(events),
            tuple(e for e in casts if e.t_s <= 10),
            tuple(e for e in casts if e.name in rules["cooldowns"]),
            forms,
            spans,
            heals,
            healing_spells,
            damage,
            defensive_uptime,
            actor_catalog,
            tuple(resources),
            metrics.deaths(con, pf, pf.actor_id),
            unknown("no verified threat measurement was acquired"),
        )


DRUID = register(DruidClassicEra())
