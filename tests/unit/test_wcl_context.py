"""Character context: graded fields, faction only from canonical names, explicit partitions."""

from __future__ import annotations

import json
import random
from typing import Any

import httpx
import pytest

from necropsy.analysis.evidence import Faction
from necropsy.wcl import client as c
from necropsy.wcl.context import SUPPORTED_ZONE_ID, faction_field, rankings_query, resolve
from necropsy.wcl.sites import VANILLA
from necropsy.wcl.urls import parse_character_url
from tests.wcl_fakes import FakeClock, Script, ok

URL = "https://vanilla.warcraftlogs.com/character/id/86583560"


def _character(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 86583560,
        "canonicalID": 86583560,
        "name": "Haplina",
        "classID": 3,
        "level": 60,
        "hidden": False,
        "faction": {"id": 1, "name": "Alliance"},
        "server": {
            "id": 1,
            "name": "Ashbringer",
            "slug": "ashbringer",
            "region": {"id": 2, "name": "Europe", "slug": "EU"},
        },
    }
    base.update(over)
    return base


ZONE = {
    "id": SUPPORTED_ZONE_ID,
    "name": "Naxxramas",
    "partitions": [
        {"id": 1, "name": "Phase 6", "compactName": "P6", "default": True},
        {"id": 2, "name": "Season of Mastery", "compactName": "SoM", "default": False},
    ],
}


def _rankings(kills: int) -> str:
    return json.dumps({"rankings": [{"encounter": {"id": 1}, "totalKills": kills}]})


def _first(character: dict[str, Any] | None) -> httpx.Response:
    return ok({"characterData": {"character": character}, "worldData": {"zone": ZONE}})


def _second(p1: Any, p2: Any) -> httpx.Response:
    return ok({"characterData": {"character": {"p1": p1, "p2": p2}}})


def _resolve(script: Script, **kw: Any) -> Any:
    client = c.WclClient(
        VANILLA, lambda e: "t", transport=script.transport, clock=FakeClock(), rng=random.Random(0)
    )
    return resolve(client, parse_character_url(kw.pop("url", URL)), **kw)


def test_single_partition_with_rankings_is_chosen() -> None:
    script = Script(_first(_character()), _second(_rankings(12), _rankings(0)))
    context = _resolve(script)
    assert context.faction.value is Faction.ALLIANCE and context.faction.level == "observed"
    assert context.faction.source == "wcl-character-faction-name"
    assert context.partition is not None and context.partition.id == 1
    assert context.same_faction_ready and context.ambiguity is None
    assert (context.name.value, context.server.value, context.region.value) == (
        "Haplina",
        "Ashbringer",
        "EU",
    )
    first = script.bodies()[0]
    assert first["variables"] == {"zone": SUPPORTED_ZONE_ID, "id": 86583560}


def test_several_partitions_with_rankings_need_a_choice() -> None:
    script = Script(_first(_character()), _second(_rankings(3), _rankings(5)))
    context = _resolve(script)
    assert context.partition is None and "choose a partition" in (context.ambiguity or "")
    assert not context.same_faction_ready


def test_unreadable_rankings_are_not_guessed() -> None:
    script = Script(_first(_character()), _second(_rankings(3), json.dumps({"weird": 1})))
    context = _resolve(script)
    assert context.partition is None and context.ambiguity


def test_an_explicit_partition_skips_the_rankings_query() -> None:
    script = Script(_first(_character()))
    context = _resolve(script, partition=2)
    assert context.partition is not None and context.partition.id == 2
    assert len(script.requests) == 1
    bad = _resolve(Script(_first(_character())), partition=9)
    assert bad.partition is None and "not one of" in (bad.ambiguity or "")


@pytest.mark.parametrize(
    "raw",
    [{"id": 1}, {"id": 1, "name": "Allianz"}, {"id": 2, "name": "horde"}, None, {}],
)
def test_faction_is_unknown_unless_a_canonical_name_is_returned(raw: Any) -> None:
    found = faction_field(raw)
    assert found.level == "unknown" and found.value is None and found.note


def test_unknown_faction_blocks_same_faction_work_and_keeps_the_raw_value() -> None:
    script = Script(_first(_character(faction={"id": 1})), _second(_rankings(4), _rankings(0)))
    context = _resolve(script)
    assert context.faction.level == "unknown"
    assert context.raw_faction == {"id": 1}
    assert not context.same_faction_ready


def test_missing_character_is_not_found() -> None:
    with pytest.raises(c.NotFound):
        _resolve(Script(_first(None)))


def test_named_url_sends_name_server_and_region_and_reports_canonical_id() -> None:
    script = Script(
        _first(_character(id=5, canonicalID=86583560)), _second(_rankings(1), _rankings(0))
    )
    context = _resolve(
        script, url="https://vanilla.warcraftlogs.com/character/eu/ashbringer/Haplina"
    )
    assert script.bodies()[0]["variables"] == {
        "zone": SUPPORTED_ZONE_ID,
        "name": "Haplina",
        "server": "ashbringer",
        "region": "eu",
    }
    assert any("canonical character id is 86583560" in n for n in context.notes)


def test_hidden_character_is_noted() -> None:
    script = Script(_first(_character(hidden=True)), _second(_rankings(1), _rankings(0)))
    assert any("hidden" in n for n in _resolve(script).notes)


def test_rankings_query_only_contains_integer_partitions() -> None:
    text = rankings_query([1, 2])
    assert "p1: zoneRankings(zoneID: $zone, partition: 1)" in text and "rateLimitData" in text
