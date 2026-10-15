# 03 — Role-aware personal selection and leader references

## Goal
Keep personal selected-spec/duty separate from faction leader practice and optional global context.

## Integration analysis
- **Existing code found:** `report/analysis_json.py, report/druid.py, wcl/acquire.py`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [ ] **03.1** (agent) Serialize generic combat entries and build matching faction/spec/metric/role comparisons with sparse n; keep no-personal encounters visible and ungraded.
- [ ] **03.2** (agent) Support all requested encounters, ranking metadata/source links, unknowns and optional collapsed global comparisons through existing acquisition and report seams.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded: Keep / Fix before closing / Record / Risk / Verdict.
- [ ] Verdict is `CLOSE`

## Progress log
TBD — implementation not started.


2026-10-15 · implementation checkpoint · Catalog/policy/query/class selection, seven registered combat plugins, shared event/totals extraction, role-qualified personal selection and comparisons, class-aware shared view/template/schema/exports and docs are wired. All14category offline/package tests plus partial and tank/mixed negatives pass (17). All14category browser cases cover56page/viewports. Catalog/query/metric18checks pass. Druid/cohort regression118pass and oldHunter4artifact byteguard pass. Full local fast run911passed1obsolete CLI wording assertion; assertion updated and55CLI/catalog checks pass. Real Mage/Paladin/Priest acquisition/replay now passes with5event references each; remaining public class captures and final broad checks still in progress. No domain sign-off inferred.
