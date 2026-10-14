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
- [ ] **02.2** (product-owner) Provide or authorize accessible Classic Era Naxxramas Druid reports covering all requested roles and hybrid/uncertain cases; confirm player-data handling and a domain reviewer.
- [ ] **02.3** (agent) Freeze approved raw fixtures with hashes/provenance and a role-specific golden-fact register. Acquire evidence streams required for healing, incoming damage, forms, buffs/debuffs and any available threat; unavailable signals stay unknown.
- [ ] **02.4** (agent) Prove old Hunter v0/v1 snapshots and JSON remain readable and unchanged in meaning. No format/schema bump unless an ADR explains necessity and the compatibility/rebuild route.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
TBD — implementation has not started. Record date, per-subject slice number, box IDs, observed behavior, verification, documentation impact, and pushed checkpoint.
