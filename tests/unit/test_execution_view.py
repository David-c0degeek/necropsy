"""Execution plans compare actor actions rather than incoming casts or partial absence."""

from copy import deepcopy
from typing import Any

from necropsy.report.render.execution_view import execution


def _entry() -> dict[str, Any]:
    return {
        "player": "Leader",
        "report_code": "REPORT",
        "fight_id": 1,
        "kill_duration_s": 120,
        "ability_use": {"value": {"Healing Touch": 2}, "refs": [{"actor": 7}]},
        "druid": {
            "opener": [],
            "timeline": [
                {"kind": "cast", "name": "Healing Touch", "source_id": 8, "t_s": 1},
                {"kind": "cast", "name": "Healing Touch", "source_id": 7, "t_s": 12},
            ],
        },
    }


def test_execution_first_cast_is_the_actor_not_an_incoming_heal() -> None:
    rows = execution(_entry(), _entry(), "druid")
    action = next(r for r in rows if r["label"] == "Healing Touch")
    assert "2 uses · 1.00 uses/min · first use 12.00s" in action["lines"][0]["text"]
    assert action["lines"][0]["sources"][0]["url"].endswith("REPORT#fight=1")
    assert rows[0]["label"] == "Opener"


def test_missing_personal_role_keeps_leader_execution_without_a_personal_zero() -> None:
    action = next(r for r in execution(None, _entry(), "druid") if r["label"] == "Healing Touch")
    assert "You: Unknown uses" in action["lines"][0]["text"]
    assert "Faction leader: 2 uses" in action["lines"][1]["text"]


def test_incomplete_actor_stream_does_not_claim_a_first_use_or_zero() -> None:
    partial = deepcopy(_entry())
    partial["ability_use"]["value"] = None
    action = next(r for r in execution(partial, _entry(), "druid") if r["label"] == "Healing Touch")
    assert "Unknown uses · Unknown uses/min · first use Unknown" in action["lines"][0]["text"]
