# 05 — Class-aware reports and playbooks

## Goal
Expose Druid roles and useful class-specific details through the existing report and package.

## Integration analysis
- **Existing code found:** `report/analysis_json.py, report/render/playbook_view.py, view.py, templates, assets, report/package.py`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [x] **05.1** (agent) Extend analysis JSON with explicitly versioned/compatible class-specific metrics; preserve legacy hunter fields/readers where required and synchronize the generated JSON schema.
- [x] **05.2** (agent) Reuse shared rendering and evidence components with class-aware labels, role-specific summaries, KISS cards and full supporting detail. Show talent/build versus observed role, overrides, hybrid phases and unknowns clearly.
- [x] **05.3** (agent) Extend package CSV/evidence exports and user/developer docs; verify old Hunter pages and desktop/mobile layouts remain complete without new class terms leaking into historical outputs.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-14 · 1 · 05.1 05.2 05.3 · Shared report/package pipeline dispatches class sections and templates; legacy Hunter pages and bytes preserved. Druid practice notes, role-specific measurements, full source timeline, forms/resources/targets and all cohort detail exported as CSV/JSON. Browser inspection covered 16 real page/viewport combinations (1400/390), no overflow, remote requests or JS errors; dedicated synthetic browser cases additionally check escaping/search/theme. README, user/developer docs, schema, ADR and validation limits updated. Closing peer review pending. Checkpoint commit/push follows this record.

2026-10-14 · 2 · Scoped Claude core review AGREE round 1 / blocking 0; 86 independent tests passed. Addressed important incidental-duty finding with explicit 20% secondary cast-share heuristic and regression cases; preserved minor actions. Role taxonomy/domain gates remain open. Reporting/docs are requested in a separate bounded final review because the first review explicitly did not read those line by line.

2026-10-14 · 3 · Claude output review AGREE round 2 / blocking 0 / important 0 against 107e024; exact limitations of that review remain recorded. Added named actor catalog, faction/external context, graded resources, comparison CSV and optional detail compatibility; role raw catalog includes Swiftmend/Hurricane/Ravage/Pounce. Per-phase hybrid comparisons are not implemented: unsupported whole-fight aggregates are deliberately declined, with activity spans retained. Latest focused/browser/real replay checks pass; final guard/record review and updated CI follow.
