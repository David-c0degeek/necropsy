"""A runner exit or a fabricated ZIP cannot substitute for certified v2 scopes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from necropsy.snapshot.archive import (
    ArchiveError,
    VerifiedArchive,
    format_entries_manifest,
    sha256_file,
)
from necropsy.snapshot.model import SnapshotError
from necropsy.snapshot.v1_writer import write_snapshot
from necropsy.wcl.acquire import Run, acquire, finalize_reports
from necropsy.wcl.cache import Cache
from necropsy.wcl.sites import VANILLA
from scripts import capture_queue as cq
from scripts.capture_runner import Entry
from scripts.check_capture_archive import main, verify_capture
from tests.integration.test_encounter_snapshot import NaxxEncounterWcl
from tests.integration.test_live_snapshot import _client, _rewrite
from tests.unit.test_wcl_acquire import PATCHWERK, Player, _context


@pytest.fixture(scope="module")
def captures(tmp_path_factory: pytest.TempPathFactory) -> dict[bool, Any]:
    root = tmp_path_factory.mktemp("capture-verification")
    context = _context()
    assert context.partition is not None
    context = replace(
        context,
        zone_id=2006,
        partition=replace(context.partition, id=1),
        ranking_category="Marksmanship",
        ranking_metric="dps",
    )
    captures = {}
    for enabled in (False, True):
        out = root / str(enabled)
        out.mkdir()
        (out / "cache").mkdir()
        fake = NaxxEncounterWcl([Player(f"Ally{i}") for i in range(5)], Player("Haplina"))
        client, store = _client(fake), Cache(out / "cache")
        try:
            result = acquire(
                client,
                store,
                VANILLA,
                context,
                encounters=(PATCHWERK,),
                encounter_context=enabled,
                endpoint="user",
            )
            assert result.stopped is None
            finalize_reports(Run(client, store, VANILLA, endpoint="user"), result)
            captures[enabled] = write_snapshot(result, store, out, "capture")
        finally:
            client.close()
    return captures


def _expected(written: Any) -> tuple[Entry, dict[str, Any]]:
    with VerifiedArchive(written.archive) as archive:
        marker = archive.read_json("necropsy-snapshot.json")
    subject = marker["subject"]
    fight = marker["fights"][0]
    entry = Entry(
        "naxx-test",
        "naxxramas",
        1,
        subject["class_id"],
        subject["ranking_category"],
        subject["ranking_metric"],
        subject["faction"],
        ("https://x.invalid/subject",),
    )
    return entry, {
        "subject_id": subject["id"],
        "report": fight["reportID"],
        "fight": fight["fightID"],
        "encounter": fight["participants"][0]["encounterID"],
    }


def test_complete_v2_capture_has_digest_and_interpreter_bound_scope_receipt(captures: Any) -> None:
    written = captures[True]
    entry, expected = _expected(written)
    receipt = verify_capture(written.archive, written.sha256, written.entries, entry, **expected)
    assert receipt["status"] == "verified"
    assert receipt["archive_sha256"] == written.sha256
    assert receipt["entries_sha256"] == sha256_file(written.entries)
    assert receipt["python"] and len(receipt["verifier_sha256"]) == 64
    assert {s["role"] for s in receipt["streams"]} >= {"encounter", "critical"}
    assert all(s["pages"] > 0 for s in receipt["streams"])


def test_v1_actor_capture_cannot_pass_a_v2_smoke(captures: Any) -> None:
    written = captures[False]
    entry, expected = _expected(written)
    with pytest.raises(ValueError, match="encounter snapshot"):
        verify_capture(written.archive, written.sha256, written.entries, entry, **expected)


@pytest.mark.parametrize(
    "field",
    ["subject_id", "report", "fight", "encounter", "faction", "partition", "metric", "raid"],
)
def test_a_valid_archive_for_a_different_entry_or_fight_is_refused(
    captures: Any, field: str
) -> None:
    written = captures[True]
    entry, expected = _expected(written)
    if field in expected:
        expected[field] = "wrong-report" if field == "report" else 999999
    else:
        changes: dict[str, Any] = {
            field: {"faction": "Horde", "partition": 2, "metric": "hps", "raid": "mc"}[field]
        }
        entry = replace(entry, **changes)
    with pytest.raises(ValueError):
        verify_capture(written.archive, written.sha256, written.entries, entry, **expected)


@pytest.mark.parametrize("case", ["critical-not-in-all", "missing-critical", "cursor"])
def test_rehashed_archive_and_manifest_do_not_hide_broken_scope_proofs(
    captures: Any, tmp_path: Path, case: str
) -> None:
    written = captures[True]
    entry, expected = _expected(written)

    def change(members: dict[str, bytes]) -> None:
        marker = json.loads(members["necropsy-snapshot.json"])
        proof = next(p for p in marker["encounter_streams"] if p["role"] == "critical")
        name = f"events/{proof['report']}/fight_{proof['fight']}/encounter/critical_001.json"
        if case == "missing-critical":
            marker["encounter_streams"].remove(proof)
            del members[name]
        else:
            page = json.loads(members[name])
            if case == "cursor":
                page["nextPageTimestamp"] = 2000
            else:
                page["data"][0]["amount"] += 1
            members[name] = json.dumps(page).encode()
            proof["pages"] = [hashlib.sha256(members[name]).hexdigest()]
        members["necropsy-snapshot.json"] = json.dumps(marker).encode()

    bad = _rewrite(written, tmp_path / "bad.zip", change)
    manifest = tmp_path / "bad.entries"
    with VerifiedArchive(bad) as archive:
        manifest.write_text(format_entries_manifest(archive.iter_digests()), encoding="utf-8")
    with pytest.raises(SnapshotError):
        verify_capture(bad, sha256_file(bad), manifest, entry, **expected)


def test_wrong_outer_digest_and_arbitrary_zip_are_refused(captures: Any, tmp_path: Path) -> None:
    written = captures[True]
    entry, expected = _expected(written)
    with pytest.raises(ArchiveError, match="digest mismatch"):
        verify_capture(written.archive, "0" * 64, written.entries, entry, **expected)
    path = tmp_path / "fake.zip"
    path.write_bytes(b"smoke-1")
    with pytest.raises(ArchiveError):
        verify_capture(path, sha256_file(path), written.entries, entry, **expected)


def test_only_complete_v2_context_can_suppress_capture(
    captures: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    for enabled in (False, True):
        written = captures[enabled]
        monkeypatch.setattr(cq, "ROOT", written.archive.parent)
        covered = cq.complete_encounter_coverage(written.archive.name, written.sha256)
        assert covered == ({51118} if enabled else set())
        # Naxx encounter captures derive their target streams (v3) and still count.
        with VerifiedArchive(written.archive) as archive:
            version = archive.read_json("necropsy-snapshot.json")["formatVersion"]
        assert version == (3 if enabled else 1)


def test_command_binds_the_queue_and_refuses_to_reuse_a_receipt(
    captures: Any, tmp_path: Path
) -> None:
    written = captures[True]
    entry, expected = _expected(written)
    queue = tmp_path / "queue.json"
    queue.write_text(
        json.dumps(
            {
                "version": 1,
                "entries": [
                    {
                        "entry_id": entry.entry_id,
                        "raid": entry.raid,
                        "partition": entry.partition,
                        "class_id": entry.class_id,
                        "category": entry.category,
                        "metric": entry.metric,
                        "faction": entry.faction,
                        "candidates": list(entry.candidates),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "receipt.json"
    args = [
        str(written.archive),
        "--sha256",
        written.sha256,
        "--entries",
        str(written.entries),
        "--queue",
        str(queue),
        "--entry",
        entry.entry_id,
        "--out",
        str(out),
    ]
    for key, value in expected.items():
        args.extend(["--" + key.replace("_", "-"), str(value)])
    assert main(args) == 0
    receipt = out.read_bytes()
    assert json.loads(receipt)["queue_sha256"] == sha256_file(queue)
    assert main(args) == 2
    assert out.read_bytes() == receipt
