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
    help="Local-first Warcraft Logs forensics.",
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
    """Analyze Warcraft Logs data offline and produce forensic playbooks."""


@app.command("ingest")
def ingest_command(
    snapshot: Annotated[Path, typer.Argument(help="Raw snapshot archive (.zip).")],
    db: Annotated[Path, typer.Option("--db", help="DuckDB database to build.")],
    sha256: Annotated[
        str | None, typer.Option(help="Refuse the archive unless its SHA-256 matches.")
    ] = None,
    entries: Annotated[
        Path | None,
        typer.Option(help="Entries manifest; every member is checked against it."),
    ] = None,
    replace: Annotated[
        bool, typer.Option("--replace", help="Overwrite a database built from another snapshot.")
    ] = False,
) -> None:
    """Normalize a raw snapshot into a DuckDB analysis database (offline)."""
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


@app.command("offline")
def offline_command(
    snapshot: Annotated[Path, typer.Argument(help="Raw snapshot archive (.zip).")],
    out: Annotated[Path, typer.Option("--out", help="Directory for analysis.json.")],
    db: Annotated[
        Path | None,
        typer.Option(help="Keep the analysis database here (reused if it matches)."),
    ] = None,
    cross_faction: Annotated[
        bool,
        typer.Option(
            "--cross-faction",
            help="Also show the cross-faction view. Never merged into the realistic benchmark.",
        ),
    ] = False,
    sha256: Annotated[
        str | None, typer.Option(help="Refuse the archive unless its SHA-256 matches.")
    ] = None,
    entries: Annotated[
        Path | None, typer.Option(help="Entries manifest; every member is checked against it.")
    ] = None,
    replace: Annotated[
        bool, typer.Option("--replace", help="Overwrite a --db built from another snapshot.")
    ] = False,
) -> None:
    """Analyze a snapshot offline and write analysis.json."""
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


def main() -> None:
    _force_utf8_output()
    app()
