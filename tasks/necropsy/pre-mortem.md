# Pre-Mortem Record

> Durable, plan-scoped bridge between Pre-Mortem, implementation, and Captain
> Hindsight. Created 2026-10-13 for subject 07 (live acquisition) from the
> navigator's pre-mortem in the unit-11 huddle.
>
> **History rule.** Prediction fields describe what was believed *before*
> implementation. Once implementation begins, do not rewrite them to match what
> happened. Hindsight appends calibration alongside the prediction instead.

## Prediction register

| ID | Predicted severity | Failure | Basis | Predicted detection | Guardrail | Resolution | Plan refs |
|---|---|---|---|---|---|---|---|
| PM-1 | High | After an auth failure, credentials leak (stdout/stderr, exception text, chained tracebacks, debug repr, callback-server logs) or are stored in a file fallback. | `[evidence: D:/repos/wcl_access_test/wcl_auth.py::exchange_authorization_code formats raw HTTP error detail; its save/load helpers fall back to local files; BaseHTTPRequestHandler logs request lines by default]` | Silent | Keyring backend allowlist checked before any read/write (no null/fail/plaintext/file/custom backends, no file fallback); callback handler logging disabled; token-endpoint errors, exception chains and reprs sanitised, including reflected `error_description`; sentinel tests prove client secret, Basic header value, access/refresh tokens and OAuth code never appear in output, exception strings or chained tracebacks; tests never touch the real credential store; refresh keeps an omitted refresh token, replaces a rotated one, leaves stored credentials unchanged on failed exchange/save; `invalid_grant` gives a clear "login needed" state. | Mitigated (07.2 shipped f4ddddc: allowlisted single backend, staged sign-in, generation writes, sanitised errors, sentinel tests; real-store behaviour unverified until 07.9) | 07.2; D036 |
| PM-2 | High | A server throttle or malformed pagination leaves the CLI sleeping or retrying forever, or returns a silently incomplete cohort. | `[evidence: rateLimitData reports hourly counters and seconds until reset, not future query cost; GraphQL can return partial data with errors]` | Before production | Finite retries with an overall deadline; capped backoff with jitter; Retry-After as seconds or HTTP date; cancellation; no retry of auth/permission/schema errors; rate metadata kept even on errors; typed invalid-response failures; repeated page/cursor detection and a page budget; missing or malformed `hasMorePages` is never read as complete; unknown projected cost shown as unknown and conservative; an estimate above the fresh hourly budget fails or needs an explicit policy, never loops over resets; no silent /user → /client downgrade after denied/private data. | Pending | 07.1, 07.4, 07.5; D037 |
| PM-3 | High | A wrong host, partition or faction becomes a confident context and contaminates same-faction acquisition. | `[evidence: tasks/necropsy/lessons.md records faction-code differences between WCL fields; exporter Profile($characterID, $zoneID) needs a known zone and does not discover it; WCL URL families differ by site]` | Before merge | HTTPS host allowlist and exact path / positive-id parsing (reject userinfo, ports, lookalike hosts, unsafe decoded separators); no credential-bearing cross-origin redirects; explicit GameFaction mapping with provenance, distinct from combatant faction codes; unknown fields stay unknown; zone/partition candidates obtained explicitly before any zoneID-requiring query, genuine ambiguity left for the user; tests for missing/null/hidden character, renamed canonical ID, multiple partitions, JSON scalar decoding and per-field confidence; real recorded responses and synthetic fixtures labelled separately. | Pending | 07.3, 07.4; D038 |
| PM-4 | High | A resumed acquisition mixes cache identities: event pages fetched after a report revision change are filed under the old revision with its bundle, or a path reused for a different actor/filter/time range/endpoint looks complete, and a snapshot is certified complete with wrong evidence. | `[evidence: recorded exporter REPORT_QUERY returns revision while EVENTS_QUERY does not; the 07.5 plan pinned revision once and cached pages by actor/direction]` `[inference: a report can change during a multi-request fetch; no incident observed]` | Silent | Every events request also asks for the report revision and each page is accepted only when it equals the bundle's; a missing/invalid/different revision leaves the stream incomplete (no marker) and raises a typed restart for the new generation. A network resume re-reads the current revision; offline reuse may deliberately use an older immutable generation. The marker records the canonical query identity (site host, code, revision, fight, actor, role, direction, time bounds, filters, query version, endpoint; never auth data) and is reused only when identity and every page hash/count match; report code, fight id/encounter/time bounds and site are validated before writing. A marker's existence never implies completeness. | Mitigated in the cache/fetch slice (navigator AGREE round 3): guard implemented and tested offline; live behaviour unverified until 07.7 | 07.5; D042 |
| PM-5 | High | Recovery or retry breaks the cache write boundary or immutability: a hostile report code, symlink or junction moves writes or cleanup outside the cache root; a check-then-rename race replaces a completed object; a crash after the last page leaves a marker naming absent or changed files. | `[evidence: the 07.5 layout uses the API report code in paths and clears interrupted streams; tmp+fsync+rename is atomic replacement, not no-overwrite; report/publish.py already refuses link and artifact collisions]` | Before production | Report codes, site family and numeric ids validated against strict patterns; resolved containment and link/reparse-point checks on every created, read, replaced or cleaned path; cleanup touches only the stream's own uncommitted pages and temps; one writer per stream via an exclusive lock file; a completed object is verified and reused or raises a conflict, never replaced; marker written last after verified pages and validated on every read; explicit cache format version; failure-injection tests around page publication, marker write, read-time tampering, concurrent writers, links and hostile keys; recovery is refetch, completed generations kept. | Mitigated in the cache/fetch slice (navigator AGREE round 3): guard implemented and tested offline; live behaviour unverified until 07.7 | 07.5; D042 |

## Captain Hindsight calibration

| PM ID | Outcome | Observed impact | Actual detection | Mitigation effectiveness | Severity calibration | Hindsight note / evidence |
|---|---|---|---|---|---|---|

## Misses

| ID | Failure | Observed impact | Actual detection | Why Pre-Mortem missed it | Future lesson | Evidence / refs |
|---|---|---|---|---|---|---|

## Calibration questions

Captain Hindsight should be able to answer, from this file and the implementation evidence:

- Did we predict the right failure class?
- Did we predict its severity accurately?
- Did we predict where it would be detected accurately?
- Did the chosen guardrail actually work?
- What escaped prediction entirely?
