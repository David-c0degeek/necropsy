"""Classic Era Druid actions, healing, incoming damage and evidenced encounter duties."""

from __future__ import annotations

import json
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
from necropsy.analysis.generic import metrics
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


@dataclass(frozen=True, slots=True)
class DruidEvent:
    timestamp: int
    t_s: float
    kind: str
    source_id: int | None
    target_id: int | None
    ability_id: int | None
    name: str | None
    amount: int | None
    overheal: int | None
    uid: str
    copy: int
    raw: dict[str, Any]


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
    resources: tuple[dict[str, Any], ...]
    deaths: DeathsFinding
    threat: Evidenced[float]
    limitations: tuple[str, ...] = LIMITATIONS


def _ref(pf: ParticipantFight, rows: list[DruidEvent], detail: str) -> EvidenceRef:
    return EvidenceRef.events(
        pf.report_code,
        pf.fight_id,
        pf.actor_id,
        [(r.uid, r.copy) for r in rows],
        detail=detail,
    )


def _events(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> list[DruidEvent]:
    rows = con.execute(
        """SELECT e.timestamp, e.type, e.source_id, e.target_id, e.ability_game_id,
                  a.name, e.amount, e.overheal, e.event_uid, e.copy_index, e.raw
           FROM events e LEFT JOIN abilities a
             ON a.report_code = e.report_code AND a.game_id = e.ability_game_id
           WHERE e.report_code = ? AND e.fight_id = ?
             AND (e.source_id = ? OR e.target_id = ?)
             AND e.timestamp BETWEEN ? AND ?
           ORDER BY e.timestamp, e.event_uid, e.copy_index""",
        [pf.report_code, pf.fight_id, pf.actor_id, pf.actor_id, pf.start_time, pf.end_time],
    ).fetchall()
    return [
        DruidEvent(
            int(ts),
            pf.relative_s(int(ts)),
            kind,
            source,
            target,
            ability,
            name,
            amount,
            overheal,
            uid,
            int(copy),
            json.loads(raw) if isinstance(raw, str) else raw,
        )
        for ts, kind, source, target, ability, name, amount, overheal, uid, copy, raw in rows
    ]


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
    forms: dict[str, Evidenced[tuple[tuple[int, int], ...]]],
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
    repeated = {r: es for r, es in candidates.items() if len(es) >= minimum}
    refs = [_ref(pf, es, f"repeated {r.value} casts") for r, es in repeated.items()]
    if FightRole.TANK in repeated:
        refs.append(
            _ref(pf, tank_hits, "encounter enemy damage alongside repeated bear-only actions")
        )
    roles = tuple(sorted(repeated, key=lambda r: r.value))
    observed_roles: Evidenced[tuple[FightRole, ...]] = (
        inferred(roles, *refs, rule_id="druid-duty-signals-v1", params={"minimum_casts": minimum})
        if roles
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
            rule_id="druid-duty-signals-v1",
            params={"minimum_casts": minimum},
        )
    spans = tuple(
        {
            "role": r.value,
            "first_action_s": es[0].t_s,
            "last_action_s": es[-1].t_s,
            "casts_observed": len(es),
            "evidence": observed(tuple((e.uid, e.copy) for e in es), _ref(pf, es, r.value)),
        }
        for r, es in sorted(repeated.items(), key=lambda item: item[1][0].timestamp)
    )
    return observed_roles, resolved_role, spans


def _totals(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    events: list[DruidEvent],
) -> tuple[dict[str, Evidenced[float]], Evidenced[dict[int, int]], Evidenced[dict[int, int]]]:
    source = coverage(con, pf, pf.actor_id, Direction.SOURCE)
    target = coverage(con, pf, pf.actor_id, Direction.TARGET)
    heals = [e for e in events if e.kind == "heal" and e.source_id == pf.actor_id]
    damage = [e for e in events if e.kind == "damage" and e.source_id == pf.actor_id]
    incoming = [e for e in events if e.kind == "damage" and e.target_id == pf.actor_id]
    support = [e for e in events if e.kind == "heal" and e.target_id == pf.actor_id]
    seconds = pf.duration_ms / 1000
    values: dict[str, Evidenced[float]] = {}
    for name, rows, cov in (
        ("damage", damage, source),
        ("effective_healing", heals, source),
        ("incoming_damage", incoming, target),
        ("healing_received", support, target),
    ):
        ref = _ref(pf, rows, name)
        if any(e.amount is None for e in rows):
            values[name] = unknown(f"{name} has events without amount", ref)
        else:
            values[name] = complete_or_unknown(
                float(sum(e.amount or 0 for e in rows)),
                [cov],
                ref,
                note="sum of WCL event amount; effective amount excludes overheal",
            )
        total = values[name]
        values[f"{name}_per_second"] = (
            complete_or_unknown(total.value / seconds, [cov], *total.refs)
            if total.value is not None and seconds > 0
            else unknown(f"{name} rate unavailable")
        )
    ref = _ref(pf, heals, "overhealing")
    values["overhealing"] = (
        unknown("heal events omit overheal; missing is not zero", ref)
        if any(e.overheal is None for e in heals)
        else complete_or_unknown(
            float(sum(e.overheal or 0 for e in heals)),
            [source],
            ref,
        )
    )
    effective, over = values["effective_healing"].value, values["overhealing"].value
    values["overhealing_pct"] = (
        complete_or_unknown(100 * over / (effective + over), [source], ref)
        if effective is not None and over is not None and effective + over > 0
        else unknown("no known nonzero total healing denominator", ref)
    )
    for field in ("absorbed", "blocked", "resisted", "mitigated", "unmitigatedAmount"):
        ref = _ref(pf, incoming, f"incoming damage field {field}")
        readings = [e.raw.get(field) for e in incoming]
        values[f"incoming_{field}"] = (
            unknown(f"incoming events omit {field}; missing is not zero", ref)
            if any(type(v) not in (int, float) for v in readings)
            else complete_or_unknown(
                float(sum(v for v in readings if v is not None)), [target], ref
            )
        )

    def by_target(rows: list[DruidEvent], detail: str) -> Evidenced[dict[int, int]]:
        ref = _ref(pf, rows, detail)
        if any(e.target_id is None or e.amount is None for e in rows):
            return unknown("target or amount missing from event", ref)
        grouped: dict[int, int] = defaultdict(int)
        for event in rows:
            assert event.target_id is not None and event.amount is not None
            grouped[event.target_id] += event.amount
        return complete_or_unknown(dict(grouped), [source], ref)

    return values, by_target(heals, "healing by target"), by_target(damage, "damage by target")


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
        forms = _form_windows(con, pf, profile, rules)
        signals, role, spans = _duties(con, pf, events, forms, rules)
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
        resources = []
        for event in events:
            raw = event.raw
            side = raw.get("resourceActor")
            resource_actor = (
                event.source_id if side == 1 else event.target_id if side == 2 else None
            )
            if resource_actor != pf.actor_id:
                continue
            for resource in raw.get("classResources") or []:
                reading = (
                    observed(resource, _ref(pf, [event], "actor resource reading"))
                    if type(resource.get("max")) in (int, float) and resource["max"] > 0
                    else unknown(
                        "resource capacity is missing or zero; no usable resource reading",
                        _ref(pf, [event], "resource payload"),
                    )
                )
                resources.append(
                    {
                        "t_s": event.t_s,
                        "reading": resource,
                        "evidence": reading,
                        "event_uid": event.uid,
                        "copy": event.copy,
                    }
                )
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
            tuple(resources),
            metrics.deaths(con, pf, pf.actor_id),
            unknown("no verified threat measurement was acquired"),
        )


DRUID = register(DruidClassicEra())
