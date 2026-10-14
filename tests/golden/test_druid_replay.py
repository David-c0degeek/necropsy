"""Real Druid snapshot replay, independently counted amounts, and package evidence."""

from __future__ import annotations

import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pytest

from necropsy.report.offline import run_offline
from tests.fixture_paths import is_lfs_pointer

pytestmark = pytest.mark.golden
ROOT = Path(__file__).parent / "druid"


def _raw_total(path: Path, report: str, fight: int, player: str, metric: str) -> int:
    """Deduplicate page/stream copies by exact event identity, independently of SQL."""
    with zipfile.ZipFile(path) as zf:
        bundle = json.loads(zf.read(f"reports/{report}/bundle.json"))["reportData"]["report"]
        actor = next(a["id"] for a in bundle["masterData"]["actors"] if a["name"] == player)
        events = {}
        streams: dict[str, Counter[str]] = defaultdict(Counter)
        prefix = f"events/{report}/fight_{fight}/player_{actor}_"
        for name in zf.namelist():
            if not name.startswith(prefix) or not any(s in name for s in ("/source_", "/target_")):
                continue
            page = json.loads(zf.read(name))
            for event in page["data"]:
                identity = json.dumps(event, sort_keys=True)
                events[identity] = event
                streams[name.rsplit("_", 1)[0]][identity] += 1
        occurrences: Counter[str] = Counter()
        for counts in streams.values():
            occurrences |= counts
        kind = "heal" if metric == "effective_healing" else "damage"
        side = "targetID" if metric == "incoming_damage" else "sourceID"
        return sum(
            events[key]["amount"] * copies
            for key, copies in occurrences.items()
            if events[key]["type"] == kind and events[key].get(side) == actor
        )


@pytest.mark.parametrize("category", ["balance", "restoration", "feral", "guardian"])
def test_real_druid_snapshot_replays_with_separate_role_evidence(
    tmp_path: Path, category: str
) -> None:
    provenance = json.loads((ROOT / "provenance.json").read_text(encoding="utf-8"))
    record = next(r for r in provenance["fixtures"] if r["category"] == category)
    archive = ROOT / record["path"]
    if is_lfs_pointer(archive):
        pytest.skip("Druid Git LFS fixture needed: git lfs pull")
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == record["sha256"]
    out = tmp_path / "report"
    run_offline(archive, out)
    doc = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    boss = doc["bosses"][0]
    entries: list[dict[str, Any]] = [boss["subject"], *boss["overall_cohort"]]
    facts = json.loads((ROOT / "facts.json").read_text(encoding="utf-8"))
    for case in (c for c in facts["cases"] if c["fixture"] == category):
        entry = next(e for e in entries if e["player"] == case["player"])
        assert entry["druid"]["role"]["value"] == case["role"]
        assert entry["druid"]["metrics"][case["metric"]]["value"] == case["amount"]
        assert (
            _raw_total(archive, case["report"], case["fight"], case["player"], case["metric"])
            == case["amount"]
        )
    assert doc["subject"]["class_id"] == 2
    assert len(boss["overall_cohort"]) == 5
    assert all("hunter" not in e for e in entries)
    with zipfile.ZipFile(out / f"necropsy-{doc['subject']['id']}-2006.zip") as zf:
        manifest = json.loads(zf.read("manifest.json"))
        for record in manifest["files"]:
            assert hashlib.sha256(zf.read(record["path"])).hexdigest() == record["sha256"]
        assert "tables/roles.csv" in zf.namelist()
        assert "tables/timeline.csv" in zf.namelist()
