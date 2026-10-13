"""Hunter plugin and ranking damage over synthetic snapshots."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.analysis.benchmark import RaptorRoles, raptor_roles
from necropsy.analysis.classes import plugin_for
from necropsy.analysis.classes.classic_era.hunter import HunterAnalysis
from necropsy.analysis.context import participant_fights
from necropsy.analysis.encounters import EncounterRules, encounter_rules
from necropsy.analysis.evidence import EvidenceLevel
from necropsy.analysis.generic import targets
from necropsy.analysis.generic.environment import environment_profile
from necropsy.normalize.ingest import ingest
from tests.snapshot_builder import FIGHT, SnapshotSpec, build, ev, page

PLAYER = "player_1_Hunter"
PET = "pet_2_Cat"
AUTO, AIMED, MULTI, RAPTOR, RF, REFOCUS, QS = 75, 20904, 25294, 14266, 3045, 24531, 6150
BOSS_ID = 50
ABILITIES = [
    {"gameID": 3009, "name": "Claw", "type": "1", "icon": "x"},
    {"gameID": 23110, "name": "Dash", "type": "1", "icon": "x"},
    {"gameID": 24579, "name": "Demoralizing Screech", "type": "1", "icon": "x"},
    {"gameID": 23148, "name": "Dive", "type": "1", "icon": "x"},
]
BOSS = {
    "id": BOSS_ID,
    "name": "Patchwerk",
    "type": "NPC",
    "subType": "Boss",
    "server": None,
    "gameID": 16028,
    "petOwner": None,
    "icon": "x",
}
CHICKEN = {
    "id": 3,
    "name": "Battle Chicken",
    "type": "Pet",
    "subType": "Pet",
    "server": None,
    "gameID": 8836,
    "petOwner": 1,
    "icon": "x",
}
CAT = {
    "id": 2,
    "name": "Cat",
    "type": "Pet",
    "subType": "Pet",
    "server": None,
    "gameID": 999999,
    "petOwner": 1,
    "icon": "x",
}
COMBATANT = {
    "timestamp": 0,
    "type": "combatantinfo",
    "sourceID": 1,
    "fight": FIGHT,
    "faction": 1,
    "specID": 0,
    "talents": [{"id": 20}, {"id": 31}, {"id": 0}],
    "auras": [],
    "gear": [{"id": 0}] * 12
    + [{"id": 19953}, {"id": 23206}]
    + [{"id": 0}] * 3
    + [{"id": 22812, "permanentEnchant": 664}],
}

MC_PLAYER = {
    "id": 9,
    "name": "Teammate",
    "type": "Player",
    "subType": "Priest",
    "server": "Realm",
    "gameID": 9,
    "petOwner": None,
    "icon": "x",
}


def cast(ts: int, ability: int, target: int | None = BOSS_ID, **kw: Any) -> dict[str, Any]:
    return ev(ts, "cast", source=1, target=target, abilityGameID=ability, **kw)


def dmg(ts: int, source: int, ability: int, amount: int, target: int = BOSS_ID) -> dict[str, Any]:
    return ev(ts, source=source, target=target, abilityGameID=ability, amount=amount)


def _autos(start: int, gap: int, n: int) -> list[dict[str, Any]]:
    return [cast(start + i * gap, AUTO) for i in range(n)]


def _spec(
    source: list[dict[str, Any]],
    target: list[dict[str, Any]] | None = None,
    pet_source: list[dict[str, Any]] | None = None,
    **kw: Any,
) -> SnapshotSpec:
    pets = kw.pop("pets", {1: {2: "Cat", 3: "Battle Chicken"}})
    more_actors = kw.pop("more_actors", [])
    return SnapshotSpec(
        pets=pets,
        streams={
            f"{PLAYER}/source": [page([COMBATANT, *source])],
            f"{PLAYER}/target": [page(target or [])],
            f"{PET}/source": [page(pet_source or [])],
            f"{PET}/target": [page([])],
            "pet_3_Battle Chicken/source": [page([])],
            "pet_3_Battle Chicken/target": [page([])],
        },
        extra_actors=[BOSS, CAT, CHICKEN, *more_actors],
        extra_abilities=ABILITIES,
        **kw,
    )


@pytest.fixture
def db(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[duckdb.DuckDBPyConnection]:
    out = tmp_path / "a.duckdb"
    ingest(build(tmp_path / "s.zip", request.param), out)
    con = duckdb.connect(str(out), read_only=True)
    yield con
    con.close()


def _analyze(con: duckdb.DuckDBPyConnection) -> HunterAnalysis:
    plugin = plugin_for("classic_era", 3)
    assert plugin is not None
    pf = participant_fights(con)[0]
    result = plugin.analyze(con, pf, environment_profile(con, pf))
    assert isinstance(result, HunterAnalysis)
    return result


ROTATION = [
    *_autos(1000, 3000, 12),
    cast(2000, AIMED),
    cast(2500, MULTI),
    cast(5000, RAPTOR),
    cast(5000, REFOCUS),
    cast(1500, RF),
    cast(40000, 14311, target=7, targetIsFriendly=True),
    cast(41000, 19503, target=BOSS_ID),
]


@pytest.mark.parametrize("db", [_spec(ROTATION)], indirect=True)
def test_shots_opener_and_intervals(db: duckdb.DuckDBPyConnection) -> None:
    a = _analyze(db)
    assert len(a.shots["auto_shot"].casts.value or ()) == 12
    assert [c.t_s for c in a.shots["aimed_shot"].casts.value or ()] == [2.0]
    assert a.shots["auto_shot"].per_minute.value == pytest.approx(12 / (100 / 60))
    assert [c.kind for c in a.opener.value or ()][:4] == [
        "auto_shot",
        "rapid_fire",
        "aimed_shot",
        "multi_shot",
    ]
    intervals = a.auto_intervals.value or ()
    assert len(intervals) == 11
    first = intervals[0]
    assert first.gap_s == 3.0
    assert first.inside == {"aimed_shot": (2.0,), "multi_shot": (2.5,)}
    # Raptor and Refocus share a timestamp: both are kept in the second interval.
    assert intervals[1].inside == {"raptor_strike": (5.0,), "refocus": (5.0,)}
    assert [c.kind for c in a.friendly_crowd_control.value or ()] == ["cc:Freezing Trap"]


@pytest.mark.parametrize("db", [_spec(ROTATION)], indirect=True)
def test_no_haste_aura_on_the_target_stream_means_not_hasted(db: duckdb.DuckDBPyConnection) -> None:
    # Rapid Fire was cast but its aura never appears on the target stream and the
    # starting snapshot is empty: RF is known not active, Quick Shots too.
    a = _analyze(db)
    intervals = a.auto_intervals.value or ()
    assert all(iv.ranged_haste.value is False for iv in intervals)
    assert a.auto_gap.baseline_count == 9
    assert a.auto_gap.flagged.value == ()
    assert a.auto_gap.flagged.level is EvidenceLevel.INFERRED


LONG = [*_autos(1000, 3000, 8), cast(30000, AUTO), cast(33000, AUTO)]


@pytest.mark.parametrize("db", [_spec(LONG)], indirect=True)
def test_long_clean_interval_is_flagged(db: duckdb.DuckDBPyConnection) -> None:
    a = _analyze(db)
    assert a.auto_gap.median_gap_s == 3.0
    assert a.auto_gap.flagged.value == (8,)
    assert dict(a.auto_gap.flagged.params)["baseline_count"] == 9


FEW = _autos(1000, 3000, 4)


@pytest.mark.parametrize("db", [_spec(FEW)], indirect=True)
def test_too_few_clean_intervals_is_unknown(db: duckdb.DuckDBPyConnection) -> None:
    gap = _analyze(db).auto_gap
    assert gap.flagged.level is EvidenceLevel.UNKNOWN
    assert gap.baseline_count == 3


HASTED = [*_autos(1000, 2000, 8)]
RF_AURA = [
    ev(1000, "applybuff", source=1, target=1, abilityGameID=RF),
    ev(16000, "removebuff", source=1, target=1, abilityGameID=RF),
]


@pytest.mark.parametrize("db", [_spec(HASTED, RF_AURA)], indirect=True)
def test_hasted_intervals_leave_the_baseline(db: duckdb.DuckDBPyConnection) -> None:
    a = _analyze(db)
    assert all(iv.ranged_haste.value is True for iv in a.auto_intervals.value or ())
    assert a.auto_gap.baseline_count == 0


PET_SOURCE = [
    ev(3000, "cast", source=2, target=BOSS_ID, abilityGameID=3009),
    ev(4000, "cast", source=2, target=1, abilityGameID=23110),
    dmg(3000, 2, 3009, 400),
]


@pytest.mark.parametrize("db", [_spec([cast(1000, AUTO)], pet_source=PET_SOURCE)], indirect=True)
def test_pet_classification_and_family(db: duckdb.DuckDBPyConnection) -> None:
    a = _analyze(db)
    categories = {p.name: p.category.value for p in a.pets}
    assert categories == {"Cat": "hunter-pet", "Battle Chicken": "engineering"}
    pet = a.hunter_pets[0]
    assert pet.family.value == "Cat"
    assert pet.family.level is EvidenceLevel.INFERRED
    assert pet.dps.value == pytest.approx(4.0)
    assert a.gear.renataki_at_pull.value is True
    assert a.gear.ranged.value is not None and a.gear.ranged.value.permanent_enchant == 664


SCREECH = [
    ev(3000, "cast", source=2, target=BOSS_ID, abilityGameID=24579),
    ev(4000, "cast", source=2, target=1, abilityGameID=23148),
]


@pytest.mark.parametrize("db", [_spec([cast(1000, AUTO)], pet_source=SCREECH)], indirect=True)
def test_ambiguous_family_stays_unknown(db: duckdb.DuckDBPyConnection) -> None:
    pet = _analyze(db).hunter_pets[0]
    assert pet.family.level is EvidenceLevel.UNKNOWN
    assert pet.family_candidates == ("Bat", "Carrion Bird", "Owl")
    assert (24579, "Demoralizing Screech") in (pet.abilities.value or ())


CHICKEN_LIKE_CAT = [ev(3000, "cast", source=3, target=BOSS_ID, abilityGameID=3009)]


@pytest.mark.parametrize(
    "db",
    [
        SnapshotSpec(
            pets={1: {3: "Battle Chicken"}},
            streams={
                f"{PLAYER}/source": [page([cast(1000, AUTO)])],
                f"{PLAYER}/target": [page([])],
                "pet_3_Battle Chicken/source": [page(CHICKEN_LIKE_CAT)],
                "pet_3_Battle Chicken/target": [page([])],
            },
            extra_actors=[BOSS, CHICKEN],
            extra_abilities=ABILITIES,
        )
    ],
    indirect=True,
)
def test_game_id_rule_beats_ability_inference(db: duckdb.DuckDBPyConnection) -> None:
    a = _analyze(db)
    assert [p.category.value for p in a.pets] == ["engineering"]
    assert a.hunter_pets == ()


DAMAGE = [
    dmg(1000, 1, AUTO, 1000),
    dmg(2000, 1, 13241, 300, target=1),  # own Sapper Charge
    dmg(2500, 1, 13241, 50, target=2),  # own pet
    dmg(3000, 1, AUTO, 80, target=9),  # a mind-controlled raid member: counted
]


@pytest.mark.parametrize(
    "db",
    [_spec(DAMAGE, pet_source=[dmg(1500, 2, 3009, 200)], more_actors=[MC_PLAYER])],
    indirect=True,
)
def test_ranking_damage_excludes_only_self_damage(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    result = targets.ranking_damage(db, pf, None, None)
    assert (result.raw.value, result.external.value, result.ranked.value) == (1630, 1280, 1280)
    excluded = targets.ranking_damage(db, pf, lambda gid, name: name == "Patchwerk", "test-rule")
    assert excluded.ranked.value == 80
    assert dict(excluded.ranked.params)["encounter_exclusions"] == "test-rule"
    assert excluded.by_target.value is not None
    rows = {(r.actor_id, r.category): r.damage for r in excluded.by_target.value}
    assert rows[(BOSS_ID, "excluded")] == 1200
    assert rows[(9, "counted")] == 80
    assert rows[(1, "own")] == 300 and rows[(2, "own")] == 50
    counted = sum(r.damage for r in excluded.by_target.value if r.category == "counted")
    assert counted == excluded.ranked.value


@pytest.mark.parametrize(
    "db", [_spec([dmg(1000, 1, AUTO, 1000)], with_pets_json=False)], indirect=True
)
def test_missing_pet_listing_makes_ranking_unknown(db: duckdb.DuckDBPyConnection) -> None:
    result = targets.ranking_damage(db, participant_fights(db)[0], None, None)
    assert result.raw.level is EvidenceLevel.UNKNOWN
    assert result.ranked.level is EvidenceLevel.UNKNOWN


def test_registry_has_only_the_hunter() -> None:
    assert plugin_for("classic_era", 3) is not None
    assert plugin_for("classic_era", 1) is None


UNLISTED = [dmg(1000, 1, AUTO, 1000), dmg(2000, 1, AUTO, 70, target=77)]


@pytest.mark.parametrize("db", [_spec(UNLISTED)], indirect=True)
def test_unlisted_target_blocks_encounter_exclusions(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    plain = targets.ranking_damage(db, pf, None, None)
    assert (plain.external.value, plain.ranked.value) == (1070, 1070)
    ruled = targets.ranking_damage(db, pf, lambda gid, name: False, "test-rule")
    assert ruled.external.value == 1070
    assert ruled.ranked.level is EvidenceLevel.UNKNOWN
    assert ruled.by_target.value is not None
    categories = {r.actor_id: r.category for r in ruled.by_target.value}
    assert categories[77] == "unclassifiable"
    assert plain.by_target.value is not None
    assert {r.actor_id: r.category for r in plain.by_target.value}[77] == "counted"


ZERO_NO_TARGET = [
    dmg(1000, 1, AUTO, 1000),
    ev(2000, source=1, target=None, abilityGameID=1, amount=0),
]


@pytest.mark.parametrize("db", [_spec(ZERO_NO_TARGET)], indirect=True)
def test_zero_damage_without_target_id_is_still_unknown(db: duckdb.DuckDBPyConnection) -> None:
    result = targets.ranking_damage(db, participant_fights(db)[0], None, None)
    assert result.raw.value == 1000
    assert result.external.level is EvidenceLevel.UNKNOWN


NO_TARGET = [
    dmg(1000, 1, AUTO, 1000),
    ev(2000, source=1, target=None, abilityGameID=13241, amount=300),
]


@pytest.mark.parametrize("db", [_spec(NO_TARGET)], indirect=True)
def test_damage_without_target_id_makes_external_unknown(db: duckdb.DuckDBPyConnection) -> None:
    result = targets.ranking_damage(db, participant_fights(db)[0], None, None)
    assert result.raw.value == 1300
    assert result.external.level is EvidenceLevel.UNKNOWN
    assert result.ranked.level is EvidenceLevel.UNKNOWN


BOSS_PET = {
    "id": 60,
    "name": "Corpse Scarab",
    "type": "Pet",
    "subType": "Pet",
    "server": None,
    "gameID": 16698,
    "petOwner": BOSS_ID,
    "icon": "x",
}
STRANGER = {
    "id": 61,
    "name": "Stranger",
    "type": "Player",
    "subType": "Rogue",
    "server": "R",
    "gameID": 61,
    "petOwner": None,
    "icon": "x",
}
CC = [
    cast(1000, 13327, target=9),  # Reckless Charge (first ID) on a listed raid member
    cast(2000, 22641, target=9),  # Reckless Charge (second ID)
    cast(3000, 19503, target=60),  # Scatter Shot on a pet whose owner is a listed enemy
    cast(4000, 19503, target=BOSS_ID),  # Scatter Shot on a listed enemy
]


@pytest.mark.parametrize(
    "db",
    [_spec(CC, more_actors=[MC_PLAYER, BOSS_PET], friendly_players=[1, 9], enemy_npcs=[BOSS_ID])],
    indirect=True,
)
def test_friendly_crowd_control_uses_fight_membership(db: duckdb.DuckDBPyConnection) -> None:
    a = _analyze(db)
    assert [c.t_s for c in a.friendly_crowd_control.value or ()] == [1.0, 2.0]
    assert a.friendly_crowd_control.claim.value == "complete"
    sources = {c.target_id: c.side_source for c in a.friendly_crowd_control.value or ()}
    assert sources == {9: "fight-friendly-list"}


@pytest.mark.parametrize(
    "db", [_spec([cast(1000, 19503, target=61)], more_actors=[STRANGER])], indirect=True
)
def test_unknown_side_makes_friendly_cc_partial(db: duckdb.DuckDBPyConnection) -> None:
    result = _analyze(db).friendly_crowd_control
    assert result.value == ()
    assert result.claim.value == "value"
    assert "partial" in (result.note or "")


PARTIAL_GEAR = {**COMBATANT, "gear": [{"id": 5}] * 12}
EMPTY_TRINKETS = {**COMBATANT, "gear": [{"id": 5}] * 12 + [{"id": 0}, {"id": 0}]}


@pytest.mark.parametrize(
    "db",
    [
        SnapshotSpec(
            pets={1: {}},
            streams={
                f"{PLAYER}/source": [page([PARTIAL_GEAR, cast(1000, AUTO)])],
                f"{PLAYER}/target": [page([])],
            },
            extra_actors=[BOSS],
        )
    ],
    indirect=True,
)
def test_missing_trinket_slots_make_renataki_unknown(db: duckdb.DuckDBPyConnection) -> None:
    gear = _analyze(db).gear
    assert gear.renataki_at_pull.level is EvidenceLevel.UNKNOWN
    assert gear.trinkets.level is EvidenceLevel.UNKNOWN


@pytest.mark.parametrize(
    "db",
    [
        SnapshotSpec(
            pets={1: {}},
            streams={
                f"{PLAYER}/source": [page([EMPTY_TRINKETS, cast(1000, AUTO)])],
                f"{PLAYER}/target": [page([])],
            },
            extra_actors=[BOSS],
        )
    ],
    indirect=True,
)
def test_recorded_empty_trinket_slots_are_known(db: duckdb.DuckDBPyConnection) -> None:
    gear = _analyze(db).gear
    assert gear.renataki_at_pull.value is False
    assert [t.item_id for t in gear.trinkets.value or ()] == [0, 0]


CONTROLLED_NPC = {
    "id": 62,
    "name": "Deathknight Understudy",
    "type": "NPC",
    "subType": "NPC",
    "server": None,
    "gameID": 16803,
    "petOwner": 9,
    "icon": "x",
}


@pytest.mark.parametrize(
    "db",
    [
        _spec(
            [cast(1000, 19503, target=62)],
            more_actors=[MC_PLAYER, CONTROLLED_NPC],
            enemy_npcs=[BOSS_ID],
        )
    ],
    indirect=True,
)
def test_unlisted_npc_side_is_undecided(db: duckdb.DuckDBPyConnection) -> None:
    # Not in any fight list; its owner (a raid member) is not listed either.
    result = _analyze(db).friendly_crowd_control
    assert result.claim.value == "value"
    assert "partial" in (result.note or "")


@pytest.mark.parametrize(
    "db",
    [
        _spec(
            [cast(1000, 19503, target=62)],
            more_actors=[MC_PLAYER, CONTROLLED_NPC],
            friendly_players=[1, 9],
        )
    ],
    indirect=True,
)
def test_npc_owned_by_a_listed_raid_member_is_friendly(db: duckdb.DuckDBPyConnection) -> None:
    result = _analyze(db).friendly_crowd_control
    assert [c.target_id for c in result.value or ()] == [62]
    assert (result.value or ())[0].side_source == "fight-friendly-list"


@pytest.mark.parametrize(
    "db",
    [
        _spec(
            [cast(1000, 14311, target=-1), cast(2000, 13327, target=9)],
            more_actors=[MC_PLAYER],
            friendly_players=[1, 9],
        )
    ],
    indirect=True,
)
def test_ground_trap_has_no_unit_target(db: duckdb.DuckDBPyConnection) -> None:
    result = _analyze(db).friendly_crowd_control
    assert result.claim.value == "complete"
    assert [c.target_id for c in result.value or ()] == [9]


@pytest.mark.parametrize(
    "db",
    [
        _spec([cast(1000, 19503, target=None)]),
        _spec([cast(1000, 13327, target=-1)]),
    ],
    indirect=True,
)
def test_unit_cc_without_a_real_target_is_undecided(db: duckdb.DuckDBPyConnection) -> None:
    # A missing target ID, or the Environment placeholder on a unit-targeted
    # ability, cannot prove the target was not a raid member.
    result = _analyze(db).friendly_crowd_control
    assert result.claim.value == "value"
    assert "partial" in (result.note or "")


ADD = {
    "id": 60,
    "name": "Add",
    "type": "NPC",
    "subType": "NPC",
    "server": None,
    "gameID": 4242,
    "petOwner": None,
    "icon": "x",
}
TRASH = {**ADD, "id": 61, "name": "Trash", "gameID": 4343}
STRAY = {**ADD, "id": 62, "name": "Stray", "gameID": 4444}
RULES = EncounterRules(
    1,
    "Boss",
    frozenset({16028}),
    frozenset(),
    frozenset({16028, 4242}),
    "r",
    start_trash_game_ids=frozenset({4343}),
)
RAPTORS = [
    cast(1000, RAPTOR),
    cast(4000, RAPTOR, target=60),
    cast(7000, RAPTOR, target=61),
    cast(9000, RAPTOR, target=62),
]


@pytest.mark.parametrize(
    "db",
    [_spec(RAPTORS, more_actors=[ADD, TRASH, STRAY], enemy_npcs=[BOSS_ID, 60, 61, 62])],
    indirect=True,
)
def test_raptor_casts_split_by_target_role(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    casts = _analyze(db).shots["raptor_strike"].casts
    roles = raptor_roles(db, pf, RULES, casts)
    assert roles.value == RaptorRoles(boss=1, non_boss=3, native_adds=1, start_trash=1, foreign=1)
    assert roles.rule_id == "cast-target-role-v1"


@pytest.mark.parametrize(
    "db",
    [_spec(RAPTORS[:2], more_actors=[ADD], enemy_npcs=[BOSS_ID])],
    indirect=True,
)
def test_raptor_on_an_undecided_side_makes_roles_unknown(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    casts = _analyze(db).shots["raptor_strike"].casts
    roles = raptor_roles(db, pf, RULES, casts)
    assert roles.level is EvidenceLevel.UNKNOWN
    assert roles.note is not None and "no resolved hostile NPC target" in roles.note


NAMELESS_WORSHIPPER = {**ADD, "id": 77, "name": "Naxxramas Worshipper", "gameID": None}


@pytest.mark.parametrize(
    "db",
    [_spec([dmg(1000, 1, AUTO, 1000, target=77)], more_actors=[NAMELESS_WORSHIPPER])],
    indirect=True,
)
def test_named_target_without_game_id_blocks_exclusions(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    faerlina = encounter_rules("classic_era", "naxxramas", 51110)
    result = targets.ranking_damage(db, pf, faerlina.excluded_from_ranking, faerlina.exclusion_rule)
    assert result.external.value == 1000
    assert result.ranked.level is EvidenceLevel.UNKNOWN
    assert result.by_target.value is not None
    assert [r.category for r in result.by_target.value] == ["unclassifiable"]


HOSTILE_PLAYER = {**MC_PLAYER, "id": 70, "gameID": 0}
HOSTILE_PET = {**CAT, "id": 71, "petOwner": None, "gameID": 555}


@pytest.mark.parametrize(
    ("db", "target"),
    [
        (_spec([cast(1000, RAPTOR, target=70)], more_actors=[HOSTILE_PLAYER], enemy_npcs=[70]), 70),
        (_spec([cast(1000, RAPTOR, target=71)], more_actors=[HOSTILE_PET], enemy_npcs=[71]), 71),
        (
            _spec(
                [cast(1000, RAPTOR, target=72)],
                more_actors=[{**ADD, "id": 72, "type": None}],
                enemy_npcs=[72],
            ),
            72,
        ),
    ],
    indirect=["db"],
)
def test_raptor_on_a_non_npc_target_is_unknown(db: duckdb.DuckDBPyConnection, target: int) -> None:
    pf = participant_fights(db)[0]
    casts = _analyze(db).shots["raptor_strike"].casts
    assert casts.value is not None and [c.target_id for c in casts.value] == [target]
    roles = raptor_roles(db, pf, RULES, casts)
    assert roles.level is EvidenceLevel.UNKNOWN
