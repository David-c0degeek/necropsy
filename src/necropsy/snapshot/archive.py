"""Verified, read-only access to snapshot zip archives.

Snapshots are read straight from their zip archive; nothing is extracted to
disk. Opening an archive checks the whole-file digest once, rejects unsafe or
ambiguous member names, and bounds both declared and actually-read sizes. When
an entries manifest is supplied, the member set must match it exactly and every
member read is checked against its recorded SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
import zlib
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import TracebackType
from typing import Any, Self

DEFAULT_MAX_MEMBER_BYTES = 256 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 8 * 1024 * 1024 * 1024
_CHUNK = 1024 * 1024
_SUPPORTED_COMPRESSION = frozenset({zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})
_ENCRYPTED_FLAG = 0x1


class ArchiveError(Exception):
    """The archive is untrusted, inconsistent with its manifest, or unreadable."""


class EntryOrigin(StrEnum):
    """Where a member's bytes came from."""

    SOURCE = "source"
    """Byte-identical copy of a member of the original WCL export."""

    GENERATED = "generated"
    """Written by Necropsy tooling (for example a subset descriptor or a wrapper)."""

    ACQUIRED = "acquired"
    """An API response Necropsy fetched itself, as published in its verified cache."""


@dataclass(frozen=True, slots=True)
class EntryDigest:
    name: str
    size: int
    sha256: str
    origin: EntryOrigin


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_member_name(name: str) -> None:
    """Reject member names that could escape a root or alias another member."""
    if not name or "\x00" in name:
        raise ArchiveError(f"empty or NUL-containing member name: {name!r}")
    if "\\" in name:
        raise ArchiveError(f"backslash in member name: {name!r}")
    if name.startswith("/") or ":" in name.split("/", 1)[0]:
        raise ArchiveError(f"absolute or drive-qualified member name: {name!r}")
    parts = name.rstrip("/").split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ArchiveError(f"traversal or empty segment in member name: {name!r}")


def format_entries_manifest(entries: Iterable[EntryDigest]) -> str:
    """Serialize entries as `<sha256>  <size>  <origin>  <name>` lines, sorted by name."""
    lines = [
        f"{e.sha256}  {e.size}  {e.origin.value}  {e.name}"
        for e in sorted(entries, key=lambda e: e.name)
    ]
    return "\n".join(lines) + "\n"


def parse_entries_manifest(text: str) -> dict[str, EntryDigest]:
    entries: dict[str, EntryDigest] = {}
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split("  ", 3)
        if len(fields) != 4:
            raise ArchiveError(f"entries manifest line {line_no}: expected 4 fields")
        sha, size, origin, name = fields
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ArchiveError(f"entries manifest line {line_no}: bad sha256")
        check_member_name(name)
        if name in entries:
            raise ArchiveError(f"entries manifest line {line_no}: duplicate name {name!r}")
        try:
            entries[name] = EntryDigest(name, int(size), sha, EntryOrigin(origin))
        except ValueError as exc:
            raise ArchiveError(f"entries manifest line {line_no}: {exc}") from exc
    return entries


def load_entries_manifest(path: Path) -> dict[str, EntryDigest]:
    return parse_entries_manifest(path.read_text(encoding="utf-8"))


class VerifiedArchive:
    """Context-managed, verified read access to one snapshot zip."""

    def __init__(
        self,
        path: Path,
        *,
        expected_sha256: str | None = None,
        entries: Mapping[str, EntryDigest] | None = None,
        max_member_bytes: int = DEFAULT_MAX_MEMBER_BYTES,
        max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    ) -> None:
        self.path = path
        self._expected_sha256 = expected_sha256
        self._entries = dict(entries) if entries is not None else None
        self._max_member_bytes = max_member_bytes
        self._max_total_bytes = max_total_bytes
        self._zip: zipfile.ZipFile | None = None
        self._infos: dict[str, zipfile.ZipInfo] = {}
        self.sha256: str | None = None

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def open(self) -> None:
        if not self.path.is_file():
            raise ArchiveError(f"archive not found: {self.path}")
        self.sha256 = sha256_file(self.path)
        if self._expected_sha256 is not None and self.sha256 != self._expected_sha256:
            raise ArchiveError(
                f"archive digest mismatch for {self.path.name}: "
                f"expected {self._expected_sha256}, got {self.sha256}"
            )
        try:
            archive = zipfile.ZipFile(self.path)
        except zipfile.BadZipFile as exc:
            raise ArchiveError(f"not a readable zip archive: {self.path}") from exc
        try:
            self._infos = self._validate_members(archive.infolist())
        except BaseException:
            archive.close()
            raise
        self._zip = archive

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()
            self._zip = None

    def _validate_members(self, infos: list[zipfile.ZipInfo]) -> dict[str, zipfile.ZipInfo]:
        members: dict[str, zipfile.ZipInfo] = {}
        total = 0
        for info in infos:
            check_member_name(info.filename)
            if info.filename in members:
                raise ArchiveError(f"duplicate member name: {info.filename!r}")
            if info.flag_bits & _ENCRYPTED_FLAG:
                raise ArchiveError(f"encrypted member: {info.filename!r}")
            if info.compress_type not in _SUPPORTED_COMPRESSION:
                raise ArchiveError(
                    f"unsupported compression {info.compress_type} for {info.filename!r}"
                )
            if info.is_dir():
                continue
            if info.file_size > self._max_member_bytes:
                raise ArchiveError(f"member exceeds size cap: {info.filename!r}")
            total += info.file_size
            if total > self._max_total_bytes:
                raise ArchiveError("archive exceeds total uncompressed size cap")
            members[info.filename] = info
        if self._entries is not None:
            self._check_against_manifest(members)
        return members

    def _check_against_manifest(self, members: Mapping[str, zipfile.ZipInfo]) -> None:
        assert self._entries is not None
        missing = sorted(set(self._entries) - set(members))
        extra = sorted(set(members) - set(self._entries))
        if missing or extra:
            raise ArchiveError(
                f"member set differs from manifest: missing={missing[:5]} extra={extra[:5]} "
                f"(counts {len(missing)}/{len(extra)})"
            )
        for name, info in members.items():
            if info.file_size != self._entries[name].size:
                raise ArchiveError(f"declared size differs from manifest for {name!r}")

    def _require_open(self) -> zipfile.ZipFile:
        if self._zip is None:
            raise ArchiveError("archive is not open")
        return self._zip

    def names(self) -> list[str]:
        """File member names, sorted. Directory entries are not listed."""
        self._require_open()
        return sorted(self._infos)

    def __contains__(self, name: object) -> bool:
        return name in self._infos

    def read_bytes(self, name: str) -> bytes:
        archive = self._require_open()
        info = self._infos.get(name)
        if info is None:
            raise ArchiveError(f"no such member: {name!r}")
        digest = hashlib.sha256()
        chunks: list[bytes] = []
        read = 0
        try:
            with archive.open(info) as handle:
                while chunk := handle.read(_CHUNK):
                    read += len(chunk)
                    if read > info.file_size or read > self._max_member_bytes:
                        raise ArchiveError(f"member yields more bytes than declared: {name!r}")
                    digest.update(chunk)
                    chunks.append(chunk)
        except (zipfile.BadZipFile, zlib.error, EOFError, OSError) as exc:
            raise ArchiveError(f"corrupt member {name!r}: {exc}") from exc
        if read != info.file_size:
            raise ArchiveError(f"member is truncated: {name!r}")
        if self._entries is not None and digest.hexdigest() != self._entries[name].sha256:
            raise ArchiveError(f"member digest differs from manifest: {name!r}")
        return b"".join(chunks)

    def read_json(self, name: str) -> Any:
        return json.loads(self.read_bytes(name))

    def iter_digests(self, origin: EntryOrigin = EntryOrigin.SOURCE) -> Iterator[EntryDigest]:
        """Hash every member; used to build an entries manifest from a trusted archive."""
        for name in self.names():
            data = self.read_bytes(name)
            yield EntryDigest(name, len(data), hashlib.sha256(data).hexdigest(), origin)
