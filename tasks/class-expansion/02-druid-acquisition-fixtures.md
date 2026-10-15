# 02 — Druid acquisition and evidence fixtures

## Goal
Acquire identity-verified role-comparable Druid evidence and establish real validation fixtures.

## Integration analysis
- **Existing code found:** `wcl/context.py, cohort.py, acquire.py, fetch.py; snapshot/model.py, v1.py, v1_writer.py, normalize/ingest.py`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [ ] **02.1** (agent) Generalize existing context/cohort/acquire code and snapshot v1 class guards using the declared class/role contract; verify actual WCL category/metric/spec filters. Unsupported categories remain explicit; never substitute DPS samples for healers or tanks.
- [x] **02.2** (product-owner) Provide or authorize accessible Classic Era Naxxramas Druid reports covering all requested roles and hybrid/uncertain cases; confirm player-data handling and a domain reviewer.
- [x] **02.3** (agent) Freeze approved raw fixtures with hashes/provenance and a role-specific golden-fact register. Acquire evidence streams required for healing, incoming damage, forms, buffs/debuffs and any available threat; unavailable signals stay unknown.
- [x] **02.4** (agent) Prove old Hunter v0/v1 snapshots and JSON remain readable and unchanged in meaning. No format/schema bump unless an ADR explains necessity and the compatibility/rebuild route.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [x] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-14 · 1 · 02.1 02.2 02.4 · WCL live taxonomy and metric/category filters verified; raw snapshots frozen for Balance/Restoration/Feral/Guardian with five deep samples and 25 metadata rows per Patchwerk run. Four real fixture replays pass independent arithmetic and package hashes. Raw/member digests and installed gitleaks scan recorded. Hunter subset JSON/HTML/ZIP byte-identical; full Hunter golden 229 pass / 4 expected xfails. Raw hybrid evidence and approved domain facts still required for 02.3; user authorized public fixture handling. Checkpoint commit/push follows this record.


2026-10-15 · final engineering checkpoint · Six real Druid replays pass, including Four Horsemen tank/hybrid and own Sapphiron healing. 855 fast pass; full initial golden/acceptance 233 pass / four retained xfails; expanded six-Druid replay six pass; browser suite 23 pass; all 24 real page/viewport checks plus six artifact checks/output scans pass. Ruff lint/format, strict mypy and wheel/sdist build pass. Hunter JSON/both pages/ZIP byte-identical after inline-heading whitespace correction. Linux/Windows CI b4fd2e8 passed; final changed-fixture/template checkpoint CI follows. Portable raw scans: 169,740,861 + 62,401,552 bytes, no leaks. Review packet names exact human questions. Final independent review remains pending; checkpoint commit/push covers this record.

## Captain Hindsight — 2026-10-15

### Keep

Retain six immutable real captures, hashes and independent arithmetic; old Hunter replay. Existing acquisition, normalization, evidence and publication remain the runtime path. Behavior was exercised from saved raw evidence to package and browser, not inferred from compilation.

### Fix before closing

Final Claude review and current-tip CI passed. No engineering defect is currently known; never mark the remaining human-owned boxes accepted from agent checks.

### Record

ADR 0005 records class/metric/duty compatibility. Decisions D007–D011 cover tank evidence, bounded validation, secondary duty share, cleanup reuse and explicit metric selection. PM-1–PM-3 calibration and CH-MISS-1/2 are retained in pre-mortem.md; durable lessons are in tasks/lessons.md. No shipped-code plan reference was found by targeted search outside tasks.

### Risk

Role thresholds are provisional. Exact-build samples can be sparse; resource/form/overheal/threat/assignment gaps stay unknown. Selected fights across three bosses do not establish full-raid or final domain acceptance. No requested role was deferred.

### Verdict

CLOSE — all subject boxes and engineering checks pass. Cross-subject domain acceptance remains open in its explicitly owned boxes; no domain approval is inferred here.


2026-10-15 · engineering review receipt · Claude mail 180: AGREE round=3 blocking=0 important=0 at db89d3a; 92 independent focused tests pass. It reviewed the changed roles/cohort/acquire/analyze/snapshot-reader/document/Druid analyzer-report/base-template code, and explicitly excluded remaining views/offline/writer/CLI/export/schema/docs/plan/raw-fact surfaces from that round. Earlier scoped rounds plus lead inspection, six real artifact/package replays, schema tests and 24 browser cases cover those paths; no claim of blanket independent review is made. Optional CohortKey.metric storage nit retained as-is: the property preserves Hunter's serialized key bytes, all supported combinations are tested, and unsupported combinations fail canonical policy. Future categories must extend that policy and query tests together. Linux and Windows CI db89d3a passed: https://github.com/David-c0degeek/necropsy/actions/runs/38646145402. This is a record-only close-out; no runtime or test edits follow the reviewed code.


2026-10-15 · selected-spec correction · D012/D013 reopen the affected agent boxes.
User confirmed one selected spec view with all bosses visible, matching personal
data only, and separately labelled top-player examples when personal data is
missing. Implemented CLI aliases/conflict refusal, role eligibility, requested
empty bosses, exemplar/metadata separation, coverage/learning CSVs, personal-first
Druid acquisition and finalization reserve with policy restoration. Hunter26
recorded request bodies/endpoints and all four saved artifacts match72744c5.
Latest broad run:877 fast pass; subsequently added the multi-boss snapshot-order
regression (passes) and conflict checks. Native DuckDB failed during overlapping
large replays (malformed JSON/native access violation); isolated Guardian replay
passed. Serial full golden/acceptance rerun is pending; no normalizer change was
made without a reproducible cause. Tank-view real fixture and32,499,807 extracted
bytes passed arithmetic/secret checks. Full Balance run is waiting once on the
observed reset, after cancelling the old acquisition and retaining its cache.

## Captain Hindsight — selected-spec correction

### Keep
Keep spec/category/observed-duty separation, personal eligibility and explicitly
labelled learning examples. Retain all requested bosses and guard unknowns.

### Fix before closing
Finish latest serial golden/browser checks, current CI, independent scoped review
and actual multi-boss live view verification. Do not count the old close-out as
approval of these new behaviors.

### Record
D012/D013 and ADR0005 describe the clarified view and acquisition order. PM/CH
calibration records the missed view contract and budget-order issue. User's yes
confirms the view model only; domain heuristic/advice gates remain open.

### Risk
API budget limits comparison depth; native bulk-loader failures during concurrent
verification need a clean serial result before claiming latest replay success.
No source log or ranking category alone proves a selected encounter duty.

### Verdict
DO NOT CLOSE — latest verification, live capture and scoped review are pending.
