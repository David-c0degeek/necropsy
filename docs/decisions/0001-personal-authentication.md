# Personal authentication through one approved OS store

Status: Accepted for personal use · Date: 2026-10-13

[Decision index](README.md) · [Authentication reference](../auth.md)

## Context

The personal CLI needs a confidential WCL client secret and user-token state.
An automatically chosen keyring facade can include insecure file backends or
silently read through a chain. A failed credential update must not destroy a
previous working sign-in.

## Decision

Use exactly one approved OS backend selected by concrete class identity and call
it directly. Refuse unapproved stores and file fallbacks. Keep secret and user
token in one record per client ID. Chunk values under a new generation and commit
the head last; stage sign-in until exchange succeeds. Keep client-credentials
tokens in memory. Bind the local callback before opening the browser and check
OAuth state. Use bounded waits and sanitized errors.

## Alternatives and consequences

Using the generic keyring facade or a JSON fallback would make backend behavior
less predictable and was rejected. Unsupported or ambiguous store setups fail
explicitly and require configuration. Generation writes protect prior readable
records but do not turn the credential backend into a transactional database.

A confidential secret belongs to a user's own client setup. This decision does
not authorize distributing a shared secret. A public PKCE client must replace
the confidential-client flow before application distribution. The personal flow was
observed with Windows WinVault and the authenticated user API on 2026-10-14;
see [live validation](../live-validation.md) for coverage and limits. Other real
credential stores and public-client PKCE remain unverified.

Implementation: [credentials](../../src/necropsy/wcl/credentials.py),
[auth](../../src/necropsy/wcl/auth.py), [commands](../../src/necropsy/wcl/cli.py).
