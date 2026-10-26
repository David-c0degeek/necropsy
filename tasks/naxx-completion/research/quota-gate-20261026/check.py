"""Verify migration of the preserved production state without network or state writes."""

import argparse
import collections
import hashlib
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.capture_runner import Paths, Runner  # noqa: E402

SOURCE = ROOT / "workspace/quota-gate-20261026/state-before-clear-20261026T1345.json"
SOURCE_SHA256 = "9dd2a0ffdc7f031f9e8e1797a2e69adf056a5daa74b148e196e314b2146a5dfa"
QUEUE = ROOT / "tasks/naxx-completion/capture-queue.json"
QUEUE_SHA256 = "888b8d8d0355e985c7d8017f61b3dd864af56fd58d3701771647ce4eb9fc8552"
RECEIPT = Path(__file__).with_name("receipt.json")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check():
    raw = SOURCE.read_bytes()
    require(digest(raw) == SOURCE_SHA256, "preserved production state differs")
    require(digest(QUEUE.read_bytes()) == QUEUE_SHA256, "capture queue differs")
    source = json.loads(raw)
    require(source["queue_sha256"] == QUEUE_SHA256, "state belongs to another queue")
    records = json.dumps(source["entries"], sort_keys=True).encode()
    results = []
    # Frozen clocks test the observed incident window and the supplied pre-clear time.
    for at, expected_gate in (
        ("2026-10-26T12:41:46+00:00", "2026-10-26T13:40:47+00:00"),
        ("2026-10-26T13:43:54+00:00", None),
    ):
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            state = scratch / "state"
            state.mkdir()
            (state / "state.json").write_bytes(raw)
            paths = Paths(QUEUE, state, scratch / "out", scratch / "cache", scratch / "www")
            runner = Runner(paths, now=lambda at=at: datetime.fromisoformat(at))
            runner.load()
            require(
                runner.state == source | {"quota_until_utc": expected_gate},
                f"migration changed more than the expected gate at {at}",
            )
            require((state / "state.json").read_bytes() == raw, "load wrote preserved state")
            results.append(
                {"clock": at, "expected_gate": expected_gate, "all_other_state_equal": True}
            )
    return {
        "kind": "Offline migration proof for a hash-pinned pre-clear production state",
        "source": {"path": SOURCE.relative_to(ROOT).as_posix(), "sha256": SOURCE_SHA256},
        "queue_sha256": QUEUE_SHA256,
        "runner_sha256": digest((ROOT / "scripts/capture_runner.py").read_bytes()),
        "entries": len(source["entries"]),
        "entry_records_sha256": digest(records),
        "counts": dict(
            sorted(collections.Counter(e["state"] for e in source["entries"].values()).items())
        ),
        "preserved_attention_incident": source["incident"],
        "state_version": source["version"],
        "clocks": results,
        "limits": [
            "The fixture is a retained on-NAS state copy, not an off-server backup.",
            "A clean checkout needs the pinned private workspace input restored before replay.",
            "Expired waits do not create a new deadline or clear an existing attention incident.",
            "No WCL call, production-state write, credential access or live recovery occurs.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = check()
    if args.out:
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(result, indent=2) + "\n")
    else:
        require(result == json.loads(RECEIPT.read_bytes()), "migration receipt differs")
    print("PASS: production-state migration preserves every field except the expected gate")
