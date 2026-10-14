# 04 — Restoration, tank and hybrid analysis

## Goal
Evaluate healing, tanking and mixed duties with appropriate observed metrics and limitations.

## Integration analysis
- **Existing code found:** `analysis/generic/metrics.py, environment.py, coverage/context evidence and encounter rule modules`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [x] **04.1** (agent) Analyze restoration effective healing, overhealing, spell use, resource/cooldown timing and target/assignment context where observable; do not rank quality from raw HPS alone.
- [x] **04.2** (agent) Analyze feral tank incoming damage, deaths, mitigation/form/cooldown coverage and tanking windows; use threat only when actually available and retain healing support/assignment uncertainty. Do not treat low DPS as a tank failure.
- [x] **04.3** (agent) Represent hybrid/mixed responsibilities as explicit phases or multiple evidenced roles per fight; preserve transitions and uncertainty. Define benchmark applicability per phase/role and decline unsupported aggregates.
- [ ] **04.4** (domain-sme) Review healing, tank and hybrid examples and acceptance facts; confirm practical advice respects assignments and cannot infer causality from unavailable raid-wide evidence.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [x] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-14 · 1 · 04.1 04.2 04.3 · Effective healing/overheal/spell/target data, incoming damage/support, available mitigation, defensive/form coverage and deaths implemented. Hybrid activity spans preserve multiple roles and decline unsupported aggregate benchmarks. Restoration Haplina 43,558 effective healing / 339.189210 HPS; missing overheal remains unknown. Guardian cohort Harryjam has 211,627 incoming damage and repeated bear-only actions; Suncat category alone does not prove tank duty. Synthetic hybrid/direct-hit/AoE tests pass; real mixed-duty run pending API reset; no claim of domain approval. Checkpoint commit/push follows this record.

2026-10-14 · 2 · Scoped Claude core review AGREE round 1 / blocking 0; 86 independent tests passed. Addressed important incidental-duty finding with explicit 20% secondary cast-share heuristic and regression cases; preserved minor actions. Role taxonomy/domain gates remain open. Reporting/docs are requested in a separate bounded final review because the first review explicitly did not read those line by line.


2026-10-15 · final engineering checkpoint · Six real Druid replays pass, including Four Horsemen tank/hybrid and own Sapphiron healing. 855 fast pass; full initial golden/acceptance 233 pass / four retained xfails; expanded six-Druid replay six pass; browser suite 23 pass; all 24 real page/viewport checks plus six artifact checks/output scans pass. Ruff lint/format, strict mypy and wheel/sdist build pass. Hunter JSON/both pages/ZIP byte-identical after inline-heading whitespace correction. Linux/Windows CI b4fd2e8 passed; final changed-fixture/template checkpoint CI follows. Portable raw scans: 169,740,861 + 62,401,552 bytes, no leaks. Review packet names exact human questions. Final independent review remains pending; checkpoint commit/push covers this record.

## Captain Hindsight — 2026-10-15

### Keep

Retain healing/incoming support, tank evidence and multiple duties without hybrid aggregates. Existing acquisition, normalization, evidence and publication remain the runtime path. Behavior was exercised from saved raw evidence to package and browser, not inferred from compilation.

### Fix before closing

Resolve 04.4 healing/tank/hybrid domain review. No engineering defect is currently known; never mark the remaining human-owned boxes accepted from agent checks.

### Record

ADR 0005 records class/metric/duty compatibility. Decisions D007–D011 cover tank evidence, bounded validation, secondary duty share, cleanup reuse and explicit metric selection. PM-1–PM-3 calibration and CH-MISS-1/2 are retained in pre-mortem.md; durable lessons are in tasks/lessons.md. No shipped-code plan reference was found by targeted search outside tasks.

### Risk

Role thresholds are provisional. Exact-build samples can be sparse; resource/form/overheal/threat/assignment gaps stay unknown. Selected fights across three bosses do not establish full-raid or final domain acceptance. No requested role was deferred.

### Verdict

DO NOT CLOSE — 04.4 healing/tank/hybrid domain review. The smallest next actions are the named review/CI or human decisions; do not expand acquisition or rerun already-passing checks without a new reason.
