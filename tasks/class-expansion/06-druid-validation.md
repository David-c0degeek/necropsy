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
- [x] **06.1** (agent) Run real saved-fixture ingest→analysis→report→package for each Druid role, mixed/uncertain cases and Hunter regressions; cross-check golden facts, coverage, role-specific cohorts, hashes and secret scans.
- [x] **06.2** (agent) Prepare and execute opt-in live Druid acceptance only with authorized accessible reports and credentials; record inaccessible data, metadata/event separation, budget waits and limitations rather than claiming full coverage.
- [ ] **06.3** (product-owner) Review the Druid report/playbook for all requested roles and accept remaining documented limits; authorize any explicitly deferred role or reduced scope before closure.
- [ ] **06.4** (agent) Complete latest CI/build/browser checks, cleanup triage, documentation, durable lessons, PM calibration, subject Hindsight and independent Claude review before final sign-off.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [x] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-14 · 1 · 06.1–06.4 · Readiness baseline 822 pass. Intermediate expanded fast suite 832 pass; latest full suite running after additional changes. Hunter golden 229 pass / 4 known xfails; four new real Druid fixture replays pass; installed scanner no leaks over 169.74 MB extracted raw members. Raw hybrid fixture, final latest verification/CI, scoped Claude review and human acceptance remain open. A dedicated tank acquisition stopped on the hourly-budget guard before fresh finalization; no snapshot fabricated. Bounded mixed-duty retry waits on the original reset. Checkpoint commit/push follows this record.

2026-10-14 · 2 · Latest stable broad checkpoint: 848 fast pass; full golden/acceptance 233 pass / 4 retained xfails. 16 real browser cases and four synthetic browser cases pass; existing acceptance artifact checker plus output secret scans pass for all four one-boss categories. Raw ZIP/commit scans passed. Current API reset deadline was observed at approximately 22:04:45 UTC (00:04:45 Amsterdam); queued production library run requests Guardian / Suncat / Four Horsemen (51121) with one bounded reset wait. On completion, preserve snapshot bytes and replay with current code before recording any role facts. Reproducer is the existing acquire/Run/finalize_reports/write_snapshot/run_offline library pipeline; cache workspace/druid-cache, output workspace/druid-mixed. No mixed-role success is claimed while waiting.

2026-10-15 · 3 · User confirms mostly healing on Sapphiron. Added explicit Balance/HPS selection independently of category/build/duty (D011), with synthetic production acquisition→snapshot→ingest→document regression and conflicting-metric rejection. 164 focused tests plus the new integration case pass; full mypy (130 files), Ruff lint/format and wheel/sdist build pass. Regenerated all four real outputs and repeated 16 browser cases successfully. Full fast/golden suites are running against stable sources. Prior tip 2e7e648 failed CI only on CLI help line E501; fixed here and verified locally. No full-suite result claimed before completion.


2026-10-15 · final engineering checkpoint · Six real Druid replays pass, including Four Horsemen tank/hybrid and own Sapphiron healing. 855 fast pass; full initial golden/acceptance 233 pass / four retained xfails; expanded six-Druid replay six pass; browser suite 23 pass; all 24 real page/viewport checks plus six artifact checks/output scans pass. Ruff lint/format, strict mypy and wheel/sdist build pass. Hunter JSON/both pages/ZIP byte-identical after inline-heading whitespace correction. Linux/Windows CI b4fd2e8 passed; final changed-fixture/template checkpoint CI follows. Portable raw scans: 169,740,861 + 62,401,552 bytes, no leaks. Review packet names exact human questions. Final independent review remains pending; checkpoint commit/push covers this record.

## Captain Hindsight — 2026-10-15

### Keep

Retain production acquisition and six complete artifact replays with independent checks. Existing acquisition, normalization, evidence and publication remain the runtime path. Behavior was exercised from saved raw evidence to package and browser, not inferred from compilation.

### Fix before closing

Resolve 06.3 product review, final Claude review and current-tip CI. No engineering defect is currently known; never mark the remaining human-owned boxes accepted from agent checks.

### Record

ADR 0005 records class/metric/duty compatibility. Decisions D007–D011 cover tank evidence, bounded validation, secondary duty share, cleanup reuse and explicit metric selection. PM-1–PM-3 calibration and CH-MISS-1/2 are retained in pre-mortem.md; durable lessons are in tasks/lessons.md. No shipped-code plan reference was found by targeted search outside tasks.

### Risk

Role thresholds are provisional. Exact-build samples can be sparse; resource/form/overheal/threat/assignment gaps stay unknown. Selected fights across three bosses do not establish full-raid or final domain acceptance. No requested role was deferred.

### Verdict

DO NOT CLOSE — 06.3 product review, final Claude review and current-tip CI. The smallest next actions are the named review/CI or human decisions; do not expand acquisition or rerun already-passing checks without a new reason.
