# 02 — PKCE sign-in and token lifecycle

## Goal
Users authorize their own WCL account without entering or receiving a shared client secret.

## Integration analysis
- **Existing code found:** `wcl/auth.py, wcl/credentials.py, wcl/cli.py; reuse one OAuth/store implementation`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [x] **02.1** (agent) Extend the existing browser/loopback login with a fresh S256 verifier/challenge and state for each attempt; token exchange uses the verified public-client contract. Exercise successful login, denied/cancelled login, wrong state and expired/reused code.
- [x] **02.2** (agent) Extend the existing approved OS credential store for explicitly tagged auth modes and per-user tokens; preserve existing personal records, stage writes, test refresh/rotation/failure and logout without credential leakage.
- [x] **02.3** (agent) Wire the CLI sign-in path and actionable errors; document the difference between public app identity and personal user authorization, with no mandatory secret prompt for distributed mode.

## Hindsight checkpoint
Before marking DONE: Codex performs solo review and records Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt (master D003; user ended Claude pairing). No CLOSE while a required human action or observable risk remains unresolved.

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

## Progress log
2026-10-15 · 1 · 02.1–02.3 · Public login wired into existing Auth/CLI/store: fresh S256/state, five-minute single-use attempt, separate tagged public records, legacy personal compatibility, refresh/rotation and sanitized failures. Actual listener state/denial/timeout tests retained. 53 focused auth/PKCE tests pass; 130 focused auth/store/acquisition/acceptance checks pass. Observed: public token exchange lacks Authorization/client_secret, user API receives bearer token, client endpoint fails before HTTP, failed switching keeps personal record, CLI public login needs no secret. Real provider refresh behavior remains an explicit independent gate. Docs: auth/connection/install, ADR0007, README, architecture, roadmap, contributor/live guides and changelog. Pushed checkpoint follows.

## Closing review
Keep: one approved store/client; old records survive successful/failed mode switches.
Fix before closing: none for implemented behavior and synthetic verification scope.
Record: D004/D006, ADR0007; PM-1/PM-2 mitigations verified before merge.
Risk: registered app/live refresh is not certified by synthetic tests; tracked in 01/03/05.
Verdict: CLOSE engineering subject per D004.


Checkpoint disposition: engineering commit 0cfdab0 pushed to origin/main; final
local golden/browser checks pass and exact evidence is in verification.md.
