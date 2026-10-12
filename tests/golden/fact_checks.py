"""Fact checkers: compute golden facts from the analysis database.

Each checker names the database scope it needs: the committed 12-fight subset
(fast suite) or the full export (golden suite). A fact is `verified-against-raw`
only if a checker computes it from raw-derived data and it matches.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

import duckdb

from necropsy.analysis.context import ParticipantFight, owned_pets, participant_fights
from necropsy.analysis.evidence import Faction
from necropsy.analysis.generic import environment, metrics

Scope = Literal["subset", "full"]
Checker = Callable[[duckdb.DuckDBPyConnection], Any]

SUBSET_BOSSES = ("Patchwerk", "Grobbulus", "Gothik the Harvester", "Kel'Thuzad")
NAXX_BOSSES = (
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
)


@dataclass(frozen=True)
class FactCheck:
    fact_id: str
    scope: Scope
    compute: Checker


CHECKS: dict[str, FactCheck] = {}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def check(fact_id: str, scope: Scope) -> Callable[[Checker], Checker]:
    def register(fn: Checker) -> Checker:
        if fact_id in CHECKS:
            raise ValueError(f"duplicate checker {fact_id}")
        CHECKS[fact_id] = FactCheck(fact_id, scope, fn)
        return fn

    return register


def _participant(con: duckdb.DuckDBPyConnection, boss: str, player: str) -> ParticipantFight:
    found = [p for p in participant_fights(con) if p.boss == boss and p.player == player]
    if len(found) != 1:
        raise LookupError(f"{player} on {boss}: {len(found)} participant fights")
    return found[0]


def _top(con: duckdb.DuckDBPyConnection, boss: str) -> list[ParticipantFight]:
    return [p for p in participant_fights(con) if p.boss == boss and p.kind == "top"]


def _casts_named(con: duckdb.DuckDBPyConnection, pf: ParticipantFight, name: str) -> int:
    ids = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT game_id FROM abilities WHERE report_code = ? AND name = ?",
            [pf.report_code, name],
        ).fetchall()
    ]
    times = metrics.cast_times(con, pf, pf.actor_id, ids)
    if times.value is None:
        raise LookupError(f"cast list unknown for {pf.player}")
    return len(times.value)


def _wf(pf: ParticipantFight, con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    finding = environment.windfury(con, pf)
    return {"status": finding.status.name, "extraAttacks": finding.extra_attacks.value}


def _dps(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> float:
    actors = [pf.actor_id] + [p.actor_id for p in owned_pets(con, pf)]
    by_ability = metrics.damage_by_ability(con, pf, actors)
    if by_ability.value is None:
        raise LookupError(f"damage unknown for {pf.player}")
    return round(sum(by_ability.value.values()) / pf.duration_ms * 1000.0, 2)


def _faction_split(pfs: list[ParticipantFight], con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    counts = Counter(environment.faction(con, pf).value for pf in pfs)
    if None in counts:
        raise LookupError(f"{counts[None]} participants with unknown faction")
    return {
        "alliance": counts.get(Faction.ALLIANCE, 0),
        "horde": counts.get(Faction.HORDE, 0),
    }


def _raptor_checker(player: str) -> Checker:
    def compute(con: duckdb.DuckDBPyConnection) -> Any:
        return _casts_named(con, _participant(con, "Patchwerk", player), "Raptor Strike")

    return compute


for _player in ("Smcadogx", "Charies", "Andrenn", "Xert", "Xal"):
    check(f"patchwerk.{slug(_player)}.raptor-casts", "subset")(_raptor_checker(_player))


@check("patchwerk.smcadogx.faction", "subset")
def _smcadogx_faction(con: duckdb.DuckDBPyConnection) -> Any:
    value = environment.faction(con, _participant(con, "Patchwerk", "Smcadogx")).value
    return None if value is None else value.value


@check("patchwerk.smcadogx.race", "subset")
def _smcadogx_race(con: duckdb.DuckDBPyConnection) -> Any:
    finding = environment.race(con, _participant(con, "Patchwerk", "Smcadogx"))
    spells = {
        r[0]
        for r in con.execute(
            "SELECT DISTINCT e.ability_game_id FROM events e WHERE e.event_uid IN "
            "(SELECT unnest(?::VARCHAR[]))",
            [[uid for ref in finding.race.refs for uid, _ in ref.event_ids]],
        ).fetchall()
    }
    return {
        "race": finding.race.value,
        "evidence": finding.status.name,
        "spell": spells.pop() if len(spells) == 1 else sorted(spells),
    }


@check("patchwerk.smcadogx.windfury", "subset")
def _patchwerk_wf(con: duckdb.DuckDBPyConnection) -> Any:
    return _wf(_participant(con, "Patchwerk", "Smcadogx"), con)


@check("grobbulus.smcadogx.windfury", "subset")
def _grobbulus_wf(con: duckdb.DuckDBPyConnection) -> Any:
    return _wf(_participant(con, "Grobbulus", "Smcadogx"), con)


@check("patchwerk.alliance-comparators.windfury", "subset")
def _alliance_wf(con: duckdb.DuckDBPyConnection) -> Any:
    return {
        p: environment.windfury(con, _participant(con, "Patchwerk", p)).status.name
        for p in ("Charies", "Andrenn", "Xert", "Xal")
    }


@check("grobbulus.haplina.pet-death", "subset")
def _snape_death(con: duckdb.DuckDBPyConnection) -> Any:
    pf = _participant(con, "Grobbulus", "Haplina")
    snape = [p for p in owned_pets(con, pf) if p.name == "Snape"]
    found = metrics.deaths(con, pf, snape[0].actor_id)
    if found.deaths.value is None or not found.complete:
        raise LookupError("Snape deaths unknown")
    return round(found.deaths.value[0].t_s, 3)


@check("grobbulus.haplina.pet-death-count", "subset")
def _snape_death_count(con: duckdb.DuckDBPyConnection) -> Any:
    pf = _participant(con, "Grobbulus", "Haplina")
    snape = [p for p in owned_pets(con, pf) if p.name == "Snape"]
    found = metrics.deaths(con, pf, snape[0].actor_id)
    if found.deaths.value is None or not found.complete:
        raise LookupError("Snape deaths unknown")
    return len(found.deaths.value)


@check("haplina.talents", "subset")
def _haplina_talents(con: duckdb.DuckDBPyConnection) -> Any:
    return environment.talents(con, _participant(con, "Patchwerk", "Haplina")).value


def _boss_checkers(boss: str) -> tuple[Checker, Checker, Checker]:
    def kill_duration(con: duckdb.DuckDBPyConnection) -> Any:
        return _participant(con, boss, "Haplina").duration_ms / 1000.0

    def dps(con: duckdb.DuckDBPyConnection) -> Any:
        return _dps(con, _participant(con, boss, "Haplina"))

    def faction_split(con: duckdb.DuckDBPyConnection) -> Any:
        return _faction_split(_top(con, boss), con)

    return kill_duration, dps, faction_split


for _boss in NAXX_BOSSES:
    _scope: Scope = "subset" if _boss in SUBSET_BOSSES else "full"
    _kill, _dps_check, _split = _boss_checkers(_boss)
    check(f"{slug(_boss)}.haplina.kill-duration", _scope)(_kill)
    check(f"{slug(_boss)}.haplina.dps", _scope)(_dps_check)
    check(f"{slug(_boss)}.top5.faction-split", "full")(_split)


@check("cohort.faction-split", "full")
def _cohort_faction(con: duckdb.DuckDBPyConnection) -> Any:
    return _faction_split([p for p in participant_fights(con) if p.kind == "top"], con)


def matches(expected: Any, actual: Any, tolerance: float | None) -> bool:
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and set(expected) == set(actual)
            and all(matches(expected[k], actual[k], tolerance) for k in expected)
        )
    if isinstance(expected, bool) or not isinstance(expected, int | float):
        return bool(expected == actual)
    if not isinstance(actual, int | float):
        return False
    return abs(expected - actual) <= (tolerance or 0)
