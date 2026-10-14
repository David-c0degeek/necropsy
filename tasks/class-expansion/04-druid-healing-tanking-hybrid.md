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
- [ ] **04.1** (agent) Analyze restoration effective healing, overhealing, spell use, resource/cooldown timing and target/assignment context where observable; do not rank quality from raw HPS alone.
- [ ] **04.2** (agent) Analyze feral tank incoming damage, deaths, mitigation/form/cooldown coverage and tanking windows; use threat only when actually available and retain healing support/assignment uncertainty. Do not treat low DPS as a tank failure.
- [ ] **04.3** (agent) Represent hybrid/mixed responsibilities as explicit phases or multiple evidenced roles per fight; preserve transitions and uncertainty. Define benchmark applicability per phase/role and decline unsupported aggregates.
- [ ] **04.4** (domain-sme) Review healing, tank and hybrid examples and acceptance facts; confirm practical advice respects assignments and cannot infer causality from unavailable raid-wide evidence.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
TBD — implementation has not started. Record date, per-subject slice number, box IDs, observed behavior, verification, documentation impact, and pushed checkpoint.
