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


## Engineering calibration — 2026-10-15

| ID | Resolution | Calibration | Observed impact / detection | Remaining horizon |
|---|---|---|---|---|
| PM-1 | Prevented | Prevented Prediction | Cross-mode same-ID tests preserve legacy JSON; failed exchange and four partial-write points preserve personal selection. Public client request refuses before HTTP; synthetic CLI acquisition uses only user. Detected before merge. | Live WCL permission matrix still open in 03.1. |
| PM-2 | Mitigated | Prevented Prediction | RFC S256 vector, fresh independent attempts, expiry/consume checks and existing real callback denial/state/timeout tests pass. Token and verifier never appear in output/reprs. Detected before merge. | Provider invalid_grant/replay and actual registered callback remain live acceptance work. |
| PM-3 | Mitigated | Inconclusive | Isolated Windows wheel install, public CLI/user-API mock, real offline replay/package integrity, unlimited extracted gitleaks and real WinVault chunked probe pass. Public metadata omits player sample references; no fixtures/caches/plans ship. | Another person/machine has not run; registration unpublished. Release is gated, not approved. |

Mitigations are effective for observed engineering behavior; original severity
remains appropriate. Provider/account permissions and independent acceptance
cannot be disproven by local tests. No material unpredicted runtime failure found.
The Windows ZIP-normalization test initially expected a raw separator to survive
Python normalization; corrected the test to exercise traversal, not spelling.


### Registered-app observation

Actual registered S256 browser/callback and public refresh rotation passed on
Windows; saved public record has no secret. User API lookup, leaderboard,
current/archived REPORT_QUERY and event query passed for this account without
extra requested scopes. PM-1 and PM-2 remain Prevented Prediction/Mitigated:
provider observations now support the synthetic boundary checks. PM-3 remains
Mitigated/Inconclusive for independent-user horizon; only another account/person
and machine plus publication approval can close it. No silent endpoint fallback.


### Independent acceptance and publication authorization

User explicitly confirms the independent account/machine test passed and approves
publication. PM-3 resolution remains Mitigated; calibration is Prevented Prediction
for the engineering artifact boundary and owner-attested before-release acceptance.
No failure observed/reported. Independent OS/raw receipt/hash were not supplied,
so do not upgrade attestation into agent-observed evidence or broaden platforms.
Publication remains gated on successful artifact/CI checks and remote hash verification.


### Final release calibration

PM-1: Prevented; Prevented Prediction. Same-ID public/personal isolation, staged
writes and no-fallback boundary are tested and live public endpoint use is observed.
PM-2: Mitigated; Prevented Prediction. Fresh S256/state and bounded consumed
attempts are tested; actual callback and public refresh rotation pass.
PM-3: Mitigated; Prevented Prediction for the release boundary. Independent test
is owner-attested passed, publication approved, uploaded assets byte-verified,
and v0.1.0 published to the existing private repository. Independent OS/raw receipt
was not supplied and remains explicitly unobserved by the agent. No broader
platform/privacy claim or material runtime miss was introduced. All predictions
retain their original text; no retained risk has an unresolved release obligation.
