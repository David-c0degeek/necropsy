"""Real class captures replay with independently counted raw totals and packages."""

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from necropsy.report.offline import run_offline
from necropsy.report.package import package_name
from necropsy.snapshot.archive import load_entries_manifest
from tests.fixture_paths import is_lfs_pointer
from tests.golden.test_druid_replay import _raw_total

pytestmark = pytest.mark.golden
ROOT = Path(__file__).parent / "classes"


@pytest.mark.parametrize(
    "record",
    json.loads((ROOT / "provenance.json").read_text(encoding="utf-8"))["fixtures"],
    ids=lambda r: r["label"],
)
def test_public_class_capture_has_raw_totals_role_boundaries_and_package(
    tmp_path: Path,
    record: dict[str, Any],
) -> None:
    archive = ROOT / record["path"]
    if is_lfs_pointer(archive):
        pytest.skip("Class Git LFS fixtures needed: git lfs pull")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert digest == record["sha256"]
    out = tmp_path / "out"
    run_offline(
        archive,
        out,
        expected_sha256=digest,
        entries=load_entries_manifest(archive.with_suffix(".entries")),
    )
    doc = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
    boss = doc["bosses"][0]
    assert (boss["subject"] is not None) == record["personal"]
    assert (boss["playbook"]["reference"] is not None) == record["reference"]
    entries = ([boss["subject"]] if boss["subject"] else []) + boss["overall_cohort"]
    facts = json.loads((ROOT / "facts.json").read_text(encoding="utf-8"))["cases"]
    for fact in (f for f in facts if f["fixture"] == record["label"]):
        entry = next(
            e
            for e in entries
            if e["player"] == fact["player"]
            and e["report_code"] == fact["report"]
            and e["fight_id"] == fact["fight"]
        )
        # These labels pin inferred behavior; the provenance retains pending domain review.
        assert entry["combat"]["role"]["value"] == fact["role_regression"]
        for metric, expected in fact["metrics"].items():
            assert (
                _raw_total(archive, fact["report"], fact["fight"], fact["player"], metric)
                == expected
            )
            assert entry["combat"]["metrics"][metric]["value"] == expected
    if record["kind"] == "budget-only":
        assert not entries and boss["playbook"]["comparisons"] == []
        assert "BudgetExceeded" in doc["acquisition"]["stopped"]
        assert boss["benchmarks"]["baseline"]["medians"] == {}
    if record["label"] == "warrior-protection":
        assert any(e["combat"]["role"]["value"] == "dps" for e in boss["overall_cohort"])
        assert all(e["combat"]["role"]["value"] == "tank" for e in boss["cohort"])
    with zipfile.ZipFile(out / package_name(doc)) as package:
        manifest = json.loads(package.read("manifest.json"))
        for item in manifest["files"]:
            assert hashlib.sha256(package.read(item["path"])).hexdigest() == item["sha256"]
        assert "tables/ability-use.csv" in package.namelist() or record["kind"] == "budget-only"
