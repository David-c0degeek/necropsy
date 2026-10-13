"""`necropsy auth ...` and `necropsy resolve`: sign-in and character context."""

from __future__ import annotations

import webbrowser
from datetime import UTC, datetime
from typing import Annotated

import typer

from necropsy.wcl.auth import Auth, AuthError, AuthState, CallbackListener, new_state
from necropsy.wcl.client import RATE_FIELDS, WclClient, WclError
from necropsy.wcl.context import describe, resolve
from necropsy.wcl.credentials import CredentialStore, CredentialStoreError
from necropsy.wcl.sites import VANILLA, UnsupportedSite, require_supported
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


__all__ = ["auth_app", "resolve_command"]
