"""Command-line entry point."""

import sys
from pathlib import Path
from typing import Annotated

import typer

from necropsy import __version__
from necropsy.analysis.roles import load_overrides
from necropsy.normalize.ingest import IngestError, ingest
from necropsy.report.offline import run_offline
from necropsy.report.package import REPORT_FILE, write_outputs
from necropsy.report.publish import PublishError
from necropsy.report.render import RenderError
from necropsy.snapshot.archive import ArchiveError, load_entries_manifest
from necropsy.snapshot.model import SnapshotError
from necropsy.wcl.cli import analyze_command, auth_app, resolve_command

app = typer.Typer(
    name="necropsy",
    help="Local-first Warcraft Logs forensics. Acquire supported Naxxramas logs or replay a snapshot.",
    epilog="Start here: necropsy offline SNAPSHOT.zip --out workspace/analysis, then open "
    "report.html.",
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
    """Acquire supported logs or replay a snapshot. Use COMMAND --help for options."""


@app.command("ingest")
def ingest_command(
    snapshot: Annotated[
        Path, typer.Argument(help="v6 export, fixture subset, or live snapshot ZIP.")
    ],
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
    snapshot: Annotated[
        Path, typer.Argument(help="v6 export, fixture subset, or live snapshot ZIP.")
    ],
    out: Annotated[
        Path, typer.Option("--out", help="Write analysis.json, the report and playbook here.")
    ],
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
    package: Annotated[
        bool,
        typer.Option("--package/--no-package", help="Also write the shareable ZIP package."),
    ] = True,
    role_overrides: Annotated[
        Path | None, typer.Option(help="JSON report/fight role overrides with explicit reasons.")
    ] = None,
) -> None:
    """Analyze bosses, comparisons and recommendations. Write the report offline."""
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
            package=package,
            role_overrides=load_overrides(role_overrides) if role_overrides else None,
        )
    except (
        ArchiveError,
        SnapshotError,
        IngestError,
        PublishError,
        RenderError,
        OSError,
        ValueError,
    ) as exc:
        typer.echo(f"offline analysis failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"bosses:           {result.bosses}")
    typer.echo(f"recommendations:  {result.recommendations}")
    for path in result.files:
        typer.echo(f"wrote:            {path}")
    typer.echo(f"Next: open {out / REPORT_FILE} in your browser.")


@app.command("render")
def render_command(
    analysis: Annotated[Path, typer.Argument(help="An analysis.json written by Necropsy.")],
    out: Annotated[Path, typer.Option("--out", help="Write the report and playbook here.")],
    package: Annotated[
        bool,
        typer.Option("--package/--no-package", help="Also write the shareable ZIP package."),
    ] = True,
) -> None:
    """Rebuild the report, playbook and package from an existing analysis.json."""
    try:
        paths = write_outputs(analysis.read_bytes(), out, include_package=package)
    except (ValueError, PublishError, OSError) as exc:
        typer.echo(f"render failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    for path in paths:
        typer.echo(f"wrote:            {path}")
    typer.echo(f"Next: open {out / REPORT_FILE} in your browser.")


app.add_typer(auth_app, name="auth")
app.command("resolve")(resolve_command)
app.command("analyze")(analyze_command)


def main() -> None:
    _force_utf8_output()
    app()
