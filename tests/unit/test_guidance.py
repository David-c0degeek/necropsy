"""Execution guidance: conditions decide, unknown stays conditional, false is inapplicable."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from necropsy.analysis import guidance
from necropsy.analysis.encounters import encounter_rules
from necropsy.analysis.evidence import EvidenceLevel, EvidenceRef, derived, unknown

CRYPTSTALKER = [22436, 22437]
RENATAKI, SLAYERS_CREST, SWARMGUARD = 19953, 23041, 21670
REF = EvidenceRef("R", 1, 1, "x")


def _entry(kill_ms: float | None, gear: list[int] | None, non_boss: float | None = None) -> Any:
    rows = None
    ranked: Any = unknown("x")
    if non_boss is not None:
        ranked = derived(100.0, REF)
        rows = (
            SimpleNamespace(
                category="counted", kind="NPC", game_id=15928, name="b", damage=100 - non_boss
            ),
            SimpleNamespace(
                category="counted", kind="NPC", game_id=15929, name="a", damage=non_boss
            ),
        )
    return SimpleNamespace(
        profile=SimpleNamespace(
            kill_duration_ms=unknown("x") if kill_ms is None else derived(kill_ms, REF),
            gear=SimpleNamespace(
                value=None if gear is None else [SimpleNamespace(item_id=i) for i in gear]
            ),
            faction=SimpleNamespace(level=EvidenceLevel.OBSERVED),
        ),
        ranking=SimpleNamespace(ranked=ranked, by_target=SimpleNamespace(value=rows)),
    )


def _boss(encounter_id: int) -> Any:
    rules = encounter_rules("classic_era", "naxxramas", encounter_id)
    return SimpleNamespace(encounter_id=encounter_id, rules=rules)


def _items(g: guidance.Guidance) -> dict[str, guidance.GuidanceItem]:
    return {i.key: i for i in g.items}


def test_one_rapid_fire_follows_kill_time_and_set_bonus() -> None:
    short = guidance.build("naxxramas", _boss(51118), _entry(84_000, CRYPTSTALKER), (), False)
    assert short.rapid_fire.duration_s == 19.0
    assert _items(short)["one-rapid-fire"].status == "applies"
    long = guidance.build("naxxramas", _boss(51118), _entry(307_000, []), (), False)
    assert _items(long)["one-rapid-fire"].status == "otherwise"
    no_gear = guidance.build("naxxramas", _boss(51118), _entry(84_000, None), (), False)
    item = _items(no_gear)["one-rapid-fire"]
    assert item.status == "conditional" and item.condition is not None
    assert item.condition.level == "unknown"


@pytest.mark.parametrize(
    ("trinkets", "status"),
    [
        ([RENATAKI, SLAYERS_CREST], "applies"),
        ([RENATAKI, SWARMGUARD], "inapplicable"),
        ([SLAYERS_CREST], "inapplicable"),
        (None, "conditional"),
    ],
)
def test_refocus_lockout_needs_a_shared_category(trinkets: list[int] | None, status: str) -> None:
    g = guidance.build("naxxramas", _boss(51118), _entry(84_000, trinkets), (), False)
    assert _items(g)["refocus-trinket-lockout"].status == status


def test_ranked_share_condition_needs_three_known_entries_and_keeps_inferred() -> None:
    boss = _boss(51120)  # Thaddius
    few = (_entry(1, [], 20.0), _entry(1, [], None), _entry(1, [], 30.0))
    g = guidance.build("naxxramas", boss, _entry(1, []), few, False)
    assert _items(g)["rapid-fire-phase"].status == "conditional"
    adds = tuple(_entry(1, [], v) for v in (20.0, 10.0, 30.0))
    g = guidance.build("naxxramas", boss, _entry(1, []), adds, True)
    item = _items(g)["rapid-fire-phase"]
    assert item.status == "applies" and item.condition is not None
    assert item.condition.level == "inferred"
    boss_only = tuple(_entry(1, [], v) for v in (0.0, 1.0, 0.0))
    g = guidance.build("naxxramas", boss, _entry(1, []), boss_only, False)
    assert _items(g)["rapid-fire-phase"].status == "otherwise"


def test_every_item_is_general_advice_with_its_basis() -> None:
    for encounter in (51118, 51120, 51119, 51108):
        g = guidance.build("naxxramas", _boss(encounter), _entry(84_000, []), (), False)
        for item in g.items:
            assert item.kind == "general-advice" and item.based_on
            assert item.rule == "naxx-execution-v1"
