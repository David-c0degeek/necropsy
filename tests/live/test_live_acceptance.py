"""Manual live acceptance of `necropsy analyze` against Warcraft Logs.

Never runs by itself: it needs BOTH the `--run-live` option and NECROPSY_LIVE_URL,
plus a signed-in credential store. Run it deliberately:

    uv run pytest -m live --run-live tests/live/test_live_acceptance.py

Environment: NECROPSY_LIVE_URL (character URL), NECROPSY_LIVE_CACHE (cache
directory), NECROPSY_LIVE_OUT (a new output directory), optional
NECROPSY_LIVE_ENDPOINT (client|user), NECROPSY_LIVE_PARTITION and
NECROPSY_LIVE_HISTORY (a saved historical analysis.json to compare with).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.live


def live_settings(config: pytest.Config) -> dict[str, Any] | None:
    """The live run's settings, or None unless the run was deliberately enabled."""
    url = os.environ.get("NECROPSY_LIVE_URL")
    if not config.getoption("--run-live") or not url:
        return None
    partition = os.environ.get("NECROPSY_LIVE_PARTITION")
    return {
        "url": url,
        "cache": Path(os.environ.get("NECROPSY_LIVE_CACHE", "necropsy-live-cache")),
        "out": Path(os.environ.get("NECROPSY_LIVE_OUT", "necropsy-live-out")),
        "endpoint": os.environ.get("NECROPSY_LIVE_ENDPOINT", "client"),
        "partition": None if partition is None else int(partition),
        "history": os.environ.get("NECROPSY_LIVE_HISTORY"),
        "wait_for_reset": os.environ.get("NECROPSY_LIVE_WAIT_FOR_RESET") == "1",
        "category": os.environ.get("NECROPSY_LIVE_CATEGORY"),
    }


def test_live_analyze_acceptance(request: pytest.FixtureRequest) -> None:
    settings = live_settings(request.config)
    if settings is None:
        pytest.skip("live acceptance needs --run-live and NECROPSY_LIVE_URL")
    from necropsy.wcl import cli as wcl_cli
    from necropsy.wcl.acceptance import (
        check_run,
        compare_with_history,
        history_matches_context,
        load_history,
        secret_scan,
        write_receipt,
    )
    from necropsy.wcl.analyze import run_analyze
    from necropsy.wcl.urls import parse_character_url

    history = None
    if settings["history"]:  # validated before any credential or network use
        ref = parse_character_url(settings["url"])
        history = load_history(Path(settings["history"]), ref.character_id, settings["partition"])

    outcome = run_analyze(
        settings["url"],
        cache=settings["cache"],
        out=settings["out"],
        partition=settings["partition"],
        endpoint=settings["endpoint"],
        wait_for_reset=settings["wait_for_reset"],
        category=settings["category"],
        tokens=wcl_cli._tokens,
        client_factory=wcl_cli._client,
        before_acquire=None
        if history is None
        else (lambda context: history_matches_context(history, context)),
    )
    assert outcome.code in (0, 4), outcome.lines
    assert outcome.snapshot is not None
    written = outcome.snapshot
    out = settings["out"]
    assert outcome.acquisition is not None
    checked = check_run(
        out,
        written.archive,
        written.entries,
        written.sha256,
        requested=outcome.acquisition.requested,
        sha256_file=written.sha256_file,
    )
    scan = secret_scan(out)
    receipt = {
        "result": "complete" if outcome.code == 0 else "partial",
        "result_scope": "acquisition coverage",
        "artifact_checks": "passed",
        "limits": [
            "Complete acquisition coverage can still contain unknown analysis values.",
            "This check does not validate game mechanics or recommendation correctness.",
        ],
        "exit_code": outcome.code,
        "endpoint": settings["endpoint"],
        "wait_for_reset": settings["wait_for_reset"],
        "reset_wait": outcome.reset_wait,
        "partition": checked["document"]["zone"]["partition"],
        "category": settings["category"],
        "snapshot_sha256": written.sha256,
        "package_sha256": checked["package_sha256"],
        "summary": outcome.lines,
        "secret_scan": scan,
        "comparison": compare_with_history(checked["document"], history),
    }
    write_receipt(out / "live-acceptance.json", receipt)
    print(f"Receipt: {out / 'live-acceptance.json'}")
    print(f"Acquisition coverage: {receipt['result']}; artifact checks: passed")
    print(f"Historical comparison: {receipt['comparison']['historical_comparison']}")
    print(f"Secret scan: {scan['status']} — see the receipt for scan limits")
    assert scan["status"] in ("passed", "unavailable"), scan
