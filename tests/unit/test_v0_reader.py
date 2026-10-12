from pathlib import Path
from typing import Any

import pytest

from necropsy.snapshot.archive import VerifiedArchive
from necropsy.snapshot.model import (
    ActorRole,
    Direction,
    SnapshotError,
    SnapshotScope,
    StreamRead,
    StreamStatus,
)
from necropsy.snapshot.v0 import V0Snapshot
from tests.snapshot_builder import BOSS, FIGHT, REPORT, SnapshotSpec, build, ev, page

PLAYER = "player_1_Hunter"
PET = "pet_2_Cat"


def _complete_streams() -> dict[str, list[dict[str, Any] | None]]:
    return {
        f"{PLAYER}/source": [page([ev(1), ev(2)])],
        f"{PLAYER}/target": [page([ev(3, source=50, target=1)])],
        f"{PET}/source": [page([ev(4, source=2)])],
        f"{PET}/target": [page([])],
    }


def _read_all(path: Path) -> tuple[V0Snapshot, dict[tuple[str, int | None, str], StreamRead]]:
    archive = VerifiedArchive(path)
    archive.open()
    reader = V0Snapshot(archive)
    reads = {
        (r.role.value, r.actor_id, r.direction.value): reader.read_stream(r)
        for r in reader.expected_streams()
    }
    return reader, reads


def test_complete_snapshot(tmp_path: Path) -> None:
    path = build(tmp_path / "s.zip", SnapshotSpec(streams=_complete_streams()))
    reader, reads = _read_all(path)
    d = reader.descriptor()
    assert d.scope is SnapshotScope.FULL
    assert d.subject.name == "Subject"
    assert [(f.report_code, f.fight_id) for f in d.fights] == [(REPORT, FIGHT)]
    assert set(reads) == {
        ("player", 1, "source"),
        ("player", 1, "target"),
        ("pet", 2, "source"),
        ("pet", 2, "target"),
    }
    assert all(r.status is StreamStatus.COMPLETE for r in reads.values())
    assert len(reads[("player", 1, "source")].events) == 2
    assert reader.issues() == []
    assert len(list(reader.reports())) == 1
    assert [s for s, _ in reader.rankings()] == [f"leaderboards/51118_{BOSS}.json"]


def test_missing_pets_listing_is_unknown_pet_discovery(tmp_path: Path) -> None:
    streams = _complete_streams()
    path = build(tmp_path / "s.zip", SnapshotSpec(streams=streams, with_pets_json=False))
    reader, reads = _read_all(path)
    discovery = [r for r in reader.expected_streams() if r.role is ActorRole.PET_DISCOVERY]
    assert len(discovery) == 1
    assert discovery[0].direction is Direction.LISTING
    assert reads[("pet-discovery", None, "listing")].status is StreamStatus.MISSING


def test_participant_without_player_dir_is_missing(tmp_path: Path) -> None:
    participants = [
        {
            "kind": "top",
            "boss": BOSS,
            "encounterID": 51118,
            "leaderboardPosition": 1,
            "player": "Hunter",
            "server": "Realm",
        },
        {
            "kind": "top",
            "boss": BOSS,
            "encounterID": 51118,
            "leaderboardPosition": 2,
            "player": "Ghost",
            "server": "Realm",
        },
    ]
    path = build(
        tmp_path / "s.zip", SnapshotSpec(streams=_complete_streams(), participants=participants)
    )
    _, reads = _read_all(path)
    assert reads[("player", None, "source")].status is StreamStatus.MISSING
    assert reads[("player", None, "target")].ref.actor_name == "Ghost"


@pytest.mark.parametrize(
    ("pages", "status"),
    [
        ([page([ev(1)], 2.0), page([ev(2)])], StreamStatus.COMPLETE),
        ([page([ev(1)], 2.0)], StreamStatus.INCOMPLETE),
        ([{"data": [ev(1)]}], StreamStatus.MALFORMED),
        ([page([ev(1)]), page([ev(2)])], StreamStatus.MALFORMED),
        ([None], StreamStatus.MALFORMED),
    ],
)
def test_stream_completeness(
    tmp_path: Path, pages: list[dict[str, Any] | None], status: StreamStatus
) -> None:
    streams = _complete_streams()
    streams[f"{PLAYER}/source"] = pages
    path = build(tmp_path / "s.zip", SnapshotSpec(streams=streams))
    _, reads = _read_all(path)
    assert reads[("player", 1, "source")].status is status


def test_non_contiguous_pages_are_malformed(tmp_path: Path) -> None:
    streams = _complete_streams()
    extra = {
        f"events/{REPORT}/fight_{FIGHT}/{PLAYER}/source_003.json": b'{"data": [], '
        b'"nextPageTimestamp": null}'
    }
    path = build(tmp_path / "s.zip", SnapshotSpec(streams=streams, extra_members=extra))
    _, reads = _read_all(path)
    assert reads[("player", 1, "source")].status is StreamStatus.MALFORMED


def test_identical_events_across_a_page_boundary_are_kept_and_flagged(tmp_path: Path) -> None:
    hit = ev(5)
    streams = _complete_streams()
    streams[f"{PLAYER}/source"] = [page([ev(1), hit], 5.0), page([hit, ev(6)])]
    path = build(tmp_path / "s.zip", SnapshotSpec(streams=streams))
    _, reads = _read_all(path)
    read = reads[("player", 1, "source")]
    assert read.status is StreamStatus.COMPLETE
    assert read.events.count(hit) == 2
    assert read.boundary_ambiguities == 1


def test_manifest_error_marks_stream_error(tmp_path: Path) -> None:
    errors = [
        {
            "stage": "player_events",
            "report": REPORT,
            "fightID": FIGHT,
            "player": "Hunter",
            "error": "boom",
        }
    ]
    path = build(tmp_path / "s.zip", SnapshotSpec(streams=_complete_streams(), errors=errors))
    _, reads = _read_all(path)
    assert reads[("player", 1, "source")].status is StreamStatus.ERROR
    assert reads[("pet", 2, "source")].status is StreamStatus.COMPLETE


def test_unrecognised_member_is_an_issue(tmp_path: Path) -> None:
    path = build(
        tmp_path / "s.zip",
        SnapshotSpec(streams=_complete_streams(), extra_members={"notes.txt": b"x"}),
    )
    reader, _ = _read_all(path)
    assert reader.issues() == ["unrecognised member: notes.txt"]


def _subset(participants: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "kind": "necropsy.fixture-subset",
        "formatVersion": 1,
        "fights": [{"reportID": REPORT, "fightID": FIGHT, "participants": participants}],
    }


def test_subset_scope_comes_from_subset_descriptor(tmp_path: Path) -> None:
    subset = _subset([{"kind": "top", "player": "Hunter", "boss": BOSS, "leaderboardPosition": 1}])
    path = build(tmp_path / "s.zip", SnapshotSpec(streams=_complete_streams(), subset=subset))
    reader, _ = _read_all(path)
    d = reader.descriptor()
    assert d.scope is SnapshotScope.SUBSET
    assert d.fights[0].participants[0].server == "Realm"


@pytest.mark.parametrize(
    "subset",
    [
        {"kind": "something-else", "formatVersion": 1, "fights": []},
        {"kind": "necropsy.fixture-subset", "formatVersion": 2, "fights": []},
        _subset([{"kind": "top", "player": "Nobody", "boss": BOSS}]),
        {
            "kind": "necropsy.fixture-subset",
            "formatVersion": 1,
            "fights": [{"reportID": "OTHER", "fightID": 1, "participants": []}],
        },
    ],
)
def test_invalid_subset_descriptor_is_rejected(tmp_path: Path, subset: dict[str, Any]) -> None:
    path = build(tmp_path / "s.zip", SnapshotSpec(streams=_complete_streams(), subset=subset))
    with VerifiedArchive(path) as archive, pytest.raises(SnapshotError):
        V0Snapshot(archive)


def test_ambiguous_subset_enrichment_is_rejected(tmp_path: Path) -> None:
    twice = {
        "kind": "top",
        "boss": BOSS,
        "encounterID": 51118,
        "player": "Hunter",
        "server": "Realm",
    }
    subset = _subset([{"kind": "top", "player": "Hunter", "boss": BOSS}])
    spec = SnapshotSpec(
        streams=_complete_streams(), participants=[twice, dict(twice)], subset=subset
    )
    path = build(tmp_path / "s.zip", spec)
    with VerifiedArchive(path) as archive, pytest.raises(SnapshotError, match="matches 2"):
        V0Snapshot(archive)


def test_repeated_multi_event_group_across_boundary_is_flagged(tmp_path: Path) -> None:
    first, second = ev(5, ability=1), ev(5, ability=2)
    streams = _complete_streams()
    streams[f"{PLAYER}/source"] = [page([ev(1), first, second], 5.0), page([first, second])]
    path = build(tmp_path / "s.zip", SnapshotSpec(streams=streams))
    _, reads = _read_all(path)
    read = reads[("player", 1, "source")]
    assert len(read.events) == 5
    assert read.boundary_ambiguities == 1


def test_same_timestamp_but_different_events_across_boundary_is_not_flagged(
    tmp_path: Path,
) -> None:
    streams = _complete_streams()
    streams[f"{PLAYER}/source"] = [page([ev(5, ability=1)], 5.0), page([ev(5, ability=2)])]
    path = build(tmp_path / "s.zip", SnapshotSpec(streams=streams))
    _, reads = _read_all(path)
    assert reads[("player", 1, "source")].boundary_ambiguities == 0
