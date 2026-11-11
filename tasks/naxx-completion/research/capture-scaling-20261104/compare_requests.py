"""Compare old and new acquisition query sequences against identical synthetic data.

The baseline is HEAD's acquire.py using the same transport/cache dependencies.
This measures report-request counts, not live point costs or elapsed time.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any

import httpx

from necropsy.wcl import acquire as current
from necropsy.wcl.cache import Cache
from necropsy.wcl.client import RateLimit, WclClient
from necropsy.wcl.sites import VANILLA

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from tests.unit.test_wcl_acquire import PATCHWERK, FakeWcl, Player, _cohort, _context
from tests.wcl_fakes import FakeClock


def run(module: Any, shared_report: bool) -> dict[str, Any]:
    players = _cohort(30, guild=None)
    subject = Player("Haplina")
    if shared_report:
        subject.report, subject.fight, subject.actor_id = "Shared", 1, 1
        for index, player in enumerate(players, 2):
            player.report, player.fight, player.actor_id = "Shared", index, index
    fake = FakeWcl(players, subject)
    client = WclClient(
        VANILLA, lambda _: "synthetic", transport=httpx.MockTransport(fake), clock=FakeClock()
    )
    client.last_rate = RateLimit(36000, 10, 1800)
    try:
        with tempfile.TemporaryDirectory() as folder:
            store = Cache(Path(folder))
            acquisition = module.acquire(
                client, store, VANILLA, _context(), encounters=(PATCHWERK,)
            )
            module.finalize_reports(module.Run(client, store, VANILLA), acquisition)
            boss = acquisition.bosses[0]
            return {
                "metadata_rows": len(boss.metadata),
                "comparison_players": [e.name for e in boss.cohort if e.status == "complete"],
                "subject_status": boss.subject.status,
                "selected_report_sets": len(acquisition.reports),
                "ranking_bearing_report_requests": sum(
                    "rankings(" in r["query"] for r in fake.requests
                ),
                "screen_requests": sum("NecropsyReportScreen" in r["query"] for r in fake.requests),
                "all_http_requests": len(fake.requests),
            }
    finally:
        client.close()


def main() -> None:
    git = shutil.which("git")
    assert git is not None
    source = subprocess.check_output([git, "show", "HEAD:src/necropsy/wcl/acquire.py"])
    baseline = types.ModuleType("capture_acquisition_baseline")
    sys.modules[baseline.__name__] = baseline
    exec(compile(source, "HEAD:src/necropsy/wcl/acquire.py", "exec"), baseline.__dict__)  # noqa: S102
    results = {}
    for shared in (False, True):
        old, new = run(baseline, shared), run(current, shared)
        for key in (
            "metadata_rows",
            "comparison_players",
            "subject_status",
            "selected_report_sets",
        ):
            assert old[key] == new[key], f"selection changed: {key}"
        results["shared_upload" if shared else "separate_uploads"] = {"before": old, "after": new}
    document = {
        "kind": "Synthetic operation-count comparison; no API calls or live cost claim",
        "baseline_acquire_sha256": hashlib.sha256(source).hexdigest(),
        "current_acquire_sha256": hashlib.sha256(Path(current.__file__).read_bytes()).hexdigest(),
        "baseline_commit": subprocess.check_output([git, "rev-parse", "HEAD"], text=True).strip(),
        "cases": results,
    }
    destination = Path(__file__).with_name("request-comparison.json")
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2)
        stream.write("\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
