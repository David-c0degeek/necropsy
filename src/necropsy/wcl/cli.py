"""`necropsy auth ...` and `necropsy resolve`: sign-in and character context."""

from __future__ import annotations

import os
import sys
import webbrowser
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.status import Status

from necropsy.raids import RAIDS, with_raid
from necropsy.snapshot.v1_writer import WriteError
from necropsy.wcl.analyze import AnalyzeError, run_analyze
from necropsy.wcl.auth import (
    CLIENT_ID_ENV,
    PUBLIC_CLIENT_ID,
    Auth,
    AuthError,
    AuthMode,
    AuthState,
    CallbackListener,
    PkceAttempt,
    new_state,
)
from necropsy.wcl.cache import CacheError
from necropsy.wcl.client import RATE_FIELDS, WclClient, WclError
from necropsy.wcl.context import describe, resolve
from necropsy.wcl.credentials import CredentialStore, CredentialStoreError
from necropsy.wcl.sites import VANILLA, Site, UnsupportedSite, require_supported
from necropsy.wcl.urls import BadCharacterUrl, parse_character_url

auth_app = typer.Typer(
    help="Sign in to Warcraft Logs (authorization stays in the OS credential store).",
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
    mode: Annotated[
        AuthMode, typer.Option(help="Public PKCE (no shared secret), or your personal client.")
    ] = AuthMode.PUBLIC,
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
    """Authorize your WCL account in a browser; save tokens in the OS store."""
    try:
        if mode is AuthMode.PUBLIC and new_secret:
            raise AuthError("--new-secret requires --mode personal")
        auth = _auth()
        saved_id = auth.client_id() if mode is auth.mode() else None
        cid = (
            client_id
            or os.environ.get(CLIENT_ID_ENV)
            or (PUBLIC_CLIENT_ID if mode is AuthMode.PUBLIC else None)
            or saved_id
            or typer.prompt("WCL public client id" if mode is AuthMode.PUBLIC else "WCL client id")
        )
        if not cid.strip():
            raise AuthError("a registered WCL client id is required")
        existing = auth.record(cid, mode=mode)
        secret = None
        if mode is AuthMode.PERSONAL and (new_secret or existing is None):
            secret = typer.prompt("WCL client secret (hidden)", hide_input=True)
        attempt = PkceAttempt(cid) if mode is AuthMode.PUBLIC else None
        state = attempt.state if attempt else new_state()
        url = auth.authorize_url(cid, state, challenge=attempt.challenge if attempt else None)
        with CallbackListener(state) as listener:  # bound before the browser opens
            typer.echo("Sign in to Warcraft Logs in your browser:")
            typer.echo(f"  {url}")
            if browser:
                webbrowser.open(url)
            code = listener.wait()
        token = (
            auth.complete_public_sign_in(attempt, code)
            if attempt
            else auth.complete_sign_in(cid, secret, code)
        )
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
        mode = auth.mode()
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
    typer.echo(f"auth mode:        {mode.value}")
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


def _raid_url(url: str, raid: str | None) -> str:
    if raid is None:
        return url
    selected = next((r for r in RAIDS if r.slug == raid.lower()), None)
    if selected is None:
        raise typer.BadParameter("choose naxxramas, aq40, bwl or mc", param_hint="--raid")
    try:
        return with_raid(url, selected.zone_id)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="URL") from None


def resolve_command(
    url: Annotated[str, typer.Argument(help="A Warcraft Logs character URL.")],
    raid: Annotated[str | None, typer.Option(help="Raid: naxxramas, aq40, bwl or mc.")] = None,
    partition: Annotated[
        int | None, typer.Option(help="Partition id when several hold rankings.")
    ] = None,
    endpoint: Annotated[
        str, typer.Option(help="Use client or user; public PKCE requires user.")
    ] = "client",
) -> None:
    """Show who a character URL points to: character, faction, zone and partition."""
    try:
        if endpoint not in {"client", "user"}:
            raise AuthError("endpoint must be client or user")
        url = _raid_url(url, raid)
        ref = parse_character_url(url)
        require_supported(ref.site)
        auth = _auth()
        client = WclClient(ref.site, auth.token_for)
        try:
            context = resolve(
                client,
                ref,
                partition=partition,
                endpoint="user" if endpoint == "user" else "client",
            )
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


class _Activity:
    """Animate on terminals; emit durable, immediately flushed stages in logs."""

    def __init__(self) -> None:
        self.console = Console(stderr=True)
        self.status: Status | None = None

    def __enter__(self) -> _Activity:
        if self.console.is_terminal:
            self.status = self.console.status("Starting analysis", spinner="line")
            self.status.start()
        return self

    def update(self, message: str) -> None:
        if self.status is not None:
            self.status.update(message)
        self.console.print(message, markup=False, highlight=False)

    def __exit__(self, *args: object) -> None:
        if self.status is not None:
            self.status.stop()


def analyze_command(
    url: Annotated[str, typer.Argument(help="A Warcraft Logs character URL.")],
    cache: Annotated[
        Path,
        typer.Option("--cache", help="Keep fetched API data here for later runs. Required."),
    ],
    out: Annotated[
        Path,
        typer.Option(
            "--out", help="Write results here. Use --resume to continue a saved analysis."
        ),
    ],
    raid: Annotated[str | None, typer.Option(help="Raid: naxxramas, aq40, bwl or mc.")] = None,
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
    category: Annotated[
        str | None,
        typer.Option(
            help="Classic Era WCL ranking category for this class (e.g. Fire, Holy, Fury)."
        ),
    ] = None,
    spec: Annotated[
        str | None,
        typer.Option(
            help="Legacy alias for --category (WCL pool, not a talent tree). "
            "Use --talent-tree for declared game build intent."
        ),
    ] = None,
    talent_tree: Annotated[
        str | None,
        typer.Option(
            help="Declared game talent tree (e.g. Combat, Arcane); not a WCL filter. "
            "Choose --category separately; observed talents remain per fight."
        ),
    ] = None,
    faction: Annotated[
        str | None,
        typer.Option(help="Your faction: Alliance or Horde; checked against the character."),
    ] = None,
    metric: Annotated[
        str | None,
        typer.Option(help="Ranking metric; use hps for Balance-category healing logs."),
    ] = None,
    package: Annotated[
        bool,
        typer.Option("--package/--no-package", help="Also write the shareable ZIP package."),
    ] = True,
    resume: Annotated[
        bool,
        typer.Option(
            "--resume", help="Continue this output directory after a quota stop or interruption."
        ),
    ] = False,
    wait_for_reset: Annotated[
        bool,
        typer.Option(
            "--wait-for-reset",
            help="Allow one observed hourly reset wait (at most one hour) during this run.",
        ),
    ] = False,
) -> None:
    """Acquire one Classic Era raid and write its Report and Playbook.

    Uses saved WCL credentials and the network. Exit 0: complete report;
    4: partial report; 2: choose a partition; 3: finalization stopped, no report;
    1: failure. Saved snapshots can be replayed with offline.
    """
    url = _raid_url(url, raid)
    if sys.stdin.isatty() and not resume:
        if faction is None:
            faction = typer.prompt("Character faction (Alliance/Horde)")
        if spec is None and category is None:
            spec = typer.prompt(
                "Spec/category (e.g. Balance, Fire, Holy, Fury; all for legacy Hunter)",
                default="all",
            )
    try:
        with _Activity() as activity:
            outcome = run_analyze(
                url,
                cache=cache,
                out=out,
                partition=partition,
                endpoint=endpoint,
                cross_faction=cross_faction,
                name=name,
                package=package,
                category=category,
                spec=spec,
                talent_tree=talent_tree,
                faction=faction,
                metric=metric,
                wait_for_reset=wait_for_reset,
                tokens=_tokens,
                client_factory=_client,
                progress=activity.update,
                resume=resume,
            )
    except KeyboardInterrupt:
        typer.echo(
            "Interrupted. Keep the cache and output directory; continue with --resume.", err=True
        )
        raise typer.Exit(code=130) from None
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
