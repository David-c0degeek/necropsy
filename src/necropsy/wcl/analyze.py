"""`necropsy analyze`: one character URL to a live snapshot, report and playbook.

Everything that can be checked offline is checked before credentials are read or
any request is sent: the URL and site, the options, and that the cache and output
directories are plain directories. New runs require fresh output directories;
explicit resumes verify checkpoint options and owned output digests before
replacing partial pages. One endpoint serves the whole
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
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from necropsy.analysis.roles import CLASS_NAMES, ranking_policy, selected_spec
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
from necropsy.wcl.checkpoint import Checkpoint, Journal, saved_options
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
    reset_wait: dict[str, float | int] | None = None


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
    allowed = allowed or set()
    found = [
        n
        for n in (ANALYSIS_FILE, REPORT_FILE, PLAYBOOK_FILE)
        if os.path.lexists(out / n) and n not in allowed
    ]
    found += sorted(p.name for p in out.glob("necropsy-*.zip") if p.name not in allowed)
    snap = out / SNAPSHOT_DIR
    if os.path.lexists(snap):
        if _linkish(snap) or not snap.is_dir():
            found.append(SNAPSHOT_DIR)
        else:
            for p in sorted(snap.iterdir()):
                if p.name.endswith(".lock") or (f"snapshot/{p.name}" in allowed):
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
    url: str,
    cache: Path,
    out: Path,
    partition: int | None,
    endpoint: str,
    name: str | None,
    *,
    resume: bool = False,
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
    if earlier and not resume:
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
    wait_for_reset: bool = False,
    tokens: TokenSource,
    client_factory: ClientFactory,
    resolver: Resolver | None = None,
    before_acquire: Callable[[CharacterContext], None] | None = None,
    category: str | None = None,
    metric: str | None = None,
    spec: str | None = None,
    faction: str | None = None,
    progress: Callable[[str], None] | None = None,
    resume: bool = False,
) -> Outcome:
    ref, cache_dir, out_dir = check_inputs(
        url, cache, out, partition, endpoint, name, resume=resume
    )
    if resume:
        saved = saved_options(out_dir)
        if category is None and spec is None:
            category = saved["category"]
        faction = faction if faction is not None else saved["faction"]
        partition = partition if partition is not None else saved["partition"]
        name = name if name is not None else saved["name"]
        metric = metric if metric is not None else saved["metric"]
    try:
        category = selected_spec(category)
        selected = selected_spec(spec)
        if category is not None and selected is not None and category != selected:
            raise ValueError("--spec and --category select different ranking categories")
        category = selected or category
        if faction is not None:
            faction = faction.strip().capitalize()
            if faction not in ("Alliance", "Horde"):
                raise ValueError("choose --faction Alliance or Horde")
    except ValueError as error:
        raise AnalyzeError(str(error)) from None
    chosen: Endpoint = "user" if endpoint == "user" else "client"
    resolver = resolver or resolve
    with item_lock(out_dir / LOCK):
        checkpoint = Checkpoint(
            out_dir,
            {
                "url": url,
                "cache": str(cache_dir),
                "partition": partition,
                "endpoint": endpoint,
                "cross_faction": cross_faction,
                "name": name,
                "package": package,
                "category": category,
                "metric": metric,
                "faction": faction,
            },
            resume,
        )
        if earlier_outputs(out_dir, checkpoint.allowed):
            raise AnalyzeError(f"{out_dir} gained an analysis; choose a new output directory")
        if progress is not None:
            progress("Loading Warcraft Logs credentials")
        client = client_factory(ref.site, tokens())
        client.progress = progress
        client.policy = replace(client.policy, wait_for_reset=wait_for_reset)
        try:
            outcome = _run(
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
                category=category,
                metric=metric,
                faction=faction,
                progress=progress,
                checkpoint=checkpoint,
                resume=resume,
            )
            if outcome.code:
                outcome.lines.append(
                    "After the hourly reset, resume with: "
                    + shell_command(
                        [
                            "necropsy",
                            "analyze",
                            url,
                            "--cache",
                            str(cache_dir),
                            "--out",
                            str(out_dir),
                            "--endpoint",
                            endpoint,
                            "--resume",
                            *(["--partition", str(partition)] if partition is not None else []),
                            *(["--spec", category] if category else []),
                            *(["--metric", metric] if metric else []),
                            *(["--faction", faction] if faction else []),
                            *(["--name", name] if name else []),
                            *(["--cross-faction"] if cross_faction else []),
                            *([] if package else ["--no-package"]),
                        ]
                    )
                )
            return outcome
        except AnalyzeError as error:
            error.lines += ("Saved progress is kept. Retry the original command with --resume.",)
            raise
        finally:
            client.close()
            if not resume and client.journal is None and not checkpoint.allowed:
                # A refused context (e.g. ambiguous partition) has no acquisition
                # to resume; allow the corrected choice in this same directory.
                checkpoint.path.unlink(missing_ok=True)


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
    category: str | None = None,
    metric: str | None = None,
    faction: str | None = None,
    progress: Callable[[str], None] | None = None,
    checkpoint: Checkpoint | None = None,
    resume: bool = False,
) -> Outcome:
    def notify(message: str) -> None:
        if progress is not None:
            progress(message)

    notify("Resolving character, faction and partition")
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
    if faction is not None and context.faction.value.value != faction:
        raise AnalyzeError(
            f"selected faction {faction} differs from the character's observed faction "
            f"{context.faction.value.value}; choose the character's faction for the main list"
        )
    if context.class_id.value not in CLASS_NAMES:
        raise AnalyzeError("only Classic Era classes can be analysed")
    try:
        policy = ranking_policy(context.class_id.value, category, metric)
    except ValueError as error:
        raise AnalyzeError(str(error)) from None
    context = replace(context, ranking_category=policy.category, ranking_metric=metric)
    if before_acquire is not None:
        before_acquire(context)  # last chance to refuse before any acquisition request
    if checkpoint is not None:
        checkpoint.bind(
            {
                "character": context.character_id.value,
                "class": context.class_id.value,
                "faction": context.faction.value.value,
                "zone": context.zone_id,
                "partition": context.partition.id if context.partition is not None else None,
            }
        )
        client.journal = Journal(plain_dir(checkpoint.root / "requests", "request checkpoint"))
    store = Cache(cache_dir)
    before = Reading(client.last_rate, client.last_rate_at)
    acquisition = acquire(
        client,
        store,
        ref.site,
        context,
        endpoint=endpoint,
        cross_faction=cross_faction,
        progress=progress,
    )
    notify("Finalizing acquired reports")
    if client.journal is not None:
        client.journal.scope = "finalization"
    try:
        finalize_reports(
            Run(
                client,
                store,
                ref.site,
                endpoint,
                class_id=context.class_id.value,
                category=category,
                metric=metric,
            ),
            acquisition,
        )
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
    snapshot_root = out_dir / SNAPSHOT_DIR
    if resume and checkpoint is not None:
        snapshot_root = plain_dir(checkpoint.root / "snapshots", "saved snapshots") / uuid4().hex
    snapshot_dir = plain_dir(snapshot_root, "snapshot directory")
    notify("Writing snapshot")
    written = write_snapshot(acquisition, store, snapshot_dir, stem)
    if checkpoint is not None:
        checkpoint.record([written.archive, written.entries, written.sha256_file])
    mine = {
        p.relative_to(out_dir).as_posix()
        for p in (written.archive, written.entries, written.sha256_file)
    }
    if checkpoint is not None:
        mine |= checkpoint.allowed
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
    notify("Analyzing snapshot and writing report, playbook and package")
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
    if checkpoint is not None:
        checkpoint.record(list(result.files))
    lines = _boss_lines(acquisition)
    if client.journal is not None and client.journal.reused:
        lines.append(f"reused {client.journal.reused} saved Warcraft Logs requests")
    if acquisition.stopped:
        lines.append(f"stopped early: {acquisition.stopped}")
    lines.append(_points(before, after, client))
    if client.reset_wait is not None:
        lines.append(
            f"hourly reset wait: {client.reset_wait['elapsed_wait_s']:g} seconds "
            f"(observed reset countdown: {client.reset_wait['observed_reset_in_s']} seconds)"
        )
    lines.append(f"snapshot: {written.archive}")
    lines += [f"wrote: {p}" for p in result.files]
    lines.append(f"Next: open {out_dir / REPORT_FILE} in your browser.")
    complete = not acquisition.stopped and all(
        b.coverage.get("complete") for b in acquisition.bosses
    )
    complete = complete and len(acquisition.bosses) == len(acquisition.requested)
    return Outcome(0 if complete else 4, lines, written, acquisition, client.reset_wait)


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
