"""Observed local debuffs cannot invent initial state, assignment or global phases."""

from html import unescape
from pathlib import Path

import duckdb
import pytest

from necropsy.analysis.context import participant_fights
from necropsy.analysis.encounters.effects import actor_effects, mechanic_removals
from necropsy.analysis.generic.metrics import aura_states
from necropsy.normalize.ingest import ingest
from necropsy.report.analysis_json import AnalysisDocument, build_document
from necropsy.report.render import build_view, render_playbook, render_report
from tests.class_fixture import snapshot


@pytest.mark.parametrize("partial", [False, True])
def test_successful_removals_are_effects_not_cast_or_opportunity_counts(
    tmp_path: Path, partial: bool
) -> None:
    archive = snapshot(tmp_path, 4, "Fire", "Fireball", "dps", partial=partial)
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE snapshot_meta SET zone_id=2000, partition_id=1")
        con.execute("UPDATE fights SET encounter_id=50663")
        con.execute("UPDATE benchmark_participants SET encounter_id=50663")
        rows = [
            ("dispel", 1, 2, '{"isBuff":false,"extraAbilityGameID":19703}'),
            ("dispel", 2, 1, '{"isBuff":false,"extraAbilityGameID":19703}'),
            ("dispel", 1, 2, '{"isBuff":true,"extraAbilityGameID":19703}'),
            ("dispel", 1, 2, '{"isBuff":false,"extraAbilityGameID":12345}'),
            ("cast", 1, 2, '{"isBuff":false,"extraAbilityGameID":19703}'),
        ]
        for index, (kind, source, target, raw) in enumerate(rows):
            con.execute(
                "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,"
                "type,source_id,target_id,ability_game_id,raw) "
                "VALUES ('REPORT1',7,?,0,?,?,?,?,475,?)",
                [f"removal-{index}", 5000 + index, kind, source, target, raw],
            )
        pf = next(p for p in participant_fights(con) if p.kind == "you")
        curse, doom, control = mechanic_removals(con, pf)
        assert curse.removals.value == (None if partial else 1)
        assert curse.observations.value == ((5, 2, 475, 19703),)
        assert doom.removals.value == (None if partial else 0)
        assert control.removals.value == (None if partial else 0)
        con.execute("UPDATE snapshot_meta SET partition_id=3")
        assert mechanic_removals(con, pf) == ()


@pytest.mark.parametrize(
    "raw",
    [
        '{"extraAbilityGameID":19703}',
        '{"isBuff":false}',
        '{"isBuff":false,"extraAbilityGameID":"19703"}',
    ],
)
def test_unusable_dispel_metadata_cannot_supply_a_known_zero(tmp_path: Path, raw: str) -> None:
    archive = snapshot(tmp_path, 4, "Fire", "Fireball", "dps")
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE snapshot_meta SET zone_id=2000, partition_id=1")
        con.execute("UPDATE fights SET encounter_id=50663")
        con.execute("UPDATE benchmark_participants SET encounter_id=50663")
        con.execute(
            "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,"
            "type,source_id,target_id,ability_game_id,raw) "
            "VALUES ('REPORT1',7,'unresolved',0,5000,'dispel',1,2,475,?)",
            [raw],
        )
        pf = next(p for p in participant_fights(con) if p.kind == "you")
        curse = mechanic_removals(con, pf)[0]
        assert curse.removals.value is None and curse.observations.value is None


@pytest.mark.parametrize(
    "scenario,expected_affected,expected_unknown",
    [
        ("cycle", 10, 5),
        ("none", 0, 100),
        ("first-remove", 0, 5),
        ("refresh", 90, 10),
        ("partial", None, None),
        ("outgoing", 0, 100),
        ("foreign", 0, 100),
        ("outside", 0, 100),
        ("short", 0, 1),
        ("wrong-kind", 0, 100),
        ("conflicting", 85, 15),
        ("simultaneous", 0, 100),
        ("death", 5, 95),
    ],
)
def test_effect_state_is_bounded_by_actual_actor_transitions(
    tmp_path: Path, scenario: str, expected_affected: float | None, expected_unknown: float | None
) -> None:
    archive = snapshot(tmp_path, 11, "Fury", "Bloodthirst", "dps")
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        con.execute(
            "UPDATE snapshot_meta SET zone_id=2000, zone_name='Molten Core', partition_id=1"
        )
        con.execute("UPDATE fights SET encounter_id=50663, name='Lucifron'")
        con.execute("UPDATE benchmark_participants SET encounter_id=50663, boss='Lucifron'")
        con.execute("UPDATE actors SET game_id=12118 WHERE actor_id=50")
        transitions = {
            "cycle": [(5000, "applydebuff"), (15000, "removedebuff")],
            "partial": [(5000, "applydebuff"), (15000, "removedebuff")],
            "first-remove": [(5000, "removedebuff")],
            "refresh": [(5000, "refreshdebuff"), (10000, "applydebuff")],
            "outgoing": [(5000, "applydebuff")],
            "foreign": [(5000, "applydebuff")],
            "outside": [(-1000, "applydebuff"), (200000, "removedebuff")],
            "wrong-kind": [(5000, "applybuff")],
            "conflicting": [
                (5000, "applydebuff"),
                (10000, "removedebuff"),
                (15000, "refreshdebuff"),
                (20000, "applydebuff"),
            ],
            "simultaneous": [(5000, "applydebuff"), (5000, "removedebuff")],
            "death": [(5000, "applydebuff"), (10000, "death"), (15000, "resurrect")],
        }.get(scenario, [])
        for index, (timestamp, kind) in enumerate(transitions):
            con.execute(
                "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,"
                "type,source_id,target_id,ability_game_id,raw) "
                "VALUES ('REPORT1',7,?,0,?,?,?,?,?, '{}')",
                [
                    f"effect-{index}",
                    timestamp,
                    kind,
                    1 if scenario == "outgoing" else 50,
                    2 if scenario == "outgoing" else 1,
                    12345 if scenario == "foreign" else 19703,
                ],
            )
        if scenario == "partial":
            con.execute(
                "UPDATE stream_coverage SET status='incomplete' "
                "WHERE actor_id=1 AND direction='target'"
            )
        if scenario == "short":
            con.execute("UPDATE fights SET end_time=1000")
        pf = next(p for p in participant_fights(con) if p.kind == "you")
        curse, doom = actor_effects(con, pf)
        assert curse.known_affected_s.value == expected_affected
        assert curse.unknown_state_s.value == expected_unknown
        assert doom.known_affected_s.value == (None if scenario == "partial" else 0)
        if scenario == "partial":
            assert curse.windows.value is None
            assert curse.transitions.value == (
                (5, "applydebuff", 19703),
                (15, "removedebuff", 19703),
            )
            return
        assert curse.windows.value is not None
        if scenario == "cycle":
            assert curse.windows.value == ((0, 5, None), (5, 15, True), (15, 100, False))
            # Historical callers retain their explicit legacy first-event policy.
            assert aura_states(con, pf, 1, [19703], None).value == (
                (0, 5000, False),
                (5000, 15000, True),
                (15000, 100000, False),
            )
            doc = build_document(con)
            AnalysisDocument.model_validate(doc)
            view = build_view(doc, "0" * 64)
            for html in (render_report(view), render_playbook(view)):
                assert (
                    "Lucifron's Curse: 10.00s known affected; 5.00s with unknown state."
                    in unescape(html)
                )
                assert curse.limitation in unescape(html)
                assert curse.source in html
        con.execute("UPDATE snapshot_meta SET partition_id=3")
        assert actor_effects(con, pf) == ()
        con.execute("UPDATE snapshot_meta SET partition_id=1, zone_id=2002")
        assert actor_effects(con, pf) == ()
