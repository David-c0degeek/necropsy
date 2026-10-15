# 01 — Class, build and encounter-role contracts

> Current status: COMPLETE — latest final Captain Hindsight below supersedes earlier pending review records.

## Goal
Replace Hunter assumptions with explicit class, build and per-fight role contracts while preserving existing outputs.

## Integration analysis
- **Existing code found:** `analysis/classes/__init__.py::ClassPlugin/plugin_for, analysis/context.py, analysis/benchmark.py, report/analysis_json.py`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [x] **01.1** (agent) Inventory Hunter-specific acquisition, snapshots, benchmarks, recommendations, JSON and renderer assumptions. Extend ClassPlugin/registry and shared evidence contracts without a second analysis pipeline; record compatibility and pre-mortem decisions before implementation.
- [x] **01.2** (agent) Separate observed class, talents/build, WCL ranking category/spec, encounter assignment and inferred per-fight role. Support feral DPS, balance DPS, restoration healing, feral tanking and hybrid/mixed roles; return uncertain when evidence cannot distinguish them.
- [x] **01.3** (agent) Define documented user overrides with provenance; preserve observed conflicting evidence and do not promote an override or talent label into an observed role. Define DPS/HPS/tanking-specific cohort dimensions with no cross-role median mixing.
- [x] ~~**01.4** (domain-sme) Review the Druid role taxonomy and success criteria, including hybrid responsibilities, overhealing/assignment limits, tank survivability/threat limits and what combat logs cannot prove.~~ ABANDONED; additional SME-review requirement retired by product-owner acceptance, see D017.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

## Progress log
2026-10-14 · 1 · 01.1 01.2 01.3 · Class registry dispatch, separate build/category/observed role/assignment override, exact role-keyed cohorts and optional schema-1 fields implemented. 14 Druid behavior tests cover role signals, uncertainty, overrides, resources and negative tank/AoE cases; four category selection cases reject cross-class/spec rows. Domain taxonomy review remains open. Checkpoint commit/push follows this record.

2026-10-14 · 2 · Scoped Claude core review AGREE round 1 / blocking 0; 86 independent tests passed. Addressed important incidental-duty finding with explicit 20% secondary cast-share heuristic and regression cases; preserved minor actions. Role taxonomy/domain gates remain open. Reporting/docs are requested in a separate bounded final review because the first review explicitly did not read those line by line.


2026-10-15 · final engineering checkpoint · Six real Druid replays pass, including Four Horsemen tank/hybrid and own Sapphiron healing. 855 fast pass; full initial golden/acceptance 233 pass / four retained xfails; expanded six-Druid replay six pass; browser suite 23 pass; all 24 real page/viewport checks plus six artifact checks/output scans pass. Ruff lint/format, strict mypy and wheel/sdist build pass. Hunter JSON/both pages/ZIP byte-identical after inline-heading whitespace correction. Linux/Windows CI b4fd2e8 passed; final changed-fixture/template checkpoint CI follows. Portable raw scans: 169,740,861 + 62,401,552 bytes, no leaks. Review packet names exact human questions. Final independent review remains pending; checkpoint commit/push covers this record.

## Captain Hindsight — 2026-10-15

### Keep

Retain separate class/build/category/metric/duty and explicit overrides. Existing acquisition, normalization, evidence and publication remain the runtime path. Behavior was exercised from saved raw evidence to package and browser, not inferred from compilation.

### Fix before closing

Resolve 01.4 taxonomy review. No engineering defect is currently known; never mark the remaining human-owned boxes accepted from agent checks.

### Record

ADR 0005 records class/metric/duty compatibility. Decisions D007–D011 cover tank evidence, bounded validation, secondary duty share, cleanup reuse and explicit metric selection. PM-1–PM-3 calibration and CH-MISS-1/2 are retained in pre-mortem.md; durable lessons are in tasks/lessons.md. No shipped-code plan reference was found by targeted search outside tasks.

### Risk

Role thresholds are provisional. Exact-build samples can be sparse; resource/form/overheal/threat/assignment gaps stay unknown. Selected fights across three bosses do not establish full-raid or final domain acceptance. No requested role was deferred.

### Verdict

DO NOT CLOSE — 01.4 taxonomy review. The smallest next actions are the named review/CI or human decisions; do not expand acquisition or rerun already-passing checks without a new reason.


2026-10-15 · engineering review receipt · Claude mail 180: AGREE round=3 blocking=0 important=0 at db89d3a; 92 independent focused tests pass. It reviewed the changed roles/cohort/acquire/analyze/snapshot-reader/document/Druid analyzer-report/base-template code, and explicitly excluded remaining views/offline/writer/CLI/export/schema/docs/plan/raw-fact surfaces from that round. Earlier scoped rounds plus lead inspection, six real artifact/package replays, schema tests and 24 browser cases cover those paths; no claim of blanket independent review is made. Optional CohortKey.metric storage nit retained as-is: the property preserves Hunter's serialized key bytes, all supported combinations are tested, and unsupported combinations fail canonical policy. Future categories must extend that policy and query tests together. Linux and Windows CI db89d3a passed: https://github.com/David-c0degeek/necropsy/actions/runs/38646145402. This is a record-only close-out; no runtime or test edits follow the reviewed code.


## Final Captain Hindsight — approved close-out, 2026-10-15

### Keep
Retain the shared acquisition/snapshot/event/evidence/render/package pipeline, verified selection dimensions, sparse comparisons, all-boss personal eligibility, actor-owned ability timing and immutable raw fixtures. Existing source verification and actual report/browser/raw arithmetic receipts remain the evidence, rather than the checklist itself.

### Fix before closing
None for the accepted scope. David approved the delivered implementation and instructed reconciliation and completion. Additional standalone Druid SME adjudication is explicitly retired by the product owner; no unperformed review is claimed. The user ended Claude pairing, so no Claude completion gate remains.

### Record
Master decisions, manual-action statuses, terminal PM resolutions, durable lessons and final acceptance are reconciled together. Source c016c4b has green Windows/Linux CI and 246 golden/acceptance passes with four retained expected failures. Subsequent commits change documentation/tracking only. Current close-out checks and the final gate review are recorded in the master plans.

### Risk
Duty thresholds remain heuristics; assignments, threat, quality and optimal play cannot be inferred from missing evidence. Role-regression labels are not independently adjudicated ground truth. Real Holy Priest healing validation is unavailable and accepted as a disclosed limitation. Long-term observation remains inconclusive, with future refinement separately scoped.

### Verdict
CLOSE — implementation, verification and accepted product scope are complete. Earlier pending verdicts remain historical; this is the current verdict.
