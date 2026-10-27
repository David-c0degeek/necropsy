"""The committed comparison follow-up register replays from its pinned archives."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import comparison_followup as followup

pytestmark = pytest.mark.golden
REGISTER = Path(__file__).parents[2] / "tasks/naxx-completion/followup-comparisons.json"


def test_register_matches_a_fresh_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    saved = json.loads(REGISTER.read_bytes())
    monkeypatch.chdir(Path(__file__).parents[2])
    archives = sorted({c["archive"]["path"] for c in saved["cells"]})
    fresh = [cell for path in archives for cell in followup.cells(Path(path))]
    assert fresh == saved["cells"] and saved["minimum"] == followup.minimum()
    assert saved["needs_followup"] == sum(1 for c in fresh if c["needs_followup"])
