"""Ordered raids cannot bypass deferred/partial work; queue extension preserves progress."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts import capture_runner as cr
from tests.unit.test_capture_runner import ENTRY, START, Clock, _runner


def queues(tmp: Path) -> tuple[Path, Path]:
    rows = [
        ENTRY | {"entry_id": f"{r}-capture", "raid": r} for r in ("naxxramas", "aq40", "bwl", "mc")
    ]
    old, new = tmp / "old.json", tmp / "new.json"
    old.write_text(json.dumps({"version": 1, "entries": rows[:1]}))
    new.write_text(
        json.dumps({"version": 2, "raid_order": [r["raid"] for r in rows], "entries": rows})
    )
    return old, new


def test_extension_keeps_all_existing_progress_and_is_idempotent(tmp_path: Path) -> None:
    old, new = queues(tmp_path)
    runner = _runner(tmp_path, Clock(), queue=old)
    info = runner.state["entries"]["naxxramas-capture"]
    info.update(
        state=cr.DEFERRED,
        attempts=12,
        candidate=1,
        reason="quota-reset stop",
        retry_at=cr.iso(START + timedelta(hours=1)),
        archives=[{"path": "keep.zip"}],
    )
    runner.state["quota_until_utc"] = info["retry_at"]
    runner.state["outbox"] = [{"key": "keep-alert"}]
    runner.save()
    before = copy.deepcopy(runner.state)
    raw = runner.state_file.read_bytes()
    result = cr.extend_queue(old, new, runner.paths.state)
    assert result["preserved_entries"] == 1 and result["appended_entries"] == 3
    after = json.loads(runner.state_file.read_bytes())
    assert after["entries"]["naxxramas-capture"] == before["entries"]["naxxramas-capture"]
    assert all(after[k] == v for k, v in before.items() if k not in {"entries", "queue_sha256"})
    assert (runner.paths.state / result["backup"]).read_bytes() == raw
    assert after["entries"]["aq40-capture"]["state"] == cr.PENDING
    assert cr.extend_queue(old, new, runner.paths.state)["already_migrated"]
    assert json.loads(runner.state_file.read_bytes()) == after
    loaded = _runner(tmp_path, Clock(), queue=new)
    assert loaded.raid_order == ("naxxramas", "aq40", "bwl", "mc")
    assert loaded.next_entry() == (None, START + timedelta(hours=1))


@pytest.mark.parametrize(
    "mutation", ["candidate", "remove", "reorder", "inflight", "hash", "extra-state", "locked"]
)
def test_bad_queue_extension_never_changes_state(tmp_path: Path, mutation: str) -> None:
    old, new = queues(tmp_path)
    runner = _runner(tmp_path, Clock(), queue=old)
    if mutation in {"candidate", "remove", "reorder"}:
        data = json.loads(new.read_bytes())
        if mutation == "candidate":
            data["entries"][0]["candidates"] = ["https://different.invalid"]
        elif mutation == "remove":
            data["entries"] = data["entries"][1:]
            data["raid_order"] = data["raid_order"][1:]
        else:
            data["entries"] = list(reversed(data["entries"]))
        new.write_text(json.dumps(data))
    elif mutation == "inflight":
        runner.state["inflight"] = {"entry": "naxxramas-capture"}
    elif mutation == "hash":
        runner.state["queue_sha256"] = "0" * 64
    elif mutation == "extra-state":
        runner.state["entries"]["unlisted"] = cr.pending_entry()
    cr.write_json(runner.state_file, runner.state)
    before = runner.state_file.read_bytes()
    if mutation == "locked":
        with cr.single_instance(runner.paths.state / "runner.lock"), pytest.raises(cr.QueueError):
            cr.extend_queue(old, new, runner.paths.state)
    else:
        with pytest.raises(cr.QueueError):
            cr.extend_queue(old, new, runner.paths.state)
    assert runner.state_file.read_bytes() == before


def test_stage_order_survives_waits_and_restart_and_partials_need_review(tmp_path: Path) -> None:
    _, new = queues(tmp_path)
    clock = Clock()
    runner = _runner(tmp_path, clock, queue=new)
    naxx = runner.state["entries"]["naxxramas-capture"]
    naxx.update(state=cr.RETRY, retry_at=cr.iso(START + timedelta(minutes=5)))
    assert runner.next_entry() == (None, START + timedelta(minutes=5))
    runner.save()
    runner = _runner(tmp_path, clock, queue=new)
    naxx = runner.state["entries"]["naxxramas-capture"]
    naxx["state"] = cr.PARTIAL
    assert runner.next_entry() == (None, None)
    assert runner.run() == 3
    assert runner.state["controller"]["state"] == cr.ATTENTION
    assert "partial or refused" in runner.stage_problem()  # type: ignore[operator]
    runner.set_controller(cr.RUNNING)  # clearing attention cannot skip the raid
    assert runner.run() == 3
    for raid in ("naxxramas", "aq40", "bwl", "mc"):
        assert runner.active_raid() == raid
        runner.state["entries"][raid + "-capture"]["state"] = cr.COMPLETE
    assert runner.active_raid() is None and runner.stage_problem() is None


def test_approved_stages_let_later_raids_start_without_marking_entries_complete(
    tmp_path: Path,
) -> None:
    _, new = queues(tmp_path)
    runner = _runner(tmp_path, Clock(), queue=new)
    entries = runner.state["entries"]
    entries["naxxramas-capture"]["state"] = cr.PARTIAL
    assert runner.run() == 3 and runner.stage_problem() is not None
    digest = runner.state["queue_sha256"]
    request = runner.paths.state / cr.APPROVE_REQUEST

    for bad in (
        {"queue_sha256": "0" * 64, "raids": ["naxxramas"]},
        {"queue_sha256": digest, "raids": ["zg"]},
    ):
        cr.write_json(request, bad)
        assert runner.apply_approvals() is False and not request.exists()
        assert runner.state["controller"]["state"] == cr.ATTENTION
        assert "approved_stages" not in runner.state

    assert (
        cr.main(
            ["approve-stage", "--state", str(runner.paths.state)]
            + [a for r in ("naxxramas", "aq40", "bwl") for a in ("--raid", r)]
        )
        == 0
    )
    runner.idle()
    assert runner.state["controller"]["state"] == cr.RUNNING
    assert runner.state["approved_stages"] == ["naxxramas", "aq40", "bwl"]
    assert entries["naxxramas-capture"]["state"] == cr.PARTIAL
    assert runner.active_raid() == "aq40"
    assert runner.next_entry()[0].entry_id == "aq40-capture"  # type: ignore[union-attr]

    entries["aq40-capture"]["state"] = cr.REFUSED
    entries["bwl-capture"]["state"] = cr.PARTIAL
    assert runner.active_raid() == "mc"  # pre-approved stages pass once ended
    entries["mc-capture"]["state"] = cr.PARTIAL
    assert runner.active_raid() == "mc" and runner.stage_problem() is not None  # mc not approved

    runner.save()
    reloaded = _runner(tmp_path, Clock(), queue=new)
    assert reloaded.state["approved_stages"] == ["naxxramas", "aq40", "bwl"]
    assert reloaded.active_raid() == "mc"


def test_approval_while_not_held_records_without_resuming(tmp_path: Path) -> None:
    _, new = queues(tmp_path)
    runner = _runner(tmp_path, Clock(), queue=new)
    runner.set_controller(cr.ATTENTION, "free space below the floor on /x")
    cr.write_json(
        runner.paths.state / cr.APPROVE_REQUEST,
        {"queue_sha256": runner.state["queue_sha256"], "raids": ["naxxramas"]},
    )
    assert runner.apply_approvals() is False
    assert runner.state["controller"]["state"] == cr.ATTENTION
    assert runner.state["approved_stages"] == ["naxxramas"]


@pytest.mark.parametrize(
    "order", [None, [], ["mc", "mc"], ["unknown"], ["mc"], ["mc", "bwl", "aq40", "naxxramas"]]
)
def test_invalid_stage_order_is_refused(tmp_path: Path, order: Any) -> None:
    _, new = queues(tmp_path)
    data = json.loads(new.read_bytes())
    data["raid_order"] = order
    new.write_text(json.dumps(data))
    with pytest.raises(cr.QueueError):
        cr.load_queue(new)


def test_pinned_campaign_keeps_naxx_prefix_and_parked_queue_unchanged() -> None:
    root = Path(__file__).parents[2]
    campaign = root / "tasks/capture-campaign/capture-queue.json"
    raw = campaign.read_bytes()
    data = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == campaign.with_suffix(".sha256").read_text().strip()
    assert len(cr.load_queue(campaign)[1]) == 127
    previous = json.loads((root / "tasks/naxx-completion/capture-queue.json").read_bytes())
    assert data["entries"][:34] == previous["entries"]
    assert data["raid_order"] == ["naxxramas", "aq40", "bwl", "mc"]
    assert all(
        hashlib.sha256((root / p).read_bytes()).hexdigest() == h for p, h in data["pins"].items()
    )
