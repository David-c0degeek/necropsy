# 04 — Shared class playbooks and exports

## Goal
Use the Hunter hierarchy and substantive execution rows for every supported class.

## Integration analysis
- **Existing code found:** `report/render, report/package.py, docs/analysis-json.schema.json`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [ ] **04.1** (agent) Reuse shared loadout/execution/equipment/ability components with class-aware templates; ensure no Druid/Hunter mechanics leak to other classes.
- [ ] **04.2** (agent) Extend optional schema and common CSV/package exports with actual production callers; synchronize user docs, help, schema and ADR.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded: Keep / Fix before closing / Record / Risk / Verdict.
- [ ] Verdict is `CLOSE`

## Progress log
TBD — implementation not started.
