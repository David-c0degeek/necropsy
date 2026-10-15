"""Presentation summaries must not upgrade missing or uncertain analytical truth."""

from copy import deepcopy
from typing import Any

from necropsy.report.render.experience import experience


def document() -> dict[str, Any]:
    return {
        "zone": {"name": "Naxxramas"},
        "coverage": {"streams_not_complete": 0, "snapshot_issues": 0, "event_anomalies": 0},
        "bosses": [
            {
                "encounter_id": 1,
                "boss": "A boss",
                "subject": {
                    "kill_duration_s": 60,
                    "environment": {"faction": {"value": "Horde", "level": "inferred"}},
                },
                "benchmarks": {
                    "baseline": {
                        "entries": 3,
                        "medians": {
                            "rate": {"value": {"value": None, "level": "unknown"}},
                        },
                    }
                },
                "recommendations": [],
            }
        ],
    }


def test_summary_preserves_unknown_inferred_and_input() -> None:
    raw = document()
    original = deepcopy(raw)
    ux = experience(raw, "Hunter")
    assert raw == original
    assert ux["faction"] == "Horde" and ux["faction_level"] == "inferred"
    assert ux["bosses"][0]["quality"] == "Limited sample"
    assert ux["bosses"][0]["state"] == "No finding flagged"
    assert ux["priorities"] == []
    assert ux["finding_count"] == 0
    assert "not a clean bill" in ux["bosses"][0]["summary"]


def test_missing_personal_data_is_not_a_clean_result() -> None:
    raw = document()
    raw["bosses"][0]["subject"] = None
    raw["bosses"][0]["benchmarks"]["baseline"] = None
    raw["coverage"]["streams_not_complete"] = 2
    raw["zone"]["name"] = "Unrecognized raid"
    ux = experience(raw, "Unknown")
    assert ux["class_key"] == "neutral" and ux["raid_key"] == "neutral"
    assert ux["faction"] == "Unknown"
    assert ux["bosses"][0]["state"] == "Not assessed"
    assert ux["bosses"][0]["sources"] == "Unknown"
    assert ux["bosses"][0]["kill"] == "Unknown"
    assert ux["coverage"] == "Coverage needs review"


def test_priority_order_deduplicates_rules_without_inventing_advice() -> None:
    raw = document()
    recs = [
        {
            "rule": rule,
            "severity": severity,
            "confidence": "low",
            "controllability": "raid-assignment",
            "recommendation": f"Saved advice {rule}",
            "finding": "Saved observation",
            "evidence": ["path"],
            "limitations": ["Partial"],
        }
        for rule, severity in (("one", "low"), ("two", "high"), ("three", "medium"))
    ]
    raw["bosses"][0]["recommendations"] = recs
    second = deepcopy(raw["bosses"][0])
    second["encounter_id"] = 2
    raw["bosses"].append(second)
    ux = experience(raw, "Druid")
    assert [p["rule"] for p in ux["priorities"]] == ["two", "three", "one"]
    assert all(p["boss_count"] == 2 for p in ux["priorities"])
    assert ux["finding_count"] == 6
    assert all(p["confidence"] == "low" for p in ux["priorities"])
    assert ux["priorities"][0]["limitations"] == ["Partial"]
    assert ux["priorities"][0]["recommendation"] == "Saved advice two"


def test_acquisition_shortfall_and_unknown_median_remain_visible() -> None:
    raw = document()
    raw["bosses"][0]["benchmarks"]["baseline"]["entries"] = 5
    raw["acquisition"] = {"bosses": [{"coverage": {"complete": False}}]}
    ux = experience(raw, "Priest")
    assert ux["coverage"] == "Coverage needs review"
    assert ux["bosses"][0]["quality"] == "Some comparisons unavailable"
    assert ux["limited_count"] == 1
