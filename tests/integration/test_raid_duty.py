"""Counterexamples for action-based duty under direct boss melee pressure."""

from dataclasses import replace
from pathlib import Path

import duckdb
import pytest

from necropsy.analysis.classes.classic_era.combat import _duty
from necropsy.analysis.classes.classic_era.druid import _duties
from necropsy.analysis.context import participant_fights
from necropsy.analysis.encounters import duty
from necropsy.analysis.generic.combat import event_rows
from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import AnalysisDocument, build_document
from necropsy.report.render import build_view, render_playbook, render_report
from necropsy.rules import load_rules
from tests.class_fixture import snapshot
from tests.druid_fixture import snapshot as druid_snapshot


@pytest.mark.parametrize("ability,expected", [("Shred", None), ("Maul", "feral-tank")])
def test_druid_pressure_uses_the_same_ambiguity_guard(
    tmp_path: Path, ability: str, expected: str | None
) -> None:
    archive = druid_snapshot(tmp_path, [ability] * 4)
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE snapshot_meta SET zone_id=2000, partition_id=1")
        con.execute("UPDATE fights SET encounter_id=50663")
        con.execute("UPDATE benchmark_participants SET encounter_id=50663")
        con.execute(
            "INSERT INTO actors (report_code,actor_id,type,game_id) "
            "VALUES ('REPORT1',50,'NPC',12118)"
        )
        for index in range(3):
            con.execute(
                "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,"
                "type,source_id,target_id,amount,raw) "
                "VALUES ('REPORT1',7,?,0,?,'damage',50,1,100,'{\"melee\":true}')",
                [f"pressure-{index}", 5000 + 1000 * index],
            )
        pf = participant_fights(con)[0]
        _, role, _ = _duties(con, pf, event_rows(con, pf), load_rules("classic_era", "druid"))
        assert role.value == expected


@pytest.mark.parametrize("partition", [1, 2, 3])
@pytest.mark.parametrize("ability,expected", [("Bloodthirst", None), ("Shield Slam", "tank")])
def test_pressure_does_not_turn_damage_casts_into_an_assigned_tank_job(
    tmp_path: Path, partition: int, ability: str, expected: str | None
) -> None:
    archive = snapshot(tmp_path, 11, "Protection", ability, "tank")
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        # Deliberately synthetic raid remapping; never a real-evidence receipt.
        con.execute(
            "UPDATE snapshot_meta SET zone_id=2000, zone_name='Molten Core', partition_id=?",
            [partition],
        )
        con.execute("UPDATE fights SET encounter_id=50663, name='Lucifron'")
        con.execute("UPDATE benchmark_participants SET encounter_id=50663, boss='Lucifron'")
        con.execute("UPDATE actors SET game_id=12118 WHERE actor_id=50")
        pf = next(p for p in participant_fights(con) if p.kind == "you")
        events = event_rows(con, pf)
        actions = load_rules("classic_era", "classes")["Warrior"]
        signals, role = _duty(con, pf, events, actions)
        assert signals.value == (("dps",) if ability == "Bloodthirst" else ("tank",))
        assert role.value == ("dps" if partition == 3 and ability == "Bloodthirst" else expected)
        assert len(duty.boss_melee(con, pf, events)) == 4
        assert not duty.applies(con, replace(pf, encounter_id=51118))
        context = duty.context(con, pf)
        assert context["melee_events"].value == 4
        assert context["melee_events"].claim == "complete"
        assert context["observed_melee_times_s"].value == [2, 4, 6, 8]
        # Incoming pressure survives partial streams, but its total does not.
        con.execute(
            "UPDATE stream_coverage SET status='incomplete' WHERE actor_id=1 AND direction='target'"
        )
        partial = duty.context(con, pf)
        assert partial["melee_events"].value is None
        assert partial["observed_melee_times_s"].value == [2, 4, 6, 8]
        con.execute("UPDATE stream_coverage SET status='complete'")
        # Trash, outgoing swings and another actor's boss hits do not count.
        con.execute("UPDATE actors SET game_id=11671 WHERE actor_id=50")
        assert duty.boss_melee(con, pf, events) == []
        con.execute("UPDATE actors SET game_id=12118 WHERE actor_id=50")
        if partition == 3:
            return
        doc = build_document(con)
        AnalysisDocument.model_validate(doc)
        boss = doc["bosses"][0]
        assert boss["playbook"]["duty_context"]["melee_events"]["value"] == 4
        if expected is None:
            assert boss["subject"] is None
            assert boss["playbook"]["comparisons"] == []
            assert boss["playbook"]["excluded_subject"]["combat"]["role"]["value"] is None
        view = build_view(doc, "0" * 64)
        for page in (render_report(view), render_playbook(view)):
            assert "Recorded boss melee events against you: 4." in page
            assert "does not establish assigned tank duty" in page
