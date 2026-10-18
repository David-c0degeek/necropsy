"""Coverage queries: may an analysis treat a missing event as "did not happen"?

A stream fetched to its terminal page is not automatically trustworthy: a
page-boundary ambiguity or a multiplicity disagreement with an overlapping
stream also withholds it. Callers must report UNKNOWN when this returns False.
"""

from __future__ import annotations

import duckdb

from necropsy.snapshot.model import ActorRole, Direction


def has_complete_encounter_coverage(
    con: duckdb.DuckDBPyConnection,
    report_code: str,
    fight_id: int,
    role: ActorRole = ActorRole.ENCOUNTER,
) -> bool:
    """A filtered critical stream cannot certify unrestricted encounter absence."""
    if role not in {ActorRole.ENCOUNTER, ActorRole.CRITICAL}:
        raise ValueError("encounter coverage requires an actorless event role")
    row = con.execute(
        """SELECT count(*), count(*) FILTER (
               WHERE status='complete' AND boundary_ambiguities=0
                 AND multiplicity_mismatches=0)
           FROM stream_coverage
           WHERE report_code=? AND fight_id=? AND actor_id IS NULL
             AND direction='all' AND role=?""",
        [report_code, fight_id, role.value],
    ).fetchone()
    return row == (1, 1)


def has_complete_coverage(
    con: duckdb.DuckDBPyConnection,
    report_code: str,
    fight_id: int,
    actor_id: int,
    direction: Direction,
) -> bool:
    row = con.execute(
        """
        SELECT count(*) AS streams,
               count(*) FILTER (WHERE status = 'complete'
                                 AND boundary_ambiguities = 0
                                 AND multiplicity_mismatches = 0) AS trusted
        FROM stream_coverage
        WHERE report_code = ? AND fight_id = ? AND actor_id = ? AND direction = ?
        """,
        [report_code, fight_id, actor_id, direction.value],
    ).fetchone()
    assert row is not None
    streams, trusted = row
    return bool(streams) and streams == trusted


def has_complete_encounter_event_set(
    con: duckdb.DuckDBPyConnection, report_code: str, fight_id: int
) -> bool:
    """The merged maximum-multiplicity union must contain no extra actor/critical rows.

    Ingest retains at least every occurrence in the All stream. Equal counts
    therefore prove that the union adds no other identities or copies. A trusted
    scope alone cannot establish this: a row absent from All has no overlapping
    multiplicity to disagree with. Missing count metadata withholds this proof.
    """
    if not has_complete_encounter_coverage(con, report_code, fight_id):
        return False
    row = con.execute(
        """SELECT raw_events,
               (SELECT count(*) FROM events e
                WHERE e.report_code=s.report_code AND e.fight_id=s.fight_id)
           FROM stream_coverage s
           WHERE report_code=? AND fight_id=? AND actor_id IS NULL
             AND direction='all' AND role='encounter'""",
        [report_code, fight_id],
    ).fetchone()
    return row is not None and type(row[0]) is int and row[0] >= 0 and row[0] == row[1]
