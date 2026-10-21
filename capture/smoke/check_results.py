"""Check the results of capture/smoke/run_smoke.sh against the production queue.

uv run python capture/smoke/check_results.py RESULTS_DIR
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY))

from scripts import capture_runner as cr  # noqa: E402


def lines(path: Path) -> list[Any]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main(results: Path, queue: Path | None = None) -> int:
    failures: list[str] = []

    def expect(ok: bool, what: str) -> None:
        print(("ok    " if ok else "FAIL  ") + what)
        if not ok:
            failures.append(what)

    # S1: the real analyze without a credential file.
    s1 = results / "s1"
    net = lines(s1 / "net.jsonl") if (s1 / "net.jsonl").exists() else []
    loaded = {tuple(e["argv"][:2]) for e in net if e["event"] == "audit.loaded"}
    expect(("/app/capture_runner.py", "run") in loaded, "S1 audit hook loaded in the runner")
    expect(("/usr/local/bin/necropsy", "analyze") in loaded, "S1 audit hook loaded in analyze")
    expect(all(e["event"] == "audit.loaded" for e in net), "S1 no socket attempt at all")
    state = json.loads((s1 / "state.json").read_text(encoding="utf-8"))
    expect(state["controller"]["state"] == cr.ATTENTION, "S1 queue needs attention")
    receipts = sorted((s1 / "attempts").rglob("outcome.json"))
    receipt = json.loads(receipts[0].read_text(encoding="utf-8")) if receipts else {}
    expect(len(receipts) == 1, "S1 exactly one attempt")
    expect(
        receipt.get("stop_class") == "auth" and receipt.get("exit_code") == 1,
        "S1 real auth receipt",
    )

    # S2: fake analyze, stop/restart, quota wait, alerts.
    s2 = results / "s2"
    stop = json.loads((s2 / "stop1.json").read_text(encoding="utf-8"))
    expect(stop["exit_code"] == 0 and stop["stop_seconds"] <= 90, f"S2 graceful stop {stop}")
    after = json.loads((s2 / "state-after-stop.json").read_text(encoding="utf-8"))
    expect(bool(after["inflight"] and after["inflight"]["stop_requested"]), "S2 stop recorded")
    _, entries = cr.load_queue(
        queue or REPOSITORY / "tasks" / "raid-completion" / "capture-queue.json"
    )
    by_id = {entry.entry_id: entry for entry in entries}
    calls = lines(s2 / "argv.jsonl")
    mismatched = 0
    for call in calls:
        out = call[call.index("--out") + 1]
        entry = by_id[out.split("/")[3]]
        candidate = int(out.rsplit("-", 1)[1])
        expected = [
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
            "/data/cache",
            "--out",
            out,
            "--outcome-json",
            call[call.index("--outcome-json") + 1],
            *(["--resume"] if "--resume" in call else []),
        ]
        mismatched += call != expected
    expect(mismatched == 0, f"S2 {len(calls)} analyze calls with the production argv")
    resumed = [i for i, call in enumerate(calls) if "--resume" in call]
    expect(resumed[:1] == [1], "S2 the stopped attempt resumed with --resume")
    expect(len(resumed) == 3, "S2 deferred entries resumed after the wait")
    net = lines(s2 / "net.jsonl")
    sockets = [e for e in net if e["event"].startswith("socket.")]
    expect(all(e["allowed"] for e in sockets), "S2 only the loopback fake was contacted")
    posts = lines(s2 / "notifiarr.jsonl")
    titles = [post["body"]["discord"]["text"]["title"] for post in posts]
    expect(
        titles == ["Necropsy capture started", "Necropsy capture needs attention"],
        f"S2 alerts {titles}",
    )
    final = json.loads((s2 / "state.json").read_text(encoding="utf-8"))
    expect(final["controller"]["state"] == cr.ATTENTION, "S2 auth stop paused the queue")
    expect(final["outbox"] == [] and final["alert_failures"] == 0, "S2 every alert delivered")
    print(f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--queue", type=Path, help="exact queue staged into the tested image")
    args = parser.parse_args()
    raise SystemExit(main(args.results, args.queue))
