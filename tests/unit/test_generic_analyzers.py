"""Generic analyzers over small synthetic snapshots."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from necropsy.analysis.context import (
    ContextError,
    owned_pets,
    participant_fights,
    pet_listing_known,
)
from necropsy.analysis.encounters import EncounterRules
from necropsy.analysis.encounters.findings import target_integrity
from necropsy.analysis.evidence import EvidenceLevel, Faction, RaceStatus, WindfuryStatus
from necropsy.analysis.generic import cohort, environment, metrics, targets
from necropsy.analysis.generic.environment import _attribute
from necropsy.normalize.ingest import ingest
from tests.snapshot_builder import FIGHT, SnapshotSpec, build, ev, page

PLAYER = "player_1_Hunter"
PET = "pet_2_Cat"
Streams = dict[str, list[dict[str, Any] | None]]


def _streams(
    source: list[dict[str, Any]],
    target: list[dict[str, Any]] | None = None,
    source_complete: bool = True,
) -> Streams:
    return {
        f"{PLAYER}/source": [page(source, None if source_complete else 99999.0)],
        f"{PLAYER}/target": [page(target or [])],
        f"{PET}/source": [page([ev(10, source=2, target=50)])],
        f"{PET}/target": [page([])],
    }


@pytest.fixture
def db(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[duckdb.DuckDBPyConnection]:
    spec: SnapshotSpec = request.param
    path = build(tmp_path / "s.zip", spec)
    out = tmp_path / "a.duckdb"
    ingest(path, out)
    con = duckdb.connect(str(out), read_only=True)
    yield con
    con.close()


def _spec(
    source: list[dict[str, Any]], target: list[dict[str, Any]] | None = None, **kw: Any
) -> SnapshotSpec:
    complete = kw.pop("source_complete", True)
    return SnapshotSpec(streams=_streams(source, target, complete), **kw)


WF = 10610
COMBATANT = {
    "timestamp": 0,
    "type": "combatantinfo",
    "sourceID": 1,
    "fight": FIGHT,
    "faction": 0,
    "specID": 0,
    "talents": [{"id": 20}, {"id": 31}, {"id": 0}],
    "auras": [
        {"source": 1, "ability": 23768, "stacks": 1, "name": "Sayge"},
        {"source": 5, "ability": 22888, "stacks": 1, "name": "Ony"},
    ],
    "gear": [{"id": 100, "permanentEnchant": 664}, {"id": 0}, {"id": 200}],
}


def _proc(ts: int, n: int = 1) -> dict[str, Any]:
    return ev(ts, "extraattacks", target=1, abilityGameID=WF, extraAttacks=n)


def _swing(ts: int, amount: int = 1000) -> dict[str, Any]:
    return ev(ts, abilityGameID=1, amount=amount, tag=ts)


ENV_EVENTS = [
    COMBATANT,
    ev(5, "cast", target=1, abilityGameID=20572),
    _proc(100),
    _swing(150, 900),
    _swing(2000),
]


@pytest.mark.parametrize("db", [_spec(ENV_EVENTS)], indirect=True)
def test_environment_profile(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    profile = environment.environment_profile(db, pf)
    assert profile.faction.value is Faction.HORDE
    assert profile.faction.level is EvidenceLevel.OBSERVED
    assert profile.race.race.value == "Orc"
    assert profile.race.status is RaceStatus.RACIAL_EVENT_CONFIRMED
    assert profile.talents.value == "20/31/0"
    assert profile.darkmoon_faire.value == "Sayge's Dark Fortune of Damage"
    assert profile.world_buffs.value == ("Rallying Cry of the Dragonslayer",)
    assert [g.item_id for g in profile.gear.value or ()] == [100, 0, 200]
    wf = profile.windfury
    assert wf.status is WindfuryStatus.CONFIRMED
    assert (wf.procs.value, wf.extra_attacks.value) == (1, 1)
    assert wf.attributed_damage.value == 900
    assert wf.attributed_damage.level is EvidenceLevel.INFERRED
    assert profile.kill_duration_ms.value == 100000
    assert profile.kill_duration_ms.level is EvidenceLevel.DERIVED


@pytest.mark.parametrize("db", [_spec([ev(1)])], indirect=True)
def test_unknowns_without_data(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    profile = environment.environment_profile(db, pf)
    assert profile.race.status is RaceStatus.UNKNOWN
    assert profile.race.race.value is None
    assert profile.talents.level is EvidenceLevel.UNKNOWN
    assert profile.darkmoon_faire.level is EvidenceLevel.UNKNOWN
    assert profile.windfury.status is WindfuryStatus.NOT_OBSERVED
    assert profile.windfury.attributed_damage.level is EvidenceLevel.DERIVED
    assert profile.windfury.attributed_damage.value == 0
    assert all(c.trusted for c in profile.windfury.attributed_damage.coverage)


@pytest.mark.parametrize("db", [_spec([ev(1)], source_complete=False)], indirect=True)
def test_incomplete_stream_withholds_absence(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    wf = environment.windfury(db, pf)
    assert wf.status is WindfuryStatus.UNKNOWN
    assert wf.procs.level is EvidenceLevel.UNKNOWN
    assert metrics.cast_times(db, pf, pf.actor_id, [75]).level is EvidenceLevel.UNKNOWN
    assert metrics.damage_by_ability(db, pf, [pf.actor_id]).level is EvidenceLevel.UNKNOWN


@pytest.mark.parametrize(
    "db", [_spec([_proc(100), _swing(150)], source_complete=False)], indirect=True
)
def test_confirmed_windfury_with_partial_coverage_has_unknown_counts(
    db: duckdb.DuckDBPyConnection,
) -> None:
    wf = environment.windfury(db, participant_fights(db)[0])
    assert wf.status is WindfuryStatus.CONFIRMED
    assert wf.procs.level is EvidenceLevel.UNKNOWN
    assert wf.attributed_damage.level is EvidenceLevel.UNKNOWN


def _rows(events: list[tuple[int, int]]) -> list[tuple[Any, ...]]:
    return [(ts, n, f"u{ts}", 0) for ts, n in events]


@pytest.mark.parametrize(
    ("procs", "swings", "expected"),
    [
        ([(100, 1)], [(150, 900)], (1, 0, 0, 900)),
        # an ordinary swing inside the window makes the match ambiguous
        ([(100, 1)], [(150, 900), (400, 800)], (0, 1, 0, 0)),
        # no swing inside the window
        ([(100, 1)], [(900, 800)], (0, 0, 1, 0)),
        # overlapping windows share a swing: both procs ambiguous
        ([(100, 1), (300, 1)], [(350, 900)], (0, 2, 0, 0)),
        # same-timestamp swing counts as inside the window
        ([(100, 1)], [(100, 700)], (1, 0, 0, 700)),
        # two extra attacks need two candidate swings
        ([(100, 2)], [(120, 500)], (0, 0, 1, 0)),
        ([(100, 2)], [(120, 500), (130, 600)], (1, 0, 0, 1100)),
    ],
)
def test_windfury_unique_swing_rule(
    procs: list[tuple[int, int]],
    swings: list[tuple[int, int]],
    expected: tuple[int, int, int, int],
) -> None:
    matched, ambiguous, unmatched, damage, used = _attribute(_rows(procs), _rows(swings), 400)
    assert (matched, ambiguous, unmatched, damage) == expected
    assert len(used) == len(set(used))


@pytest.mark.parametrize("db", [_spec([_proc(100), _swing(150), _swing(400)])], indirect=True)
def test_confirmed_windfury_without_unique_match_has_unknown_estimate(
    db: duckdb.DuckDBPyConnection,
) -> None:
    wf = environment.windfury(db, participant_fights(db)[0])
    assert wf.status is WindfuryStatus.CONFIRMED
    assert (wf.matched_procs, wf.ambiguous_procs) == (0, 1)
    assert wf.attributed_damage.level is EvidenceLevel.UNKNOWN


AURA = 3045
UPTIME_TARGET = [
    ev(20000, "applybuff", source=1, target=1, abilityGameID=AURA),
    ev(35000, "removebuff", source=1, target=1, abilityGameID=AURA),
    ev(90000, "applybuff", source=1, target=1, abilityGameID=AURA),
]


@pytest.mark.parametrize("db", [_spec([ev(1)], UPTIME_TARGET)], indirect=True)
def test_aura_uptime_closes_open_interval_at_fight_end(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    assert metrics.aura_uptime(db, pf, pf.actor_id, [AURA], frozenset()).value == 25.0
    assert metrics.aura_uptime(db, pf, pf.actor_id, [AURA], None).value == 25.0
    assert metrics.aura_uptime(db, pf, pf.actor_id, [999], None).level is EvidenceLevel.UNKNOWN


DEATH_TARGET = [
    ev(40000, source=50, target=1, abilityGameID=28241, amount=500),
    {
        "timestamp": 41000,
        "type": "death",
        "sourceID": -1,
        "targetID": 1,
        "fight": FIGHT,
        "abilityGameID": 0,
        "killerID": 50,
        "killingAbilityGameID": 28241,
    },
]


@pytest.mark.parametrize("db", [_spec([ev(1)], DEATH_TARGET)], indirect=True)
def test_deaths_with_recent_hits(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    found = metrics.deaths(db, pf, pf.actor_id)
    assert found.complete
    assert found.deaths.value is not None
    death = found.deaths.value[0]
    assert (death.t_s, death.killer_id, death.killing_ability_id) == (41.0, 50, 28241)
    assert [h.amount for h in death.recent_hits] == [500]
    window = metrics.activity_window(db, pf, pf.actor_id).value
    assert window is not None and window.first_damage_s == 0.001


def _npc(actor_id: int, game_id: int | None) -> dict[str, Any]:
    return {
        "id": actor_id,
        "name": f"Mob {actor_id}",
        "type": "NPC",
        "gameID": game_id,
        "petOwner": None,
        "icon": "z",
    }


LISTED = [_npc(50, 5000), _npc(51, 5100)]


@pytest.mark.parametrize(
    "db", [_spec([ev(1, target=50), ev(2, target=51)], extra_actors=LISTED)], indirect=True
)
def test_target_split_without_native_rule_is_unknown(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    split = targets.damage_by_target(db, pf, [pf.actor_id], None)
    assert split.by_target.value is not None and len(split.by_target.value) == 2
    assert split.native_damage.level is EvidenceLevel.UNKNOWN
    ruled = targets.damage_by_target(db, pf, [pf.actor_id], lambda gid, name: gid == 5000)
    assert (ruled.native_damage.value, ruled.foreign_damage.value) == (100, 100)
    assert ruled.unclassified == ()


@pytest.mark.parametrize(
    ("db", "label"),
    [
        (_spec([ev(1, target=50), ev(2, target=None)], extra_actors=LISTED), "no target"),
        (_spec([ev(1, target=50), ev(2, target=777)], extra_actors=LISTED), "actor 777"),
        (
            _spec([ev(1, target=50), ev(2, target=52)], extra_actors=[*LISTED, _npc(52, None)]),
            "Mob 52",
        ),
    ],
    indirect=["db"],
)
def test_unclassifiable_targets_make_the_split_unknown(
    db: duckdb.DuckDBPyConnection, label: str
) -> None:
    pf = participant_fights(db)[0]
    split = targets.damage_by_target(db, pf, [pf.actor_id], lambda gid, name: gid == 5000)
    assert split.by_target.value is not None
    assert split.native_damage.level is EvidenceLevel.UNKNOWN
    assert split.foreign_damage.level is EvidenceLevel.UNKNOWN
    assert [t.damage for t in split.unclassified] == [100]
    rules = EncounterRules(1, "Boss", frozenset(), frozenset(), frozenset({5000}), "r")
    found = target_integrity(db, pf, rules, [pf.actor_id], "hunter")
    assert found is not None
    assert found.foreign_share_pct.level is EvidenceLevel.UNKNOWN
    assert found.foreign_targets == ()
    assert found.unclassified_targets == ((label, 100),)


@pytest.mark.parametrize("db", [_spec([ev(1)])], indirect=True)
def test_pets_and_listing(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    assert [p.name for p in owned_pets(db, pf)] == ["Cat"]
    assert pet_listing_known(db, pf)


@pytest.mark.parametrize("db", [_spec([ev(1)], with_pets_json=False)], indirect=True)
def test_missing_pet_listing(db: duckdb.DuckDBPyConnection) -> None:
    assert not pet_listing_known(db, participant_fights(db)[0])


@pytest.mark.parametrize(
    "db",
    [
        _spec(
            [ev(1)],
            participants=[
                {
                    "kind": "top",
                    "boss": "Patchwerk",
                    "encounterID": 51118,
                    "player": "Hunter",
                    "server": "Elsewhere",
                }
            ],
        )
    ],
    indirect=True,
)
def test_participant_on_another_realm_is_rejected(db: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(ContextError, match="server"):
        participant_fights(db)


def test_cohort_distribution_counts_unknowns_separately() -> None:
    from necropsy.analysis.evidence import EvidenceRef, observed, unknown

    ref = EvidenceRef("R", 1, 1, "x")
    dist = cohort.distribution(
        [
            observed("20/31/0", ref),
            observed("20/31/0", ref),
            observed("5/31/15", ref),
            unknown("no data"),
        ]
    )
    assert dist.counts == {"20/31/0": 2, "5/31/15": 1}
    assert (dist.n_known, dist.n_unknown, dist.n_total) == (3, 1, 4)
    assert dist.share("20/31/0") == pytest.approx(2 / 3)
    empty: cohort.Distribution[str] = cohort.distribution([unknown("x")])
    assert empty.share("a") is None


A, B = 4001, 4002


def _aura(ts: int, kind: str, aura: int) -> dict[str, Any]:
    return ev(ts, kind, source=1, target=1, abilityGameID=aura)


OVERLAP = [
    _aura(20000, "applybuff", A),
    _aura(30000, "applybuff", B),
    _aura(40000, "removebuff", A),
    _aura(50000, "removebuff", B),
]


@pytest.mark.parametrize("db", [_spec([ev(1)], OVERLAP)], indirect=True)
def test_overlapping_auras_are_merged(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    union = metrics.aura_uptime(db, pf, pf.actor_id, [A, B], frozenset())
    assert union.value == 30.0
    assert union.coverage and union.coverage[0].direction == "target"
    assert metrics.aura_uptime(db, pf, pf.actor_id, [A], frozenset()).value == 20.0


STACKS = [_aura(10000, "applybuffstack", A), _aura(20000, "removebuff", A)]


@pytest.mark.parametrize("db", [_spec([ev(1)], STACKS)], indirect=True)
def test_stack_events_need_a_settled_state(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    # Without a starting snapshot the stack event shows the aura was already on.
    assert metrics.aura_uptime(db, pf, pf.actor_id, [A], None).value == 20.0
    # A starting snapshot without the aura contradicts the stack event.
    contradiction = metrics.aura_uptime(db, pf, pf.actor_id, [A], frozenset())
    assert contradiction.level is EvidenceLevel.UNKNOWN
    assert metrics.aura_uptime(db, pf, pf.actor_id, [A], frozenset({A})).value == 20.0


LATE = [_aura(-5000, "applybuff", A), _aura(150000, "removebuff", A)]


@pytest.mark.parametrize("db", [_spec([ev(1)], LATE)], indirect=True)
def test_uptime_is_clipped_to_the_fight(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    assert metrics.aura_uptime(db, pf, pf.actor_id, [A], frozenset()).value == 100.0


@pytest.mark.parametrize(
    "db",
    [
        SnapshotSpec(
            streams={
                f"{PLAYER}/source": [page([ev(1)])],
                f"{PLAYER}/target": [page(OVERLAP, 99999.0)],
                f"{PET}/source": [page([])],
                f"{PET}/target": [page([])],
            }
        )
    ],
    indirect=True,
)
def test_uptime_on_partial_target_stream_is_unknown(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    result = metrics.aura_uptime(db, pf, pf.actor_id, [A, B], frozenset())
    assert result.level is EvidenceLevel.UNKNOWN
    assert result.coverage and not result.coverage[0].trusted


def _combatant(faction: int, ts: int = 0) -> dict[str, Any]:
    return {**COMBATANT, "faction": faction, "timestamp": ts, "specID": ts}


@pytest.mark.parametrize("db", [_spec([_combatant(0), _combatant(1, 5)])], indirect=True)
def test_conflicting_faction_fields_are_unknown(db: duckdb.DuckDBPyConnection) -> None:
    result = environment.faction(db, participant_fights(db)[0])
    assert result.level is EvidenceLevel.UNKNOWN
    assert len(result.refs) == 2


@pytest.mark.parametrize("db", [_spec([_combatant(7)])], indirect=True)
def test_unrecognised_faction_code_is_unknown_not_inferred(
    db: duckdb.DuckDBPyConnection,
) -> None:
    result = environment.faction(db, participant_fights(db)[0])
    assert result.level is EvidenceLevel.UNKNOWN
    assert result.rule_id is None


@pytest.mark.parametrize("db", [_spec([_combatant(0)])], indirect=True)
def test_cohort_per_slot_distributions(db: duckdb.DuckDBPyConnection) -> None:
    profile = environment.environment_profile(db, participant_fights(db)[0])
    profiles = [profile]
    assert cohort.gear_slot_distribution(profiles, 0).counts == {100: 1}
    assert cohort.gear_slot_distribution(profiles, 1).counts == {0: 1}
    missing = cohort.gear_slot_distribution(profiles, 9)
    assert (missing.n_known, missing.n_unknown) == (0, 1)
    assert cohort.enchant_distribution(profiles, 0).counts == {664: 1}
    assert cohort.enchant_distribution(profiles, 9).n_unknown == 1
    assert cohort.item_prevalence(profiles).counts == {100: 1, 200: 1}
    seen = cohort.starting_aura_prevalence(profiles, {22888: "Ony buff", 1: "Elixir"})
    assert (seen.counts, seen.n_known) == ({"Ony buff": 1}, 1)


@pytest.mark.parametrize(
    "db",
    [
        _spec(
            [ev(1, target=50), ev(2, target=51), ev(3, target=52), ev(4, target=52)],
            extra_actors=[*LISTED, _npc(52, 5200)],
        )
    ],
    indirect=True,
)
def test_start_trash_is_neither_native_nor_foreign(db: duckdb.DuckDBPyConnection) -> None:
    pf = participant_fights(db)[0]
    rules = EncounterRules(
        1,
        "Boss",
        frozenset(),
        frozenset(),
        frozenset({5000}),
        "r",
        start_trash_game_ids=frozenset({5100}),
    )
    found = target_integrity(db, pf, rules, [pf.actor_id], "hunter")
    assert found is not None
    assert (found.native.value, found.start_trash.value, found.foreign.value) == (100, 100, 200)
    assert found.foreign_share_pct.value == 50.0
    assert found.foreign_targets == (("Mob 52", 200),)
