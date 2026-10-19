"""Unattended serial capture queue for a server (tasks/raid-completion/tower-capture-design.md).

Runs `necropsy analyze` once per queue entry and candidate, one at a time, and
decides what happens next only from the attempt's `--outcome-json` receipt,
checked against what the runner itself observed (the child's exit code, start
time and output directory) and against the actual files. Anything missing,
malformed or contradictory stops the queue as Needs attention; nothing is
inferred as complete, refused or quota-limited.

Every attempt is recorded as in flight before the child starts. Its result is
committed in the same state write that clears it, so a crash before or after
that write never applies a result twice. Standard library only and Python 3.11
compatible, so the watchdog also runs on the server host's own Python.

    python capture_runner.py run --queue Q --state DIR --out DIR --cache DIR --www DIR
    python capture_runner.py clear-attention --state DIR
    python capture_runner.py watchdog --status www/status.json --secrets DIR --memory FILE
    python capture_runner.py test-alert --secrets DIR
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from datetime import time as clock_time
from pathlib import Path
from typing import IO, Any

QUEUE_VERSION = 1
STATE_VERSION = 2
OUTCOME_VERSION = 1

RUNNING, WAITING, ATTENTION, FINISHED = "running", "waiting", "attention", "finished"
HEADLINES = {
    RUNNING: "Running",
    WAITING: "Waiting for quota",
    ATTENTION: "Needs attention",
    FINISHED: "Finished",
}
# Entry states. Terminal: complete, partial, refused.
PENDING, DEFERRED, RETRY, COMPLETE, PARTIAL, REFUSED = (
    "pending",
    "deferred",
    "retry",
    "complete",
    "partial",
    "refused",
)
TERMINAL = frozenset({COMPLETE, PARTIAL, REFUSED})
EXPECTED_EXIT = {
    "none": {0},
    "source-limit": {4},
    "quota-reset": {1, 3, 4},
    "quota-reserve": {4},
    "refused": {1, 2},
    "auth": {1},
    "transient": {1},
    "interrupted": {130},
    "error": {1},
}
NEEDS_SNAPSHOT = frozenset({"none", "source-limit"})
NEEDS_CHECKPOINT = frozenset({"quota-reset", "quota-reserve"})
"""A quota stop may lack a checkpoint only when none existed (a stop while resolving
the character); it then retries fresh, without --resume."""
TRANSIENT_DELAYS = (timedelta(minutes=5), timedelta(minutes=15), timedelta(minutes=45))
RESET_MARGIN = timedelta(minutes=2)
MAX_CANDIDATES = 3
ALERT_DELAYS = (
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
)
ALERT_TRIES = 12
LOG_PART_BYTES = 50 * 1024**2
"""Each attempt keeps log.txt plus one rotated log.1.txt: at most 100 MB."""
CLEAR_REQUEST = "clear-attention.request"
STOP_BUDGET_S = 90
"""The container's stop grace (docker --stop-timeout) must exceed noticing a stop
(poll, 1 s), the child's termination grace (20 s) and the log drain (30 s)."""


class QueueError(Exception):
    """The queue or state is unusable; the runner refuses to start."""


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(when: datetime | None) -> str | None:
    return None if when is None else when.astimezone(UTC).isoformat(timespec="seconds")


def parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        when = datetime.fromisoformat(value)
    except ValueError:
        return None
    return when if when.utcoffset() is not None else None


def write_json(path: Path, value: Any, mode: int = 0o644) -> None:
    """Atomic, synced replace in the same directory."""
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        with contextlib.suppress(OSError):
            Path(tmp).chmod(mode)
        Path(tmp).replace(path)
        tmp = ""
    finally:
        if tmp:
            with contextlib.suppress(OSError):
                Path(tmp).unlink()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_private(path: Path) -> bytes:
    """A secret file's bytes, POSIX-checked like the necropsy credential file (ADR 0023).

    The directory must be 0700 and the file a 0600 regular file, both owned by
    this user, opened without following links or blocking. Windows (tests
    only) skips the mode checks.
    """
    if sys.platform == "win32":
        return path.read_bytes()
    directory = os.lstat(path.parent)
    if (
        not stat.S_ISDIR(directory.st_mode)
        or directory.st_uid != os.getuid()
        or stat.S_IMODE(directory.st_mode) != 0o700
    ):
        raise PermissionError("the secrets directory must be a 0700 directory owned by this user")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise PermissionError("a secret must be a 0600 regular file owned by this user")
        return handle.read()


# -- queue --------------------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    entry_id: str
    raid: str
    partition: int
    class_id: int
    category: str
    metric: str
    faction: str
    candidates: tuple[str, ...]
    class_name: str = ""

    def label(self) -> dict[str, Any]:
        return {
            "id": self.entry_id,
            "raid": self.raid,
            "class_id": self.class_id,
            "class": self.class_name or f"Class {self.class_id}",
            "category": self.category,
            "metric": self.metric,
            "faction": self.faction,
        }


def load_queue(path: Path) -> tuple[str, list[Entry]]:
    raw = path.read_bytes()
    try:
        data = json.loads(raw)
        if data.get("version") != QUEUE_VERSION:
            raise ValueError("unsupported queue version")
        entries = []
        seen: set[str] = set()
        for item in data["entries"]:
            candidates = tuple(str(c) for c in item["candidates"])
            if not candidates or len(candidates) > MAX_CANDIDATES:
                raise ValueError(f"entry {item['entry_id']} needs 1-{MAX_CANDIDATES} candidates")
            entry = Entry(
                str(item["entry_id"]),
                str(item["raid"]),
                int(item["partition"]),
                int(item["class_id"]),
                str(item["category"]),
                str(item["metric"]),
                str(item["faction"]),
                candidates,
                str(item.get("class", "")),
            )
            if entry.entry_id in seen or not entry.entry_id.replace("-", "").isalnum():
                raise ValueError(f"entry id {entry.entry_id!r} is duplicated or unsafe")
            seen.add(entry.entry_id)
            entries.append(entry)
        if "summary" in data and data["summary"] is None:
            raise ValueError("queue summary must be an object when supplied")
        validate_summary(data.get("summary"), len(entries))
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise QueueError(f"the queue is invalid: {error}") from None
    return hashlib.sha256(raw).hexdigest(), entries


def validate_summary(value: Any, scheduled: int) -> dict[str, int | None]:
    """Absent reuse data stays unknown; a supplied contradictory block is refused."""
    keys = (
        "universe_runs",
        "scheduled_runs",
        "capture_ready_runs",
        "all_registered_runs",
        "offline_reuse_runs",
    )
    if value is None:
        return {key: scheduled if key == "scheduled_runs" else None for key in keys}
    if not isinstance(value, dict) or any(
        type(value.get(key)) is not int or value[key] < 0 for key in keys
    ):
        raise ValueError("queue summary must contain nonnegative integer run counts")
    if (
        value["scheduled_runs"] != scheduled
        or value["universe_runs"] != scheduled + value["capture_ready_runs"]
        or value["capture_ready_runs"] != value["all_registered_runs"] + value["offline_reuse_runs"]
    ):
        raise ValueError("queue summary counts disagree")
    return {key: value[key] for key in keys}


def public_reason(reason: str) -> str:
    """Fixed explanations only: arbitrary receipt strings and host paths stay private."""
    if reason == "running":
        return "Acquiring and saving raid data."
    if reason == "complete":
        return "Capture finished and its archive was verified."
    if reason == "finished with incomplete source data":
        return "Capture ended with source limitations; review the saved evidence."
    if reason == "the Warcraft Logs sign-in needs attention":
        return "Warcraft Logs sign-in needs attention. Capture is paused."
    if reason in ("quota-reset stop", "quota-reserve stop"):
        return "Waiting for the observed quota reset."
    if reason in (
        "quota-reset stop without a known reset time",
        "quota-reserve stop without a known reset time",
    ):
        return "Quota reset time is unknown. Review is needed."
    if reason == "waiting for the hourly quota reset":
        return "Waiting until a scheduled retry. No new capture is running."
    if reason.startswith(
        (
            "free space below the floor",
            "free space fell below the floor",
            "stopped: free space below the floor",
        )
    ):
        return "Available free space is below the safety floor. Capture is paused."
    if reason in (
        "the checkpoint that existed before this attempt is gone",
        "the outcome receipt's checkpoint does not match the saved checkpoint",
    ):
        return "The saved checkpoint could not be verified. Capture is paused for review."
    if reason == "the runner died during an attempt; its exit is unknown":
        return "The previous capture stopped unexpectedly; its exit is unknown. Review is needed."
    if reason == "a snapshot was saved but its report failed; finish it with necropsy offline":
        return "An archive was saved; its report needs offline recovery."
    if reason == "this candidate was refused":
        return "This public candidate could not be used."
    if reason in ("transient failure", "interrupted failure"):
        return "A temporary failure will be retried after backoff."
    if reason in ("transient failures did not clear", "interrupted failures did not clear"):
        return "Repeated temporary failures need review."
    if reason == "every queue entry has ended; this does not mean all data is complete":
        return "Every scheduled run has ended. Partial and refused results still need review."
    if reason.startswith("resuming after a requested stop"):
        return "Continuing after a requested stop."
    return "Review the private runner diagnostics on Tower." if reason else ""


# -- outcome receipts -----------------------------------------------------------


@dataclass(frozen=True)
class Verdict:
    """What the controller does after one attempt."""

    entry_state: str
    reason: str
    retry_at: datetime | None = None
    pause: bool = False
    """Stop the whole queue as Needs attention (not just this entry)."""
    next_candidate: bool = False
    archive: dict[str, str] | None = None


def _typed(data: Any) -> str | None:
    """Why the receipt's shape is wrong, or None."""
    if not isinstance(data, dict):
        return "the outcome receipt is not an object"
    expected: dict[str, tuple[type, ...]] = {
        "version": (int,),
        "exit_code": (int,),
        "stop_class": (str,),
        "reset_at_utc": (str, type(None)),
        "out": (str,),
        "checkpoint_sha256": (str, type(None)),
        "snapshot": (dict, type(None)),
        "written_at_utc": (str,),
    }
    for key, types in expected.items():
        value = data.get(key)
        if not isinstance(value, types) or isinstance(value, bool):
            return f"the outcome receipt field {key} has the wrong type"
    snapshot = data["snapshot"]
    if snapshot is not None and not (
        isinstance(snapshot.get("archive"), str) and isinstance(snapshot.get("sha256"), str)
    ):
        return "the outcome receipt snapshot is malformed"
    return None


def verify_outcome(receipt: Path, inflight: dict[str, Any]) -> dict[str, Any] | str:
    """The receipt when it matches what the runner observed and the files on disk.

    `inflight` holds the runner's own record: the child's exit code, start time
    and output directory. The receipt's own values are never trusted alone.
    """
    try:
        data = json.loads(receipt.read_bytes())
    except FileNotFoundError:
        return "no outcome receipt was written"
    except (OSError, ValueError):
        return "the outcome receipt is unreadable"
    problem = _typed(data)
    if problem:
        return problem
    if data["version"] != OUTCOME_VERSION:
        return "the outcome receipt has an unknown format"
    stop = data["stop_class"]
    if stop not in EXPECTED_EXIT:
        return f"unknown stop class {stop!r}"
    exit_code = inflight["exit"]
    if data["exit_code"] != exit_code or exit_code not in EXPECTED_EXIT[stop]:
        return f"exit code {exit_code} disagrees with the receipt ({stop})"
    written = parse_iso(data["written_at_utc"])
    started = parse_iso(inflight["started_utc"])
    if written is None or started is None or written < started - timedelta(seconds=5):
        return "the outcome receipt is older than this attempt"
    out = Path(inflight["out"]).resolve()
    if Path(data["out"]).resolve() != out:
        return "the outcome receipt names another output directory"
    run = out / ".necropsy-run" / "run.json"
    actual = sha256_file(run) if run.is_file() else None
    if data["checkpoint_sha256"] != actual:
        return "the outcome receipt's checkpoint does not match the saved checkpoint"
    if inflight.get("checkpoint_before") is not None and actual is None:
        return "the checkpoint that existed before this attempt is gone"
    if stop in NEEDS_CHECKPOINT and actual is None and data["checkpoint_sha256"] is not None:
        return "a quota stop left no checkpoint to resume"
    snapshot = data["snapshot"]
    if stop in NEEDS_SNAPSHOT and snapshot is None:
        return "a finished capture names no snapshot"
    if snapshot is not None:
        archive = Path(snapshot["archive"]).resolve()
        if not archive.is_relative_to(out):
            return "the snapshot is outside this candidate's output directory"
        if not archive.is_file() or sha256_file(archive) != snapshot["sha256"]:
            return "the snapshot is missing or does not match its recorded SHA-256"
    checked: dict[str, Any] = data
    return checked


def decide(data: dict[str, Any], transient_attempts: int, now: datetime) -> Verdict:
    stop = data["stop_class"]
    snapshot = data["snapshot"]
    archive = None if snapshot is None else {k: snapshot[k] for k in ("archive", "sha256")}
    if stop == "none":
        return Verdict(COMPLETE, "complete", archive=archive)
    if stop == "source-limit":
        return Verdict(PARTIAL, "finished with incomplete source data", archive=archive)
    if stop in ("quota-reset", "quota-reserve"):
        reset = parse_iso(data["reset_at_utc"])
        if reset is None:
            return Verdict(DEFERRED, f"{stop} stop without a known reset time", pause=True)
        return Verdict(DEFERRED, f"{stop} stop", retry_at=max(reset, now) + RESET_MARGIN)
    if stop == "refused":
        return Verdict(REFUSED, "this candidate was refused", next_candidate=True)
    if stop == "auth":
        return Verdict(PENDING, "the Warcraft Logs sign-in needs attention", pause=True)
    if stop in ("transient", "interrupted"):
        if transient_attempts >= len(TRANSIENT_DELAYS):
            return Verdict(RETRY, f"{stop} failures did not clear", pause=True)
        delay = TRANSIENT_DELAYS[transient_attempts]
        return Verdict(RETRY, f"{stop} failure", retry_at=now + delay)
    reason = "the run failed unexpectedly"
    if archive is not None:
        reason = "a snapshot was saved but its report failed; finish it with necropsy offline"
    return Verdict(PENDING, reason, pause=True, archive=archive)


# -- alerts ---------------------------------------------------------------------


@dataclass
class Notifier:
    """Notifiarr passthrough with the key and channel read from a private file."""

    secrets: Path | None
    post: Callable[[str, bytes], None] | None = None

    def send(self, title: str, text: str) -> bool:
        if self.secrets is None:
            return False
        try:
            data = json.loads(read_private(self.secrets / "notifiarr.json"))
            key, channel = str(data["api_key"]), int(data["channel_id"])
            body = json.dumps(
                {
                    "notification": {"name": "necropsy-capture", "event": title},
                    "discord": {
                        "ids": {"channel": channel},
                        "text": {"title": title, "description": text},
                    },
                }
            ).encode("utf-8")
            url = f"https://notifiarr.com/api/v1/notification/passthrough/{key}"
            (self.post or _post)(url, body)
            return True
        except Exception:
            return False


ALERT_USER_AGENT = "necropsy-capture"
"""Notifiarr sits behind Cloudflare, which refuses urllib's default User-Agent."""


def _post(url: str, body: bytes) -> None:
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "User-Agent": ALERT_USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status >= 300:
            raise OSError(f"alert delivery answered {response.status}")


# -- child supervision ------------------------------------------------------------


def _copy_log(source: IO[bytes], log: Path) -> None:
    """Copy child output into log.txt, rotating once to log.1.txt (bounded)."""
    rotated = log.with_name("log.1.txt")
    out = log.open("wb")
    written = 0
    try:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            while chunk:
                if written >= LOG_PART_BYTES:
                    out.close()
                    log.replace(rotated)
                    out = log.open("wb")
                    written = 0
                part = chunk[: LOG_PART_BYTES - written]
                out.write(part)
                written += len(part)
                chunk = chunk[len(part) :]
    finally:
        out.close()


def _stop_child(child: subprocess.Popen[bytes], grace_s: float) -> None:
    if child.poll() is not None:
        return
    with contextlib.suppress(ProcessLookupError, OSError):
        if sys.platform == "win32":
            child.terminate()
        else:
            os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=grace_s)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError, OSError):
            if sys.platform == "win32":
                child.kill()
            else:
                os.killpg(child.pid, signal.SIGKILL)
        child.wait()


# -- controller -----------------------------------------------------------------


@dataclass
class Paths:
    queue: Path
    state: Path
    out: Path
    cache: Path
    www: Path
    secrets: Path | None = None


@dataclass
class Runner:
    paths: Paths
    necropsy: Sequence[str] = ("necropsy",)
    now: Callable[[], datetime] = utcnow
    sleep: Callable[[float], None] = time.sleep
    notifier: Notifier | None = None
    attempt_timeout_s: float = 6 * 3600
    free_floor_bytes: int = 50 * 1024**3
    heartbeat_s: float = 60.0
    poll_s: float = 1.0
    stop_grace_s: float = 20.0
    exit_when_idle: bool = False
    """Tests stop at Finished or Needs attention; a server runner stays up."""
    state: dict[str, Any] = field(default_factory=dict)
    entries: list[Entry] = field(default_factory=list)
    summary: dict[str, int | None] = field(default_factory=dict)
    stopping: threading.Event = field(default_factory=threading.Event)
    _published: datetime | None = None

    # -- persistence
    @property
    def state_file(self) -> Path:
        return self.paths.state / "state.json"

    def load(self) -> None:
        digest, self.entries = load_queue(self.paths.queue)
        raw_queue = self.paths.queue.read_bytes()
        if hashlib.sha256(raw_queue).hexdigest() != digest:
            raise QueueError("the queue changed while it was loading")
        self.summary = validate_summary(json.loads(raw_queue).get("summary"), len(self.entries))
        if self.state_file.exists():
            state = json.loads(self.state_file.read_bytes())
            if state.get("version") != STATE_VERSION or state.get("queue_sha256") != digest:
                raise QueueError("the state belongs to a different queue; refusing to mix them")
            self.state = state
        else:
            self.state = {
                "version": STATE_VERSION,
                "queue_sha256": digest,
                "controller": {"state": RUNNING, "reason": "", "finished_at": None},
                "entries": {},
                "inflight": None,
                "outbox": [],
                "delivered": [],
                "alert_failures": 0,
                "last_progress_utc": None,
            }
        for entry in self.entries:
            self.state["entries"].setdefault(
                entry.entry_id,
                {
                    "state": PENDING,
                    "candidate": 0,
                    "transient": 0,
                    "retry_at": None,
                    "reason": "",
                    "archives": [],
                    "attempts": 0,
                },
            )

    def save(self) -> None:
        write_json(self.state_file, self.state)
        self.publish()

    def set_controller(self, state: str, reason: str = "") -> None:
        finished = iso(self.now()) if state == FINISHED else None
        self.state["controller"] = {"state": state, "reason": reason, "finished_at": finished}

    # -- status
    def status(self) -> dict[str, Any]:
        controller = self.state["controller"]
        counts = dict.fromkeys((COMPLETE, PARTIAL, REFUSED, PENDING, DEFERRED, RETRY), 0)
        rows, archives = [], 0
        by_id = {e.entry_id: e for e in self.entries}
        for entry in self.entries:
            info = self.state["entries"][entry.entry_id]
            counts[info["state"]] += 1
            archives += len(info["archives"])
            rows.append(
                entry.label()
                | {
                    "result": info["state"],
                    "reason": public_reason(info["reason"]),
                    "retry_at_utc": info["retry_at"],
                    "archives": len(info["archives"]),
                }
            )
        due = [
            when
            for info in self.state["entries"].values()
            if info["state"] in (DEFERRED, RETRY)
            and (when := parse_iso(info["retry_at"])) is not None
        ]
        inflight = self.state["inflight"]
        current = None
        if inflight is not None and inflight["entry"] in by_id:
            active = by_id[inflight["entry"]]
            current = active.label() | {
                "attempt": inflight["attempt"],
                "candidate": inflight["candidate"] + 1,
                "candidate_count": len(active.candidates),
            }
        return {
            "version": 1,
            "headline": HEADLINES[controller["state"]],
            "state": controller["state"],
            "reason": self.public_context(controller["reason"]),
            "queue_sha256": self.state["queue_sha256"],
            "summary": self.summary,
            "heartbeat_utc": iso(self.now()),
            "last_progress_utc": self.state["last_progress_utc"],
            "next_retry_utc": iso(min(due)) if due else None,
            "finished_at_utc": controller["finished_at"],
            "current": current,
            "counts": counts,
            "usable_archives": archives,
            "alert_failures": self.state["alert_failures"],
            "alerts_pending": len(self.state["outbox"]),
            "entries": rows,
        }

    def public_context(self, reason: str) -> str:
        """Remove only a known queue identifier before applying the fixed copy allowlist."""
        for entry in self.entries:
            prefix = entry.entry_id + ": "
            if reason.startswith(prefix):
                return public_reason(reason[len(prefix) :])
        return public_reason(reason)

    def publish(self) -> None:
        write_json(self.paths.www / "status.json", self.status())
        self._published = self.now()

    def heartbeat(self) -> None:
        if self._published is None or (self.now() - self._published).total_seconds() >= (
            self.heartbeat_s
        ):
            self.publish()

    # -- alerts: a durable outbox, delivered with bounded retries
    def alert(self, key: str, title: str, text: str) -> None:
        """Queue an alert once per key; delivery happens in flush()."""
        if key in self.state["delivered"] or any(a["key"] == key for a in self.state["outbox"]):
            return
        self.state["outbox"].append(
            {"key": key, "title": title, "text": text, "tries": 0, "next_try_utc": None}
        )

    def flush(self) -> None:
        if self.notifier is None or not self.state["outbox"]:
            return
        now, changed = self.now(), False
        for item in list(self.state["outbox"]):
            when = parse_iso(item["next_try_utc"])
            if when is not None and when > now:
                continue
            changed = True
            if self.notifier.send(item["title"], item["text"]):
                self.state["outbox"].remove(item)
                self.state["delivered"].append(item["key"])
                continue
            item["tries"] += 1
            self.state["alert_failures"] += 1
            if item["tries"] >= ALERT_TRIES:
                self.state["outbox"].remove(item)
                continue
            delay = ALERT_DELAYS[min(item["tries"] - 1, len(ALERT_DELAYS) - 1)]
            item["next_try_utc"] = iso(now + delay)
        if changed:
            self.save()

    def commit(self) -> None:
        self.save()
        self.flush()

    # -- control
    def attention(self, reason: str, key: str) -> None:
        """Pause as a new incident; only a clear naming this incident resumes it."""
        self.state["incident"] = self.state.get("incident", 0) + 1
        self.set_controller(ATTENTION, reason)
        self.alert(
            key,
            "Necropsy capture needs attention",
            self.public_context(reason) + " Open Capture watch for the last saved status.",
        )

    def next_entry(self) -> tuple[Entry | None, datetime | None]:
        """The next runnable entry, or the earliest retry time when all are waiting."""
        now = self.now()
        earliest: datetime | None = None
        for entry in self.entries:
            info = self.state["entries"][entry.entry_id]
            if info["state"] in TERMINAL:
                continue
            retry = parse_iso(info["retry_at"])
            if retry is not None and retry > now:
                earliest = retry if earliest is None else min(earliest, retry)
                continue
            return entry, None
        return None, earliest

    def floor_problem(self) -> str | None:
        for path in (self.paths.out, self.paths.cache, self.paths.state):
            if shutil.disk_usage(path).free < self.free_floor_bytes:
                return f"free space below the floor on {path}"
        return None

    def run(self) -> int:
        """Work through the loaded queue.

        Returns 0 when stopping and, with `exit_when_idle`, 0 at Finished or 3
        at Needs attention. A server runner instead stays up at both, keeps its
        heartbeat and alert outbox going, and continues when a clear request
        appears. A state or status write that fails (for example a full disk)
        returns 3: continuing would lose track of what was captured.
        """
        try:
            return self._run()
        except OSError as error:
            if self.notifier is not None:
                self.notifier.send(
                    "Necropsy capture needs attention",
                    f"the runner could not save its state ({type(error).__name__})",
                )
            return 3

    def _run(self) -> int:
        if self.state["controller"]["state"] not in (ATTENTION, FINISHED):
            self.set_controller(RUNNING)
            self.alert(
                "start:" + self.state["queue_sha256"],
                "Necropsy capture started",
                f"{len(self.entries)} scheduled capture runs. "
                "This collects evidence; it does not validate cells.",
            )
        self.commit()
        while not self.stopping.is_set():
            controller = self.state["controller"]["state"]
            if controller in (ATTENTION, FINISHED):
                if self.exit_when_idle:
                    return 3 if controller == ATTENTION else 0
                self.idle()
                continue
            entry, wait_until = self.next_entry()
            if entry is None and wait_until is None:
                self.set_controller(
                    FINISHED, "every queue entry has ended; this does not mean all data is complete"
                )
                counts = self.status()["counts"]
                self.alert(
                    "finished",
                    "Necropsy capture finished",
                    f"complete {counts[COMPLETE]}, partial {counts[PARTIAL]}, "
                    f"refused {counts[REFUSED]}. Every scheduled run has ended; "
                    "partial and refused results still need review. No cell completion is implied.",
                )
                self.commit()
                continue
            if entry is None:
                assert wait_until is not None
                self.set_controller(WAITING, "waiting for the hourly quota reset")
                self.commit()
                self.wait(wait_until)
                continue
            problem = self.floor_problem()
            if problem:
                self.attention(problem, f"floor:{iso(self.now())}")
                self.commit()
                continue
            self.set_controller(RUNNING)
            self.attempt(entry)
        return 0

    def idle(self) -> None:
        """At Finished or Needs attention: heartbeat, alert retries, clear requests."""
        request = self.paths.state / CLEAR_REQUEST
        if request.exists():
            if self.clear_matches(request):
                inflight = self.state["inflight"]
                if inflight is not None and inflight["exit"] is None:
                    # A person cleared it: the unknown attempt is dropped and the entry
                    # resumes from its checkpoint.
                    self.state["inflight"] = None
                self.set_controller(RUNNING)
                self.commit()
            # Consumed or stale: a later restart sees no attention for that incident,
            # so the request can never clear a different pause.
            request.unlink()
            return
        self.heartbeat()
        self.flush()
        self.sleep(self.poll_s)

    def clear_matches(self, request: Path) -> bool:
        """A clear applies once, to the current attention incident of this queue."""
        try:
            data = json.loads(request.read_bytes())
        except (OSError, ValueError):
            return False
        return (
            isinstance(data, dict)
            and self.state["controller"]["state"] == ATTENTION
            and data.get("queue_sha256") == self.state["queue_sha256"]
            and data.get("incident") == self.state.get("incident")
        )

    def wait(self, until: datetime) -> None:
        while not self.stopping.is_set():
            if (until - self.now()).total_seconds() <= 0:
                return
            self.heartbeat()
            self.flush()
            self.sleep(self.poll_s)

    def attempt(self, entry: Entry) -> None:
        info = self.state["entries"][entry.entry_id]
        candidate = info["candidate"]
        out = self.paths.out / entry.entry_id / f"candidate-{candidate}"
        out.mkdir(parents=True, exist_ok=True)
        # A directory left by a crash before the state recorded it is kept as evidence
        # and skipped; attempt directories are never reused.
        number = info["attempts"] + 1
        root = self.paths.state / "attempts" / entry.entry_id
        root.mkdir(parents=True, exist_ok=True)
        while (root / f"{number:03d}").exists():
            number += 1
        info["attempts"] = number
        attempt_dir = root / f"{number:03d}"
        attempt_dir.mkdir()
        receipt = attempt_dir / "outcome.json"
        resume = (out / ".necropsy-run" / "run.json").is_file()
        command = [
            *self.necropsy,
            "analyze",
            entry.candidates[candidate],
            "--raid",
            entry.raid,
            "--partition",
            str(entry.partition),
            "--spec",
            entry.category,
            "--metric",
            entry.metric,
            "--faction",
            entry.faction,
            "--endpoint",
            "user",
            "--cache",
            str(self.paths.cache),
            "--out",
            str(out),
            "--outcome-json",
            str(receipt),
            *(["--resume"] if resume else []),
        ]
        self.state["inflight"] = {
            "entry": entry.entry_id,
            "attempt": info["attempts"],
            "candidate": candidate,
            "started_utc": iso(self.now()),
            "out": str(out),
            "receipt": str(receipt),
            "exit": None,
            "stop_requested": False,
            "checkpoint_before": (
                sha256_file(out / ".necropsy-run" / "run.json") if resume else None
            ),
        }
        info["reason"] = "running"
        self.commit()
        how, code = self.supervise(command, attempt_dir / "log.txt")
        inflight = self.state["inflight"]
        if how == "stopped":
            self.mark_stop_requested()
            self.publish()
            return
        if how == "floor":
            self.state["inflight"] = None
            info["reason"] = "stopped: free space below the floor; resumes from its checkpoint"
            self.attention("free space fell below the floor during a capture", "floor-run")
            self.commit()
            return
        inflight["exit"] = code
        self.save()
        self.apply()

    def apply(self) -> None:
        """Commit the in-flight attempt's result and clear it in one state write."""
        inflight = self.state["inflight"]
        entry = next(e for e in self.entries if e.entry_id == inflight["entry"])
        info = self.state["entries"][entry.entry_id]
        data = verify_outcome(Path(inflight["receipt"]), inflight)
        self.state["inflight"] = None
        if isinstance(data, str):
            info["reason"] = data
            self.attention(f"{entry.entry_id}: {data}", f"receipt:{inflight['receipt']}")
            self.commit()
            return
        now = self.now()
        verdict = decide(data, info["transient"], now)
        info["reason"] = verdict.reason
        info["retry_at"] = iso(verdict.retry_at)
        if verdict.archive is not None and verdict.archive not in info["archives"]:
            info["archives"].append(verdict.archive)
            self.state["last_progress_utc"] = iso(now)
        if verdict.entry_state == DEFERRED and verdict.retry_at is not None:
            self.state["last_progress_utc"] = iso(now)
        info["transient"] = info["transient"] + 1 if verdict.entry_state == RETRY else 0
        if verdict.next_candidate:
            self.alert(
                f"refused:{entry.entry_id}:{inflight['candidate']}",
                "Necropsy capture refused a candidate",
                f"{entry.class_name or 'Class ' + str(entry.class_id)} {entry.category}, "
                f"{entry.raid.upper()}, {entry.faction}: candidate {inflight['candidate'] + 1} "
                f"of {len(entry.candidates)} could not be used. "
                + (
                    "Trying the next checked candidate."
                    if inflight["candidate"] + 1 < len(entry.candidates)
                    else "No checked candidates remain for this run."
                ),
            )
            if inflight["candidate"] + 1 < len(entry.candidates):
                info["candidate"] = inflight["candidate"] + 1
                info["state"] = PENDING
                info["retry_at"] = None
            else:
                info["state"] = REFUSED
        else:
            info["state"] = verdict.entry_state
        if verdict.pause:
            self.attention(f"{entry.entry_id}: {verdict.reason}", f"pause:{inflight['receipt']}")
        self.commit()

    def supervise(self, command: list[str], log: Path) -> tuple[str, int | None]:
        """("exit", code), ("stopped", None) or ("floor", None); the child is always reaped."""
        child = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=sys.platform != "win32",
        )
        assert child.stdout is not None
        copier = threading.Thread(target=_copy_log, args=(child.stdout, log), daemon=True)
        copier.start()
        deadline = time.monotonic() + self.attempt_timeout_s
        last_floor = time.monotonic()
        try:
            while True:
                try:
                    code = child.wait(timeout=self.poll_s)
                    return "exit", code
                except subprocess.TimeoutExpired:
                    pass
                if self.stopping.is_set():
                    # Record the intent before the (possibly long) cleanup, so a death
                    # during it still resumes instead of asking for attention.
                    self.mark_stop_requested()
                    return "stopped", None
                if time.monotonic() > deadline:
                    _stop_child(child, self.stop_grace_s)
                    return "exit", child.returncode
                if time.monotonic() - last_floor >= self.heartbeat_s:
                    last_floor = time.monotonic()
                    if self.floor_problem():
                        return "floor", None
                self.heartbeat()
        finally:
            _stop_child(child, self.stop_grace_s)
            copier.join(timeout=30)

    def mark_stop_requested(self) -> None:
        inflight = self.state.get("inflight")
        if inflight is not None and not inflight["stop_requested"]:
            inflight["stop_requested"] = True
            write_json(self.state_file, self.state)

    def reconcile(self) -> None:
        """After a restart, finish an attempt the previous runner left in flight.

        A known exit code is applied exactly once. An unknown one means the runner
        stopped or died while the child ran: a requested stop resumes from the
        checkpoint; anything else needs a person, because the receipt alone can't
        prove what happened.
        """
        inflight = self.state["inflight"]
        if inflight is None:
            return
        if inflight["exit"] is not None:
            self.apply()
            return
        info = self.state["entries"][inflight["entry"]]
        if inflight["stop_requested"]:
            self.state["inflight"] = None
            info["reason"] = "resuming after a requested stop"
            self.save()
            return
        if self.state["controller"]["state"] == ATTENTION:
            return  # already the open incident; a restart must not start a new one
        info["reason"] = "the runner died during an attempt; its exit is unknown"
        self.attention(f"{inflight['entry']}: {info['reason']}", f"died:{inflight['receipt']}")
        self.save()


# -- watchdog (runs from host cron, outside the runner's container) ----------------

STALE_AFTER = timedelta(minutes=10)
STALL_AFTER = timedelta(hours=8)
"""Longer than one supervised attempt (6 h) plus margin."""
BACKUP_WINDOW = (clock_time(3, 0), clock_time(3, 45))
"""The nightly appdata backup stops and restarts containers (host local time)."""


def watchdog_check(status: Any, now: datetime, local: datetime) -> tuple[str, str] | None:
    """(alert key, message) when the runner looks dead or stuck, else None.

    A dead runner cannot alert for itself, which is why this runs separately; a
    whole-host outage still can't be reported from that host.
    """
    if not isinstance(status, dict):
        return "unreadable", "the capture status could not be read"
    beat = parse_iso(status.get("heartbeat_utc"))
    if beat is None or now - beat > STALE_AFTER:
        quiet = status.get("state") == FINISHED and not status.get("alerts_pending")
        if quiet or BACKUP_WINDOW[0] <= local.time() < BACKUP_WINDOW[1]:
            return None
        return "stale", f"the capture runner has not reported since {iso(beat) or 'unknown'}"
    if status.get("state") in (WAITING, FINISHED, ATTENTION):
        return None
    progress = parse_iso(status.get("last_progress_utc"))
    if progress is not None and now - progress > STALL_AFTER:
        return "stall", f"no capture progress since {iso(progress)}"
    return None


def watchdog(status_path: Path, memory_path: Path, notifier: Notifier) -> int:
    """Alert once per problem; 0 healthy, 1 a problem is open."""
    try:
        status = json.loads(status_path.read_bytes())
    except (OSError, ValueError):
        status = None
    now = utcnow()
    problem = watchdog_check(status, now, datetime.now())
    try:
        memory = json.loads(memory_path.read_bytes())
    except (OSError, ValueError):
        memory = {}
    if not isinstance(memory, dict):
        memory = {}
    if problem is None:
        if memory.get("open"):
            write_json(memory_path, {"open": None, "since": None})
        return 0
    key, message = problem
    if memory.get("open") != key and notifier.send("Necropsy capture watchdog", message):
        write_json(memory_path, {"open": key, "since": iso(now)})
    return 1


@contextlib.contextmanager
def single_instance(path: Path) -> Any:
    """An OS-held lock; a second runner on the same state exits at once."""
    handle = path.open("a+b")
    try:
        if sys.platform == "win32":
            import msvcrt

            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise QueueError("another runner holds this state") from None
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise QueueError("another runner holds this state") from None
        yield
    finally:
        handle.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    for name in ("queue", "state", "out", "cache", "www"):
        run.add_argument(f"--{name}", type=Path, required=True)
    run.add_argument("--secrets", type=Path)
    dog = sub.add_parser("watchdog")
    dog.add_argument("--status", type=Path, required=True)
    dog.add_argument("--secrets", type=Path, required=True)
    dog.add_argument("--memory", type=Path, required=True)
    clear = sub.add_parser("clear-attention", help="Let a stopped queue continue after a fix.")
    clear.add_argument("--state", type=Path, required=True)
    test = sub.add_parser("test-alert")
    test.add_argument("--secrets", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "test-alert":
        sent = Notifier(args.secrets).send(
            "Necropsy capture test alert", "If you can read this, alerts reach you."
        )
        print("sent" if sent else "not sent")
        return 0 if sent else 1
    if args.command == "watchdog":
        return watchdog(args.status, args.memory, Notifier(args.secrets))
    if args.command == "clear-attention":
        try:
            state = json.loads((args.state / "state.json").read_bytes())
        except (OSError, ValueError):
            print("no readable runner state", file=sys.stderr)
            return 2
        if state.get("controller", {}).get("state") != ATTENTION:
            print("the queue is not waiting for attention; nothing to clear", file=sys.stderr)
            return 2
        request = {"queue_sha256": state["queue_sha256"], "incident": state.get("incident")}
        write_json(args.state / CLEAR_REQUEST, request)
        print(f"requested a clear of incident {request['incident']}; the runner continues shortly")
        return 0
    paths = Paths(args.queue, args.state, args.out, args.cache, args.www, args.secrets)
    for directory in (paths.state, paths.out, paths.cache, paths.www):
        directory.mkdir(parents=True, exist_ok=True)
    runner = Runner(paths, notifier=Notifier(args.secrets))

    def request_stop(*_: Any) -> None:
        runner.stopping.set()

    signal.signal(signal.SIGTERM, request_stop)
    try:
        with single_instance(paths.state / "runner.lock"):
            runner.load()
            runner.reconcile()
            return runner.run()
    except QueueError as error:
        print(f"capture runner refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
