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
- [ ] **02.1** (agent) Extend the existing browser/loopback login with a fresh S256 verifier/challenge and state for each attempt; token exchange uses the verified public-client contract. Exercise successful login, denied/cancelled login, wrong state and expired/reused code.
- [ ] **02.2** (agent) Extend the existing approved OS credential store for explicitly tagged auth modes and per-user tokens; preserve existing personal records, stage writes, test refresh/rotation/failure and logout without credential leakage.
- [ ] **02.3** (agent) Wire the CLI sign-in path and actionable errors; document the difference between public app identity and personal user authorization, with no mandatory secret prompt for distributed mode.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
TBD — implementation has not started. Record date, per-subject slice number, box IDs, observed behavior, verification, documentation impact, and pushed checkpoint.
