"""Zone overview on the full export reproduces the reference's global facts (golden)."""

from __future__ import annotations

from typing import Any

import pytest

from tests.analysis_db import connect, full_db
from tests.golden.fact_checks import _document

pytestmark = pytest.mark.golden


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    with connect(full_db()) as con:
        return _document(con)


def _top(tally: dict[str, Any]) -> str:
    return str(tally["counts"][0]["key"])


def test_badges_and_global_setup(document: dict[str, Any]) -> None:
    overview = document["overview"]
    assert overview["recorded_entries"] == 75
    assert {c["key"]: c["count"] for c in overview["by_faction"]} == {"Alliance": 63, "Horde": 12}
    setup = overview["setup"]
    assert _top(setup["talents"]) == "20/31/0"
    assert _top(setup["darkmoon"]) == "Sayge's Dark Fortune of Damage"
    assert _top(setup["ranged_weapon"]) == "Nerubian Slavemaker"
    assert "Cryptstalker" in _top(setup["armor_pattern"])
    assert setup["subject_ammo"]["recommended_name"] == "Doomshot"
    assert setup["faction"] == "Alliance"


def test_patchwerk_correction(document: dict[str, Any]) -> None:
    patchwerk = document["overview"]["corrections"][0]
    assert (patchwerk["rank_one_player"], patchwerk["rank_one_race"]) == ("Smcadogx", "Orc")
    assert patchwerk["rank_one_windfury"] == "confirmed"
    assert [w[0] for w in patchwerk["same_faction_weavers"]] == ["Charies", "Andrenn", "Xal"]
    assert patchwerk["pure_ranged_reference"][0] == "Xert"


def test_mark_of_the_champion_does_not_apply_to_faerlina(document: dict[str, Any]) -> None:
    faerlina = next(b for b in document["bosses"] if b["boss"] == "Grand Widow Faerlina")
    [mark] = faerlina["playbook"]["static"]["type_bonuses"]
    assert mark["applies_to_boss"] is False
    assert faerlina["playbook"]["static"]["encounter"]["creature_type"] == "Humanoid"


def test_armor_pattern_counts_armor_slots_apart_from_the_set_ring(
    document: dict[str, Any],
) -> None:
    setup = document["overview"]["setup"]
    assert _top(setup["armor_pattern"]) == "7-piece Cryptstalker Armor"
    assert _top(setup["set_extras"]) == "Cryptstalker Armor: finger"
    [crypt] = document["bosses"][0]["subject"]["set_armor"]
    assert (crypt["armor_pieces"], crypt["other_slots"]) == (7, ["finger"])


def test_guidance_conditions_on_the_full_export(document: dict[str, Any]) -> None:
    def items(boss: str) -> dict[str, Any]:
        section = next(b for b in document["bosses"] if b["boss"] == boss)
        return {i["key"]: i for i in section["playbook"]["static"]["guidance"]["items"]}

    assert items("Gothik the Harvester")["waves-or-boss"]["status"] == "applies"
    assert items("Gothik the Harvester")["one-rapid-fire"]["status"] == "otherwise"
    assert items("Thaddius")["rapid-fire-phase"]["condition"]["status"] == "true"
    assert not [
        k
        for k in items("Kel'Thuzad")
        if k not in {"one-rapid-fire", "refocus-after-specials", "refocus-trinket-lockout"}
    ]
    horsemen = next(b for b in document["bosses"] if b["boss"] == "The Four Horsemen")
    assert horsemen["playbook"]["static"]["type_bonuses"][0]["applies_to_boss"] is True


def test_rank_one_proven_non_use_is_not_unknown(document: dict[str, Any]) -> None:
    gothik = next(b for b in document["bosses"] if b["boss"] == "Gothik the Harvester")
    rank_one = gothik["playbook"]["rapid_fire"]["rank_one"]
    assert rank_one["entry"]["player"] == "Andrenn"
    assert (rank_one["first_s"], rank_one["used"]) == (None, False)
