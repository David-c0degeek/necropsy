"""`necropsy analyze`: one character URL to a live snapshot, report and playbook.

Everything that can be checked offline is checked before credentials are read or
any request is sent: the URL and site, the options, and that the cache and output
directories are plain directories and that the output directory holds no earlier
analysis (the report pages are written by the offline publisher, which replaces
files, so a fresh output directory is required). One endpoint serves the whole
run. A lock in the output directory keeps two runs apart for the whole run.

Exit codes: 0 complete; 4 report written but coverage partial or the run stopped
early; 3 finalization stopped, no new snapshot or report; 2 a choice is needed
(partition); 1 anything else (unsupported context, refused input, failures).
"""

from __future__ import annotations

import os
import re
import shlex
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from necropsy.report.offline import run_offline
from necropsy.report.package import ANALYSIS_FILE, PLAYBOOK_FILE, REPORT_FILE
from necropsy.snapshot.archive import load_entries_manifest
from necropsy.snapshot.v1_writer import Written, write_snapshot
from necropsy.wcl.acquire import (
    Acquisition,
    MixedRevision,
    Run,
    RunStopped,
    acquire,
    finalize_reports,
)
from necropsy.wcl.cache import Cache, item_lock
from necropsy.wcl.client import Endpoint, WclClient
from necropsy.wcl.context import CharacterContext, resolve
from necropsy.wcl.fetch import Reading, fetch_meta
from necropsy.wcl.sites import Site, require_supported
from necropsy.wcl.urls import CharacterRef, parse_character_url

ENDPOINTS: tuple[Endpoint, ...] = ("client", "user")
SNAPSHOT_DIR = "snapshot"
LOCK = ".necropsy-analyze.lock"
_NAME = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,79}")
_LINK_TAGS = {0xA000000C, 0xA0000003}  # Windows symlink and junction (mount point)
HUNTER_CLASS_ID = 3


class AnalyzeError(Exception):
    """A refusal or failure with the exit code it maps to."""

    def __init__(self, message: str, code: int = 1, lines: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.code = code
        self.lines = lines


@dataclass
class Outcome:
    code: int
    lines: list[str] = field(default_factory=list)
    snapshot: Written | None = None
    acquisition: Acquisition | None = None


TokenSource = Callable[[], Callable[[str], str]]
"""Returns the token provider for an endpoint; called only after offline checks."""
ClientFactory = Callable[[Site, Callable[[str], str]], WclClient]
Resolver = Callable[..., CharacterContext]


def _linkish(path: Path) -> bool:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        return True
    return getattr(info, "st_reparse_tag", 0) in _LINK_TAGS


def plain_dir(path: Path, what: str) -> Path:
    """`path` as an existing plain directory; missing parts are created as plain dirs.

    Refuses a symlink or junction anywhere on the way (other reparse points, such
    as cloud-synced folders, are accepted).
    """
    path = path.absolute()
    for part in [*reversed(path.parents), path]:
        if os.path.lexists(part) and _linkish(part):
            raise AnalyzeError(f"the {what} path goes through a link: {part}")
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir() or _linkish(path):
        raise AnalyzeError(f"the {what} must be a plain directory: {path}")
    return path


def earlier_outputs(out: Path, allowed: set[str] | None = None) -> list[str]:
    """Analysis outputs already in `out` (`allowed` snapshot member names excepted)."""
    found = [n for n in (ANALYSIS_FILE, REPORT_FILE, PLAYBOOK_FILE) if os.path.lexists(out / n)]
    found += sorted(p.name for p in out.glob("necropsy-*.zip"))
    snap = out / SNAPSHOT_DIR
    if os.path.lexists(snap):
        if _linkish(snap) or not snap.is_dir():
            found.append(SNAPSHOT_DIR)
        else:
            for p in sorted(snap.iterdir()):
                if p.name.endswith(".lock") or (allowed is not None and p.name in allowed):
                    continue
                found.append(f"{SNAPSHOT_DIR}/{p.name}")
    return found


def powershell_quote(arg: str) -> str:
    """One PowerShell argument: single quotes, apostrophes doubled (no interpolation)."""
    if arg and all(ch.isalnum() or ch in "-_./:\\" for ch in arg):
        return arg
    return "'" + arg.replace("'", "''") + "'"


def shell_command(args: list[str], *, windows: bool | None = None) -> str:
    """A command line safe to paste: PowerShell quoting on Windows, POSIX elsewhere."""
    if sys.platform == "win32" if windows is None else windows:
        return " ".join(powershell_quote(a) for a in args)
    return shlex.join(args)


def _boss_lines(acquisition: Acquisition) -> list[str]:
    from necropsy.snapshot.v1_writer import _boss_names

    names = _boss_names()
    lines = []
    done = {b.encounter_id for b in acquisition.bosses}
    for b in acquisition.bosses:
        name = names.get(b.encounter_id, str(b.encounter_id))
        reasons = list(b.coverage.get("reasons") or [])
        if b.coverage.get("complete"):
            lines.append(f"{name}: complete")
        else:
            more = f" (+{len(reasons) - 1} more)" if len(reasons) > 1 else ""
            lines.append(f"{name}: partial — {reasons[0] if reasons else 'see the report'}{more}")
    for encounter in acquisition.requested:
        if encounter not in done:
            lines.append(f"{names.get(encounter, encounter)}: not attempted")
    return lines


def _points(before: Reading, after: Reading, client: WclClient) -> str:
    meta = fetch_meta(client, before, after)
    value = meta["account_points_between_readings"]
    if value is None:
        return "account points between readings: unknown (" + str(meta["points_note"]) + ")"
    return f"account points between readings: {value:g} (account-wide; may include other activity)"


def check_inputs(
    url: str, cache: Path, out: Path, partition: int | None, endpoint: str, name: str | None
) -> tuple[CharacterRef, Path, Path]:
    """Everything that needs no credentials and no network."""
    try:
        ref = parse_character_url(url)
        require_supported(ref.site)
    except Exception as error:  # BadCharacterUrl / UnsupportedSite carry their message
        raise AnalyzeError(str(error)) from None
    if endpoint not in ENDPOINTS:
        raise AnalyzeError(f"endpoint must be one of {', '.join(ENDPOINTS)}")
    if partition is not None and (isinstance(partition, bool) or partition <= 0):
        raise AnalyzeError("partition must be a positive number")
    if name is not None and not _NAME.fullmatch(name):
        raise AnalyzeError("the snapshot name may use letters, digits, '.', '_' and '-' only")
    cache_dir = plain_dir(cache, "cache directory")
    out_dir = plain_dir(out, "output directory")
    earlier = earlier_outputs(out_dir)
    if earlier:
        raise AnalyzeError(
            f"{out_dir} already holds an analysis ({', '.join(earlier)}); "
            "choose a new output directory"
        )
    return ref, cache_dir, out_dir


def run_analyze(
    url: str,
    *,
    cache: Path,
    out: Path,
    partition: int | None = None,
    endpoint: str = "client",
    cross_faction: bool = False,
    name: str | None = None,
    package: bool = True,
    tokens: TokenSource,
    client_factory: ClientFactory,
    resolver: Resolver | None = None,
    before_acquire: Callable[[CharacterContext], None] | None = None,
) -> Outcome:
    ref, cache_dir, out_dir = check_inputs(url, cache, out, partition, endpoint, name)
    chosen: Endpoint = "user" if endpoint == "user" else "client"
    resolver = resolver or resolve
    with item_lock(out_dir / LOCK):
        if earlier_outputs(out_dir):
            raise AnalyzeError(f"{out_dir} gained an analysis; choose a new output directory")
        client = client_factory(ref.site, tokens())
        try:
            return _run(
                ref,
                client,
                cache_dir,
                out_dir,
                partition,
                chosen,
                cross_faction,
                name,
                package,
                resolver,
                before_acquire=before_acquire,
            )
        finally:
            client.close()


def _run(
    ref: CharacterRef,
    client: WclClient,
    cache_dir: Path,
    out_dir: Path,
    partition: int | None,
    endpoint: Endpoint,
    cross_faction: bool,
    name: str | None,
    package: bool,
    resolver: Resolver,
    before_acquire: Callable[[CharacterContext], None] | None = None,
) -> Outcome:
    context = resolver(client, ref, partition=partition, endpoint=endpoint)
    if context.ambiguity:
        lines = [f"needs a choice: {context.ambiguity}"]
        lines += [
            f"  partition {p.id}: {p.name}"
            + (
                ""
                if p.has_rankings is None
                else (" (has rankings)" if p.has_rankings else " (no rankings)")
            )
            for p in context.partitions
        ]
        raise AnalyzeError("choose a partition with --partition", code=2, lines=tuple(lines))
    if context.faction.level != "observed":
        raise AnalyzeError(f"the character's faction is unknown: {context.faction.note}")
    if context.class_id.value != HUNTER_CLASS_ID:
        raise AnalyzeError("only Hunters can be analysed for now")
    if before_acquire is not None:
        before_acquire(context)  # last chance to refuse before any acquisition request
    store = Cache(cache_dir)
    before = Reading(client.last_rate, client.last_rate_at)
    acquisition = acquire(
        client, store, ref.site, context, endpoint=endpoint, cross_faction=cross_faction
    )
    try:
        finalize_reports(Run(client, store, ref.site, endpoint), acquisition)
    except RunStopped as stop:
        raise AnalyzeError(
            f"stopped while finalizing reports: {stop}; no snapshot or report was written "
            f"(fetched data stays in the cache {cache_dir} for the next run)",
            code=3,
        ) from None
    except MixedRevision as error:
        raise AnalyzeError(f"{error}; rerun to fetch the changed report again") from None
    after = Reading(client.last_rate, client.last_rate_at)
    stem = name or "{}-{}-{}".format(
        context.character_id.value, context.zone_id, datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    )
    snapshot_dir = plain_dir(out_dir / SNAPSHOT_DIR, "snapshot directory")
    written = write_snapshot(acquisition, store, snapshot_dir, stem)
    mine = {written.archive.name, written.entries.name, written.sha256_file.name}
    stray = earlier_outputs(out_dir, allowed=mine)
    if stray:
        raise AnalyzeError(
            f"{out_dir} gained other output ({', '.join(stray)}); the snapshot is kept at "
            f"{written.archive}"
        )
    recover = shell_command(
        [
            "necropsy",
            "offline",
            str(written.archive),
            "--sha256",
            written.sha256,
            "--entries",
            str(written.entries),
            "--out",
            str(out_dir),
            *(["--cross-faction"] if cross_faction else []),
            *([] if package else ["--no-package"]),
        ]
    )
    try:
        result = run_offline(
            written.archive,
            out_dir,
            expected_sha256=written.sha256,
            entries=load_entries_manifest(written.entries),
            cross_faction=cross_faction,
            package=package,
        )
    except Exception as error:
        raise AnalyzeError(
            f"the snapshot was saved but the report could not be written: {error}",
            lines=(f"snapshot: {written.archive}", f"finish offline with: {recover}"),
        ) from None
    lines = _boss_lines(acquisition)
    if acquisition.stopped:
        lines.append(f"stopped early: {acquisition.stopped}")
    lines.append(_points(before, after, client))
    lines.append(f"snapshot: {written.archive}")
    lines += [f"wrote: {p}" for p in result.files]
    lines.append(f"Next: open {out_dir / REPORT_FILE} in your browser.")
    complete = not acquisition.stopped and all(
        b.coverage.get("complete") for b in acquisition.bosses
    )
    complete = complete and len(acquisition.bosses) == len(acquisition.requested)
    return Outcome(0 if complete else 4, lines, written, acquisition)


__all__ = [
    "LOCK",
    "SNAPSHOT_DIR",
    "AnalyzeError",
    "Outcome",
    "check_inputs",
    "earlier_outputs",
    "plain_dir",
    "run_analyze",
]
