"""Class-specific action sets over shared combat evidence for Classic Era."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import duckdb

from necropsy.analysis.class_catalog import CATEGORIES, CLASS_NAMES
from necropsy.analysis.classes import register
from necropsy.analysis.context import ParticipantFight, coverage, owned_pets, pet_listing_known
from necropsy.analysis.encounters import duty, encounter_rules
from necropsy.analysis.evidence import Evidenced, EvidenceRef, inferred, observed, unknown
from necropsy.analysis.generic import combat, metrics
from necropsy.analysis.generic.environment import EnvironmentProfile
from necropsy.analysis.generic.metrics import DeathsFinding
from necropsy.raids import raid_for_encounter
from necropsy.rules import load_rules
from necropsy.snapshot.model import Direction

LIMITATIONS = (
    "Ranking categories group builds; talents and category alone do not prove encounter duty.",
    "Repeated actions and direct encounter hits infer duties, not assigned responsibilities.",
    "HPS depends on assignments and raid damage; tank DPS is not survival or threat quality.",
    "Ability counts and timing describe recorded fights; they do not prove an optimal rotation.",
    "Incomplete actor or pet coverage remains unknown; missing evidence is not zero.",
)


@dataclass(frozen=True)
class CombatAnalysis:
    class_id: Evidenced[int]
    build: Evidenced[str]
    ranking_category: Evidenced[str]
    observed_roles: Evidenced[tuple[str, ...]]
    role: Evidenced[str]
    assignment: Evidenced[str]
    selected_role: str
    metrics: dict[str, Evidenced[float]]
    casts: Evidenced[dict[str, int]]
    timeline: tuple[combat.CombatEvent, ...]
    opener: tuple[combat.CombatEvent, ...]
    cooldowns: tuple[combat.CombatEvent, ...]
    healing_targets: Evidenced[dict[int, int]]
    healing_spells: Evidenced[dict[str, int]]
    damage_targets: Evidenced[dict[int, int]]
    actor_catalog: Evidenced[dict[int, dict[str, Any]]]
    resources: tuple[dict[str, Any], ...]
    deaths: DeathsFinding
    threat: Evidenced[float]
    core_abilities: tuple[str, ...]
    pets: tuple[dict[str, Any], ...]
    pets_known: bool
    override: None = None
    forms: dict[str, Any] = field(default_factory=dict)
    activity_spans: tuple[dict[str, Any], ...] = ()
    defensive_uptime_s: dict[str, Any] = field(default_factory=dict)
    limitations: tuple[str, ...] = LIMITATIONS


def _duty(
    con: duckdb.DuckDBPyConnection,
    pf: ParticipantFight,
    events: list[combat.CombatEvent],
    actions: dict[str, Any],
) -> tuple[Evidenced[tuple[str, ...]], Evidenced[str]]:
    casts = [e for e in events if e.kind == "cast" and e.source_id == pf.actor_id]
    ambiguous = set(actions["damage"]) & set(actions["healing"])

    def matches(event: combat.CombatEvent, role: str, group: str) -> bool:
        if event.name not in actions[group]:
            return False
        if event.name not in ambiguous:
            return True
        kind = "heal" if role == "healer" else "damage"
        return any(
            effect.kind == kind
            and effect.source_id == pf.actor_id
            and effect.name == event.name
            and effect.target_id == event.target_id
            and abs(effect.timestamp - event.timestamp) <= 1000
            for effect in events
        )

    groups = {
        role: [e for e in casts if matches(e, role, key)]
        for role, key in (("dps", "damage"), ("healer", "healing"), ("tank", "tanking"))
    }
    rules = encounter_rules(
        "classic_era", raid_for_encounter(pf.encounter_id).slug, pf.encounter_id
    )
    bosses = {
        int(a)
        for a, game_id in con.execute(
            "SELECT actor_id, game_id FROM actors WHERE report_code=? AND type='NPC'",
            [pf.report_code],
        ).fetchall()
        if game_id is not None
        and (
            rules.is_boss(int(game_id))
            or (rules.native_game_ids is not None and rules.is_native(int(game_id), None))
        )
    }
    hits = [
        e
        for e in events
        if e.kind == "damage"
        and e.target_id == pf.actor_id
        and e.source_id in bosses
        and (e.name in ("Melee", "Hateful Strike") or e.raw.get("melee") is True)
    ]
    if len(hits) < 3:
        groups["tank"] = []
    total = sum(len(groups[r]) for r in ("dps", "healer"))
    roles = tuple(
        r
        for r, es in groups.items()
        if len(es) >= 3 and (r == "tank" or not total or len(es) / total >= 0.2)
    )
    if "tank" in roles:
        roles = tuple(r for r in roles if r != "dps")
    refs = [combat.event_ref(pf, groups[r], f"repeated {r} actions") for r in roles]
    if "tank" in roles:
        refs.append(combat.event_ref(pf, hits, "direct encounter hits with tank actions"))
    params = {"minimum_actions": 3, "minimum_secondary_share": 0.2}
    signals = (
        inferred(roles, *refs, rule_id="class-duty-actions-v1", params=params)
        if roles
        else unknown("insufficient repeated actions to distinguish duty")
    )
    complete = all(
        coverage(con, pf, pf.actor_id, d).trusted for d in (Direction.SOURCE, Direction.TARGET)
    )
    role = (
        inferred(
            roles[0] if len(roles) == 1 else "hybrid",
            *refs,
            rule_id="class-duty-actions-v1",
            params=params,
        )
        if complete and roles
        else unknown("missing duty signals or incomplete actor streams")
    )
    role = duty.guard_action_duty(con, pf, events, role, tank_actions="tank" in roles)
    return signals, role


class ClassicEraCombat:
    game = "classic_era"

    def __init__(self, class_id: int) -> None:
        self.class_id = class_id
        self.name = CLASS_NAMES[class_id]

    def analyze(
        self,
        con: duckdb.DuckDBPyConnection,
        pf: ParticipantFight,
        profile: EnvironmentProfile,
    ) -> CombatAnalysis:
        actions = load_rules(self.game, "classes")[self.name]
        events = combat.event_rows(con, pf)
        totals, heals, damage = combat.event_totals(con, pf, events)
        signals, role = _duty(con, pf, events, actions)
        categories = {
            r[0]
            for r in con.execute(
                "SELECT DISTINCT spec FROM benchmark_participants WHERE report_code=? "
                "AND fight_id=? AND player=?",
                [pf.report_code, pf.fight_id, pf.player],
            ).fetchall()
        }
        ref = EvidenceRef(pf.report_code, pf.fight_id, pf.actor_id, "benchmark_participants")
        category = (
            observed(str(next(iter(categories))), ref)
            if len(categories) == 1 and next(iter(categories)) in CATEGORIES[self.class_id]
            else unknown("missing, conflicting or unsupported ranking category", ref)
        )
        casts = [e for e in events if e.kind == "cast" and e.source_id == pf.actor_id]
        pets = []
        for pet in owned_pets(con, pf):
            pet_pf = replace(pf, actor_id=pet.actor_id)
            pet_totals, _, _ = combat.event_totals(con, pet_pf, combat.event_rows(con, pet_pf))
            pets.append(
                {
                    "actor_id": pet.actor_id,
                    "name": pet.name,
                    "damage": pet_totals["damage"],
                    "dps": pet_totals["damage_per_second"],
                    "casts": metrics.ability_counts(con, pet_pf),
                    "deaths": metrics.deaths(con, pf, pet.actor_id),
                }
            )
        healing_spells: dict[str, int] = {}
        heal_events = [e for e in events if e.kind == "heal" and e.source_id == pf.actor_id]
        for event in heal_events:
            name = event.name or f"Ability {event.ability_id} (name unknown)"
            healing_spells[name] = healing_spells.get(name, 0) + (event.amount or 0)
        # Preserve whole-stream unknowns and missing amounts, including empty streams.
        from necropsy.analysis.evidence import complete_or_unknown

        spells = (
            unknown("healing events omit amounts", ref)
            if any(e.amount is None for e in heal_events)
            else complete_or_unknown(
                healing_spells,
                [coverage(con, pf, pf.actor_id, Direction.SOURCE)],
                combat.event_ref(pf, heal_events, "healing by spell"),
            )
        )
        return CombatAnalysis(
            observed(self.class_id, EvidenceRef(pf.report_code, None, pf.actor_id, "actors")),
            profile.talents,
            category,
            signals,
            role,
            unknown("raid assignment was not supplied"),
            role.value or "uncertain",
            totals,
            metrics.ability_counts(con, pf),
            tuple(events),
            tuple(e for e in casts if e.t_s <= 10),
            tuple(e for e in casts if e.name in actions["cooldowns"]),
            heals,
            spells,
            damage,
            combat.actor_catalog(con, pf, events),
            combat.resource_readings(pf, events),
            metrics.deaths(con, pf, pf.actor_id),
            unknown("no verified threat measurement acquired"),
            tuple(actions["damage"] + actions["healing"] + actions["tanking"]),
            tuple(pets),
            pet_listing_known(con, pf),
        )


PLUGINS = tuple(register(ClassicEraCombat(cid)) for cid in CATEGORIES)
