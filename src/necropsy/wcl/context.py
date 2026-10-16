"""Resolve a character URL into the context an acquisition needs.

Every field carries how it is known. Faction is OBSERVED only when WCL returns
a recognised canonical faction name; an ID alone, a localized name or a missing
value stays UNKNOWN with the raw API object kept, and an UNKNOWN faction blocks
same-faction acquisition. The zone is the supported zone from rule data; the
partition comes from the zone's own list, and when several partitions hold
rankings and none was chosen the result is an ambiguity for the user to settle.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from necropsy.analysis.evidence import Faction
from necropsy.wcl.client import RATE_FIELDS, Endpoint, InvalidResponse, NotFound, WclClient
from necropsy.wcl.urls import CharacterRef

SUPPORTED_ZONE_ID = 2006
"""Naxxramas: the only zone with encounter rules so far."""

_FACTION_NAMES = {"Alliance": Faction.ALLIANCE, "Horde": Faction.HORDE}

_CHARACTER_FIELDS = """
      id canonicalID name classID level hidden
      faction { id name }
      server { id name slug region { id name slug } }
"""

CHARACTER_QUERY = f"""
query NecropsyCharacter($id: Int, $name: String, $server: String, $region: String, $zone: Int!) {{
  characterData {{
    character(id: $id, name: $name, serverSlug: $server, serverRegion: $region) {{
{_CHARACTER_FIELDS}
    }}
  }}
  worldData {{ zone(id: $zone) {{ id name partitions {{ id name compactName default }} }} }}
  {RATE_FIELDS}
}}
"""


def rankings_query(partitions: list[int]) -> str:
    """One query asking for the character's zone rankings in each partition."""
    aliases = "\n".join(
        f"      p{int(p)}: zoneRankings(zoneID: $zone, partition: {int(p)})" for p in partitions
    )
    return f"""
query NecropsyRankings($id: Int!, $zone: Int!) {{
  characterData {{
    character(id: $id) {{
{aliases}
    }}
  }}
  {RATE_FIELDS}
}}
"""


@dataclass(frozen=True, slots=True)
class Field:
    value: Any
    level: str
    """`observed` or `unknown`."""
    source: str
    note: str | None = None


@dataclass(frozen=True, slots=True)
class Partition:
    id: int
    name: str
    default: bool
    has_rankings: bool | None
    """None when the rankings could not be read for this partition."""


@dataclass(frozen=True)
class CharacterContext:
    character_id: Field
    canonical_id: Field
    name: Field
    server: Field
    region: Field
    class_id: Field
    faction: Field
    raw_faction: Any
    zone_id: int
    zone_name: Field
    partitions: tuple[Partition, ...]
    partition: Partition | None
    """The chosen partition, or None when the choice is ambiguous or impossible."""
    ambiguity: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    ranking_category: str | None = None
    """Explicit WCL selection category; neither talents nor observed fight duty."""
    ranking_metric: str | None = None
    talent_tree: str | None = None
    """User-declared tree preference; never observed talents or an API filter."""

    @property
    def same_faction_ready(self) -> bool:
        return self.faction.level == "observed" and self.partition is not None


def _observed(value: Any, source: str) -> Field:
    if value is None or value == "":
        return Field(None, "unknown", source, "not returned by WCL")
    return Field(value, "observed", source)


def faction_field(raw: Any) -> Field:
    """OBSERVED only from a recognised canonical name; never from an ID alone."""
    name = raw.get("name") if isinstance(raw, dict) else None
    if isinstance(name, str) and name in _FACTION_NAMES:
        return Field(_FACTION_NAMES[name], "observed", "wcl-character-faction-name")
    reason = (
        "WCL returned no faction"
        if not raw
        else f"unrecognised faction {raw!r}; kept for later reconciliation"
    )
    return Field(None, "unknown", "wcl-character-faction-name", reason)


def _decode_json_scalar(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            raise InvalidResponse("zoneRankings is not valid JSON") from None
    return value


def _has_rankings(value: Any) -> bool | None:
    data = _decode_json_scalar(value)
    if data is None:
        return False
    if not isinstance(data, dict):
        return None
    rankings = data.get("rankings")
    if rankings is None:
        return None
    if not isinstance(rankings, list):
        return None
    return any(isinstance(r, dict) and (r.get("totalKills") or 0) > 0 for r in rankings)


def resolve(
    client: WclClient,
    ref: CharacterRef,
    *,
    partition: int | None = None,
    endpoint: Endpoint = "client",
) -> CharacterContext:
    variables: dict[str, Any] = {"zone": SUPPORTED_ZONE_ID}
    if ref.character_id is not None:
        variables["id"] = ref.character_id
    else:
        variables.update(name=ref.name, server=ref.realm, region=ref.region)
    result = client.query(CHARACTER_QUERY, variables, endpoint=endpoint)
    character = (result.data.get("characterData") or {}).get("character")
    if character is None:
        raise NotFound("WCL has no such character (or it is hidden)", result.rate)
    if not isinstance(character, dict):
        raise InvalidResponse("character is not an object", result.rate)
    zone = (result.data.get("worldData") or {}).get("zone")
    if not isinstance(zone, dict):
        raise InvalidResponse("the supported zone is missing from WCL's answer", result.rate)
    notes: list[str] = []
    if character.get("hidden"):
        notes.append("WCL marks this character as hidden; rankings may be unavailable")
    raw_partitions = zone.get("partitions") or []
    if not isinstance(raw_partitions, list):
        raise InvalidResponse("zone partitions is not a list", result.rate)
    cid = character.get("id")
    if not isinstance(cid, int) or cid <= 0:
        raise InvalidResponse("character id missing", result.rate)
    listed = [
        (int(p["id"]), str(p.get("name") or p["id"]), bool(p.get("default")))
        for p in raw_partitions
        if isinstance(p, dict) and isinstance(p.get("id"), int)
    ]
    presence: dict[int, bool | None] = {}
    if listed and partition is None:
        ranks = client.query(
            rankings_query([p for p, _, _ in listed]),
            {"id": cid, "zone": SUPPORTED_ZONE_ID},
            endpoint=endpoint,
        )
        holder = (ranks.data.get("characterData") or {}).get("character") or {}
        for pid, _, _ in listed:
            presence[pid] = _has_rankings(holder.get(f"p{pid}"))
    partitions = tuple(
        Partition(pid, name, default, presence.get(pid)) for pid, name, default in listed
    )
    chosen: Partition | None = None
    ambiguity: str | None = None
    if partition is not None:
        chosen = next((p for p in partitions if p.id == partition), None)
        if chosen is None:
            ambiguity = f"partition {partition} is not one of this zone's partitions"
    else:
        with_data = [p for p in partitions if p.has_rankings]
        unknown = [p for p in partitions if p.has_rankings is None]
        if len(with_data) == 1 and not unknown:
            chosen = with_data[0]
        elif not partitions:
            ambiguity = "WCL listed no partitions for this zone"
        else:
            names = ", ".join(f"{p.id} ({p.name})" for p in (with_data or partitions))
            ambiguity = f"choose a partition with --partition: {names}"
    raw_server = character.get("server")
    server: dict[str, Any] = raw_server if isinstance(raw_server, dict) else {}
    raw_region = server.get("region")
    region: dict[str, Any] = raw_region if isinstance(raw_region, dict) else {}
    canonical = character.get("canonicalID")
    if isinstance(canonical, int) and canonical != cid:
        notes.append(f"WCL's canonical character id is {canonical}")
    return CharacterContext(
        character_id=_observed(cid, "wcl-character-id"),
        canonical_id=_observed(canonical, "wcl-character-canonical-id"),
        name=_observed(character.get("name"), "wcl-character-name"),
        server=_observed(server.get("name"), "wcl-character-server"),
        region=_observed(region.get("slug"), "wcl-character-region"),
        class_id=_observed(character.get("classID"), "wcl-character-class"),
        faction=faction_field(character.get("faction")),
        raw_faction=character.get("faction"),
        zone_id=SUPPORTED_ZONE_ID,
        zone_name=_observed(zone.get("name"), "wcl-zone-name"),
        partitions=partitions,
        partition=chosen,
        ambiguity=ambiguity,
        notes=tuple(notes),
    )


def describe(context: CharacterContext) -> Mapping[str, Any]:
    """A plain summary for CLI output (no secrets involved)."""
    return {
        "character": context.name.value,
        "id": context.character_id.value,
        "server": context.server.value,
        "region": context.region.value,
        "faction": context.faction.value.value if context.faction.value else "unknown",
        "zone": context.zone_name.value,
        "partition": None if context.partition is None else context.partition.name,
    }


__all__ = [
    "CHARACTER_QUERY",
    "SUPPORTED_ZONE_ID",
    "CharacterContext",
    "Field",
    "Partition",
    "describe",
    "faction_field",
    "rankings_query",
    "resolve",
]
