import hashlib
import warnings
import zipfile
from pathlib import Path

import pytest

from necropsy.snapshot.archive import (
    ArchiveError,
    EntryDigest,
    EntryOrigin,
    VerifiedArchive,
    check_member_name,
    format_entries_manifest,
    parse_entries_manifest,
    sha256_file,
)

MEMBERS = {
    "manifest.json": b'{"ok": true}',
    "events/ABC/fight_1/player_1_A/source_001.json": b'{"data": []}',
}


def _zip(path: Path, members: dict[str, bytes], *, compression: int = zipfile.ZIP_DEFLATED) -> Path:
    with zipfile.ZipFile(path, "w", compression=compression) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


def _manifest(members: dict[str, bytes]) -> dict[str, EntryDigest]:
    return {
        name: EntryDigest(name, len(data), hashlib.sha256(data).hexdigest(), EntryOrigin.SOURCE)
        for name, data in members.items()
    }


def test_reads_members_verified_against_manifest(tmp_path: Path) -> None:
    path = _zip(tmp_path / "a.zip", MEMBERS)
    with VerifiedArchive(
        path, expected_sha256=sha256_file(path), entries=_manifest(MEMBERS)
    ) as archive:
        assert archive.names() == sorted(MEMBERS)
        assert archive.read_json("manifest.json") == {"ok": True}
        assert "manifest.json" in archive


def test_directory_entries_are_not_members(tmp_path: Path) -> None:
    path = tmp_path / "d.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("events/", b"")
        zf.writestr("events/x.json", b"{}")
    with VerifiedArchive(path) as archive:
        assert archive.names() == ["events/x.json"]


def test_whole_archive_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    path = _zip(tmp_path / "a.zip", MEMBERS)
    with pytest.raises(ArchiveError, match="digest mismatch"):
        VerifiedArchive(path, expected_sha256="0" * 64).open()


@pytest.mark.parametrize(
    "name",
    ["../escape.json", "/abs.json", "C:/x.json", "a\\b.json", "a//b.json", "a/./b.json", ""],
)
def test_unsafe_member_names_are_rejected(name: str) -> None:
    with pytest.raises(ArchiveError):
        check_member_name(name)


def test_unsafe_name_inside_archive_is_rejected(tmp_path: Path) -> None:
    path = _zip(tmp_path / "a.zip", {"../evil.json": b"{}"})
    with pytest.raises(ArchiveError, match="traversal"):
        VerifiedArchive(path).open()


def test_duplicate_member_names_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "dup.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("x.json", b"1")
            zf.writestr("x.json", b"2")
    with pytest.raises(ArchiveError, match="duplicate"):
        VerifiedArchive(path).open()


def test_unsupported_compression_is_rejected(tmp_path: Path) -> None:
    path = _zip(tmp_path / "b.zip", MEMBERS, compression=zipfile.ZIP_BZIP2)
    with pytest.raises(ArchiveError, match="unsupported compression"):
        VerifiedArchive(path).open()


def test_encrypted_flag_is_rejected(tmp_path: Path) -> None:
    path = _zip(tmp_path / "e.zip", {"x.json": b"{}"}, compression=zipfile.ZIP_STORED)
    raw = bytearray(path.read_bytes())
    # zipfile clears flag bits on write, so set the encryption bit in the
    # central directory header (signature PK\x01\x02, flags at offset 8).
    central = raw.find(b"PK\x01\x02")
    raw[central + 8] |= 0x1
    path.write_bytes(bytes(raw))
    with pytest.raises(ArchiveError, match="encrypted"):
        VerifiedArchive(path).open()


def test_member_size_cap_is_enforced(tmp_path: Path) -> None:
    path = _zip(tmp_path / "a.zip", {"big.json": b"x" * 2048})
    with pytest.raises(ArchiveError, match="size cap"):
        VerifiedArchive(path, max_member_bytes=1024).open()


def test_total_size_cap_is_enforced(tmp_path: Path) -> None:
    path = _zip(tmp_path / "a.zip", {"a.json": b"x" * 600, "b.json": b"y" * 600})
    with pytest.raises(ArchiveError, match="total"):
        VerifiedArchive(path, max_total_bytes=1000).open()


def test_manifest_member_set_mismatch_is_rejected(tmp_path: Path) -> None:
    path = _zip(tmp_path / "a.zip", MEMBERS)
    entries = _manifest(MEMBERS)
    entries.pop("manifest.json")
    with pytest.raises(ArchiveError, match="member set differs"):
        VerifiedArchive(path, entries=entries).open()


def test_manifest_size_mismatch_is_rejected(tmp_path: Path) -> None:
    path = _zip(tmp_path / "a.zip", MEMBERS)
    entries = _manifest(MEMBERS)
    e = entries["manifest.json"]
    entries["manifest.json"] = EntryDigest(e.name, e.size + 1, e.sha256, e.origin)
    with pytest.raises(ArchiveError, match="declared size"):
        VerifiedArchive(path, entries=entries).open()


def test_member_digest_mismatch_is_rejected_on_read(tmp_path: Path) -> None:
    path = _zip(tmp_path / "a.zip", MEMBERS)
    entries = _manifest(MEMBERS)
    e = entries["manifest.json"]
    entries["manifest.json"] = EntryDigest(e.name, e.size, "f" * 64, e.origin)
    with (
        VerifiedArchive(path, entries=entries) as archive,
        pytest.raises(ArchiveError, match="digest differs"),
    ):
        archive.read_bytes("manifest.json")


def test_corrupted_member_data_is_rejected(tmp_path: Path) -> None:
    payload = bytes(range(256)) * 64
    path = _zip(tmp_path / "a.zip", {"x.bin": payload}, compression=zipfile.ZIP_STORED)
    raw = bytearray(path.read_bytes())
    offset = raw.find(payload[:64])
    raw[offset + 100] ^= 0xFF
    path.write_bytes(bytes(raw))
    with VerifiedArchive(path) as archive, pytest.raises(ArchiveError, match="corrupt"):
        archive.read_bytes("x.bin")


def test_corrupted_deflated_member_is_rejected(tmp_path: Path) -> None:
    payload = b"".join(i.to_bytes(4, "little") for i in range(20000))
    path = _zip(tmp_path / "a.zip", {"x.bin": payload})
    raw = bytearray(path.read_bytes())
    data_start = raw.find(b"x.bin") + len("x.bin")
    for offset in range(data_start + 20, data_start + 60):
        raw[offset] ^= 0x5A
    path.write_bytes(bytes(raw))
    with VerifiedArchive(path) as archive, pytest.raises(ArchiveError, match="corrupt"):
        archive.read_bytes("x.bin")


def test_truncated_archive_is_rejected(tmp_path: Path) -> None:
    path = _zip(tmp_path / "a.zip", MEMBERS)
    path.write_bytes(path.read_bytes()[:40])
    with pytest.raises(ArchiveError, match="not a readable zip"):
        VerifiedArchive(path).open()


def test_reading_requires_open_archive(tmp_path: Path) -> None:
    path = _zip(tmp_path / "a.zip", MEMBERS)
    archive = VerifiedArchive(path)
    with pytest.raises(ArchiveError, match="not open"):
        archive.read_bytes("manifest.json")


def test_entries_manifest_round_trip() -> None:
    entries = _manifest(MEMBERS)
    text = format_entries_manifest(entries.values())
    assert parse_entries_manifest(text) == entries
    assert text.splitlines()[0].endswith("events/ABC/fight_1/player_1_A/source_001.json")


@pytest.mark.parametrize(
    "line",
    [
        "abc  1  source  x.json",
        f"{'a' * 64}  1  unknown  x.json",
        f"{'a' * 64}  1  source",
        f"{'a' * 64}  1  source  ../x.json",
    ],
)
def test_malformed_entries_manifest_is_rejected(line: str) -> None:
    with pytest.raises(ArchiveError):
        parse_entries_manifest(line + "\n")


def test_duplicate_entries_manifest_line_is_rejected() -> None:
    line = f"{'a' * 64}  1  source  x.json\n"
    with pytest.raises(ArchiveError, match="duplicate"):
        parse_entries_manifest(line + line)
