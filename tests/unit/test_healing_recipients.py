"""Source-owned healing on a boss is not friendly healing throughput."""

import json
from pathlib import Path

import duckdb
import pytest

from necropsy.analysis.context import participant_fights
from necropsy.analysis.generic.combat import event_rows, event_totals
from necropsy.analysis.generic.healing import recipient_metrics
from necropsy.normalize.ingest import ingest
from tests.class_fixture import snapshot


@pytest.mark.parametrize("unresolved", [False, True])
@pytest.mark.parametrize("partial", [False, True])
def test_friendly_boss_and_unknown_recipients_keep_separate_evidence(
    tmp_path: Path, unresolved: bool, partial: bool
) -> None:
    archive = snapshot(tmp_path, 7, "Holy", "Flash Heal", "healer", partial=partial)
    db = tmp_path / "analysis.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE fights SET friendly_players='[1,2]', friendly_pets='[{\"id\":3}]'")
        con.execute("UPDATE actors SET game_id=14601 WHERE actor_id=50")
        effects: list[tuple[int, int | None, int]] = [
            (1, 50, 2000),
            (1, 2, 100),
            (1, 3, 100),
            (2, 1, 9000),
        ]
        if unresolved:
            effects.append((1, None, 5000))
        for index, (source, target, amount) in enumerate(effects):
            con.execute(
                "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,"
                "type,source_id,target_id,amount,raw) "
                "VALUES ('REPORT1',7,?,0,?,'heal',?,?,?, '{}')",
                [f"recipient-{index}", 10000 + index, source, target, amount],
            )
        pf = next(p for p in participant_fights(con) if p.kind == "you")
        events = event_rows(con, pf)
        raw, _, _ = event_totals(con, pf, events)
        result = recipient_metrics(con, pf, events, frozenset({14601}), raw)
        if partial:
            assert all(
                result[name].value is None
                for name in (
                    "raw_source_healing",
                    "effective_healing",
                    "healing_to_bosses",
                    "unclassified_healing",
                    "overhealing",
                    "overhealing_pct",
                )
            )
            return
        assert result["raw_source_healing"].value == (7600 if unresolved else 2600)
        assert result["effective_healing"].value == (None if unresolved else 600)
        assert result["healing_to_bosses"].value == (None if unresolved else 2000)
        assert result["unclassified_healing"].value == (5000 if unresolved else 0)
        assert result["overhealing"].value == (None if unresolved else 80)
        assert result["effective_healing_per_second"].value == (None if unresolved else 6)
        if not unresolved:
            assert result["overhealing_pct"].value == pytest.approx(100 * 80 / 680)
            assert {ref.source for ref in result["effective_healing"].refs} == {
                "events",
                "actors",
                "fights",
            }
            # A contradictory roster cannot turn enemy healing into support.
            con.execute("UPDATE fights SET friendly_players='[1,2,50]'")
            conflict = recipient_metrics(con, pf, events, frozenset({14601}), raw)
            assert conflict["effective_healing"].value is None
            assert conflict["healing_to_bosses"].value is None
            assert conflict["unclassified_healing"].value == 2000
            # A Player actor type alone does not establish friendly membership.
            con.execute("UPDATE fights SET friendly_players=NULL, friendly_pets=NULL")
            missing = recipient_metrics(con, pf, events, frozenset({14601}), raw)
            assert missing["effective_healing"].value is None
            assert missing["unclassified_healing"].value == 200
            assert missing["raw_source_healing"].value == 2600


@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize("scenario", ["owned", "unknown", "missing-amount", "zero"])
def test_credited_absorption_requires_source_ownership_and_friendly_recipients(
    tmp_path: Path,
    partial: bool,
    scenario: str,
) -> None:
    archive = snapshot(tmp_path, 7, "Holy", "Flash Heal", "healer", partial=partial)
    db = tmp_path / "absorption.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE fights SET friendly_players='[1,2]', friendly_pets='[{\"id\":3}]'")
        con.execute("UPDATE actors SET game_id=14601 WHERE actor_id=50")
        effects: list[tuple[int, int | None, int | None]] = (
            []
            if scenario == "zero"
            else [
                (1, 2, 50),
                (1, 3, 25),
                (1, 1, 10),
                (1, 50, 200),
                (2, 1, 9000),
            ]
        )
        if scenario == "unknown":
            effects.append((1, None, 1000))
        if scenario == "missing-amount":
            effects.append((1, 2, None))
        for index, (source, target, amount) in enumerate(effects):
            con.execute(
                "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,"
                "type,source_id,target_id,amount,raw) "
                "VALUES ('REPORT1',7,?,0,?,'absorbed',?,?,?, '{}')",
                [f"shield-{index}", 10000 + index, source, target, amount],
            )
        # A damage payload's absorbed field is incoming mitigation, not a
        # source-owned shield contribution. It must never enter this numerator.
        con.execute(
            "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,"
            "type,source_id,target_id,amount,raw) VALUES "
            "('REPORT1',7,'mitigation',0,15000,'damage',50,1,100,'{\"absorbed\":777}')"
        )
        pf = next(p for p in participant_fights(con) if p.kind == "you")
        events = event_rows(con, pf)
        raw, _, _ = event_totals(con, pf, events)
        result = recipient_metrics(con, pf, events, frozenset({14601}), raw)
        if partial:
            assert all(
                result[key].value is None
                for key in (
                    "raw_source_absorption",
                    "effective_absorption",
                    "absorption_to_bosses",
                    "unclassified_absorption",
                    "healing_and_absorption",
                )
            )
            return
        assert result["effective_healing"].value == 400
        assert result["raw_source_healing"].value == 400
        assert result["overhealing_pct"].value == pytest.approx(100 * 80 / 480)
        assert result["raw_source_absorption"].value == (
            None
            if scenario == "missing-amount"
            else 1285
            if scenario == "unknown"
            else 0
            if scenario == "zero"
            else 285
        )
        assert result["effective_absorption"].value == (
            None if scenario in {"unknown", "missing-amount"} else 0 if scenario == "zero" else 85
        )
        assert result["absorption_to_bosses"].value == (
            None if scenario == "unknown" else 0 if scenario == "zero" else 200
        )
        assert result["unclassified_absorption"].value == (1000 if scenario == "unknown" else 0)
        assert result["healing_and_absorption"].value == (
            None
            if scenario in {"unknown", "missing-amount"}
            else 400
            if scenario == "zero"
            else 485
        )


@pytest.mark.parametrize("malformed", ["source", "recipient", "amount", "fraction"])
@pytest.mark.parametrize("kind", ["heal", "absorbed"])
def test_database_scalar_coercion_cannot_certify_invalid_raw_support_fields(
    tmp_path: Path,
    malformed: str,
    kind: str,
) -> None:
    archive = snapshot(tmp_path, 7, "Holy", "Flash Heal", "healer")
    db = tmp_path / "coerced.duckdb"
    ingest(archive, db)
    with duckdb.connect(str(db)) as con:
        raw: dict[str, int | float] = {"sourceID": 1, "targetID": 1, "amount": 1}
        if malformed == "source":
            raw["sourceID"] = True
        elif malformed == "recipient":
            raw["targetID"] = True
        elif malformed == "amount":
            raw["amount"] = True
        else:
            raw["amount"] = 1.6
        con.execute(
            "INSERT INTO events (report_code,fight_id,event_uid,copy_index,timestamp,"
            "type,source_id,target_id,amount,raw) "
            "VALUES ('REPORT1',7,'coerced',0,10000,?,1,1,?,?)",
            [kind, 2 if malformed == "fraction" else 1, json.dumps(raw)],
        )
        pf = next(p for p in participant_fights(con) if p.kind == "you")
        events = event_rows(con, pf)
        metrics, _, _ = event_totals(con, pf, events)
        result = recipient_metrics(con, pf, events, frozenset({14601}), metrics)
        field = "healing" if kind == "heal" else "absorption"
        assert result[f"effective_{field}"].value is None
        assert result["healing_and_absorption"].value is None
        assert result[f"raw_source_{field}"].value == (
            (401 if kind == "heal" else 1) if malformed == "recipient" else None
        )
        if kind == "absorbed":
            assert result["effective_healing"].value == 400
        elif malformed == "source":
            assert result["overhealing"].value is None
