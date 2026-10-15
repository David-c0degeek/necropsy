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
- [x] **01.1** (agent) Centralize observed class IDs, ranking category/metric/role policy and spec aliases; reject incompatible selections before requests.
- [x] **01.2** (agent) Wire generic class/spec selection into cohort queries and snapshot validation without changing legacy Hunter query defaults.

## Hindsight checkpoint
- [x] Captain Hindsight review recorded: Keep / Fix before closing / Record / Risk / Verdict.
- [x] Verdict is `CLOSE`

## Progress log
TBD — implementation not started.


2026-10-15 · implementation checkpoint · Catalog/policy/query/class selection, seven registered combat plugins, shared event/totals extraction, role-qualified personal selection and comparisons, class-aware shared view/template/schema/exports and docs are wired. All14category offline/package tests plus partial and tank/mixed negatives pass (17). All14category browser cases cover56page/viewports. Catalog/query/metric18checks pass. Druid/cohort regression118pass and oldHunter4artifact byteguard pass. Full local fast run911passed1obsolete CLI wording assertion; assertion updated and55CLI/catalog checks pass. Real Mage/Paladin/Priest acquisition/replay now passes with5event references each; remaining public class captures and final broad checks still in progress. No domain sign-off inferred.


## Solo Captain Hindsight — 2026-10-15

### Keep
Live category probes and 18 catalog/query checks establish real API filters, aliases and HPS/DPS policy. All fourteen added category contracts pass production offline/snapshot/package tests.

### Fix before closing
None for this engineering subject. Product acceptance remains separately owned in 05.4.

### Record
Unsupported Combat/Affliction/Survival ranking filters are not invented; actual talent builds remain context. Documentation impact: README, connection, architecture, class guide, schema and ADR0006 updated with implementation.

### Risk
Duty thresholds are conservative heuristics, not approved assignments. Real event fixtures cover seven categories, synthetic contracts cover all fourteen; real Holy Priest healing remains unavailable.

### Verdict
CLOSE — scoped engineering subject; no human sign-off or independent Claude verdict is claimed.
