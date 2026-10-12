"""Distributions over a cohort: what the comparison group actually used.

Unknown values are counted separately and never treated as "not used"; every
distribution reports how many values were known.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Hashable, Iterable, Mapping
from dataclasses import dataclass

from necropsy.analysis.evidence import Evidenced
from necropsy.analysis.generic.environment import EnvironmentProfile, GearItem


@dataclass(frozen=True, slots=True)
class Distribution[K: Hashable]:
    counts: dict[K, int]
    n_known: int
    n_unknown: int

    @property
    def n_total(self) -> int:
        return self.n_known + self.n_unknown

    def share(self, key: K) -> float | None:
        """Share among known values, or None when nothing is known."""
        return self.counts.get(key, 0) / self.n_known if self.n_known else None

    def most_common(self) -> list[tuple[K, int]]:
        return sorted(self.counts.items(), key=lambda kv: (-kv[1], str(kv[0])))


def distribution[K: Hashable](values: Iterable[Evidenced[K]]) -> Distribution[K]:
    counts: Counter[K] = Counter()
    unknown_count = 0
    for v in values:
        if v.value is None:
            unknown_count += 1
        else:
            counts[v.value] += 1
    return Distribution(dict(counts), sum(counts.values()), unknown_count)


def _count_where[K: Hashable](
    profiles: Iterable[EnvironmentProfile],
    extract: Callable[[EnvironmentProfile], Iterable[K] | None],
) -> Distribution[K]:
    counts: Counter[K] = Counter()
    known = unknown_count = 0
    for profile in profiles:
        values = extract(profile)
        if values is None:
            unknown_count += 1
            continue
        known += 1
        counts.update(set(values))
    return Distribution(dict(counts), known, unknown_count)


def talent_distribution(profiles: Iterable[EnvironmentProfile]) -> Distribution[str]:
    return distribution(p.talents for p in profiles)


def _slot(profile: EnvironmentProfile, slot: int) -> GearItem | None:
    """The item record for a slot, or None when gear or that slot is not recorded."""
    if profile.gear.value is None:
        return None
    return next((g for g in profile.gear.value if g.slot == slot), None)


def _per_slot(
    profiles: Iterable[EnvironmentProfile], slot: int, field: Callable[[GearItem], int]
) -> Distribution[int]:
    counts: Counter[int] = Counter()
    unknown_count = 0
    for profile in profiles:
        item = _slot(profile, slot)
        if item is None:
            unknown_count += 1
        else:
            counts[field(item)] += 1
    return Distribution(dict(counts), sum(counts.values()), unknown_count)


def gear_slot_distribution(profiles: Iterable[EnvironmentProfile], slot: int) -> Distribution[int]:
    """Item ID worn in one gear slot (0 = recorded empty). Missing gear or slot is unknown."""
    return _per_slot(profiles, slot, lambda g: g.item_id)


def enchant_distribution(profiles: Iterable[EnvironmentProfile], slot: int) -> Distribution[int]:
    """Permanent enchant on one gear slot (0 = none). Missing gear or slot is unknown."""
    return _per_slot(profiles, slot, lambda g: g.permanent_enchant or 0)


def item_prevalence(profiles: Iterable[EnvironmentProfile]) -> Distribution[int]:
    """How many profiles with known gear wear each item ID in any slot (e.g. trinkets)."""
    return _count_where(
        profiles,
        lambda p: None if p.gear.value is None else [g.item_id for g in p.gear.value if g.item_id],
    )


def starting_aura_prevalence(
    profiles: Iterable[EnvironmentProfile], auras: Mapping[int, str]
) -> Distribution[str]:
    """How many profiles with a known starting-aura snapshot had each named aura at the pull.

    Used for consumables, world buffs and other pre-pull effects; `auras` maps
    spell IDs to the names to report (several IDs may share a name).
    """
    return _count_where(
        profiles,
        lambda p: (
            None
            if p.starting_auras.value is None
            else [auras[a.ability_id] for a in p.starting_auras.value if a.ability_id in auras]
        ),
    )


def world_buff_prevalence(profiles: Iterable[EnvironmentProfile]) -> Distribution[str]:
    return _count_where(profiles, lambda p: p.world_buffs.value)


def darkmoon_distribution(profiles: Iterable[EnvironmentProfile]) -> Distribution[str]:
    return distribution(p.darkmoon_faire for p in profiles)
