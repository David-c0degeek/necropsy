# Authentication boundaries

[Home](../README.md) · [Documentation](README.md) · [Sign-in guide](warcraft-logs.md)

Public S256 PKCE is the default new sign-in. Each person authorizes their own
account without a shared client secret. Registered public-client S256 sign-in, callback, refresh rotation and representative
user-endpoint queries are observed on Windows. The product owner confirmed
independent account/machine acceptance and approved version0.1.0 publication.
The TUI guides browser sign-in and chooses the user endpoint automatically.
It waits in a cancellable background worker and uses the same PKCE/OS-vault
implementation as the CLI. Personal confidential clients remain supported with
`auth login --mode personal`.
See [installation](installation.md), [the connection guide](warcraft-logs.md), and
[the public authentication decision](decisions/0007-public-client-authentication.md).
[Live validation](live-validation.md) separates the earlier personal acquisition
from the registered public-client observations and their account-specific limits.

## Credentials and tokens

Necropsy selects exactly one approved operating-system credential backend:
Windows Credential Locker, macOS Keychain, Secret Service or KWallet. Selection
uses the concrete backend class. Reads, writes and deletes go directly to that
instance, rather than through a chaining facade. File, plaintext, null and
unrecognized backends are refused. There is no credentials-file fallback.

Public records carry an explicit mode and no secret, under separate public-client
keys. Personal confidential secrets and user-token state share a personal record
per client ID. Legacy untagged personal records remain readable. The active
selection identifies both mode and client; it is committed last. Values are chunked under a fresh generation, with the head pointer written
last; a failed write preserves the previous readable generation. Sign-in stages
new credentials until token exchange succeeds. A cancelled or failed sign-in
preserves the previous working record.

The user API uses the saved user access token. An expired token is refreshed when
a refresh token is available. A rotated refresh token replaces the previous one;
an omitted refresh token keeps it. Without a usable sign-in or refresh, the CLI
asks for sign-in again. The client API obtains a client-credentials token from the
saved client record and keeps that token in memory only.

Tokens and secrets are excluded from normal output and representations.
Credential-backend failures use fixed messages rather than printing backend
exception text. The client ID is an identifier, not a secret, and may be selected
through the command option, environment, saved ID or prompt.

## Local sign-in and request boundaries

The registered callback is `http://localhost:8765/callback`. The listener is bound
before the authorization browser opens, checks the returned state and has a
bounded wait. Each public attempt creates fresh S256 verifier/challenge and state. The verifier
stays in memory; attempts expire after five minutes and are consumed before exchange.
Public token and refresh requests carry client_id without Basic authorization.
Personal mode alone uses a hidden secret prompt. Sign-out removes the selected client's
user-token state; `--forget-secret` also removes that client's record and saved
selection. Other client records remain separate.

Supported character URLs use HTTPS and the allowed Warcraft Logs host/path
formats. Acquisition currently supports Classic Era on
`vanilla.warcraftlogs.com`. `analyze` validates its inputs and refuses earlier
outputs before accessing credentials. One endpoint serves the whole acquisition:
`client` by default, or `user` when selected. Public-mode resolve/analyze require
explicit `--endpoint user`; a client request fails before HTTP. Permission errors do not switch the
endpoint. HTTP requests do not automatically follow redirects.

Saved snapshot analysis and HTML rendering need no WCL credentials or network.
The acquisition cache contains API data and provenance, not authentication state.
Fetched logs and exported results can still contain player information.

## Implementation references

- [Credential backend selection and generation writes](../src/necropsy/wcl/credentials.py)
- [Client records, token refresh and callback handling](../src/necropsy/wcl/auth.py)
- [Sign-in and acquisition commands](../src/necropsy/wcl/cli.py)
- [HTTP client](../src/necropsy/wcl/client.py), [URL parsing](../src/necropsy/wcl/urls.py)
- [Authentication decision](decisions/0001-personal-authentication.md)
