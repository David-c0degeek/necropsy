"""Public capture status is a projection, not a copy of private runner state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import capture_queue as cq
from scripts import capture_runner as cr
from tests.unit.test_capture_runner import Clock, _runner


def test_public_projection_keeps_raw_failures_private_and_names_the_active_candidate(
    tmp_path: Path,
) -> None:
    runner = _runner(tmp_path, Clock())
    raw_queue = json.loads(runner.paths.queue.read_bytes())
    raw_queue["entries"][0]["class"] = "Mage"
    runner.paths.queue.write_text(json.dumps(raw_queue), encoding="utf-8")
    runner.load()
    entry = runner.entries[0]
    private = "unknown stop class 'TOKEN-SECRET https://private.invalid /mnt/user/secrets/token'"
    info = runner.state["entries"][entry.entry_id]
    info["reason"] = private
    runner.state["controller"]["reason"] = f"{entry.entry_id}: {private}"
    runner.state["inflight"] = {"entry": entry.entry_id, "attempt": 4, "candidate": 0}
    status = runner.status()
    public = json.dumps(status)
    for secret in ("TOKEN-SECRET", "private.invalid", "/mnt/user", *entry.candidates):
        assert secret not in public
    assert status["current"]["class"] == "Mage"
    assert status["current"]["candidate"] == 1
    assert status["current"]["candidate_count"] == len(entry.candidates)
    assert runner.state["entries"][entry.entry_id]["reason"] == private
    assert status["summary"]["scheduled_runs"] == 1
    assert status["summary"]["capture_ready_runs"] is None


@pytest.mark.parametrize(
    "change",
    [
        {"scheduled_runs": 2},
        {"universe_runs": 99},
        {"offline_reuse_runs": 3},
        {"capture_ready_runs": -1},
        {"all_registered_runs": True},
        {"universe_runs": "3"},
    ],
)
def test_contradictory_public_queue_metadata_is_refused(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    runner = _runner(tmp_path, Clock())
    queue = json.loads(runner.paths.queue.read_bytes())
    queue["summary"] = {
        "universe_runs": 3,
        "scheduled_runs": 1,
        "capture_ready_runs": 2,
        "all_registered_runs": 1,
        "offline_reuse_runs": 1,
    } | change
    runner.paths.queue.write_text(json.dumps(queue), encoding="utf-8")
    with pytest.raises(cr.QueueError, match="summary"):
        runner.load()


@pytest.mark.parametrize("summary", [None, [], {}])
def test_present_but_malformed_summary_is_not_treated_as_absent(
    tmp_path: Path, summary: Any
) -> None:
    runner = _runner(tmp_path, Clock())
    queue = json.loads(runner.paths.queue.read_bytes())
    queue["summary"] = summary
    runner.paths.queue.write_text(json.dumps(queue), encoding="utf-8")
    with pytest.raises(cr.QueueError, match="summary"):
        runner.load()


def test_queue_summary_is_derived_from_the_reviewed_plan() -> None:
    plan = {
        "entries": [
            {"queued": True},
            {"queued": False, "disposition": {"bosses": [{"disposition": "registered"}]}},
            {"queued": False, "disposition": {"bosses": [{"disposition": "offline-reuse"}]}},
        ]
    }
    summary = cq.public_summary(plan, 1)
    assert summary == {
        "universe_runs": 3,
        "scheduled_runs": 1,
        "capture_ready_runs": 2,
        "all_registered_runs": 1,
        "offline_reuse_runs": 1,
    }
    assert cr.validate_summary(summary, 1) == summary
    with pytest.raises(ValueError):
        cq.public_summary(plan, 2)


def test_attention_alerts_use_public_copy_without_losing_private_diagnostics(
    tmp_path: Path,
) -> None:
    runner = _runner(tmp_path, Clock())
    events: list[dict[str, Any]] = []
    runner.notifier = cr.Notifier(
        runner.paths.secrets, post=lambda _url, body: events.append(json.loads(body))
    )
    private = "unknown receipt https://private.invalid/token-SECRET at /mnt/user/appdata/secrets"
    runner.attention(private, "test-incident")
    runner.commit()
    assert events and "SECRET" not in json.dumps(events)
    assert "private.invalid" not in json.dumps(events)
    assert runner.state["controller"]["reason"] == private
    assert "Capture watch" in events[0]["discord"]["text"]["description"]


def test_known_public_reasons_distinguish_partial_auth_and_unknown_quota() -> None:
    assert "source limitations" in cr.public_reason("finished with incomplete source data")
    assert "sign-in" in cr.public_reason("the Warcraft Logs sign-in needs attention")
    assert "unknown" in cr.public_reason("quota-reset stop without a known reset time")
    assert "offline recovery" in cr.public_reason(
        "a snapshot was saved but its report failed; finish it with necropsy offline"
    )
