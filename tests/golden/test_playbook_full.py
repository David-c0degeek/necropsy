"""Playbook decisions on the full export reproduce the reference playbook's facts (golden)."""

from __future__ import annotations

from typing import Any

import pytest

from tests.analysis_db import connect, full_db
from tests.golden.fact_checks import _boss_doc

pytestmark = pytest.mark.golden


@pytest.fixture(scope="module")
def patchwerk() -> dict[str, Any]:
    with connect(full_db()) as con:
        playbook: dict[str, Any] = _boss_doc(con, "Patchwerk")["playbook"]
    return playbook


def test_patchwerk_weapon_sets(patchwerk: dict[str, Any]) -> None:
    weave_set, ranged_set = patchwerk["weapons"][0], patchwerk["weapons"][1]
    assert [e["player"] for e in weave_set["entries"]] == ["Charies", "Andrenn", "Xal"]
    assert weave_set["raptor_users"] == 3 and weave_set["main_hand"] == 23039
    assert [e["player"] for e in ranged_set["entries"]] == ["Xert"]
    assert ranged_set["raptor_users"] == 0


def test_patchwerk_other_faction_melee_package(patchwerk: dict[str, Any]) -> None:
    [package] = patchwerk["melee_packages"]
    assert package["entry"]["player"] == "Smcadogx" and package["race"] == "Orc"
    assert package["race_proven"] and package["windfury_status"] == "confirmed"
    assert package["windfury_procs"] == 9 and package["white_swings"] == 13
    assert any(d["kind"] == "other-faction-melee-package" for d in patchwerk["do_not"])


def test_patchwerk_cooldowns_and_pet(patchwerk: dict[str, Any]) -> None:
    assert round(patchwerk["rapid_fire"]["rank_one"]["first_s"], 2) == 4.20
    assert round(patchwerk["rapid_fire"]["subject_first_s"], 2) == 6.67
    assert round(patchwerk["refocus"]["rank_one"]["first_s"], 2) == 9.11
    refocus = patchwerk["refocus"]["same_faction_first_s"]
    assert refocus["value"] is None and refocus["n_values"] == 0 and refocus["n_without"] == 4
    assert refocus["reason"] == "0 of 4 known entries cast it (need 3 timings)"
    assert patchwerk["refocus"]["rank_one"]["used"] is True
    assert patchwerk["opener"]["renataki_users"] == 0
    pet = patchwerk["pet"]
    assert round(pet["subject_stopped_early_s"], 1) == 7.1 and round(pet["subject_dps"]) == 78
    assert pet["same_faction_dps_min"]["value"] < 150 < pet["same_faction_dps_max"]["value"]
    assert pet["same_faction_median_dps"]["level"] == "derived"


def test_patchwerk_raid_ask(patchwerk: dict[str, Any]) -> None:
    kinds = [a["kind"] for a in patchwerk["raid_asks"]]
    assert kinds == ["already-faster-than-rank-one"]


def test_every_boss_with_a_kill_has_a_playbook() -> None:
    with connect(full_db()) as con:
        for boss in (
            "Patchwerk",
            "Grobbulus",
            "Gluth",
            "Thaddius",
            "Noth the Plaguebringer",
            "Heigan the Unclean",
            "Loatheb",
            "Anub'Rekhan",
            "Grand Widow Faerlina",
            "Maexxna",
            "Instructor Razuvious",
            "Gothik the Harvester",
            "The Four Horsemen",
            "Sapphiron",
            "Kel'Thuzad",
        ):
            playbook = _boss_doc(con, boss)["playbook"]
            assert playbook is not None and playbook["rule_set"] == "playbook-v1", boss
