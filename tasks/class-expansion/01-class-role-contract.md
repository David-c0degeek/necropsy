# 01 — Class, build and encounter-role contracts

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
- [ ] **01.1** (agent) Inventory Hunter-specific acquisition, snapshots, benchmarks, recommendations, JSON and renderer assumptions. Extend ClassPlugin/registry and shared evidence contracts without a second analysis pipeline; record compatibility and pre-mortem decisions before implementation.
- [ ] **01.2** (agent) Separate observed class, talents/build, WCL ranking category/spec, encounter assignment and inferred per-fight role. Support feral DPS, balance DPS, restoration healing, feral tanking and hybrid/mixed roles; return uncertain when evidence cannot distinguish them.
- [ ] **01.3** (agent) Define documented user overrides with provenance; preserve observed conflicting evidence and do not promote an override or talent label into an observed role. Define DPS/HPS/tanking-specific cohort dimensions with no cross-role median mixing.
- [ ] **01.4** (domain-sme) Review the Druid role taxonomy and success criteria, including hybrid responsibilities, overhealing/assignment limits, tank survivability/threat limits and what combat logs cannot prove.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
TBD — implementation has not started. Record date, per-subject slice number, box IDs, observed behavior, verification, documentation impact, and pushed checkpoint.
