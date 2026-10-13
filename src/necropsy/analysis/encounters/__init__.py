"""Encounter rules: what a boss fight changes about how damage and behaviour are read.

Class knowledge ("how a Hunter plays") and encounter knowledge ("Gothik counts
foreign trash", "Razuvious's Understudies are not ranked") are kept apart:
class plugins never branch on bosses, and encounter rules are data.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from necropsy.rules import load_rules


@dataclass(frozen=True, slots=True)
class EncounterRules:
    encounter_id: int
    name: str
    boss_game_ids: frozenset[int]
    ranking_excluded_game_ids: frozenset[int]
    native_game_ids: frozenset[int] | None
    exclusion_rule: str
    exclusion_basis: str = "none"
    """`empirical` when the exclusions were found from recorded rankings, not documented."""
    exclusion_validation: str | None = None

    def excluded_from_ranking(self, game_id: int | None, _name: str | None) -> bool:
        return game_id is not None and game_id in self.ranking_excluded_game_ids

    def is_native(self, game_id: int | None, _name: str | None) -> bool:
        if self.native_game_ids is None:
            raise ValueError(f"no native-target rule for {self.name}")
        return game_id is not None and game_id in self.native_game_ids


@cache
def _zone(game: str, zone: str) -> dict[int, EncounterRules]:
    data = load_rules(game, f"zones/{zone}")
    meta = data["ranking_exclusions_rule"]
    rule = str(meta["rule"])
    result: dict[int, EncounterRules] = {}
    for entry in data["encounters"]:
        native = entry.get("native_targets")
        result[int(entry["id"])] = EncounterRules(
            encounter_id=int(entry["id"]),
            name=str(entry["name"]),
            boss_game_ids=frozenset(int(g) for g in entry.get("boss_game_ids") or ()),
            ranking_excluded_game_ids=frozenset(
                int(e["game_id"]) for e in entry.get("ranking_exclusions") or ()
            ),
            native_game_ids=None
            if native is None
            else frozenset(int(e["game_id"]) for e in native),
            exclusion_rule=rule,
            exclusion_basis=str(meta["basis"]),
            exclusion_validation=str(meta["validated"]),
        )
    return result


def encounter_rules(game: str, zone: str, encounter_id: int) -> EncounterRules:
    """Rules for one encounter; an unlisted encounter gets no exclusions and no native rule."""
    known = _zone(game, zone)
    if encounter_id in known:
        return known[encounter_id]
    return EncounterRules(
        encounter_id, f"encounter {encounter_id}", frozenset(), frozenset(), None, "none"
    )
