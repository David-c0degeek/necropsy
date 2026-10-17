"""Immutable on-disk cache of Warcraft Logs report data, safe to resume.

Callers, including the analyze CLI, pass an explicit cache directory.

Layout under the root (format version in `cache-format.json`):

    <family>/<reportCode>/r<revision>/fight_<id>/report_<endpoint>_<sha256>.json
    <family>/<reportCode>/r<revision>/fight_<id>/<endpoint>_<role>_<actorId>_<direction>/page_NNN.json
    <family>/<reportCode>/r<revision>/fight_<id>/<endpoint>_<role>_<actorId>_<direction>/stream.json

Actorless encounter/critical scopes use <endpoint>_<role>_all instead. The
critical scope binds its server filter; it is not unrestricted fight coverage.

Guarantees, and their limits:

- Every file is published whole: bytes go to an owned temp file in the same
  directory, are flushed and fsynced, and appear under the final name through a
  hard link, which fails if the name exists. A reader sees no file or the whole
  file. Durability after power loss is what fsync plus link give on the
  filesystem in use; the directory entry itself is not fsynced on every platform.
- Nothing published is ever replaced: an existing file with the same bytes is
  reused, different bytes raise `CacheConflict`. A filesystem without hard links
  raises `CacheUnsupported`; there is no fallback that could replace bytes.
- A stream is complete only through its marker (`stream.json`), published last
  after every page, and re-verified on every read: identity equal to the request
  and every page's SHA-256 and event count matching. A missing or malformed
  marker never means complete.
- One writer per item: an OS advisory lock (released by the OS if the process
  dies) guards each bundle and stream. The next lock holder removes only that
  stream's unmarked pages and temps; completed generations are never touched.
- Paths are built only from validated parts (report code pattern, supported site
  family, positive integer ids) and every directory on the way is checked to stay
  inside the root and not be a link or reparse point.

The cache holds API response data only, never tokens, secrets or headers.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import re
import stat
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from necropsy.wcl.sites import SITES, Site

CACHE_FORMAT = 2
_CODE = re.compile(r"[A-Za-z0-9]{1,32}")
_ROLES = frozenset({"player", "pet", "encounter", "critical"})
CRITICAL_FILTER = 'type = "damage" AND isCritical = true'
_DIRECTIONS = frozenset({"source", "target"})
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class CacheError(Exception):
    """The cache cannot be used safely for this request."""


class UnsafeKey(CacheError):
    """A key part would not give a safe path inside the cache."""


class CacheConflict(CacheError):
    """Published bytes differ from what this request would publish."""


class CacheBusy(CacheError):
    """Another live process holds the lock for this item."""


class CacheUnsupported(CacheError):
    """The filesystem cannot give no-overwrite publication (no hard links)."""


class CacheCorrupt(CacheError):
    """A completion marker does not match its pages or its request."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def valid_report_code(code: Any) -> bool:
    """True for a plain WCL report code (letters and digits, 1-32 characters)."""
    return isinstance(code, str) and _CODE.fullmatch(code) is not None


def _positive(value: Any, what: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise UnsafeKey(f"{what} must be a positive integer, got {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class FightKey:
    """Cache key: site + report code + revision + fight."""

    site: Site
    code: str
    revision: int
    fight: int

    def __post_init__(self) -> None:
        canonical = SITES.get(self.site.host)
        if canonical is None or canonical != self.site or not canonical.supported:
            raise UnsafeKey(f"{self.site.host!r} is not a supported Warcraft Logs site")
        if not isinstance(self.code, str) or not _CODE.fullmatch(self.code):
            raise UnsafeKey(f"report code {self.code!r} is not a plain report code")
        if (
            not isinstance(self.revision, int)
            or isinstance(self.revision, bool)
            or self.revision < 0
        ):
            raise UnsafeKey(f"revision must be a non-negative integer, got {self.revision!r}")
        _positive(self.fight, "fight id")

    @property
    def parts(self) -> tuple[str, ...]:
        return (self.site.family, self.code, f"r{self.revision}", f"fight_{self.fight}")


@dataclass(frozen=True, slots=True)
class StreamKey:
    fight: FightKey
    role: str
    actor_id: int | None
    direction: str
    endpoint: str = "client"

    def __post_init__(self) -> None:
        if self.role not in _ROLES:
            raise UnsafeKey(f"role {self.role!r} is not a supported event scope")
        if self.role in {"encounter", "critical"}:
            if self.actor_id is not None or self.direction != "all":
                raise UnsafeKey("encounter streams require no actor and direction all")
        else:
            if self.direction not in _DIRECTIONS:
                raise UnsafeKey(f"direction {self.direction!r} is not source or target")
            _positive(self.actor_id, "actor id")
        _endpoint(self.endpoint)

    @property
    def name(self) -> str:
        if self.actor_id is None:
            return f"{self.endpoint}_{self.role}_all"
        return f"{self.endpoint}_{self.role}_{self.actor_id}_{self.direction}"


def _is_link(path: Path) -> bool:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        return True
    return bool(getattr(info, "st_file_attributes", 0) & _REPARSE)


def is_link(path: Path) -> bool:
    """True for a symlink, junction or other reparse point (never followed)."""
    return os.path.lexists(path) and _is_link(path)


def _present(path: Path) -> bool:
    """True when anything (a dangling link included) exists at `path`; links are refused."""
    if not os.path.lexists(path):
        return False
    if _is_link(path):
        raise UnsafeKey(f"{path} is a link or reparse point")
    return True


def _contained(root: Path, *parts: str, create: bool) -> Path:
    """`root/parts...`, refusing links, reparse points and escapes at every step."""
    path = root
    for part in parts:
        if part in ("", ".", "..") or any(c in part for c in "/\\:\0"):
            raise UnsafeKey(f"unsafe path part {part!r}")
        path = path / part
        if not _present(path):
            if not create:
                return path
            with contextlib.suppress(FileExistsError):
                path.mkdir()
            _present(path)
        if not path.is_dir() or not path.resolve().is_relative_to(root):
            raise UnsafeKey(f"{path} is not a directory inside the cache")
    return path


def _read(path: Path) -> bytes:
    if not _present(path):
        raise FileNotFoundError(path)
    if not path.is_file():
        raise UnsafeKey(f"{path} is not a regular file")
    return path.read_bytes()


def publish(path: Path, data: bytes) -> str:
    """Publish whole bytes under `path` without ever replacing an existing file.

    Returns `published` or `reused`; raises CacheConflict for different bytes.
    """
    if _present(path):
        if _read(path) == data:
            return "reused"
        raise CacheConflict(f"{path.name} already holds different bytes")
    temp = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    try:
        with temp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            if _read(path) == data:
                return "reused"
            raise CacheConflict(f"{path.name} already holds different bytes") from None
        except OSError as error:
            raise CacheUnsupported(
                f"cannot publish without overwriting: hard links unavailable ({error.strerror})"
            ) from None
        return "published"
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp.unlink()


@contextlib.contextmanager
def item_lock(path: Path) -> Iterator[None]:
    """Exclusive OS advisory lock on `path` (kept file); the OS releases it if we die.

    The lock file must be an ordinary file: a link (dangling ones included) is
    refused before opening, and the opened file must be the one checked.
    """
    _present(path)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as error:
        raise UnsafeKey(f"cannot open lock {path.name}: {error.strerror}") from None
    try:
        opened, named = os.fstat(fd), path.lstat()
        if (
            not stat.S_ISREG(opened.st_mode)
            or _is_link(path)
            or (opened.st_ino, opened.st_dev) != (named.st_ino, named.st_dev)
        ):
            raise UnsafeKey(f"{path} is not an ordinary lock file")
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise CacheBusy(f"another process is writing {path.stem}") from None
        try:
            yield
        finally:
            if sys.platform == "win32":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                with contextlib.suppress(OSError):
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# -- stream requests and pages ------------------------------------------------

ENDPOINTS = frozenset({"client", "user"})


def _endpoint(value: Any) -> str:
    if not isinstance(value, str) or value not in ENDPOINTS:
        raise UnsafeKey(f"endpoint {value!r} is not client or user")
    return value


def _digest(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise UnsafeKey("a generation digest must be a full lowercase SHA-256")
    return value


IDENTITY_FIELDS: dict[str, type | tuple[type, ...]] = {
    "site": str,
    "code": str,
    "revision": int,
    "fight": int,
    "actor_id": (int, type(None)),
    "role": str,
    "direction": str,
    "start_time": (int, float),
    "end_time": (int, float),
    "data_type": str,
    "limit": int,
    "include_resources": bool,
    "translate": bool,
    "query_version": int,
    "endpoint": str,
}
"""The canonical request a stream answers; fetch-time data belongs in `meta`."""


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def check_identity(key: StreamKey, identity: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse an identity that is incomplete, mistyped or not the key's own request."""
    found = dict(identity)
    fields = dict(IDENTITY_FIELDS)
    if key.role == "critical":
        fields["filter_expression"] = str
    if set(found) != set(fields):
        missing = sorted(set(fields) - set(found))
        extra = sorted(set(found) - set(fields))
        raise UnsafeKey(f"stream identity fields differ: missing {missing}, extra {extra}")
    for name, kind in fields.items():
        value = found[name]
        if isinstance(value, bool) and kind is not bool:
            raise UnsafeKey(f"identity {name} must not be a boolean")
        if not isinstance(value, kind):
            raise UnsafeKey(f"identity {name} has the wrong type: {value!r}")
    fight = key.fight
    expected = {
        "site": fight.site.host,
        "code": fight.code,
        "revision": fight.revision,
        "fight": fight.fight,
        "actor_id": key.actor_id,
        "role": key.role,
        "direction": key.direction,
        "endpoint": key.endpoint,
    }
    for name, value in expected.items():
        if found[name] != value:
            raise UnsafeKey(f"identity {name} {found[name]!r} is not the key's {value!r}")
    if key.role == "critical" and found["filter_expression"] != CRITICAL_FILTER:
        raise UnsafeKey("critical stream identity has a different event filter")
    start, end = _finite(found["start_time"]), _finite(found["end_time"])
    if start is None or end is None or start < 0 or end <= start:
        raise UnsafeKey("identity time bounds are not finite, ordered and non-negative")
    if found["data_type"] != "All" or found["limit"] <= 0 or found["query_version"] <= 0:
        raise UnsafeKey("identity filters are not a supported events request")
    if found["endpoint"] not in ENDPOINTS:
        raise UnsafeKey(f"identity endpoint {found['endpoint']!r} is unknown")
    return found


class _PageCheck:
    """Pagination semantics: progressive in-bounds cursors, then one explicit null."""

    def __init__(self, identity: Mapping[str, Any]) -> None:
        self.start = float(identity["start_time"])
        self.end = float(identity["end_time"])
        self.critical = identity["role"] == "critical"
        self.done = False
        self.count = 0

    def page(self, page: Any) -> None:
        self.count += 1
        n = self.count
        if self.done:
            raise CacheCorrupt(f"page {n} follows the terminal page")
        if not isinstance(page, Mapping) or set(page) != {"data", "nextPageTimestamp"}:
            raise CacheCorrupt(f"page {n} is not an events page")
        data = page["data"]
        if not isinstance(data, list) or not all(isinstance(e, dict) for e in data):
            raise CacheCorrupt(f"page {n} data is not a list of events")
        if self.critical and any(e.get("type") != "damage" for e in data):
            raise CacheCorrupt(f"page {n} critical-damage scope contains other events")
        cursor = page["nextPageTimestamp"]
        if cursor is None:
            self.done = True
            return
        following = _finite(cursor)
        if following is None or following <= self.start or following > self.end:
            raise CacheCorrupt(f"page {n} cursor {cursor!r} is not a forward in-bounds time")
        self.start = following

    def finish(self) -> None:
        if self.count == 0:
            raise CacheCorrupt("a stream needs at least one page")
        if not self.done:
            raise CacheCorrupt("the stream ended without an explicit terminal page")


def check_pages(identity: Mapping[str, Any], pages: Iterable[Any]) -> None:
    """Raise CacheCorrupt unless `pages` paginate `identity` to an explicit terminal page."""
    check = _PageCheck(identity)
    for page in pages:
        check.page(page)
    check.finish()


_PAGE = re.compile(r"page_\d{3}\.json")
_OWNED_TEMP = re.compile(r"\.(page_\d{3}\.json|stream\.json)\.\d+\.[0-9a-f]{8}\.tmp")


@dataclass(frozen=True, slots=True)
class StreamPages:
    identity: dict[str, Any]
    pages: tuple[dict[str, Any], ...]
    """Each page as published: the API's `events` object (data + nextPageTimestamp)."""
    meta: dict[str, Any]
    """Fetch provenance recorded when the stream was completed (never credentials)."""
    reused: bool = False
    """True when read back from an earlier completion rather than fetched now."""


MetaSource = Mapping[str, Any] | Callable[[], Mapping[str, Any]] | None


class Cache:
    def __init__(self, root: Path) -> None:
        if not root.is_dir() or _is_link(root):
            raise CacheError(f"cache root {root} must be an existing, real directory")
        self.root = root.resolve()
        try:
            publish(
                self.root / "cache-format.json", canonical_bytes({"cache_format": CACHE_FORMAT})
            )
        except CacheConflict:
            raise CacheError(
                f"{root} holds a cache of another format; use a new cache directory "
                "and keep the existing cache unchanged"
            ) from None

    def _fight_dir(self, key: FightKey, create: bool) -> Path:
        return _contained(self.root, *key.parts, create=create)

    # -- report bundles -------------------------------------------------------

    def put_bundle(self, key: FightKey, bundle: Mapping[str, Any]) -> str:
        """Publish a report generation; return its full content digest, never a latest pointer."""
        endpoint = _endpoint(bundle.get("endpoint"))
        report = bundle.get("report")
        if not isinstance(report, dict):
            raise UnsafeKey("a bundle must contain a report object")
        self._bound_report(key, report, (key.fight,))
        data = canonical_bytes(bundle)
        digest = hashlib.sha256(data).hexdigest()
        folder = self._fight_dir(key, create=True)
        with item_lock(folder / ".report.lock"):
            publish(folder / f"report_{endpoint}_{digest}.json", data)
        return digest

    def get_bundle(self, key: FightKey, endpoint: str, digest: str) -> dict[str, Any] | None:
        endpoint, digest = _endpoint(endpoint), _digest(digest)
        path = self._fight_dir(key, create=False) / f"report_{endpoint}_{digest}.json"
        if not _present(path):
            return None
        value = self._generation(path, digest)
        if value.get("endpoint") != endpoint or not isinstance(value.get("report"), dict):
            raise CacheCorrupt(f"{path.name} is not the requested bundle")
        self._bound_report(key, value["report"], (key.fight,))
        return value

    @staticmethod
    def _bound_report(key: FightKey, report: Mapping[str, Any], ids: tuple[int, ...]) -> None:
        if (
            report.get("code") != key.code
            or type(report.get("revision")) is not int
            or report.get("revision") != key.revision
        ):
            raise CacheCorrupt("report generation does not match its code/revision key")
        fights = report.get("fights")
        if not isinstance(fights, list) or any(
            not isinstance(f, dict) or type(f.get("id")) is not int for f in fights
        ):
            raise CacheCorrupt("report generation has no typed fight set")
        found = [f["id"] for f in fights]
        if len(found) != len(set(found)) or sorted(found) != list(ids):
            raise CacheCorrupt("report generation does not match its fight set")

    def _generation(self, path: Path, digest: str) -> dict[str, Any]:
        data = _read(path)
        if hashlib.sha256(data).hexdigest() != digest:
            raise CacheCorrupt(f"{path.name} differs from its generation digest")
        try:
            value = json.loads(data)
        except ValueError:
            raise CacheCorrupt(f"{path.name} is not valid JSON") from None
        if not isinstance(value, dict):
            raise CacheCorrupt(f"{path.name} is not an object")
        return value

    # -- combined report sets ---------------------------------------------------

    def _report_set_path(
        self, key: FightKey, fight_ids: tuple[int, ...], endpoint: str, digest: str
    ) -> Path:
        endpoint, digest = _endpoint(endpoint), _digest(digest)
        ids = tuple(sorted(set(fight_ids)))
        if not ids or ids != tuple(fight_ids):
            raise UnsafeKey("fight ids must be a non-empty, sorted, duplicate-free tuple")
        for fid in ids:
            _positive(fid, "fight id")
        if key.fight not in ids:
            raise UnsafeKey("the locating fight is not in the report set")
        folder = _contained(self.root, *key.parts[:3], create=True)
        # The full record digest also covers the fight set. No second hash is needed.
        return folder / f"report_set_{endpoint}_{digest}.json"

    def put_report_set(
        self, key: FightKey, fight_ids: tuple[int, ...], endpoint: str, report: Mapping[str, Any]
    ) -> str:
        """Publish one combined report answer for exactly `fight_ids` of this revision.

        `key.fight` must be one of the fight ids (it only locates the revision).
        """
        if key.fight not in fight_ids:
            raise UnsafeKey("the locating fight is not in the report set")
        self._bound_report(key, report, fight_ids)
        record = {"fight_ids": list(fight_ids), "endpoint": endpoint, "report": dict(report)}
        data = canonical_bytes(record)
        digest = hashlib.sha256(data).hexdigest()
        path = self._report_set_path(key, fight_ids, endpoint, digest)
        with item_lock(path.with_name(f".{path.stem}.lock")):
            publish(path, data)
        return digest

    def get_report_set(
        self, key: FightKey, fight_ids: tuple[int, ...], endpoint: str, digest: str
    ) -> dict[str, Any] | None:
        """The combined report for exactly this fight set, or None when not cached."""
        path = self._report_set_path(key, fight_ids, endpoint, digest)
        if not _present(path):
            return None
        record = self._generation(path, digest)
        if record.get("fight_ids") != list(fight_ids) or record.get("endpoint") != endpoint:
            raise CacheCorrupt(f"{path.name} is not the report set for {list(fight_ids)}")
        report = record.get("report")
        if not isinstance(report, dict):
            raise CacheCorrupt(f"{path.name} has no report object")
        self._bound_report(key, report, fight_ids)
        return record

    # -- event streams ----------------------------------------------------------

    def _stream_dir(self, key: StreamKey, create: bool) -> Path:
        return _contained(self.root, *key.fight.parts, key.name, create=create)

    def read_stream(self, key: StreamKey, identity: Mapping[str, Any]) -> StreamPages | None:
        """The completed stream, verified against `identity`; None when not complete."""
        wanted = check_identity(key, identity)
        folder = self._stream_dir(key, create=False)
        marker = folder / "stream.json"
        if not _present(marker):
            return None
        return self._verified(folder, marker, wanted)

    def page_bytes(self, key: StreamKey, identity: Mapping[str, Any]) -> list[bytes]:
        """The exact published bytes of a completed stream's pages, after verification."""
        wanted = check_identity(key, identity)
        folder = self._stream_dir(key, create=False)
        marker = folder / "stream.json"
        if not _present(marker):
            raise CacheCorrupt(f"{key.name} is not complete")
        done = self._verified(folder, marker, wanted)
        out = []
        for n in range(1, len(done.pages) + 1):
            data = _read(folder / f"page_{n:03d}.json")
            if json.loads(data) != done.pages[n - 1]:
                raise CacheCorrupt(f"{key.name} page {n} changed while reading")
            out.append(data)
        return out

    def _verified(self, folder: Path, marker: Path, identity: dict[str, Any]) -> StreamPages:
        try:
            record = json.loads(_read(marker))
        except ValueError:
            raise CacheCorrupt(f"{marker} is not valid JSON") from None
        if not isinstance(record, dict) or record.get("cache_format") != CACHE_FORMAT:
            raise CacheCorrupt(f"{marker} has an unknown format")
        if canonical_bytes(record.get("identity")) != canonical_bytes(identity):
            raise CacheConflict(f"{folder.name} was completed for a different request")
        listed = record.get("pages")
        if not isinstance(listed, list) or record.get("terminal") is not True:
            raise CacheCorrupt(f"{marker} does not describe a terminal stream")
        check = _PageCheck(identity)
        pages = []
        for n, entry in enumerate(listed, 1):
            path = folder / f"page_{n:03d}.json"
            if not isinstance(entry, dict) or entry.get("n") != n or not _present(path):
                raise CacheCorrupt(f"{folder.name} page {n} is missing")
            data = _read(path)
            if hashlib.sha256(data).hexdigest() != entry.get("sha256"):
                raise CacheCorrupt(f"{folder.name} page {n} changed after completion")
            try:
                page = json.loads(data)
            except ValueError:
                raise CacheCorrupt(f"{folder.name} page {n} is not valid JSON") from None
            check.page(page)
            if len(page["data"]) != entry.get("events"):
                raise CacheCorrupt(f"{folder.name} page {n} event count differs")
            pages.append(page)
        check.finish()
        raw_meta = record.get("meta")
        meta: dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}
        return StreamPages(identity, tuple(pages), meta, reused=True)

    def write_stream(
        self,
        key: StreamKey,
        identity: Mapping[str, Any],
        pages: Iterable[Mapping[str, Any]],
        meta: MetaSource = None,
    ) -> StreamPages:
        """Publish pages one by one, then the marker; any failure leaves no marker.

        The identity is checked before anything is created. `pages` is consumed
        inside the lock and every page is checked before it is published; the
        marker needs at least one page and an explicit terminal page. `meta` may
        be a callable, evaluated after the last page (fetch provenance).
        An existing completed stream is verified and returned, never rewritten.
        """
        wanted = check_identity(key, identity)
        folder = self._stream_dir(key, create=True)
        with item_lock(folder.parent / f".{key.name}.lock"):
            marker = folder / "stream.json"
            if _present(marker):
                return self._verified(folder, marker, wanted)
            for leftover in folder.iterdir():
                if _PAGE.fullmatch(leftover.name) or _OWNED_TEMP.fullmatch(leftover.name):
                    if _is_link(leftover) or not leftover.is_file():
                        raise UnsafeKey(f"{leftover} is not an ordinary cache file")
                    leftover.unlink()
            check = _PageCheck(wanted)
            entries = []
            for n, page in enumerate(pages, 1):
                check.page(page)
                data = canonical_bytes(dict(page))
                publish(folder / f"page_{n:03d}.json", data)
                entries.append(
                    {
                        "n": n,
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "events": len(page["data"]),
                    }
                )
            check.finish()
            provenance = meta() if callable(meta) else meta
            record = {
                "cache_format": CACHE_FORMAT,
                "identity": wanted,
                "pages": entries,
                "terminal": True,
                "meta": dict(provenance or {}),
            }
            publish(marker, canonical_bytes(record))
            done = self._verified(folder, marker, wanted)
            return StreamPages(done.identity, done.pages, done.meta, reused=False)


__all__ = [
    "CACHE_FORMAT",
    "IDENTITY_FIELDS",
    "Cache",
    "CacheBusy",
    "CacheConflict",
    "CacheCorrupt",
    "CacheError",
    "CacheUnsupported",
    "FightKey",
    "StreamKey",
    "StreamPages",
    "UnsafeKey",
    "canonical_bytes",
    "check_identity",
    "check_pages",
    "is_link",
    "item_lock",
    "publish",
    "valid_report_code",
]
