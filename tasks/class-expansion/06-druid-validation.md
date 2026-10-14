# 06 — Druid end-to-end and regression acceptance

## Goal
Prove all requested Druid roles end to end while retaining the verified Hunter experience.

## Integration analysis
- **Existing code found:** `tests/golden/fact_checks.py, tests/browser/test_report_browser.py, wcl/acceptance.py and existing CI`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [ ] **06.1** (agent) Run real saved-fixture ingest→analysis→report→package for each Druid role, mixed/uncertain cases and Hunter regressions; cross-check golden facts, coverage, role-specific cohorts, hashes and secret scans.
- [ ] **06.2** (agent) Prepare and execute opt-in live Druid acceptance only with authorized accessible reports and credentials; record inaccessible data, metadata/event separation, budget waits and limitations rather than claiming full coverage.
- [ ] **06.3** (product-owner) Review the Druid report/playbook for all requested roles and accept remaining documented limits; authorize any explicitly deferred role or reduced scope before closure.
- [ ] **06.4** (agent) Complete latest CI/build/browser checks, cleanup triage, documentation, durable lessons, PM calibration, subject Hindsight and independent Claude review before final sign-off.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
TBD — implementation has not started. Record date, per-subject slice number, box IDs, observed behavior, verification, documentation impact, and pushed checkpoint.
