"""Static game data: ammunition, sets, creature-type bonuses, encounter facts."""

from __future__ import annotations

from necropsy.analysis import gamedata
from necropsy.rules import load_rules


def test_ammo_follows_the_ranged_weapon_type() -> None:
    crossbow = gamedata.ammo_advice(22812)  # Nerubian Slavemaker
    assert (crossbow.ranged_type, crossbow.uses_ammo, crossbow.recommended_name) == (
        "crossbow",
        "arrow",
        "Doomshot",
    )
    assert crossbow.source and "warcraft.wiki.gg" in crossbow.source
    unknown = gamedata.ammo_advice(None)
    assert unknown.recommended_name is None and unknown.reason == "ranged weapon unknown"
    unlisted = gamedata.ammo_advice(1)
    assert unlisted.recommended_name is None and unlisted.reason


def test_bullets_are_advised_for_guns() -> None:
    rule = load_rules("classic_era", "hunter")["ammunition_advice"]
    assert rule["bullet"]["name"] == "Miniature Cannon Balls"
    ammo = {i.id: i.ammo for i in gamedata.items().values() if i.ammo}
    assert ammo[12654] == "arrow" and ammo[13377] == "bullet"


def test_set_pieces_need_two_items() -> None:
    assert gamedata.set_pieces([22436]) == ()
    assert gamedata.set_pieces([22436, 22437, 22438]) == (("Cryptstalker Armor", 3),)


def test_creature_type_bonus_applicability() -> None:
    [faerlina] = gamedata.creature_type_bonuses("naxxramas", 51110)
    [patchwerk] = gamedata.creature_type_bonuses("naxxramas", 51118)
    [horsemen] = gamedata.creature_type_bonuses("naxxramas", 51121)
    assert (faerlina.applies, patchwerk.applies, horsemen.applies) == (False, True, True)


def test_every_encounter_fact_cites_a_source_or_says_why_not() -> None:
    data = load_rules("classic_era", "zones/naxxramas_facts")
    assert len(data["encounters"]) == 15
    for entry in data["encounters"]:
        if entry["source"] is None:
            assert entry["creature_type"] is None and entry["note"]
        else:
            assert entry["source"].startswith("https://")
        facts = gamedata.encounter_facts("naxxramas", int(entry["id"]))
        assert facts is not None and facts.rule == "naxx-encounter-facts-v1"


def test_game_data_names_its_build() -> None:
    source = gamedata.source()
    assert source["product"] == "wow_classic_era" and source["build"] == "1.15.9.70003"
    assert gamedata.enchant_names()[2523] == "+3% Hit"


def test_set_armor_counts_rings_apart_from_armor() -> None:
    worn = [22436, 22437, 22438, 22439, 22440, 22441, 22442, 23067]
    [crypt] = gamedata.set_armor(worn)
    assert (crypt.armor_pieces, crypt.other_pieces, crypt.other_slots) == (7, 1, ("finger",))
    assert gamedata.set_pieces(worn) == (("Cryptstalker Armor", 8),)


def test_on_use_categories_come_from_client_data() -> None:
    charm = gamedata.items()[19953].on_use
    crest = gamedata.items()[23041].on_use
    assert charm is not None and crest is not None
    assert (charm.cooldown_s, charm.category, charm.category_cooldown_s) == (180.0, 1141, 10.0)
    assert crest.category == charm.category


def test_rapid_fire_set_bonuses_need_their_threshold() -> None:
    base = gamedata.rapid_fire([])
    assert (base.duration_s, base.cooldown_s, base.ranged_haste_pct) == (15.0, 300.0, 40.0)
    assert gamedata.rapid_fire([22436]).duration_s == 15.0
    assert gamedata.rapid_fire([22436, 22437]).duration_s == 19.0
    striker = gamedata.rapid_fire([21366, 21365, 21370, 21368, 21367])
    assert striker.cooldown_s == 180.0 and striker.applied
    assert not gamedata.rapid_fire(None).known


def test_pet_profiles_total_highest_ranks_against_the_budget() -> None:
    facts = gamedata.pet_facts()
    totals = {p.key: (p.total_tp, p.fits) for p in facts.profiles}
    assert totals["reference-frost"] == (280, True)
    assert totals["frost-max-no-dash"] == (300, True)
    assert totals["frost-max-all"] == (325, False)
    assert facts.budget_tp == 300
    assert [r[1] for r in facts.frost_resistance] == [30, 60, 90, 120]
    mods = {m.family: m for m in facts.family_modifiers}
    assert mods["Cat"].damage == mods["Raptor"].damage == 1.10
    assert all(src.startswith("https://") for s in facts.sources.values() for src in s)
