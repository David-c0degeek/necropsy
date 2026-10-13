"""Command-line entry point."""

import sys
from pathlib import Path
from typing import Annotated

import typer

from necropsy import __version__
from necropsy.normalize.ingest import IngestError, ingest
from necropsy.report.offline import run_offline
from necropsy.snapshot.archive import ArchiveError, load_entries_manifest
from necropsy.snapshot.model import SnapshotError

app = typer.Typer(
    name="necropsy",
    help="Local-first Warcraft Logs forensics. Analyze saved Classic Era Hunter/Naxxramas logs.",
    epilog="Start here: necropsy offline SNAPSHOT.zip --out workspace/analysis",
    no_args_is_help=True,
    add_completion=False,
)


def _force_utf8_output() -> None:
    # Player and NPC names are often non-ASCII; a cp1252 Windows console would
    # otherwise raise UnicodeEncodeError half-way through a report.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"necropsy {__version__}")
        raise typer.Exit


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Analyze a supported saved export offline. Run a command with --help for its options."""


@app.command("ingest")
def ingest_command(
    snapshot: Annotated[Path, typer.Argument(help="v6 Hunter deep-export ZIP or fixture subset.")],
    db: Annotated[Path, typer.Option("--db", help="Save the analysis database at this path.")],
    sha256: Annotated[
        str | None, typer.Option(help="Refuse the archive unless its SHA-256 matches.")
    ] = None,
    entries: Annotated[
        Path | None,
        typer.Option(help="Member checksum manifest (not the export's manifest.json)."),
    ] = None,
    replace: Annotated[
        bool,
        typer.Option("--replace", help="Replace a database from another archive. Keep it closed."),
    ] = False,
) -> None:
    """Build a database for inspection or repeat analysis. No network access."""
    try:
        manifest = load_entries_manifest(entries) if entries else None
        summary = ingest(snapshot, db, expected_sha256=sha256, entries=manifest, replace=replace)
    except (ArchiveError, SnapshotError, IngestError) as exc:
        typer.echo(f"ingest failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"database:   {summary.database}")
    typer.echo(f"snapshot:   {summary.archive_sha256} ({summary.scope})")
    typer.echo(f"fights:     {summary.fights}")
    typer.echo(f"streams:    {summary.streams} ({summary.incomplete_streams} not complete)")
    typer.echo(
        f"events:     {summary.events} distinct occurrences "
        f"from {summary.stream_events} stream events"
    )
    typer.echo(f"anomalies:  {summary.anomalies}")
    typer.echo(f"issues:     {summary.issues}")
    typer.echo("Next: run necropsy offline on the same ZIP with --db pointing to this database.")


@app.command("offline")
def offline_command(
    snapshot: Annotated[Path, typer.Argument(help="v6 Hunter deep-export ZIP or fixture subset.")],
    out: Annotated[Path, typer.Option("--out", help="Write analysis.json in this directory.")],
    db: Annotated[
        Path | None,
        typer.Option(help="Keep/reuse a matching database here. Default: temporary database."),
    ] = None,
    cross_faction: Annotated[
        bool,
        typer.Option(
            "--cross-faction",
            help="Add separate cross-faction context; keep the same-faction baseline unchanged.",
        ),
    ] = False,
    sha256: Annotated[
        str | None, typer.Option(help="Refuse the archive unless its SHA-256 matches.")
    ] = None,
    entries: Annotated[
        Path | None,
        typer.Option(help="Member checksum manifest (not the export's manifest.json)."),
    ] = None,
    replace: Annotated[
        bool,
        typer.Option("--replace", help="Replace a --db from another archive. Keep it closed."),
    ] = False,
) -> None:
    """Analyze bosses, comparisons and recommendations. Write analysis.json offline."""
    try:
        manifest = load_entries_manifest(entries) if entries else None
        result = run_offline(
            snapshot,
            out,
            db=db,
            cross_faction=cross_faction,
            expected_sha256=sha256,
            entries=manifest,
            replace=replace,
        )
    except (ArchiveError, SnapshotError, IngestError) as exc:
        typer.echo(f"offline analysis failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"analysis:         {result.analysis}")
    typer.echo(f"bosses:           {result.bosses}")
    typer.echo(f"recommendations:  {result.recommendations}")
    typer.echo("Next: open analysis.json in your editor. Result guide: docs/reading-results.md")


def main() -> None:
    _force_utf8_output()
    app()
