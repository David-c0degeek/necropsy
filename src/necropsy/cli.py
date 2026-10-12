"""Command-line entry point."""

import sys
from typing import Annotated

import typer

from necropsy import __version__

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


def main() -> None:
    _force_utf8_output()
    app()
