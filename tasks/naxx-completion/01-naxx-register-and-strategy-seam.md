# 01 - Naxx Register And Strategy Seam

## Goal
Make Naxx a first-class raid in the completion machinery: its 510 cells exist in
the coverage register and matrix, the preflight and batch tools accept them, and
boss × class strategy items can be added to Naxx without changing existing Naxx
pages until content arrives.

## Integration analysis
To be completed before 01.1, from 00.5. Known so far:
- `raid_scope.yaml` lists aq40/bwl/mc only; `coverage_cells()` derives cells from it.
- `encounter_strategy` returns None for `naxxramas`; Naxx guidance uses its own `encounters` section (8 bosses) rendered by existing code. The strategy seam must be additive: an empty Naxx `strategy` section renders exactly as today.
- `raid_batch.engine_digest` reads `<raid>.yaml`, `<raid>_guidance.yaml`, `<raid>_facts.yaml`; Naxx file names are `naxxramas*` — check the raid key mapping.
- `check_raid_coverage.content_problems` requires sourced facts and before/during/raid strategy sections; confirm this is the right bar for Naxx or extend it.
- Preserve: saved analyses, legacy Hunter/Druid pages, all Naxx golden tests.
- 00.5 (`inventory.md`): Naxx has no encounter context. `snapshot/v2.py` rejects zone 2006, `acquire.supports_encounter_context` and `duty.applies` exclude it, and `analysis_json.py` skips the whole encounter-context block for Naxx. All 17 existing Naxx archives are v1. PM-1 and PM-2 apply.

## Boxes
- [ ] **01.1** (agent) Naxx in raid scope and the coverage register: 510 cells (or the recount), matrix rows seeded TODO, registered real actor sources added for existing archives that pass `actor_problems`. Negative tests: illegal faction cells absent; MC/BWL/AQ40 counts unchanged.
- [ ] **01.2** (agent) Strategy seam for Naxx: `encounter_strategy` serves Naxx `strategy` items when present; with none present, Naxx analysis and both pages are byte-identical to the 00.2 baseline (saved-output replays).
- [ ] **01.3** (agent) `unit_preflight`, `raid_batch` and `check_raid_coverage` accept Naxx cells; one synthetic Naxx batch test.
- [ ] **01.4** (agent) Coverage gate scoped by raid (`--require-complete --raid naxxramas` or equivalent) so the parked raids do not block Naxx sign-off.
- [ ] **01.5** (agent) Encounter context for zone 2006: v2 snapshot, acquisition of encounter and critical streams, duty, and the analysis_json block, gated on the archive's v2 encounter streams and never on the zone alone (PM-1). Every v1 Naxx archive, the Haplina export and the demo subset stay byte-identical to the 00.2 baseline. Released before 03 queues any capture (PM-2).

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
