"""Control application evidence keeps casts, coverage and NPC instances distinct."""

import json
from pathlib import Path

import duckdb
import pytest

from necropsy.analysis.context import participant_fights
from necropsy.analysis.encounters.control import applications
from necropsy.normalize.ingest import ingest
from tests.class_fixture import snapshot


@pytest.mark.parametrize(
    "case,expected",
    [
        ("success", 2),
        ("cast", 0),
        ("begin", 0),
        ("remove", 0),
        ("incoming", 0),
        ("other-spell", 0),
        ("other-npc", 0),
        ("player", 0),
        ("missing-target", None),
        ("missing-type", None),
        ("missing-game", None),
        ("conflict", None),
        ("partial", None),
        ("missing-ability", None),
        ("missing-instance", 2),
        ("missing-ability-wrong-npc", 0),
        ("wrong-ability-missing-target", 0),
    ],
)
def test_control_counts_only_source_owned_applications_to_evidenced_npcs(
    tmp_path: Path, case: str, expected: int | None
) -> None:
    archive = snapshot(tmp_path, 10, "Destruction", "Shadow Bolt", "dps", partial=case == "partial")
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE snapshot_meta SET zone_id=2000, partition_id=1")
        con.execute("UPDATE fights SET encounter_id=50666")
        con.execute("UPDATE benchmark_participants SET encounter_id=50666")
        con.execute(
            "UPDATE actors SET type=?,game_id=? WHERE actor_id=50",
            [
                None if case == "missing-type" else "Player" if case == "player" else "NPC",
                None
                if case == "missing-game"
                else 12057
                if case in ("other-npc", "missing-ability-wrong-npc")
                else 12099,
            ],
        )
        if case == "conflict":
            con.execute(
                "INSERT INTO actors (report_code,actor_id,type,game_id) "
                "VALUES ('REPORT1',50,'NPC',12057)"
            )
        for index, ability in enumerate((710, 18647)):
            con.execute(
                "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,"
                "type,source_id,target_id,ability_game_id,raw) "
                "VALUES ('REPORT1',7,?,0,?,?,?,?,?,?)",
                [
                    f"control-{index}",
                    5000 + index * 1000,
                    {"cast": "cast", "begin": "begincast", "remove": "removedebuff"}.get(
                        case, "applydebuff"
                    ),
                    2 if case == "incoming" else 1,
                    999 if case in ("missing-target", "wrong-ability-missing-target") else 50,
                    None
                    if case in ("missing-ability", "missing-ability-wrong-npc")
                    else 8994
                    if case in ("other-spell", "wrong-ability-missing-target")
                    else ability,
                    json.dumps({} if case == "missing-instance" else {"targetInstance": index + 1}),
                ],
            )
        pf = next(p for p in participant_fights(con) if p.kind == "you")
        (control,) = applications(con, pf)
        assert control.applications.value == expected
        if case in ("success", "partial", "missing-instance"):
            assert control.observations.value == (
                (5, 50, None if case == "missing-instance" else 1, 710),
                (6, 50, None if case == "missing-instance" else 2, 18647),
            )
        assert "uptime" in control.limitation and "not a failed duty" in control.limitation
        con.execute("UPDATE snapshot_meta SET subject_class_id=7")
        assert applications(con, pf) == ()
        con.execute("UPDATE snapshot_meta SET subject_class_id=10,partition_id=3")
        assert applications(con, pf) == ()
        con.execute("UPDATE snapshot_meta SET partition_id=1,zone_id=2006")
        assert applications(con, pf) == ()
