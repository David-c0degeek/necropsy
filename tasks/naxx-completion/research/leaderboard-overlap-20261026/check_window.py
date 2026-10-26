"""Offline checks of window.py's recovery with mocked host effects; no Docker or WCL.

Run: python tasks/naxx-completion/research/leaderboard-overlap-20261026/check_window.py
"""

import datetime
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import window

NOW = datetime.datetime(2026, 10, 26, 18, 0, tzinfo=datetime.UTC)
IMAGE = "sha256:image"
GATE = "2026-10-26T18:40:00+00:00"


class Mock:
    def __init__(self, fail_at=None, stale=False, state_after=None, status_after="waiting"):
        self.calls, self.fail_at, self.stale = [], fail_at, stale
        self.reads = 0
        self.started = False
        self.state = {
            "inflight": None,
            "controller": {"state": "waiting"},
            "quota_until_utc": GATE,
            "entries": {"a": {"state": "deferred"}},
        }
        self.state_after = state_after
        self.status_after = status_after

    def now(self):
        return NOW

    def run(self, *args):
        self.calls.append(args[1])
        if args[1] == "top":
            return "PID COMMAND\n1 docker-init\n2 python"
        if args[1] == "inspect":
            return json.dumps([{"Image": IMAGE, "State": {"Running": self.started}}])
        if args[1] == "start":
            self.started = True
        return ""

    def fetch(self, work, image):
        if self.fail_at == "fetch":
            raise RuntimeError("fetch crashed")
        return 0

    def state_bytes(self):
        self.reads += 1
        if self.fail_at == "after-stop" and self.reads == 2:
            raise OSError("state unreadable right after stop")
        if self.fail_at == "final-read" and self.reads == 3:
            raise OSError("state unreadable at the end of the window")
        state = self.state_after if (self.started and self.state_after) else self.state
        return json.dumps(state).encode()

    def status(self):
        beat = NOW - datetime.timedelta(minutes=5) if self.stale else NOW
        return {
            "state": self.status_after if self.started else "waiting",
            "counts": {"deferred": 1},
            "heartbeat_utc": beat.isoformat(),
        }

    def sleep(self, seconds):
        global NOW
        NOW = NOW + datetime.timedelta(seconds=seconds)


def expect(mock, ok, wait=False):
    global NOW
    NOW = datetime.datetime(2026, 10, 26, 18, 0, tzinfo=datetime.UTC)
    with tempfile.TemporaryDirectory() as directory:
        try:
            window.window(pathlib.Path(directory), IMAGE, mock, wait)
            passed = True
        except AssertionError:
            passed = False
    assert passed is ok, (mock.fail_at, mock.stale, passed)
    assert "start" in mock.calls, "the worker was not restarted"


expect(Mock(), ok=True)
for failure in ("after-stop", "final-read", "fetch"):
    expect(Mock(fail_at=failure), ok=False)  # restart still attempted
expect(Mock(stale=True), ok=False)
changed = {
    "inflight": {"entry": "a"},
    "controller": {"state": "running"},
    "quota_until_utc": None,
    "entries": {"a": {"state": "running"}},
}
expect(Mock(state_after=changed, status_after="running"), ok=False)
# Waiting for the gate: the fetch runs after it, the gate has elapsed at restart,
# and production may then run, so a changed state after the restart is accepted.
waited = Mock(state_after=changed, status_after="running")
expect(waited, ok=True, wait=True)
reached = NOW
assert reached >= window.when(GATE), reached
expect(Mock(fail_at="fetch"), ok=False, wait=True)
print("PASS: restart always attempted; failures, stale heartbeat and unexpected state refused")
