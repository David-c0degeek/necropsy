"""The unattended capture runner decides only from verified receipts and fails closed."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts import capture_runner as cr

START = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.at = START

    def now(self) -> datetime:
        return self.at

    def sleep(self, seconds: float) -> None:
        self.at += timedelta(seconds=max(seconds, 1))


class Alerts:
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[tuple[str, str]] = []
        self.fail = fail

    def __call__(self, url: str, body: bytes) -> None:
        if self.fail:
            raise OSError("unreachable")
        text = json.loads(body)["discord"]["text"]
        self.sent.append((text["title"], text["description"]))


ENTRY: dict[str, Any] = {
    "entry_id": "mc-paladin-holy-hps-alliance",
    "raid": "mc",
    "partition": 1,
    "class_id": 6,
    "category": "Holy",
    "metric": "hps",
    "faction": "Alliance",
    "candidates": ["https://example.invalid/character/1"],
}
THREE: dict[str, Any] = ENTRY | {
    "entry_id": "bwl-mage-fire-dps-horde",
    "candidates": ["https://example.invalid/a", "https://example.invalid/b", "https://x.invalid/c"],
}


def _queue(tmp_path: Path, *entries: dict[str, Any]) -> Path:
    path = tmp_path / "queue.json"
    rows = list(entries) or [ENTRY]
    path.write_text(json.dumps({"version": 1, "entries": rows}), encoding="utf-8")
    return path


def _secrets(tmp_path: Path) -> Path:
    directory = tmp_path / "secrets"
    directory.mkdir(exist_ok=True)
    path = directory / "notifiarr.json"
    path.write_text(json.dumps({"api_key": "KEY-SENTINEL", "channel_id": 42}), encoding="utf-8")
    if sys.platform != "win32":
        directory.chmod(0o700)
        path.chmod(0o600)
    return directory


def _runner(
    tmp_path: Path, clock: Clock, alerts: Alerts | None = None, queue: Path | None = None
) -> cr.Runner:
    if queue is None:
        queue = tmp_path / "queue.json"
        if not queue.exists():
            _queue(tmp_path)
    paths = cr.Paths(
        queue,
        tmp_path / "state",
        tmp_path / "out",
        tmp_path / "cache",
        tmp_path / "www",
        _secrets(tmp_path),
    )
    for directory in (paths.state, paths.out, paths.cache, paths.www):
        directory.mkdir(parents=True, exist_ok=True)
    runner = cr.Runner(
        paths,
        now=clock.now,
        sleep=clock.sleep,
        notifier=cr.Notifier(paths.secrets, post=alerts or Alerts()),
        free_floor_bytes=0,
        exit_when_idle=True,
    )
    runner.load()
    return runner


class Script:
    """Stands in for `necropsy analyze`: writes real checkpoint, archive and receipt."""

    def __init__(self, clock: Clock, steps: list[dict[str, Any] | None]) -> None:
        self.clock = clock
        self.steps = list(steps)
        self.commands: list[list[str]] = []

    def __call__(self, runner: cr.Runner) -> Any:
        def supervise(command: list[str], log: Path) -> tuple[str, int | None]:
            self.commands.append(command)
            step = self.steps.pop(0)
            if step is None:
                return "exit", 1  # no receipt written
            if step.get("stop_request"):
                runner.stopping.set()  # SIGTERM while the child runs
                return "stopped", None
            out = Path(command[command.index("--out") + 1])
            checkpoint = None
            if step.get("checkpoint", True):
                run = out / ".necropsy-run" / "run.json"
                run.parent.mkdir(parents=True, exist_ok=True)
                run.write_text(json.dumps({"n": len(self.commands)}), encoding="utf-8")
                checkpoint = hashlib.sha256(run.read_bytes()).hexdigest()
            snapshot = None
            if step.get("snapshot"):
                archive = out / "snapshot" / f"capture-{len(self.commands)}.zip"
                archive.parent.mkdir(parents=True, exist_ok=True)
                archive.write_bytes(b"zip-bytes-%d" % len(self.commands))
                snapshot = {
                    "archive": str(archive),
                    "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                }
            receipt = Path(command[command.index("--outcome-json") + 1])
            payload: dict[str, Any] = {
                "version": 1,
                "exit_code": step["exit"],
                "stop_class": step["stop"],
                "reset_at_utc": step.get("reset"),
                "out": str(out),
                "checkpoint_sha256": checkpoint,
                "snapshot": snapshot,
                "incomplete_bosses": 0,
                "written_at_utc": cr.iso(self.clock.now()),
            }
            payload.update(step.get("extra", {}))
            if "mutate" in step:
                step["mutate"](payload, out)
            receipt.write_text(json.dumps(payload), encoding="utf-8")
            self.clock.at += timedelta(minutes=step.get("minutes", 30))
            return "exit", int(step.get("native", step["exit"]))

        return supervise


def _go(runner: cr.Runner, script: Script) -> int:
    runner.supervise = script(runner)  # type: ignore[method-assign]
    runner.reconcile()
    return runner.run()


def _status(tmp_path: Path) -> dict[str, Any]:
    status: dict[str, Any] = json.loads((tmp_path / "www" / "status.json").read_bytes())
    return status


def _state(tmp_path: Path) -> dict[str, Any]:
    state: dict[str, Any] = json.loads((tmp_path / "state" / "state.json").read_bytes())
    return state


DONE: dict[str, Any] = {"exit": 0, "stop": "none", "snapshot": True}
REFUSE: dict[str, Any] = {"exit": 1, "stop": "refused", "checkpoint": False}


def test_a_quota_stop_waits_for_the_reported_reset_then_resumes_the_checkpoint(
    tmp_path: Path,
) -> None:
    clock = Clock()
    reset = cr.iso(START + timedelta(minutes=50))
    script = Script(clock, [{"exit": 4, "stop": "quota-reset", "reset": reset}, DONE])
    assert _go(_runner(tmp_path, clock), script) == 0
    first, second = script.commands
    assert "--resume" not in first and "--resume" in second
    assert clock.at >= START + timedelta(minutes=52)
    status = _status(tmp_path)
    assert status["headline"] == "Finished" and status["counts"]["complete"] == 1
    assert status["usable_archives"] == 1 and status["finished_at_utc"] is not None


def test_a_reserve_stop_is_deferred_like_a_quota_stop(tmp_path: Path) -> None:
    clock = Clock()
    reset = cr.iso(START + timedelta(minutes=40))
    script = Script(
        clock,
        [
            {"exit": 4, "stop": "quota-reserve", "reset": reset},
            {"exit": 4, "stop": "source-limit", "snapshot": True},
        ],
    )
    assert _go(_runner(tmp_path, clock), script) == 0
    assert _status(tmp_path)["counts"]["partial"] == 1


def test_a_quota_stop_without_a_reset_time_needs_attention(tmp_path: Path) -> None:
    clock = Clock()
    alerts = Alerts()
    script = Script(clock, [{"exit": 4, "stop": "quota-reset", "reset": None}])
    assert _go(_runner(tmp_path, clock, alerts), script) == 3
    status = _status(tmp_path)
    assert status["headline"] == "Needs attention" and "reset" in status["reason"]
    assert any("attention" in title for title, _ in alerts.sent)


def test_a_final_partial_without_a_stop_is_terminal_and_never_retried(tmp_path: Path) -> None:
    clock = Clock()
    script = Script(clock, [{"exit": 4, "stop": "source-limit", "snapshot": True}])
    assert _go(_runner(tmp_path, clock), script) == 0
    assert len(script.commands) == 1 and _status(tmp_path)["counts"]["partial"] == 1


def test_a_refused_candidate_moves_to_the_next_then_ends_refused(tmp_path: Path) -> None:
    clock = Clock()
    alerts = Alerts()
    runner = _runner(tmp_path, clock, alerts, queue=_queue(tmp_path, THREE))
    script = Script(clock, [REFUSE, REFUSE, REFUSE])
    assert _go(runner, script) == 0
    urls = [c[c.index("analyze") + 1] for c in script.commands]
    assert urls == list(THREE["candidates"])
    assert _status(tmp_path)["counts"]["refused"] == 1
    assert sum("refused" in title for title, _ in alerts.sent) == 3


def test_an_auth_failure_pauses_the_whole_queue_instead_of_refusing_entries(
    tmp_path: Path,
) -> None:
    clock = Clock()
    assert _go(_runner(tmp_path, clock), Script(clock, [{"exit": 1, "stop": "auth"}])) == 3
    status = _status(tmp_path)
    assert status["state"] == "attention" and status["counts"]["refused"] == 0
    assert status["counts"]["pending"] == 1


def _break(field: str, value: Any) -> Any:
    def mutate(payload: dict[str, Any], out: Path) -> None:
        payload[field] = value

    return mutate


def _wrong_hash(payload: dict[str, Any], out: Path) -> None:
    payload["snapshot"]["sha256"] = "0" * 64


def _missing_archive(payload: dict[str, Any], out: Path) -> None:
    Path(payload["snapshot"]["archive"]).unlink()


def _truncated_archive(payload: dict[str, Any], out: Path) -> None:
    Path(payload["snapshot"]["archive"]).write_bytes(b"zip")


def _outside(payload: dict[str, Any], out: Path) -> None:
    elsewhere = out.parent.parent / "elsewhere.zip"
    elsewhere.write_bytes(b"x")
    payload["snapshot"] = {"archive": str(elsewhere), "sha256": hashlib.sha256(b"x").hexdigest()}


@pytest.mark.parametrize(
    "step",
    [
        None,
        DONE | {"native": 4},
        {"exit": 0, "stop": "quota-reset"},
        {"exit": 1, "stop": "made-up"},
        DONE | {"extra": {"version": 2}},
        DONE | {"extra": {"written_at_utc": "2020-01-01T00:00:00+00:00"}},
        DONE | {"mutate": _break("stop_class", [])},
        DONE | {"mutate": _break("exit_code", True)},
        DONE | {"mutate": _break("snapshot", None)},
        DONE | {"mutate": _wrong_hash},
        DONE | {"mutate": _missing_archive},
        DONE | {"mutate": _truncated_archive},
        DONE | {"mutate": _outside},
        DONE | {"mutate": _break("out", "/somewhere/else")},
        DONE | {"mutate": _break("checkpoint_sha256", "1" * 64)},
    ],
    ids=[
        "missing",
        "exit-mismatch",
        "class-exit-mismatch",
        "unknown-class",
        "version",
        "stale",
        "list-class",
        "bool-exit",
        "complete-without-snapshot",
        "wrong-hash",
        "missing-archive",
        "truncated-archive",
        "archive-outside-output",
        "wrong-out",
        "wrong-checkpoint",
    ],
)
def test_an_untrustworthy_receipt_needs_attention(
    tmp_path: Path, step: dict[str, Any] | None
) -> None:
    clock = Clock()
    assert _go(_runner(tmp_path, clock), Script(clock, [step])) == 3
    status = _status(tmp_path)
    assert status["state"] == "attention"
    assert status["counts"]["complete"] == 0 and status["usable_archives"] == 0


def test_a_quota_stop_while_resolving_retries_fresh_without_a_checkpoint(tmp_path: Path) -> None:
    clock = Clock()
    reset = cr.iso(START + timedelta(minutes=30))
    early = {"exit": 1, "stop": "quota-reset", "reset": reset, "checkpoint": False}
    script = Script(clock, [early, DONE])
    assert _go(_runner(tmp_path, clock), script) == 0
    assert all("--resume" not in c for c in script.commands)
    assert _status(tmp_path)["counts"]["complete"] == 1


def _vanish(payload: dict[str, Any], out: Path) -> None:
    (out / ".necropsy-run" / "run.json").unlink()
    payload["checkpoint_sha256"] = None


def test_a_checkpoint_that_disappears_during_a_resume_needs_attention(tmp_path: Path) -> None:
    clock = Clock()
    reset = cr.iso(START + timedelta(minutes=30))
    script = Script(
        clock,
        [
            {"exit": 4, "stop": "quota-reset", "reset": reset},
            {"exit": 4, "stop": "quota-reset", "reset": reset, "mutate": _vanish},
        ],
    )
    assert _go(_runner(tmp_path, clock), script) == 3
    assert "checkpoint" in _status(tmp_path)["reason"]


def test_transient_failures_retry_with_backoff_then_need_attention(tmp_path: Path) -> None:
    clock = Clock()
    script = Script(clock, [{"exit": 1, "stop": "transient", "minutes": 1}] * 4)
    assert _go(_runner(tmp_path, clock), script) == 3
    assert len(script.commands) == 4
    assert clock.at >= START + timedelta(minutes=5 + 15 + 45)


def test_a_saved_snapshot_with_a_failed_report_needs_offline_recovery(tmp_path: Path) -> None:
    clock = Clock()
    script = Script(clock, [{"exit": 1, "stop": "error", "snapshot": True}])
    assert _go(_runner(tmp_path, clock), script) == 3
    status = _status(tmp_path)
    assert "offline recovery" in status["reason"] and status["counts"]["complete"] == 0
    assert "necropsy offline" in _state(tmp_path)["controller"]["reason"]
    assert status["usable_archives"] == 1


def test_a_restart_during_a_quota_wait_keeps_waiting_and_then_resumes(tmp_path: Path) -> None:
    clock = Clock()
    reset = cr.iso(START + timedelta(minutes=50))
    first = _runner(tmp_path, clock)
    quota = Script(clock, [{"exit": 4, "stop": "quota-reset", "reset": reset}])
    first.supervise = quota(first)  # type: ignore[method-assign]

    def stop_while_waiting(seconds: float) -> None:
        first.stopping.set()

    first.sleep = stop_while_waiting
    assert first.run() == 0
    assert _status(tmp_path)["headline"] == "Waiting for quota"
    later = Script(clock, [DONE])
    assert _go(_runner(tmp_path, clock), later) == 0
    assert "--resume" in later.commands[0] and clock.at >= START + timedelta(minutes=52)


@pytest.mark.parametrize("when", ["before-commit", "after-commit"])
@pytest.mark.parametrize(
    "step",
    [
        REFUSE,
        {"exit": 1, "stop": "transient"},
        {"exit": 4, "stop": "quota-reset", "reset": cr.iso(START + timedelta(hours=1))},
        {"exit": 1, "stop": "auth"},
        DONE,
    ],
    ids=["refusal", "transient", "quota", "auth", "complete"],
)
def test_a_crash_around_the_result_commit_applies_it_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, when: str, step: dict[str, Any]
) -> None:
    clock = Clock()
    queue = _queue(tmp_path, THREE)
    runner = _runner(tmp_path, clock, queue=queue)
    runner.supervise = Script(clock, [step])(runner)  # type: ignore[method-assign]
    real_commit = runner.commit

    def crashing_commit() -> None:
        applied = runner.state["inflight"] is None
        if applied and runner.state["entries"][THREE["entry_id"]]["attempts"]:
            if when == "after-commit":
                real_commit()
            raise KeyboardInterrupt
        real_commit()

    monkeypatch.setattr(runner, "commit", crashing_commit)
    with pytest.raises(KeyboardInterrupt):
        runner.run()
    once = _runner(tmp_path, clock, queue=queue)
    once.reconcile()
    first = json.dumps(once.state["entries"], sort_keys=True)
    twice = _runner(tmp_path, clock, queue=queue)
    twice.reconcile()
    assert json.dumps(twice.state["entries"], sort_keys=True) == first
    info = twice.state["entries"][THREE["entry_id"]]
    if step is REFUSE:
        assert info["candidate"] == 1
    assert info["transient"] <= 1 and twice.state["inflight"] is None


def test_a_requested_stop_resumes_from_the_checkpoint_on_restart(tmp_path: Path) -> None:
    clock = Clock()
    assert _go(_runner(tmp_path, clock), Script(clock, [{"stop_request": True}])) == 0
    assert _state(tmp_path)["inflight"]["stop_requested"] is True
    assert _go(_runner(tmp_path, clock), Script(clock, [DONE])) == 0
    status = _status(tmp_path)
    assert status["counts"]["complete"] == 1 and status["state"] == "finished"


def test_a_silent_death_needs_attention_and_a_clear_request_resumes_it(tmp_path: Path) -> None:
    clock = Clock()
    dead = _runner(tmp_path, clock)
    dead.state["inflight"] = {
        "entry": ENTRY["entry_id"],
        "attempt": 1,
        "candidate": 0,
        "started_utc": cr.iso(START),
        "out": str(tmp_path / "out" / ENTRY["entry_id"] / "candidate-0"),
        "receipt": str(tmp_path / "nowhere.json"),
        "exit": None,
        "stop_requested": False,
    }
    dead.save()
    assert _go(_runner(tmp_path, clock), Script(clock, [])) == 3
    assert "exit is unknown" in _status(tmp_path)["reason"]
    assert cr.main(["clear-attention", "--state", str(tmp_path / "state")]) == 0
    cleared = _runner(tmp_path, clock)
    cleared.exit_when_idle = False
    cleared.supervise = Script(clock, [DONE])(cleared)  # type: ignore[method-assign]

    def stop_when_done(seconds: float) -> None:
        clock.sleep(seconds)
        if cleared.state["controller"]["state"] == "finished":
            cleared.stopping.set()

    cleared.sleep = stop_when_done
    cleared.reconcile()
    assert cleared.run() == 0
    assert _status(tmp_path)["counts"]["complete"] == 1


def test_a_failed_state_write_stops_the_queue_and_alerts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = Clock()
    alerts = Alerts()
    runner = _runner(tmp_path, clock, alerts)

    def full(path: Path, value: Any, mode: int = 0o644) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(cr, "write_json", full)
    assert _go(runner, Script(clock, [])) == 3
    assert any("could not save" in text for _, text in alerts.sent)


def test_the_free_space_floor_stops_before_another_attempt(tmp_path: Path) -> None:
    clock = Clock()
    runner = _runner(tmp_path, clock)
    runner.free_floor_bytes = 2**62
    assert _go(runner, Script(clock, [])) == 3
    assert "free space" in _status(tmp_path)["reason"]


def test_a_failed_final_alert_is_retried_after_a_restart(tmp_path: Path) -> None:
    clock = Clock()
    assert _go(_runner(tmp_path, clock, Alerts(fail=True)), Script(clock, [DONE])) == 0
    state = _state(tmp_path)
    assert state["alert_failures"] >= 1 and any(a["key"] == "finished" for a in state["outbox"])
    clock.at += timedelta(hours=2)
    up = Alerts()
    assert _go(_runner(tmp_path, clock, up), Script(clock, [])) == 0
    assert any("finished" in title for title, _ in up.sent)
    state = _state(tmp_path)
    assert "finished" in state["delivered"] and state["alert_failures"] >= 1


def test_alert_retries_are_bounded(tmp_path: Path) -> None:
    clock = Clock()
    runner = _runner(tmp_path, clock, Alerts(fail=True))
    runner.alert("k", "title", "text")
    for _ in range(cr.ALERT_TRIES + 3):
        runner.flush()
        clock.at += timedelta(hours=2)
    assert runner.state["outbox"] == [] and runner.state["alert_failures"] == cr.ALERT_TRIES


def test_alerts_are_queued_once_per_key(tmp_path: Path) -> None:
    clock = Clock()
    alerts = Alerts()
    runner = _runner(tmp_path, clock, alerts)
    runner.alert("k", "title", "text")
    runner.alert("k", "title", "text")
    runner.flush()
    runner.alert("k", "title", "text")
    runner.flush()
    assert alerts.sent == [("title", "text")]


def test_the_status_never_contains_secrets_or_candidate_urls(tmp_path: Path) -> None:
    clock = Clock()
    _go(_runner(tmp_path, clock), Script(clock, [DONE]))
    text = (tmp_path / "www" / "status.json").read_text(encoding="utf-8")
    assert "KEY-SENTINEL" not in text and "example.invalid" not in text


def test_a_second_runner_on_the_same_state_is_refused(tmp_path: Path) -> None:
    lock = tmp_path / "runner.lock"
    with cr.single_instance(lock), pytest.raises(cr.QueueError), cr.single_instance(lock):
        pass


def test_a_state_from_another_queue_is_refused(tmp_path: Path) -> None:
    clock = Clock()
    _runner(tmp_path, clock).save()
    other = tmp_path / "other-queue.json"
    other.write_text(
        (tmp_path / "queue.json").read_text(encoding="utf-8").replace("Holy", "Protection"),
        encoding="utf-8",
    )
    paths = cr.Paths(other, tmp_path / "state", tmp_path / "out", tmp_path, tmp_path / "www")
    with pytest.raises(cr.QueueError, match="different queue"):
        cr.Runner(paths).load()


def _real_runner(tmp_path: Path) -> cr.Runner:
    runner = _runner(tmp_path, Clock())
    runner.now = cr.utcnow
    runner.poll_s = 0.05
    runner.heartbeat_s = 0.1
    runner.stop_grace_s = 5
    return runner


SLEEPER = [sys.executable, "-c", "import time; print('child', flush=True); time.sleep(30)"]


def test_a_hung_attempt_is_terminated_at_its_timeout(tmp_path: Path) -> None:
    runner = _real_runner(tmp_path)
    runner.attempt_timeout_s = 0.5
    how, code = runner.supervise(SLEEPER, tmp_path / "log.txt")
    assert how == "exit" and code not in (None, 0)
    assert "child" in (tmp_path / "log.txt").read_text(encoding="utf-8")


def test_a_status_write_failure_still_reaps_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _real_runner(tmp_path)
    started: list[subprocess.Popen[bytes]] = []
    real_popen = subprocess.Popen

    def tracking(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        child = real_popen(*args, **kwargs)
        started.append(child)
        return child

    def broken() -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(subprocess, "Popen", tracking)
    monkeypatch.setattr(runner, "heartbeat", broken)
    with pytest.raises(OSError):
        runner.supervise(SLEEPER, tmp_path / "log.txt")
    assert started and started[0].poll() is not None


def test_a_stop_request_during_a_run_stops_the_child_promptly(tmp_path: Path) -> None:
    runner = _real_runner(tmp_path)
    threading.Timer(0.3, runner.stopping.set).start()
    begun = datetime.now(UTC)
    how, _ = runner.supervise(SLEEPER, tmp_path / "log.txt")
    assert how == "stopped" and datetime.now(UTC) - begun < timedelta(seconds=10)


def test_the_log_is_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cr, "LOG_PART_BYTES", 1000)
    runner = _real_runner(tmp_path)
    noisy = [sys.executable, "-c", "import sys; sys.stdout.write('x' * 5000)"]
    assert runner.supervise(noisy, tmp_path / "log.txt") == ("exit", 0)
    logs = sorted(tmp_path.glob("log*.txt"))
    assert [p.name for p in logs] == ["log.1.txt", "log.txt"]
    assert all(p.stat().st_size <= 1000 for p in logs)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX secret checks")
@pytest.mark.parametrize("problem", ["mode", "dir-mode", "link"])
def test_unsafe_alert_secrets_are_refused(tmp_path: Path, problem: str) -> None:
    secrets = _secrets(tmp_path)
    target = secrets / "notifiarr.json"
    if problem == "mode":
        target.chmod(0o644)
    elif problem == "dir-mode":
        secrets.chmod(0o755)
    else:
        real = secrets / "real.json"
        target.replace(real)
        target.symlink_to(real)
    alerts = Alerts()
    assert cr.Notifier(secrets, post=alerts).send("t", "x") is False and alerts.sent == []


@pytest.mark.parametrize(
    ("status", "local", "expected"),
    [
        (None, START, "unreadable"),
        ([], START, "unreadable"),
        ({"state": "finished", "heartbeat_utc": "2020-01-01T00:00:00+00:00"}, START, None),
        (
            {"state": "running", "heartbeat_utc": cr.iso(START - timedelta(minutes=30))},
            START,
            "stale",
        ),
        (
            {"state": "running", "heartbeat_utc": cr.iso(START - timedelta(minutes=30))},
            START.replace(hour=3, minute=20),
            None,
        ),
        (
            {"state": "running", "heartbeat_utc": cr.iso(START - timedelta(minutes=30))},
            START.replace(hour=3, minute=50),
            "stale",
        ),
        (
            {
                "state": "waiting",
                "heartbeat_utc": cr.iso(START),
                "last_progress_utc": cr.iso(START - timedelta(days=1)),
            },
            START,
            None,
        ),
        (
            {
                "state": "running",
                "heartbeat_utc": cr.iso(START),
                "last_progress_utc": cr.iso(START - timedelta(hours=9)),
            },
            START,
            "stall",
        ),
        ({"state": "running", "heartbeat_utc": cr.iso(START)}, START, None),
    ],
    ids=[
        "unreadable",
        "list",
        "finished-quiet",
        "stale",
        "backup-window",
        "after-backup-window",
        "quota-wait",
        "stall",
        "healthy",
    ],
)
def test_watchdog_judges_liveness_independently(
    status: Any, local: datetime, expected: str | None
) -> None:
    problem = cr.watchdog_check(status, START, local)
    assert (problem[0] if problem else None) == expected


def test_watchdog_alerts_once_per_open_problem_and_survives_bad_memory(tmp_path: Path) -> None:
    status = tmp_path / "status.json"
    status.write_text(json.dumps({"state": "running", "heartbeat_utc": None}), "utf-8")
    alerts = Alerts()
    notifier = cr.Notifier(_secrets(tmp_path), post=alerts)
    memory = tmp_path / "memory.json"
    memory.write_text("[]", encoding="utf-8")
    assert cr.watchdog(status, memory, notifier) == 1
    assert cr.watchdog(status, memory, notifier) == 1
    assert len(alerts.sent) == 1


def test_the_runner_script_runs_without_the_package_on_its_path() -> None:
    done = subprocess.run(
        [sys.executable, "-I", str(Path(cr.__file__)), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert done.returncode == 0 and "watchdog" in done.stdout


def test_a_death_during_stop_cleanup_still_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _real_runner(tmp_path)
    runner.state["inflight"] = {
        "entry": ENTRY["entry_id"],
        "attempt": 1,
        "candidate": 0,
        "started_utc": cr.iso(START),
        "out": str(tmp_path / "out"),
        "receipt": str(tmp_path / "r.json"),
        "exit": None,
        "stop_requested": False,
        "checkpoint_before": None,
    }
    runner.save()
    real_stop = cr._stop_child

    def dies(child: Any, grace_s: float) -> None:
        real_stop(child, grace_s)
        raise KeyboardInterrupt  # the controller dies during cleanup

    monkeypatch.setattr(cr, "_stop_child", dies)
    threading.Timer(0.3, runner.stopping.set).start()
    with pytest.raises(KeyboardInterrupt):
        runner.supervise(SLEEPER, tmp_path / "log.txt")
    assert _state(tmp_path)["inflight"]["stop_requested"] is True
    restarted = _runner(tmp_path, Clock())
    restarted.reconcile()
    assert restarted.state["controller"]["state"] != "attention"


def test_an_orphaned_attempt_directory_is_kept_and_skipped(tmp_path: Path) -> None:
    clock = Clock()
    runner = _runner(tmp_path, clock)
    runner.save()
    orphan = tmp_path / "state" / "attempts" / ENTRY["entry_id"] / "001"
    orphan.mkdir(parents=True)
    (orphan / "evidence.txt").write_text("left by a crash", encoding="utf-8")
    script = Script(clock, [DONE])
    assert _go(_runner(tmp_path, clock), script) == 0
    assert "/002/" in script.commands[0][script.commands[0].index("--outcome-json") + 1].replace(
        "\\", "/"
    )
    assert (orphan / "evidence.txt").exists()


def test_a_clear_is_refused_while_nothing_needs_attention(tmp_path: Path) -> None:
    clock = Clock()
    _runner(tmp_path, clock).save()
    assert cr.main(["clear-attention", "--state", str(tmp_path / "state")]) == 2
    assert not (tmp_path / "state" / cr.CLEAR_REQUEST).exists()


@pytest.mark.parametrize(
    "request_body",
    [
        {"queue_sha256": "0" * 64, "incident": 1},
        {"queue_sha256": None, "incident": 99},
        "clear",
    ],
    ids=["wrong-queue", "wrong-incident", "unscoped"],
)
def test_a_clear_for_another_queue_or_incident_is_discarded(
    tmp_path: Path, request_body: Any
) -> None:
    clock = Clock()
    runner = _runner(tmp_path, clock)
    runner.attention("test pause", "k")
    runner.save()
    body = dict(request_body) if isinstance(request_body, dict) else request_body
    if isinstance(body, dict) and body["queue_sha256"] is None:
        body["queue_sha256"] = runner.state["queue_sha256"]
    request = tmp_path / "state" / cr.CLEAR_REQUEST
    request.write_text(json.dumps(body) if isinstance(body, dict) else body, encoding="utf-8")
    runner.idle()
    assert runner.state["controller"]["state"] == "attention" and not request.exists()


def test_a_clear_applies_once_even_if_its_removal_is_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = Clock()
    runner = _runner(tmp_path, clock)
    runner.attention("first pause", "k1")
    runner.save()
    assert cr.main(["clear-attention", "--state", str(tmp_path / "state")]) == 0
    request = tmp_path / "state" / cr.CLEAR_REQUEST
    saved = request.read_bytes()
    runner.idle()
    assert runner.state["controller"]["state"] == "running"
    request.write_bytes(saved)  # as if the process died before removing it
    restarted = _runner(tmp_path, clock)
    restarted.attention("second, unrelated pause", "k2")
    restarted.save()
    restarted.idle()
    assert restarted.state["controller"]["state"] == "attention"


def test_watchdog_alerts_when_a_finished_runner_dies_with_alerts_pending() -> None:
    old = cr.iso(START - timedelta(hours=1))
    pending = {"state": "finished", "heartbeat_utc": old, "alerts_pending": 1}
    quiet = {"state": "finished", "heartbeat_utc": old, "alerts_pending": 0}
    assert cr.watchdog_check(pending, START, START) is not None
    assert cr.watchdog_check(quiet, START, START) is None
