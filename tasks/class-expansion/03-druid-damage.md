# 03 — Feral and balance damage analysis

## Goal
Deliver distinct observed execution and recommendations for feral DPS and balance DPS.

## Integration analysis
- **Existing code found:** `analysis/classes/classic_era/hunter.py as interface precedent, analysis/generic, analysis/recommendations.py and guidance.py`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [x] **03.1** (agent) Implement a registered Classic Era Druid analyzer with pinned rule/spell data; identify forms, relevant attacks/casts, resources and cooldown sequences from affirmative evidence, with coverage-aware absence claims.
- [x] **03.2** (agent) Analyze feral DPS execution and balance DPS cast/resource/cooldown patterns against comparable same-role/build samples; distinguish fight duration, target roles, movement/assignment and external buffs from controllable execution.
- [x] **03.3** (agent) Produce evidence-linked class-specific recommendations and a concise practice opener/notes view; preserve full timelines and avoid universal optimal rotations derived from tiny samples.
- [ ] **03.4** (domain-sme) Adjudicate representative feral and balance findings against raw evidence and the stated encounter assignment; record exclusions and corrections rather than forcing agreement with a guide.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [x] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-14 · 1 · 03.1 03.2 03.3 · Registered Druid analysis covers forms, casts, resources, cooldown/utility sequences, raw actor damage and target detail. Exact build/category/role medians, action cadence, evidence-linked findings and role-specific practice notes run through production document/report/package. Haplina balance: 68,395 damage, 535.272665 event DPS, 40 qualifying casts, build 37/0/14; two same-build samples correctly leave median unknown. Feral Stinkface saved replay passes. Domain damage review remains open. Checkpoint commit/push follows this record.


2026-10-15 · final engineering checkpoint · Six real Druid replays pass, including Four Horsemen tank/hybrid and own Sapphiron healing. 855 fast pass; full initial golden/acceptance 233 pass / four retained xfails; expanded six-Druid replay six pass; browser suite 23 pass; all 24 real page/viewport checks plus six artifact checks/output scans pass. Ruff lint/format, strict mypy and wheel/sdist build pass. Hunter JSON/both pages/ZIP byte-identical after inline-heading whitespace correction. Linux/Windows CI b4fd2e8 passed; final changed-fixture/template checkpoint CI follows. Portable raw scans: 169,740,861 + 62,401,552 bytes, no leaks. Review packet names exact human questions. Final independent review remains pending; checkpoint commit/push covers this record.

## Captain Hindsight — 2026-10-15

### Keep

Retain feral/balance actions, cast cadence, resources and conservative practice notes. Existing acquisition, normalization, evidence and publication remain the runtime path. Behavior was exercised from saved raw evidence to package and browser, not inferred from compilation.

### Fix before closing

Resolve 03.4 damage-domain review. No engineering defect is currently known; never mark the remaining human-owned boxes accepted from agent checks.

### Record

ADR 0005 records class/metric/duty compatibility. Decisions D007–D011 cover tank evidence, bounded validation, secondary duty share, cleanup reuse and explicit metric selection. PM-1–PM-3 calibration and CH-MISS-1/2 are retained in pre-mortem.md; durable lessons are in tasks/lessons.md. No shipped-code plan reference was found by targeted search outside tasks.

### Risk

Role thresholds are provisional. Exact-build samples can be sparse; resource/form/overheal/threat/assignment gaps stay unknown. Selected fights across three bosses do not establish full-raid or final domain acceptance. No requested role was deferred.

### Verdict

DO NOT CLOSE — 03.4 damage-domain review. The smallest next actions are the named review/CI or human decisions; do not expand acquisition or rerun already-passing checks without a new reason.
