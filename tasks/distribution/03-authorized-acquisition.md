# 03 — Public-client acquisition and compatibility

## Goal
Acquire with the authorized user token through a researched, explicitly selected endpoint.

## Integration analysis
- **Existing code found:** `wcl/client.py, wcl/analyze.py, wcl/acquire.py, wcl/cache.py, report/offline.py`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [ ] **03.1** (agent) Use the existing WclClient and analyze orchestration with an explicit PKCE/user endpoint route; verify which public and archived ranking/report queries the token permits. Do not attempt client_credentials without a secret or silently switch endpoints.
- [x] **03.2** (agent) Preserve fixed endpoint cache identities, revision checks, partial coverage, bounded budgets and offline replay. Verify missing permission and expiry are clear failures or typed coverage limitations.
- [x] **03.3** (agent) Exercise the installed public-mode CLI with synthetic OAuth/WCL responses and replay existing Hunter snapshots unchanged; reconcile JSON schema, help, auth/usage/troubleshooting docs and ADRs.

## Hindsight checkpoint
Before marking DONE: Codex performs solo review and records Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt (master D003; user ended Claude pairing). No CLOSE while a required human action or observable risk remains unresolved.

- [x] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-15 · 1 · 03.1–03.3 · Resolve now accepts explicit endpoint; public tokens reject client_credentials before HTTP. Existing cache identity/revision/budget/offline code reused unchanged. Synthetic public Auth→CLI analyze→snapshot/report passes on user route; permission denial never falls back. Installed wheel public login plus synthetic user API and unchanged Hunter snapshot replay pass outside checkout. 130 focused checks pass. Analysis schema is unaffected. Docs updated in auth/connection/install/architecture/live acceptance/ADR0007. Real public ranking/report/archive permission verification remains open in 03.1. Pushed checkpoint follows.

## Interim review
Keep: fixed endpoint and shared acquisition/offline pipeline, actionable 401/403 errors.
Fix before closing: observe registered public token with actual ranking/report/archive queries.
Record: installed receipt and scope in verification.md; no schema migration.
Risk: endpoint contract does not establish every account's permissions.
Verdict: DO NOT CLOSE; only live portion of 03.1 remains.

