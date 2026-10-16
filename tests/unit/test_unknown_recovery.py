"""Uncertainty boundaries for partial ownership and pre-window evidence."""

from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from typing import Any

import duckdb
import pytest

from necropsy.analysis.classes.classic_era.hunter import PetCategory, _hunter_pet
from necropsy.analysis.context import ParticipantFight, hunter_pet_listing_known
from necropsy.analysis.evidence import EvidenceRef, observed
from necropsy.analysis.generic import environment, metrics
from necropsy.normalize.schema import ALL_TABLES
from necropsy.wcl.acquire import discover_pets, fight_pets
from necropsy.wcl.combatant import auras_at_start, validate_context

PF = ParticipantFight(
    "R", 3, 5, "Hunter", "Realm", "you", "Patchwerk", 51118, None, 1000, 9000, True
)


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    db = duckdb.connect()
    for table in ALL_TABLES:
        db.execute(table.ddl())
    yield db
    db.close()


def _context() -> dict[str, Any]:
    return {
        "version": 2,
        "target_game_id": 100005,
        "report": "R",
        "fight": 3,
        "actor": 5,
        "revision": 4,
        "endpoint": "user",
        "ranked_start": 1000,
        "snapshots": [
            {
                "data": [
                    {
                        "type": "combatantinfo",
                        "sourceID": 5,
                        "fight": 3,
                        "timestamp": 500,
                        "talents": [{"id": 20}, {"id": 31}, {"id": 0}],
                        "auras": [
                            {"ability": 23768, "source": 5, "name": "Sayge"},
                            {"ability": 3045, "source": 5, "name": "Rapid Fire"},
                        ],
                    }
                ],
                "nextPageTimestamp": None,
            }
        ],
        "prelude": [
            {
                "data": [
                    {
                        "type": "removebuff",
                        "timestamp": 750,
                        "abilityGameID": 3045,
                        "sourceID": 5,
                        "targetID": 5,
                        "fight": 2,
                    },
                    {
                        "type": "removebuff",
                        "timestamp": 1000,
                        "abilityGameID": 23768,
                        "sourceID": 5,
                        "targetID": 5,
                        "fight": 3,
                    },
                ],
                "nextPageTimestamp": None,
            }
        ],
    }


def test_prelude_recovers_ranked_start_without_importing_boundary_changes(
    con: duckdb.DuckDBPyConnection,
) -> None:
    context = _context()
    validate_context(context, "R", 3, 5, 4, "user", 1000)
    assert auras_at_start(context) == ((23768, "Sayge"),)
    con.execute(
        "INSERT INTO combatant_context VALUES ('R',3,5,?,'raw-context.json')", [json.dumps(context)]
    )
    auras = environment.starting_auras(con, PF)
    assert auras.value and [a.ability_id for a in auras.value] == [23768]
    assert auras.rule_id == "combatant-prelude-auras-v1"
    assert environment.talents(con, PF).value == "20/31/0"
    assert con.execute("SELECT count(*) FROM events").fetchone() == (0,)


def test_prelude_does_not_retain_a_buff_when_removal_source_is_ambiguous() -> None:
    context = _context()
    context["snapshots"][0]["data"][0]["auras"][1].pop("source")
    assert auras_at_start(context) is None
    context["snapshots"][0]["data"][0]["auras"][1]["source"] = {}
    assert auras_at_start(context) is None


@pytest.mark.parametrize(
    "change",
    [
        {"actor": 6},
        {"fight": 4},
        {"revision": 9},
        {"endpoint": "client"},
        {"prelude": []},
        {"ranked_start": True},
        {"version": 2.0},
        {"prelude": [{"data": [], "nextPageTimestamp": 1000}]},
    ],
)
def test_invalid_or_incomplete_context_is_rejected(change: dict[str, Any]) -> None:
    context = {**_context(), **change}
    with pytest.raises(ValueError):
        validate_context(context, "R", 3, 5, 4, "user", 1000)


def test_prelude_rejects_other_target_and_out_of_range_event() -> None:
    for change in ({"targetID": 6}, {"timestamp": 9999}, {"type": "damage"}):
        context = copy.deepcopy(_context())
        context["prelude"][0]["data"][0].update(change)
        with pytest.raises(ValueError):
            validate_context(context, "R", 3, 5, 4, "user", 1000)


def test_ambiguous_context_page_boundary_cannot_prove_starting_state() -> None:
    context = _context()
    event = context["prelude"][0]["data"][0]
    context["prelude"] = [
        {"data": [event], "nextPageTimestamp": 750},
        {"data": [event], "nextPageTimestamp": None},
    ]
    with pytest.raises(ValueError, match="ambiguous page boundary"):
        validate_context(context, "R", 3, 5, 4, "user", 1000)


def test_fight_scoped_talents_do_not_cross_fights_and_conflicts_stay_unknown(
    con: duckdb.DuckDBPyConnection,
) -> None:
    info = json.dumps({"talents": [{"guid": 5}, {"guid": 31}, {"guid": 15}]})
    con.execute("INSERT INTO fight_player_details VALUES ('R',4,5,?,'fight4.json','hash')", [info])
    assert environment.talents(con, PF).value is None
    con.execute("INSERT INTO fight_player_details VALUES ('R',3,5,?,'fight3.json','hash')", [info])
    assert environment.talents(con, PF).value == "5/31/15"
    con.execute(
        "INSERT INTO combatant_info (report_code,fight_id,actor_id,talent_points,event_uid) "
        "VALUES ('R',3,5,'20/31/0','event')"
    )
    assert environment.talents(con, PF).value is None


def test_confirmed_pet_is_kept_but_unowned_pet_never_guessed() -> None:
    report = {
        "masterData": {
            "actors": [
                {"id": 8, "type": "Pet", "petOwner": 5},
                {"id": 9, "type": "Pet", "petOwner": None, "gameID": 8836},
            ]
        }
    }
    fight = {"friendlyPets": [{"id": 8, "petOwner": 5}, {"id": 9, "petOwner": None}]}
    discovered = discover_pets(report, fight, 5)
    assert discovered.confirmed == (8,) and not discovered.complete
    assert fight_pets(report, fight, 5)[0] is None
    fight["friendlyPets"].append({"id": 8, "petOwner": 6})
    assert discover_pets(report, fight, 5).confirmed == ()


def test_only_known_non_hunter_guardians_can_leave_hunter_roster_complete(
    con: duckdb.DuckDBPyConnection,
) -> None:
    listed = json.dumps([{"id": 8, "petOwner": 5}, {"id": 9, "petOwner": None}])
    con.execute(
        "INSERT INTO fights (report_code,fight_id,friendly_pets) VALUES ('R',3,?)", [listed]
    )
    con.execute(
        "INSERT INTO actors (report_code,actor_id,type,game_id,pet_owner) "
        "VALUES ('R',8,'Pet',999,5),('R',9,'Pet',8836,NULL)"
    )
    con.execute(
        "INSERT INTO stream_coverage (report_code,fight_id,actor_id,role,owner_actor_id) "
        "VALUES ('R',3,NULL,'pet-discovery',5)"
    )
    assert not hunter_pet_listing_known(con, PF)  # No confirmed pet stream exported yet.
    con.execute(
        "INSERT INTO stream_coverage "
        "(report_code,fight_id,actor_id,actor_name,role,owner_actor_id) "
        "VALUES ('R',3,8,'Pet','pet',5)"
    )
    assert hunter_pet_listing_known(con, PF)
    con.execute("UPDATE actors SET game_id=9999 WHERE actor_id=9")
    assert not hunter_pet_listing_known(con, PF)  # Could be an actual Hunter pet.


def test_known_active_aura_survives_other_unknown_state_and_incomplete_stream(
    con: duckdb.DuckDBPyConnection,
) -> None:
    con.execute(
        "INSERT INTO stream_coverage "
        "(report_code,fight_id,actor_id,direction,status,"
        "boundary_ambiguities,multiplicity_mismatches) "
        "VALUES ('R',3,5,'target','complete',0,0)"
    )
    for ts, kind in [(2000, "applybuff"), (4000, "removebuff")]:
        con.execute(
            "INSERT INTO events "
            "(report_code,fight_id,target_id,ability_game_id,timestamp,type,event_uid,copy_index) "
            "VALUES ('R',3,5,3045,?,?,?,0)",
            [ts, kind, str(ts)],
        )
    states = metrics.aura_states(con, PF, 5, [3045, 6150], None)
    assert states.value == ((1000, 2000, None), (2000, 4000, True), (4000, 9000, None))
    con.execute("UPDATE stream_coverage SET status='missing'")
    assert metrics.aura_states(con, PF, 5, [3045, 6150], None).value is None


def test_family_uses_same_pet_and_owner_without_importing_other_fight_casts(
    con: duckdb.DuckDBPyConnection,
) -> None:
    con.execute(
        "INSERT INTO abilities (report_code,game_id,name) "
        "VALUES ('R',3009,'Claw'),('R',23110,'Dash')"
    )
    con.execute(
        "INSERT INTO events "
        "(report_code,fight_id,source_id,ability_game_id,type,event_uid,copy_index,timestamp) "
        "VALUES ('R',3,8,3009,'cast','claw',0,2000),('R',4,8,23110,'cast','dash',0,4000)"
    )
    con.execute(
        "INSERT INTO stream_coverage (report_code,fight_id,actor_id,role,owner_actor_id) "
        "VALUES ('R',4,8,'pet',5)"
    )
    pet = PetCategory(8, "Pet", 999, observed("hunter-pet", EvidenceRef("R", 3, 8, "actors")))
    found = _hunter_pet(con, PF, pet)
    assert found.family.value == "Cat"
    assert any(ref.fight_id == 4 for ref in found.family.refs)
    assert found.abilities.value == ((3009, "Claw"),)
    con.execute("UPDATE stream_coverage SET owner_actor_id=6")
    assert _hunter_pet(con, PF, pet).family.value is None
