"""`necropsy auth ...` and `necropsy resolve`: sign-in and character context."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from necropsy.snapshot.v1_writer import WriteError
from necropsy.wcl.analyze import AnalyzeError, run_analyze
from necropsy.wcl.auth import Auth, AuthError, AuthState, CallbackListener, new_state
from necropsy.wcl.cache import CacheError
from necropsy.wcl.client import RATE_FIELDS, WclClient, WclError
from necropsy.wcl.context import describe, resolve
from necropsy.wcl.credentials import CredentialStore, CredentialStoreError
from necropsy.wcl.sites import VANILLA, Site, UnsupportedSite, require_supported
from necropsy.wcl.urls import BadCharacterUrl, parse_character_url

auth_app = typer.Typer(
    help="Sign in to Warcraft Logs for personal use (credentials stay in the OS store).",
    no_args_is_help=True,
)

RATE_QUERY = f"query NecropsyRate {{ {RATE_FIELDS} }}"


def _fail(prefix: str, exc: Exception) -> typer.Exit:
    typer.echo(f"{prefix}: {exc}", err=True)
    return typer.Exit(code=1)


def _auth() -> Auth:
    return Auth(VANILLA, CredentialStore.open())


def _when(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%d %H:%M UTC")


@auth_app.command("login")
def login(
    client_id: Annotated[
        str | None, typer.Option(help="Your WCL API client id (not secret).")
    ] = None,
    new_secret: Annotated[
        bool,
        typer.Option(
            "--new-secret",
            help="Enter a replacement client secret for this sign-in (kept only on success).",
        ),
    ] = False,
    browser: Annotated[
        bool, typer.Option("--browser/--no-browser", help="Open the sign-in page.")
    ] = True,
) -> None:
    """Sign in once: saves the client secret and your token in your OS credential store."""
    try:
        auth = _auth()
        cid = client_id or auth.client_id() or typer.prompt("WCL client id")
        existing = auth.record(cid)
        secret = None
        if new_secret or existing is None:
            secret = typer.prompt("WCL client secret (hidden)", hide_input=True)
        state = new_state()
        url = auth.authorize_url(cid, state)
        with CallbackListener(state) as listener:  # bound before the browser opens
            typer.echo("Sign in to Warcraft Logs in your browser:")
            typer.echo(f"  {url}")
            if browser:
                webbrowser.open(url)
            code = listener.wait()
        token = auth.complete_sign_in(cid, secret, code)
    except (AuthError, CredentialStoreError) as exc:
        raise _fail("auth failed", exc) from None
    typer.echo(f"Signed in to {VANILLA.host}; token valid until {_when(token.expires_at)}.")


@auth_app.command("status")
def status(
    check: Annotated[
        bool, typer.Option("--check", help="Also ask WCL for the current points budget.")
    ] = False,
) -> None:
    """Show the sign-in state. Never prints secrets."""
    try:
        auth = _auth()
        state = auth.state()
        token = auth.stored_token() if state is not AuthState.LOGIN_NEEDED else None
        has_client = auth.client_id() is not None
        rate = None
        if check:
            client = WclClient(VANILLA, auth.token_for)
            try:
                rate = client.query(RATE_QUERY, endpoint="user").rate
            finally:
                client.close()
    except (AuthError, CredentialStoreError, WclError) as exc:
        raise _fail("auth failed", exc) from None
    typer.echo(f"site:             {VANILLA.host}")
    typer.echo(f"credential store: {auth.store.backend_name}")
    typer.echo(f"client id:        {'set' if has_client else 'not set'}")
    typer.echo(f"sign-in:          {state.value}")
    if token is not None:
        typer.echo(f"token expires:    {_when(token.expires_at)}")
    if rate is not None:
        typer.echo(
            f"points:           {rate.points_spent:.0f} of {rate.limit_per_hour} used this hour "
            f"(resets in {rate.reset_in_s // 60} min)"
        )


@auth_app.command("logout")
def logout(
    forget_secret: Annotated[
        bool, typer.Option("--forget-secret", help="Also remove the client id and secret.")
    ] = False,
) -> None:
    """Remove the stored token (and optionally the client secret)."""
    try:
        _auth().logout(forget_secret=forget_secret)
    except (AuthError, CredentialStoreError) as exc:
        raise _fail("auth failed", exc) from None
    typer.echo("Signed out." + (" Client id and secret removed." if forget_secret else ""))


def resolve_command(
    url: Annotated[str, typer.Argument(help="A Warcraft Logs character URL.")],
    partition: Annotated[
        int | None, typer.Option(help="Partition id when several hold rankings.")
    ] = None,
) -> None:
    """Show who a character URL points to: character, faction, zone and partition."""
    try:
        ref = parse_character_url(url)
        require_supported(ref.site)
        auth = _auth()
        client = WclClient(ref.site, auth.token_for)
        try:
            context = resolve(client, ref, partition=partition)
        finally:
            client.close()
    except (BadCharacterUrl, UnsupportedSite, AuthError, CredentialStoreError, WclError) as exc:
        raise _fail("resolve failed", exc) from None
    for key, value in describe(context).items():
        typer.echo(f"{key + ':':16}{'unknown' if value is None else value}")
    if context.faction.level != "observed":
        typer.echo(f"faction note:   {context.faction.note}")
    for note in context.notes:
        typer.echo(f"note:           {note}")
    if context.ambiguity:
        typer.echo(f"needs a choice: {context.ambiguity}")
        raise typer.Exit(code=2)


def _client(site: Site, tokens: Callable[[str], str]) -> WclClient:
    return WclClient(site, tokens)


def _tokens() -> Callable[[str], str]:
    return _auth().token_for


def analyze_command(
    url: Annotated[str, typer.Argument(help="A Warcraft Logs character URL.")],
    cache: Annotated[
        Path,
        typer.Option("--cache", help="Keep fetched API data here for later runs. Required."),
    ],
    out: Annotated[
        Path, typer.Option("--out", help="Write results here. Refuses earlier analysis outputs.")
    ],
    partition: Annotated[
        int | None, typer.Option(help="Partition id when several hold rankings.")
    ] = None,
    endpoint: Annotated[
        str, typer.Option(help="Use client or user for every request; no automatic fallback.")
    ] = "client",
    cross_faction: Annotated[
        bool,
        typer.Option(
            "--cross-faction",
            help="Add verified other-faction overall #1 context in a separate comparison view.",
        ),
    ] = False,
    name: Annotated[
        str | None, typer.Option(help="Snapshot stem, without .zip (default: character-zone-UTC).")
    ] = None,
    package: Annotated[
        bool,
        typer.Option("--package/--no-package", help="Also write the shareable ZIP package."),
    ] = True,
    wait_for_reset: Annotated[
        bool,
        typer.Option(
            "--wait-for-reset",
            help="Allow one observed hourly reset wait (at most one hour) during this run.",
        ),
    ] = False,
) -> None:
    """Acquire a Classic Era Hunter's Naxxramas logs and write a report.

    Uses saved WCL credentials and the network. Exit 0: complete report;
    4: partial report; 2: choose a partition; 3: finalization stopped, no report;
    1: failure. Saved snapshots can be replayed with offline.
    """
    try:
        outcome = run_analyze(
            url,
            cache=cache,
            out=out,
            partition=partition,
            endpoint=endpoint,
            cross_faction=cross_faction,
            name=name,
            package=package,
            wait_for_reset=wait_for_reset,
            tokens=_tokens,
            client_factory=_client,
        )
    except AnalyzeError as exc:
        for line in exc.lines:
            typer.echo(line, err=True)
        typer.echo(f"analyze failed: {exc}", err=True)
        raise typer.Exit(code=exc.code) from None
    except (AuthError, CredentialStoreError, WclError, CacheError, WriteError, OSError) as exc:
        raise _fail("analyze failed", exc) from None
    for line in outcome.lines:
        typer.echo(line)
    if outcome.code:
        raise typer.Exit(code=outcome.code)


__all__ = ["analyze_command", "auth_app", "resolve_command"]
