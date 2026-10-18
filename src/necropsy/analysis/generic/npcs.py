"""Shared report NPC identity and exact fight-level singleton qualification."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import duckdb

from necropsy.analysis.context import ParticipantFight

type Catalog = dict[int, set[tuple[str | None, int | None, str | None]]]


def identity(actors: Catalog, actor: int | None, wanted: tuple[int, ...]) -> bool | None:
    identities = actors.get(actor) if actor is not None else None
    if not identities or len(identities) != 1:
        return None
    kind, game_id, _ = next(iter(identities))
    if kind is None:
        return None
    if kind != "NPC":
        return False
    return game_id in wanted if game_id is not None else None


def fight_roster(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight
) -> list[dict[str, Any]] | None:
    rows = con.execute(
        "SELECT enemy_npcs FROM fights WHERE report_code=? AND fight_id=?",
        [pf.report_code, pf.fight_id],
    ).fetchall()
    if len(rows) != 1:
        return None
    raw = rows[0][0]
    roster = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(roster, list) or any(not isinstance(row, dict) for row in roster):
        return None
    return roster


def cardinalities(
    con: duckdb.DuckDBPyConnection, pf: ParticipantFight, actors: Catalog
) -> dict[int, int]:
    """Require exact raw roster cardinality bound to one normalized NPC identity."""
    roster = fight_roster(con, pf)
    if roster is None:
        return {}
    by_actor: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in roster:
        actor = row.get("id")
        if type(actor) is not int or actor < 1:
            return {}
        by_actor[actor].append(row)
    result = {}
    for actor, entries in by_actor.items():
        if len(entries) != 1:
            continue
        entry = entries[0]
        game_id, count = entry.get("gameID"), entry.get("instanceCount")
        identities = actors.get(actor, set())
        if (
            type(game_id) is int
            and game_id > 0
            and type(count) is int
            and count >= 1
            and len(identities) == 1
            and next(iter(identities))[:2] == ("NPC", game_id)
        ):
            result[actor] = count
    return result


def singletons(con: duckdb.DuckDBPyConnection, pf: ParticipantFight, actors: Catalog) -> set[int]:
    """An unnumbered target needs positive, unambiguous fight-level cardinality."""
    return {actor for actor, count in cardinalities(con, pf, actors).items() if count == 1}
