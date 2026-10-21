"""Raid modules shared by acquisition, offline analysis and application views."""

from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from necropsy.raids.aq40 import RAID as AQ40
from necropsy.raids.bwl import RAID as BWL
from necropsy.raids.mc import RAID as MC
from necropsy.raids.model import Raid
from necropsy.raids.naxxramas import RAID as NAXXRAMAS
from necropsy.rules import load_rules

RAIDS = (NAXXRAMAS, AQ40, BWL, MC)
DEFAULT_RAID = NAXXRAMAS

# Raids whose live captures may carry whole-encounter event scopes, and the Era
# partitions those scopes are defined for. Naxxramas captures made before it
# joined keep their actor-only contract: only a capture that carries the scopes
# gains encounter context.
ENCOUNTER_CONTEXT_ZONES = frozenset(r.zone_id for r in RAIDS)
ENCOUNTER_CONTEXT_PARTITIONS = frozenset({1, 2})


def raid_for_zone(zone_id: int) -> Raid:
    for raid in RAIDS:
        if type(zone_id) is int and raid.zone_id == zone_id:
            return raid
    raise ValueError(f"unsupported raid zone {zone_id!r}")


def raid_for_encounter(encounter_id: int) -> Raid:
    for raid in RAIDS:
        if any(int(e["id"]) == encounter_id for e in encounters(raid)):
            return raid
    raise ValueError(f"unsupported raid encounter {encounter_id!r}")


def encounters(raid: Raid) -> list[dict[str, Any]]:
    return list(load_rules("classic_era", f"zones/{raid.slug}")["encounters"])


def with_raid(url: str, zone_id: int) -> str:
    """Persist selection in the character URL, including checkpoints and resumes."""
    raid_for_zone(zone_id)
    parts = urlsplit(url.strip())
    query = parse_qs(parts.query, keep_blank_values=True)
    query["zone"] = [str(zone_id)]
    return urlunsplit(parts._replace(query=urlencode(query, doseq=True)))
