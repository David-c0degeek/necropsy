"""Fights to analyze and the actors in them, resolved from the database."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from necropsy.analysis.evidence import CoverageRef
from necropsy.normalize.coverage import has_complete_coverage
from necropsy.snapshot.model import Direction


class ContextError(Exception):
    """A participant cannot be resolved to exactly one actor."""


@dataclass(frozen=True, slots=True)
class ParticipantFight:
    """One selected Hunter in one fight: the subject's own fight or a cohort entry."""

    report_code: str
    fight_id: int
    actor_id: int
    player: str
    server: str | None
    kind: str
    boss: str
    encounter_id: int
    leaderboard_position: int | None
    start_time: int
    end_time: int
    kill: bool | None

    @property
    def duration_ms(self) -> int:
        return self.end_time - self.start_time

    def relative_s(self, timestamp: int) -> float:
        return (timestamp - self.start_time) / 1000.0


@dataclass(frozen=True, slots=True)
class Pet:
    actor_id: int
    name: str
    game_id: int | None


def realm_key(name: str | None) -> str | None:
    """Rankings spell realms "Pyrewood Village"; report actors spell them "PyrewoodVillage"."""
    if name is None:
        return None
    return "".join(ch for ch in name.casefold() if ch.isalnum())


def _resolve_actor(
    con: duckdb.DuckDBPyConnection, report: str, fight: int, player: str, server: str | None
) -> int:
    rows = con.execute(
        """
        SELECT DISTINCT c.actor_id, a.server
        FROM stream_coverage c
        LEFT JOIN actors a ON a.report_code = c.report_code AND a.actor_id = c.actor_id
        WHERE c.report_code = ? AND c.fight_id = ? AND c.role = 'player'
          AND c.actor_name = ? AND c.actor_id IS NOT NULL
        """,
        [report, fight, player],
    ).fetchall()
    if server is not None and len(rows) > 1:
        rows = [r for r in rows if realm_key(r[1]) == realm_key(server)]
    if len(rows) != 1:
        raise ContextError(
            f"{player!r} in {report}/{fight} resolves to {len(rows)} exported actors"
        )
    actor_id, actor_server = rows[0]
    if (
        server is not None
        and actor_server is not None
        and realm_key(actor_server) != realm_key(server)
    ):
        raise ContextError(
            f"{player!r} in {report}/{fight}: actor server {actor_server!r} != {server!r}"
        )
    return int(actor_id)


def participant_fights(con: duckdb.DuckDBPyConnection) -> list[ParticipantFight]:
    rows = con.execute(
        """
        SELECT p.report_code, p.fight_id, p.player, p.server, p.kind, p.boss, p.encounter_id,
               p.leaderboard_position, f.start_time, f.end_time, f.kill
        FROM benchmark_participants p
        JOIN fights f ON f.report_code = p.report_code AND f.fight_id = p.fight_id
        ORDER BY p.encounter_id, p.kind DESC, p.leaderboard_position NULLS FIRST, p.player
        """
    ).fetchall()
    result: list[ParticipantFight] = []
    for code, fight, player, server, kind, boss, encounter, position, start, end, kill in rows:
        result.append(
            ParticipantFight(
                report_code=code,
                fight_id=int(fight),
                actor_id=_resolve_actor(con, code, int(fight), player, server),
                player=player,
                server=server,
                kind=kind,
                boss=boss,
                encounter_id=int(encounter),
                leaderboard_position=position,
                start_time=int(start),
                end_time=int(end),
                kill=kill,
            )
        )
    return result


def owned_pets(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> list[Pet]:
    """Actors exported as pets of this participant (traps and summons included)."""
    rows = con.execute(
        """
        SELECT DISTINCT c.actor_id, c.actor_name, a.game_id
        FROM stream_coverage c
        LEFT JOIN actors a ON a.report_code = c.report_code AND a.actor_id = c.actor_id
        WHERE c.report_code = ? AND c.fight_id = ? AND c.role = 'pet'
          AND c.owner_actor_id = ?
        ORDER BY c.actor_id
        """,
        [pf.report_code, pf.fight_id, pf.actor_id],
    ).fetchall()
    return [Pet(int(r[0]), r[1], None if r[2] is None else int(r[2])) for r in rows]


def coverage(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, actor_id: int, direction: Direction
) -> CoverageRef:
    """The coverage decision for one stream, recorded on COMPLETE claims for audit."""
    return CoverageRef(
        report_code=pf.report_code,
        fight_id=pf.fight_id,
        actor_id=actor_id,
        direction=direction.value,
        trusted=has_complete_coverage(con, pf.report_code, pf.fight_id, actor_id, direction),
    )


def pet_listing_known(con: duckdb.DuckDBPyConnection, pf: ParticipantFight) -> bool:
    """False when the export lacks this participant's pet listing (pets are then UNKNOWN)."""
    row = con.execute(
        """
        SELECT count(*) FROM stream_coverage
        WHERE report_code = ? AND fight_id = ? AND role = 'pet-discovery'
          AND owner_actor_id = ?
        """,
        [pf.report_code, pf.fight_id, pf.actor_id],
    ).fetchone()
    return row is not None and row[0] == 0
