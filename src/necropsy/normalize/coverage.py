"""Coverage queries: may an analysis treat a missing event as "did not happen"?

A stream fetched to its terminal page is not automatically trustworthy: a
page-boundary ambiguity or a multiplicity disagreement with an overlapping
stream also withholds it. Callers must report UNKNOWN when this returns False.
"""

from __future__ import annotations

import duckdb

from necropsy.snapshot.model import Direction


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
