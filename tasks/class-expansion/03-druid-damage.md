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

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-14 · 1 · 03.1 03.2 03.3 · Registered Druid analysis covers forms, casts, resources, cooldown/utility sequences, raw actor damage and target detail. Exact build/category/role medians, action cadence, evidence-linked findings and role-specific practice notes run through production document/report/package. Haplina balance: 68,395 damage, 535.272665 event DPS, 40 qualifying casts, build 37/0/14; two same-build samples correctly leave median unknown. Feral Stinkface saved replay passes. Domain damage review remains open. Checkpoint commit/push follows this record.
