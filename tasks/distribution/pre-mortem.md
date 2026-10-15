# Pre-mortem: installable public authentication

2026-10-15; verdict PROCEED WITH GUARDRAILS.

## Failed future
An installed user signs in successfully but acquisition requests the confidential
endpoint, or switching modes overwrites a working personal secret. Repository-only
tests conceal missing wheel resources or accidental private data in the sdist.

## Original predictions

### PM-1 — High — mode confusion
Failure: PKCE falls through to client_credentials or replaces the personal record.
Basis: evidence: `src/necropsy/wcl/auth.py` shares the client record and
`wcl/cli.py` defaults acquisition to client; inference: adding public auth there
without an explicit mode would mix the contracts.
Detection: before production only with cross-mode failure tests.
Guardrail: agent owns 02.2/03.1; keep legacy personal keys, tag public records,
commit selection last, reject public/client requests before HTTP. Test failed
exchanges and writes, refresh rotation/failure and logout. Rollback: select
personal login again; legacy records remain readable.

### PM-2 — High — stolen/reused authorization
Failure: intercepted or stale callback exchanges a code without the original verifier.
Basis: evidence: existing callback validates state but confidential exchange has
no verifier; RFC7636 establishes the interception threat.
Detection: before merge through challenge vectors, fresh attempts, state denial,
expiry, single-use and invalid_grant tests.
Guardrail: agent owns 02.1; S256 only, in-memory verifier, bind before browser,
bounded attempt lifetime and consume before exchange; retain sanitized errors.

### PM-3 — High — installation mistaken for release proof
Failure: package includes a private export, or install works while another account
cannot authorize the registered app.
Basis: evidence: existing wheel-resource test checks selected resources only;
01.3/05.2 require registration and another person/machine.
Detection: before production via extracted artifact scan, isolated installed
replay, actual OS-store probe, independent-account receipt.
Guardrail: agent owns 04.1/04.3/05.1; release-engineer owns 01.3/05.4;
product-owner owns 05.2. Do not claim synthetic tests certify WCL permissions,
registration or independent acceptance. No publication before those gates.

## Calibration
Pending implementation; retain the predictions above unchanged. Record terminal
resolution and observed detection in the closing review; live unobserved horizons
remain Inconclusive.
