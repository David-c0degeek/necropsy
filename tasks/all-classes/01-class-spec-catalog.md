# 01 — Classic Era class and category catalog

## Goal
Offer every Classic Era class using verified ranking categories and explicit aliases.

## Integration analysis
- **Existing code found:** `analysis/roles.py, wcl/analyze.py, wcl/cohort.py, snapshot/v1.py`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [ ] **01.1** (agent) Centralize observed class IDs, ranking category/metric/role policy and spec aliases; reject incompatible selections before requests.
- [ ] **01.2** (agent) Wire generic class/spec selection into cohort queries and snapshot validation without changing legacy Hunter query defaults.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded: Keep / Fix before closing / Record / Risk / Verdict.
- [ ] Verdict is `CLOSE`

## Progress log
TBD — implementation not started.
