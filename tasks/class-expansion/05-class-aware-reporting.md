# 05 — Class-aware reports and playbooks

## Goal
Expose Druid roles and useful class-specific details through the existing report and package.

## Integration analysis
- **Existing code found:** `report/analysis_json.py, report/render/playbook_view.py, view.py, templates, assets, report/package.py`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [x] **05.1** (agent) Extend analysis JSON with explicitly versioned/compatible class-specific metrics; preserve legacy hunter fields/readers where required and synchronize the generated JSON schema.
- [x] **05.2** (agent) Reuse shared rendering and evidence components with class-aware labels, role-specific summaries, KISS cards and full supporting detail. Show talent/build versus observed role, overrides, hybrid phases and unknowns clearly.
- [x] **05.3** (agent) Extend package CSV/evidence exports and user/developer docs; verify old Hunter pages and desktop/mobile layouts remain complete without new class terms leaking into historical outputs.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

## Progress log
2026-10-14 · 1 · 05.1 05.2 05.3 · Shared report/package pipeline dispatches class sections and templates; legacy Hunter pages and bytes preserved. Druid practice notes, role-specific measurements, full source timeline, forms/resources/targets and all cohort detail exported as CSV/JSON. Browser inspection covered 16 real page/viewport combinations (1400/390), no overflow, remote requests or JS errors; dedicated synthetic browser cases additionally check escaping/search/theme. README, user/developer docs, schema, ADR and validation limits updated. Closing peer review pending. Checkpoint commit/push follows this record.

2026-10-14 · 2 · Scoped Claude core review AGREE round 1 / blocking 0; 86 independent tests passed. Addressed important incidental-duty finding with explicit 20% secondary cast-share heuristic and regression cases; preserved minor actions. Role taxonomy/domain gates remain open. Reporting/docs are requested in a separate bounded final review because the first review explicitly did not read those line by line.

2026-10-14 · 3 · Claude output review AGREE round 2 / blocking 0 / important 0 against 107e024; exact limitations of that review remain recorded. Added named actor catalog, faction/external context, graded resources, comparison CSV and optional detail compatibility; role raw catalog includes Swiftmend/Hurricane/Ravage/Pounce. Per-phase hybrid comparisons are not implemented: unsupported whole-fight aggregates are deliberately declined, with activity spans retained. Latest focused/browser/real replay checks pass; final guard/record review and updated CI follow.


2026-10-15 · final engineering checkpoint · Six real Druid replays pass, including Four Horsemen tank/hybrid and own Sapphiron healing. 855 fast pass; full initial golden/acceptance 233 pass / four retained xfails; expanded six-Druid replay six pass; browser suite 23 pass; all 24 real page/viewport checks plus six artifact checks/output scans pass. Ruff lint/format, strict mypy and wheel/sdist build pass. Hunter JSON/both pages/ZIP byte-identical after inline-heading whitespace correction. Linux/Windows CI b4fd2e8 passed; final changed-fixture/template checkpoint CI follows. Portable raw scans: 169,740,861 + 62,401,552 bytes, no leaks. Review packet names exact human questions. Final independent review remains pending; checkpoint commit/push covers this record.

## Captain Hindsight — 2026-10-15

### Keep

Retain shared document/assets/publisher and optional class detail compatibility. Existing acquisition, normalization, evidence and publication remain the runtime path. Behavior was exercised from saved raw evidence to package and browser, not inferred from compilation.

### Fix before closing

Final Claude review and current-tip CI passed. No engineering defect is currently known; never mark the remaining human-owned boxes accepted from agent checks.

### Record

ADR 0005 records class/metric/duty compatibility. Decisions D007–D011 cover tank evidence, bounded validation, secondary duty share, cleanup reuse and explicit metric selection. PM-1–PM-3 calibration and CH-MISS-1/2 are retained in pre-mortem.md; durable lessons are in tasks/lessons.md. No shipped-code plan reference was found by targeted search outside tasks.

### Risk

Role thresholds are provisional. Exact-build samples can be sparse; resource/form/overheal/threat/assignment gaps stay unknown. Selected fights across three bosses do not establish full-raid or final domain acceptance. No requested role was deferred.

### Verdict

CLOSE — all subject boxes and engineering checks pass. Cross-subject domain acceptance remains open in its explicitly owned boxes; no domain approval is inferred here.


2026-10-15 · engineering review receipt · Claude mail 180: AGREE round=3 blocking=0 important=0 at db89d3a; 92 independent focused tests pass. It reviewed the changed roles/cohort/acquire/analyze/snapshot-reader/document/Druid analyzer-report/base-template code, and explicitly excluded remaining views/offline/writer/CLI/export/schema/docs/plan/raw-fact surfaces from that round. Earlier scoped rounds plus lead inspection, six real artifact/package replays, schema tests and 24 browser cases cover those paths; no claim of blanket independent review is made. Optional CohortKey.metric storage nit retained as-is: the property preserves Hunter's serialized key bytes, all supported combinations are tested, and unsupported combinations fail canonical policy. Future categories must extend that policy and query tests together. Linux and Windows CI db89d3a passed: https://github.com/David-c0degeek/necropsy/actions/runs/38646145402. This is a record-only close-out; no runtime or test edits follow the reviewed code.
