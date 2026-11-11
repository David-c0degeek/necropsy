"""Versioned Vanilla encounter-All projections; no generated page is an API answer."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

TARGET_RULE = "target-equals-encounter-all-v1"
SOURCE_RULE = "source-owned-encounter-all-v1"
CRITICAL_RULE = "critical-hit-type-encounter-all-v1"
KNOWN_HIT_TYPES = frozenset({0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 14, 15, 16, 17})
CRITICAL_HIT_TYPES = frozenset({2, 5, 17})


class DerivationUnsupported(ValueError):
    """The input does not support this versioned rule; fetch the requested scope."""


def source_actor_ids(report: dict[str, Any], fight_id: int, actor_id: int) -> tuple[int, ...]:
    """Explicit, unambiguous transitive ownership, including unlisted catalog units."""
    master = report.get("masterData")
    if not isinstance(master, dict):
        raise DerivationUnsupported("no report actor catalog")
    actors = master.get("actors")
    if not isinstance(actors, list):
        raise DerivationUnsupported("no report actor catalog")
    owners: dict[int, int | None] = {}
    for actor in actors:
        if (
            not isinstance(actor, dict)
            or type(actor.get("id")) is not int
            or (actor["id"] <= 0 and not (actor["id"] == -1 and actor.get("petOwner") is None))
        ):
            raise DerivationUnsupported("invalid actor identity")
        ident, owner = actor["id"], actor.get("petOwner")
        if ident in owners or (owner is not None and (type(owner) is not int or owner <= 0)):
            raise DerivationUnsupported("duplicate actor or invalid owner")
        owners[ident] = owner
    raw_fights = report.get("fights")
    if not isinstance(raw_fights, list) or not all(isinstance(f, dict) for f in raw_fights):
        raise DerivationUnsupported("invalid fight catalog")
    fights = [f for f in raw_fights if f.get("id") == fight_id]
    if len(fights) != 1 or actor_id not in owners:
        raise DerivationUnsupported("no unique fight or actor")
    pets = fights[0].get("friendlyPets")
    if not isinstance(pets, list):
        raise DerivationUnsupported("fight ownership listing missing")
    listed: set[int] = set()
    for pet in pets:
        if not isinstance(pet, dict) or type(pet.get("id")) is not int:
            raise DerivationUnsupported("invalid fight unit")
        ident, owner = pet["id"], pet.get("petOwner")
        if ident not in owners or ident in listed:
            raise DerivationUnsupported("ambiguous fight unit")
        listed.add(ident)
        if owner is not None:
            if type(owner) is not int or owner not in owners or owners[ident] not in (None, owner):
                raise DerivationUnsupported("conflicting fight ownership")
            owners[ident] = owner
    owned = {actor_id}
    while True:
        before = len(owned)
        owned.update(ident for ident, owner in owners.items() if owner in owned)
        if len(owned) == before:
            break
    for ident in owned:
        seen: set[int] = set()
        node: int | None = ident
        while node is not None:
            if node in seen or node not in owners:
                raise DerivationUnsupported("cyclic or missing ownership identity")
            seen.add(node)
            node = owners[node]
    return tuple(sorted(owned))


def project_pages(
    pages: Iterable[dict[str, Any]],
    rule: str,
    *,
    actor_ids: tuple[int, ...] | None = None,
) -> list[dict[str, Any]]:
    """Retain order, multiplicity, page boundaries and the parent's complete cursor chain."""
    if rule not in {TARGET_RULE, SOURCE_RULE, CRITICAL_RULE}:
        raise DerivationUnsupported("unknown derivation rule")
    if rule == SOURCE_RULE:
        if (
            not actor_ids
            or tuple(sorted(set(actor_ids))) != actor_ids
            or any(type(i) is not int or i <= 0 for i in actor_ids)
        ):
            raise DerivationUnsupported("source projection requires canonical actor ids")
    elif actor_ids is not None:
        raise DerivationUnsupported("actor ids do not apply to this projection")
    ids = frozenset(actor_ids or ())
    output = []
    for page in pages:
        data = page["data"]
        if rule == CRITICAL_RULE and any(
            e.get("type") == "damage"
            and (type(e.get("hitType")) is not int or e["hitType"] not in KNOWN_HIT_TYPES)
            for e in data
        ):
            raise DerivationUnsupported("unknown damage hit type")
        filtered = [
            e
            for e in data
            if (
                rule == TARGET_RULE
                or (rule == SOURCE_RULE and (e.get("sourceID") in ids or e.get("targetID") in ids))
                or (
                    rule == CRITICAL_RULE
                    and e.get("type") == "damage"
                    and e.get("hitType") in CRITICAL_HIT_TYPES
                )
            )
        ]
        output.append({"data": filtered, "nextPageTimestamp": page["nextPageTimestamp"]})
    return output
