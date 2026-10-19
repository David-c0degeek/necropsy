"""WCL public PKCE and personal authentication through one approved OS store.

Sign-in is staged until exchange succeeds. Public and legacy personal records
remain separate; the active selection is committed last. Errors and reprs never
include secrets, tokens, authorization codes or PKCE verifiers.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import math
import os
import secrets
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx

from necropsy.wcl.credentials import CredentialStore
from necropsy.wcl.sites import VANILLA, Site, require_supported

CLIENT_ID_ENV = "NECROPSY_WCL_CLIENT_ID"
# A client ID is public application identity; never put a client secret here.
PUBLIC_CLIENT_ID: str | None = "01a140aa-1ee3-7323-99dc-5efc7a767af7"
REDIRECT_HOST = "127.0.0.1"
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
EXPIRY_MARGIN_S = 120
REQUEST_READ_TIMEOUT_S = 10.0
OAUTH_ERRORS = frozenset(
    {
        "invalid_request",
        "invalid_client",
        "invalid_grant",
        "unauthorized_client",
        "unsupported_grant_type",
        "invalid_scope",
        "access_denied",
        "server_error",
        "temporarily_unavailable",
    }
)
_POINTER = "client-id"


class AuthMode(StrEnum):
    PUBLIC = "public"
    PERSONAL = "personal"


def _record_name(client_id: str, mode: AuthMode = AuthMode.PERSONAL) -> str:
    prefix = "public-client" if mode is AuthMode.PUBLIC else "client"
    return f"{prefix}:{client_id}"


@dataclass
class PkceAttempt:
    """One short-lived browser transaction; sensitive material stays in memory."""

    client_id: str
    state: str = field(default_factory=lambda: secrets.token_urlsafe(24), repr=False)
    verifier: str = field(default_factory=lambda: secrets.token_urlsafe(64), repr=False)
    started_at: float = field(default_factory=time.monotonic, repr=False)
    consumed: bool = field(default=False, init=False)

    @property
    def challenge(self) -> str:
        digest = hashlib.sha256(self.verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def consume(self) -> str:
        if self.consumed or time.monotonic() - self.started_at >= 300:
            raise AuthError("sign-in attempt expired or already used; start sign-in again")
        self.consumed = True
        return self.verifier


class AuthError(Exception):
    """Sign-in failed. The message never contains a secret."""


class LoginNeeded(AuthError):
    """No usable user token: run `necropsy auth login`."""


class AuthState(StrEnum):
    SIGNED_IN = "signed-in"
    EXPIRED = "expired"
    LOGIN_NEEDED = "login-needed"


@dataclass(frozen=True)
class Token:
    access_token: str = field(repr=False)
    refresh_token: str | None = field(repr=False)
    expires_at: float

    def __repr__(self) -> str:
        refresh = "yes" if self.refresh_token else "no"
        return f"Token(expires_at={self.expires_at:.0f}, refresh={refresh})"

    def as_dict(self) -> dict[str, Any]:
        return {
            "access": self.access_token,
            "refresh": self.refresh_token,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: Any) -> Token:
        try:
            access, refresh = data["access"], data.get("refresh")
            expiry = float(data["expires_at"])
            if not isinstance(access, str) or not access or not math.isfinite(expiry):
                raise ValueError
            if refresh is not None and (not isinstance(refresh, str) or not refresh):
                raise ValueError
            return cls(access, refresh, expiry)
        except KeyError, TypeError, ValueError, AttributeError:
            raise LoginNeeded(
                "the stored sign-in is unreadable; run `necropsy auth login`"
            ) from None


@dataclass(frozen=True)
class ClientRecord:
    """A tagged public or personal record; only personal records contain a secret."""

    client_id: str
    secret: str | None = field(repr=False)
    token: Token | None = None
    mode: AuthMode = AuthMode.PERSONAL

    def to_json(self) -> str:
        return json.dumps(
            {
                "mode": self.mode.value,
                "secret": self.secret,
                "token": None if self.token is None else self.token.as_dict(),
            }
        )


def _safe_code(value: Any) -> str:
    return str(value) if isinstance(value, str) and value in OAUTH_ERRORS else "unrecognised error"


@dataclass
class Auth:
    site: Site
    store: CredentialStore
    transport: httpx.BaseTransport | None = None
    now: Callable[[], float] = time.time
    _client_token: Token | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        require_supported(self.site)

    # -- stored values ----------------------------------------------------
    def _selection(self) -> tuple[AuthMode, str | None]:
        pointer = self.store.get(_POINTER)
        if pointer and pointer.startswith("{"):
            try:
                selected = json.loads(pointer)
                cid = selected["client_id"]
                if not isinstance(cid, str) or not cid:
                    raise ValueError
                return AuthMode(selected["mode"]), cid
            except ValueError, KeyError, TypeError:
                raise LoginNeeded("stored client selection is unreadable; sign in again") from None
        return AuthMode.PERSONAL, pointer

    def client_id(self) -> str | None:
        return os.environ.get(CLIENT_ID_ENV) or self._selection()[1]

    def mode(self) -> AuthMode:
        return self._selection()[0]

    def record(
        self, client_id: str | None = None, *, mode: AuthMode | None = None
    ) -> ClientRecord | None:
        chosen = mode or self.mode()
        cid = client_id or self.client_id()
        if not cid:
            return None
        text = self.store.get(_record_name(cid, chosen))
        if text is None:
            return None
        try:
            data = json.loads(text)
            stored_mode = AuthMode(data.get("mode", "personal"))
            secret = data["secret"]
            if stored_mode is not chosen:
                raise ValueError
            if chosen is AuthMode.PERSONAL and (not isinstance(secret, str) or not secret):
                raise ValueError
            if chosen is AuthMode.PUBLIC and secret is not None:
                raise ValueError
            token = None if data.get("token") is None else Token.from_dict(data["token"])
        except ValueError, KeyError, TypeError, AttributeError:
            raise LoginNeeded(
                "the stored sign-in is unreadable; run `necropsy auth login`"
            ) from None
        return ClientRecord(cid, secret, token, chosen)

    @staticmethod
    def _pointer(record: ClientRecord) -> str:
        return (
            json.dumps({"mode": record.mode.value, "client_id": record.client_id})
            if record.mode is AuthMode.PUBLIC
            else record.client_id
        )

    def _save(self, record: ClientRecord, *, select: bool = False) -> None:
        self.store.set(_record_name(record.client_id, record.mode), record.to_json())
        if select:
            pointer = self._pointer(record)
            if self.store.get(_POINTER) != pointer:
                self.store.set(_POINTER, pointer)
            self._client_token = None

    def stored_token(self) -> Token | None:
        found = self.record()
        return None if found is None else found.token

    def state(self) -> AuthState:
        try:
            token = self.stored_token()
        except LoginNeeded:
            return AuthState.LOGIN_NEEDED
        if token is None:
            return AuthState.LOGIN_NEEDED
        if token.expires_at - EXPIRY_MARGIN_S <= self.now():
            return AuthState.EXPIRED if token.refresh_token else AuthState.LOGIN_NEEDED
        return AuthState.SIGNED_IN

    def export_values(self) -> dict[str, str]:
        """The effective sign-in as a self-contained selection plus its record.

        The selection is rebuilt from the effective client (including a client ID
        override), so the exported values select the same record on their own.
        """
        current = self.record()
        if current is None:
            raise LoginNeeded("no saved sign-in to export; run `necropsy auth login`")
        return {
            _POINTER: self._pointer(current),
            _record_name(current.client_id, current.mode): current.to_json(),
        }

    def logout(self, forget_secret: bool = False) -> None:
        current = self.record()
        if current is None:
            return
        if forget_secret:
            self.store.delete(_record_name(current.client_id, current.mode))
            self.store.delete(_POINTER)
        else:
            self.store.set(
                _record_name(current.client_id, current.mode),
                ClientRecord(current.client_id, current.secret, mode=current.mode).to_json(),
            )

    # -- token endpoint ---------------------------------------------------
    def _token_request(self, client_id: str, secret: str | None, form: dict[str, str]) -> Token:
        headers = {}
        if secret is None:
            form = {**form, "client_id": client_id}
        else:
            basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode("ascii")
            headers["Authorization"] = f"Basic {basic}"
        try:
            with httpx.Client(
                transport=self.transport, timeout=30.0, follow_redirects=False
            ) as http:
                response = http.post(self.site.token_url, data=form, headers=headers)
        except httpx.HTTPError:
            raise AuthError("could not reach the WCL sign-in service") from None
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.status_code != 200 or not isinstance(body, dict) or "access_token" not in body:
            code = _safe_code(body.get("error") if isinstance(body, dict) else None)
            if code == "invalid_grant":
                raise LoginNeeded(
                    "WCL rejected the sign-in (invalid_grant); run `necropsy auth login`"
                )
            raise AuthError(f"WCL sign-in failed (HTTP {response.status_code}, {code})")
        try:
            access = body["access_token"]
            expires_in = float(body.get("expires_in", 3600))
            refresh = body.get("refresh_token")
            if not isinstance(access, str) or not access:
                raise ValueError
            if not math.isfinite(expires_in) or expires_in <= 0:
                raise ValueError
            if refresh is not None and (not isinstance(refresh, str) or not refresh):
                raise ValueError
        except TypeError, ValueError:
            raise AuthError("WCL returned an invalid token response; sign in again") from None
        return Token(access, refresh, self.now() + expires_in)

    def complete_public_sign_in(self, attempt: PkceAttempt, code: str) -> Token:
        verifier = attempt.consume()
        token = self._token_request(
            attempt.client_id,
            None,
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
            },
        )
        self._save(ClientRecord(attempt.client_id, None, token, AuthMode.PUBLIC), select=True)
        return token

    def complete_sign_in(
        self, client_id: str, secret: str | None, code: str, redirect_uri: str = REDIRECT_URI
    ) -> Token:
        """Exchange the code with the given (staged) credentials; save only on success.

        `secret` None means: use the secret already stored for this client id.
        The record (secret + token) is written first, then the pointer to it, so
        a failure at any step leaves the previous working sign-in in place.
        """
        if secret is None:
            existing = self.record(client_id, mode=AuthMode.PERSONAL)
            if existing is None:
                raise LoginNeeded("no client secret saved for this client id; enter it to sign in")
            secret = existing.secret
        token = self._token_request(
            client_id,
            secret,
            {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
        )
        self._save(ClientRecord(client_id, secret, token), select=True)
        return token

    def refresh(self) -> Token:
        current = self.record()
        if current is None or current.token is None or not current.token.refresh_token:
            raise LoginNeeded("no stored sign-in to refresh; run `necropsy auth login`")
        new = self._token_request(
            current.client_id,
            current.secret,
            {"grant_type": "refresh_token", "refresh_token": current.token.refresh_token},
        )
        if new.refresh_token is None:
            new = Token(new.access_token, current.token.refresh_token, new.expires_at)
        self._save(ClientRecord(current.client_id, current.secret, new, current.mode))
        return new

    # -- tokens for the API client ------------------------------------------
    def user_token(self) -> str:
        state = self.state()
        if state is AuthState.LOGIN_NEEDED:
            raise LoginNeeded("not signed in to WCL; run `necropsy auth login`")
        token = self.refresh() if state is AuthState.EXPIRED else self.stored_token()
        assert token is not None
        return token.access_token

    def client_token(self) -> str:
        if self.mode() is AuthMode.PUBLIC:
            raise AuthError(
                "public sign-in requires --endpoint user; client credentials need a "
                "personal client (auth login --mode personal)"
            )
        token = self._client_token
        if token is None or token.expires_at - EXPIRY_MARGIN_S <= self.now():
            current = self.record()
            if current is None:
                raise LoginNeeded("no WCL client saved; run `necropsy auth login`")
            token = self._token_request(
                current.client_id, current.secret, {"grant_type": "client_credentials"}
            )
            self._client_token = token  # memory only
        return token.access_token

    def token_for(self, endpoint: str) -> str:
        if endpoint not in {"client", "user"}:
            raise AuthError("endpoint must be client or user")
        return self.user_token() if endpoint == "user" else self.client_token()

    def authorize_url(
        self,
        client_id: str,
        state: str,
        redirect_uri: str = REDIRECT_URI,
        *,
        challenge: str | None = None,
    ) -> str:
        params = {
            "client_id": client_id,
            "state": state,
            "redirect_uri": redirect_uri,
            "response_type": "code",
        }
        if challenge is not None:
            params.update(code_challenge=challenge, code_challenge_method="S256")
        return f"{self.site.authorize_url}?{urllib.parse.urlencode(params)}"


# -- local callback -----------------------------------------------------------
_PAGE = (
    "<!doctype html><meta charset=utf-8><title>Necropsy</title>"
    "<p>{}</p><p>You can close this window.</p>"
)


class _Handler(http.server.BaseHTTPRequestHandler):
    server_version = "necropsy"
    timeout = REQUEST_READ_TIMEOUT_S  # a slow or idle client cannot hold the listener

    def log_message(self, format: str, *args: Any) -> None:
        return  # never log request lines: they carry the code and state

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        state = params.get("state", [""])[0]
        expected: str = self.server.expected_state  # type: ignore[attr-defined]
        if any(len(values) != 1 for values in params.values()):
            outcome, message = "error:invalid-response", "Sign-in failed: ambiguous response."
        elif not secrets.compare_digest(state.encode(), expected.encode()):
            outcome, message = "error:state", "Sign-in failed: the response did not match."
        elif "error" in params:
            outcome = f"error:{_safe_code(params['error'][0])}"
            message = "Sign-in was not completed."
        elif params.get("code", [""])[0]:
            outcome = "code:" + params["code"][0]
            message = "Authorization received. Return to Necropsy to finish signing in."
        else:
            outcome, message = "error:missing-code", "Sign-in failed: no code was returned."
        self.server.result.setdefault("outcome", outcome)  # type: ignore[attr-defined]
        body = _PAGE.format(message).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)


class CallbackListener:
    """Bound on 127.0.0.1 before the browser opens; serves one sign-in callback."""

    def __init__(self, expected_state: str, port: int = REDIRECT_PORT) -> None:
        try:
            self._server = http.server.HTTPServer((REDIRECT_HOST, port), _Handler)
        except OSError:
            raise AuthError(
                f"port {port} is in use; close the program using it and sign in again"
            ) from None
        self._server.expected_state = expected_state  # type: ignore[attr-defined]
        self._server.result = {}  # type: ignore[attr-defined]
        self._server.timeout = 1.0

    def __enter__(self) -> CallbackListener:
        return self

    def __exit__(self, *_exc: object) -> None:
        self._server.server_close()

    def wait(self, timeout_s: float = 300.0, *, cancelled: Callable[[], bool] | None = None) -> str:
        result: dict[str, str] = self._server.result  # type: ignore[attr-defined]
        deadline = time.monotonic() + timeout_s
        while "outcome" not in result and time.monotonic() < deadline:
            if cancelled is not None and cancelled():
                raise AuthError("sign-in cancelled")
            self._server.handle_request()
        outcome = result.get("outcome")
        if outcome is None:
            raise AuthError("timed out waiting for the browser sign-in")
        if outcome.startswith("code:"):
            return outcome[5:]
        raise AuthError(f"sign-in failed ({outcome[6:]})")


def wait_for_code(expected_state: str, timeout_s: float = 300.0, port: int = REDIRECT_PORT) -> str:
    """Bind, then serve one callback and return the authorization code."""
    with CallbackListener(expected_state, port) as listener:
        return listener.wait(timeout_s)


def new_state() -> str:
    return secrets.token_urlsafe(24)


def validate_import(values: dict[str, str]) -> None:
    """Refuse values that are not exactly one self-contained, readable sign-in."""
    names = sorted(values)
    pointer = values.get(_POINTER)
    if len(names) != 2 or pointer is None:
        raise LoginNeeded("the imported credentials are not one exported sign-in")
    store = _Values(values)
    auth = Auth(VANILLA, store)
    mode, client_id = auth._selection()
    if not client_id or _record_name(client_id, mode) not in values:
        raise LoginNeeded("the imported credentials are not one exported sign-in")
    found = auth.record(client_id, mode=mode)
    if found is None or found.token is None:
        raise LoginNeeded("the imported credentials hold no sign-in token")


class _Values(CredentialStore):
    """Read-only values in memory, for validating an import."""

    def __init__(self, values: dict[str, str]) -> None:
        self._values = dict(values)

    def get(self, name: str) -> str | None:
        return self._values.get(name)


__all__ = [
    "CLIENT_ID_ENV",
    "OAUTH_ERRORS",
    "PUBLIC_CLIENT_ID",
    "REDIRECT_URI",
    "Auth",
    "AuthError",
    "AuthMode",
    "AuthState",
    "CallbackListener",
    "ClientRecord",
    "LoginNeeded",
    "PkceAttempt",
    "Token",
    "new_state",
    "validate_import",
    "wait_for_code",
]
