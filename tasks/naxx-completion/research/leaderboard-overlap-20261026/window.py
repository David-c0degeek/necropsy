# ruff: noqa: S603 - a host operations script that runs the fixed docker CLI
"""Tower-side sole-owner window for fetch.py; production is always restarted.

Runs on the Unraid host as root (Python 3.11). Nothing is stopped unless the
worker is idle in a gated quota wait. Every step from the stop onwards runs
inside an outer try whose finally block always attempts the restart before any
diagnostic read; cleanup errors are recorded, never allowed to skip recovery.
Afterwards the outcome is asserted, not just recorded:

- the fetch exited 0 (a floor or request-limit stop is also exit 0);
- the state bytes at the end of the window equal the post-stop snapshot;
- the worker runs and publishes a heartbeat newer than the restart;
- if the quota gate is still in the future: status waiting, inflight null,
  entries and counts unchanged. If it has elapsed, production may legitimately
  start, so preservation rests on the before-restart byte equality.

With --wait-for-gate the window waits, production still stopped, until the
saved quota gate (observed reset plus margin) before fetching, so the fetch uses
the fresh hourly database allowance that production would otherwise spend. The
gate then has elapsed by the restart, and production may run immediately.

Usage: python3 window.py WORKDIR IMAGE [--wait-for-gate]
"""

import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import time

BASE = pathlib.Path("/mnt/user/appdata/necropsy-naxx-capture-20261023")
NAME = "necropsy-capture"


def utc():
    return datetime.datetime.now(datetime.UTC)


def when(value):
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


class Ops:
    """Host effects, replaceable in the offline tests."""

    def run(self, *args):
        return subprocess.run(list(args), text=True, capture_output=True, check=True).stdout.strip()

    def fetch(self, work, image):
        command = ["docker", "run", "--rm", "--user", "99:100"]
        command += ["--mount", f"type=bind,src={BASE / 'secrets'},dst=/secrets,readonly"]
        command += ["--mount", f"type=bind,src={work},dst=/work"]
        command += ["--entrypoint", "python", image, "/work/fetch.py", "/work/out"]
        result = subprocess.run(command, text=True, capture_output=True)
        (work / "fetch.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        return result.returncode

    def state_bytes(self):
        return (BASE / "state/state.json").read_bytes()

    def status(self):
        return json.loads((BASE / "www/status.json").read_bytes())

    def sleep(self, seconds):
        time.sleep(seconds)

    def now(self):
        return utc()


def window(work, image, ops, wait_for_gate=False):
    receipt = {"started_at": ops.now().isoformat(), "image": image, "cleanup_errors": []}
    # Preconditions: nothing has been touched yet, so a failure here is harmless.
    before = ops.state_bytes()
    state = json.loads(before)
    public = ops.status()
    gate = state.get("quota_until_utc")
    assert state["inflight"] is None, state["inflight"]
    assert state["controller"]["state"] == public["state"] == "waiting", public["state"]
    assert gate and when(gate) > ops.now() + datetime.timedelta(minutes=10), gate
    if wait_for_gate:
        assert when(gate) < ops.now() + datetime.timedelta(minutes=70), "gate too far away"
    procs = ops.run("docker", "top", NAME, "-eo", "pid,comm").splitlines()[1:]
    assert len(procs) == 2 and {line.split()[1] for line in procs} == {"docker-init", "python"}
    assert json.loads(ops.run("docker", "inspect", NAME))[0]["Image"] == image
    (work / "state-before-stop.json").write_bytes(before)
    receipt.update(
        gate=gate,
        counts_before=public["counts"],
        state_sha256_before_stop=hashlib.sha256(before).hexdigest(),
    )
    stopped = None
    try:
        ops.run("docker", "stop", "--time", "90", NAME)
        stopped = ops.state_bytes()
        (work / "state-after-stop.json").write_bytes(stopped)
        receipt["state_sha256_after_stop"] = hashlib.sha256(stopped).hexdigest()
        if wait_for_gate:
            while ops.now() < when(gate):
                ops.sleep(min(30.0, (when(gate) - ops.now()).total_seconds()))
            receipt["fetch_started_after_gate"] = ops.now().isoformat()
        receipt["fetch_exit"] = ops.fetch(work, image)
        receipt["state_unchanged_during_window"] = ops.state_bytes() == stopped
    except Exception as error:
        receipt["cleanup_errors"].append(f"window: {error!r}")
    finally:
        receipt["window_end"] = ops.now().isoformat()
        restarted_at = ops.now()
        try:
            ops.run("docker", "start", NAME)
        except Exception as error:
            receipt["cleanup_errors"].append(f"restart: {error!r}")
    # Diagnostics only after the restart attempt.
    fresh = False
    current = None
    for _ in range(60):
        try:
            current = ops.status()
            if when(current["heartbeat_utc"]) >= restarted_at.replace(microsecond=0):
                fresh = True
                break
        except (OSError, ValueError, KeyError) as error:
            receipt["cleanup_errors"].append(f"status: {error!r}")
        ops.sleep(1)
    receipt["heartbeat_fresh"] = fresh
    try:
        resumed = json.loads(ops.state_bytes())
        inspect = json.loads(ops.run("docker", "inspect", NAME))[0]
        stopped_state = json.loads(stopped) if stopped is not None else None
        receipt.update(
            worker_running=inspect["State"]["Running"],
            status_after=None if current is None else current["state"],
            counts_after=None if current is None else current["counts"],
            inflight_after=resumed["inflight"],
            entries_unchanged=stopped_state is not None
            and resumed["entries"] == stopped_state["entries"],
            gate_elapsed_at_restart=when(gate) <= restarted_at,
        )
    except Exception as error:
        receipt["cleanup_errors"].append(f"verify: {error!r}")
    (work / "window-receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(receipt, indent=1))
    problems = []
    if receipt.get("fetch_exit") != 0:
        problems.append("fetch did not exit 0")
    if not receipt.get("state_unchanged_during_window"):
        problems.append("state changed during the window, or was not compared")
    if not receipt.get("worker_running") or not fresh:
        problems.append("worker not running with a fresh heartbeat")
    if receipt.get("gate_elapsed_at_restart") is not True and not (
        receipt.get("status_after") == "waiting"
        and receipt.get("inflight_after") is None
        and receipt.get("entries_unchanged")
        and receipt.get("counts_after") == receipt["counts_before"]
    ):
        problems.append("preserved gated wait not restored")
    if receipt["cleanup_errors"]:
        problems.append("cleanup errors recorded")
    assert not problems, problems
    return receipt


if __name__ == "__main__":
    window(pathlib.Path(sys.argv[1]), sys.argv[2], Ops(), "--wait-for-gate" in sys.argv[3:])
