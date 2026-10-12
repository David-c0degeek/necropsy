"""Fast checks of the committed fixtures. Never needs the Git LFS object."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from necropsy.snapshot.archive import (
    EntryOrigin,
    VerifiedArchive,
    load_entries_manifest,
    sha256_file,
)
from tests.fixture_paths import (
    golden_path,
    provenance,
    raw_entries_path,
    subset_entries_path,
    subset_path,
)


@pytest.fixture(scope="module")
def subset() -> Iterator[VerifiedArchive]:
    prov = provenance()["subset"]
    entries = load_entries_manifest(subset_entries_path())
    with VerifiedArchive(subset_path(), expected_sha256=prov["sha256"], entries=entries) as archive:
        yield archive


@pytest.fixture(scope="module")
def descriptor(subset: VerifiedArchive) -> dict[str, Any]:
    data = subset.read_json("subset.json")
    assert isinstance(data, dict)
    return data


def test_oracle_files_match_recorded_digests() -> None:
    oracle = provenance()["oracle"]
    assert oracle
    for item in oracle:
        path = golden_path(item["path"])
        assert path.stat().st_size == item["size"], item["path"]
        assert sha256_file(path) == item["sha256"], item["path"]


def test_manifests_match_recorded_digests() -> None:
    prov = provenance()
    assert sha256_file(raw_entries_path()) == prov["rawExport"]["entriesManifest"]["sha256"]
    assert sha256_file(subset_entries_path()) == prov["subset"]["entriesManifest"]["sha256"]
    raw_entries = load_entries_manifest(raw_entries_path())
    assert len(raw_entries) == prov["rawExport"]["entriesManifest"]["members"]
    assert {e.origin for e in raw_entries.values()} == {EntryOrigin.SOURCE}


def test_subset_source_members_are_byte_identical_to_full_export(subset: VerifiedArchive) -> None:
    raw_entries = load_entries_manifest(raw_entries_path())
    subset_entries = load_entries_manifest(subset_entries_path())
    generated = [e.name for e in subset_entries.values() if e.origin is EntryOrigin.GENERATED]
    assert generated == ["subset.json"]
    for name, entry in subset_entries.items():
        if entry.origin is EntryOrigin.SOURCE:
            assert raw_entries[name] == entry, name
    # Reading every member re-verifies each digest against the manifest.
    for name in subset.names():
        subset.read_bytes(name)


def test_subset_descriptor_identifies_its_source(descriptor: dict[str, Any]) -> None:
    prov = provenance()
    assert descriptor["kind"] == "necropsy.fixture-subset"
    assert descriptor["formatVersion"] == 1
    assert descriptor["source"]["sha256"] == prov["rawExport"]["sha256"]
    assert (
        descriptor["source"]["entriesManifestSha256"]
        == (prov["rawExport"]["entriesManifest"]["sha256"])
    )
    fights = descriptor["fights"]
    assert len(fights) + descriptor["excludedFightCount"] == descriptor["source"]["fightCount"]


def test_subset_scope_matches_its_members(
    subset: VerifiedArchive, descriptor: dict[str, Any]
) -> None:
    listed = {f"events/{f['reportID']}/fight_{f['fightID']}/" for f in descriptor["fights"]}
    event_members = [n for n in subset.names() if n.startswith("events/")]
    present = {"/".join(n.split("/")[:3]) + "/" for n in event_members}
    assert present == listed
    reports = {f["reportID"] for f in descriptor["fights"]}
    assert {n.split("/")[1] for n in subset.names() if n.startswith("reports/")} == reports


def test_subset_covers_the_intended_encounters(descriptor: dict[str, Any]) -> None:
    by_boss: dict[str, set[str]] = {}
    for fight in descriptor["fights"]:
        for p in fight["participants"]:
            by_boss.setdefault(p["boss"], set()).add(p["player"])
    assert by_boss["Patchwerk"] == {"Haplina", "Smcadogx", "Charies", "Andrenn", "Xert", "Xal"}
    for boss in ("Grobbulus", "Gothik the Harvester", "Kel'Thuzad"):
        assert "Haplina" in by_boss[boss]
        assert len(by_boss[boss]) == 2


def test_subset_keeps_full_export_originals_unmodified(subset: VerifiedArchive) -> None:
    raw_entries = load_entries_manifest(raw_entries_path())
    for name in ("selection.json", "manifest.json", "profile.json"):
        assert name in subset
        assert raw_entries[name].sha256 == load_entries_manifest(subset_entries_path())[name].sha256
    assert len(subset.read_json("selection.json")) == 89
