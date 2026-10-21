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
- [x] **01.1** (agent) Naxx in raid scope and the coverage register: 510 cells (or the recount), matrix rows seeded TODO, registered real actor sources added for existing archives that pass `actor_problems`. Negative tests: illegal faction cells absent; MC/BWL/AQ40 counts unchanged.
- [x] **01.2** (agent) Strategy seam for Naxx: `encounter_strategy` serves Naxx `strategy` items when present; with none present, Naxx analysis and both pages are byte-identical to the 00.2 baseline (saved-output replays).
- [ ] **01.3** (agent) `unit_preflight`, `raid_batch` and `check_raid_coverage` accept Naxx cells; one synthetic Naxx batch test.
- [x] **01.4** (agent) Coverage gate scoped by raid (`--require-complete --raid naxxramas` or equivalent) so the parked raids do not block Naxx sign-off.
- [ ] **01.5** (agent) Encounter context for zone 2006: v2 snapshot, acquisition of encounter and critical streams, duty, and the analysis_json block, gated on the archive's v2 encounter streams and never on the zone alone (PM-1). The gate is in `duty.applies` itself, because class role inference (`duty.guard_action_duty`, `combat.py`, `druid.py`) calls it upstream of rendering. Every v1 Naxx archive, the Haplina export and the demo subset stay byte-identical to the 00.2 baseline. Released before 03 queues any capture (PM-2).

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-21 · 01.1 · `raid_scope.yaml` lists naxxramas (zone 2006, 15 encounters): `coverage_cells()` 952 → 1462 (aq40 306, bwl 306, mc 340, naxxramas 510; 43 encounter entries). 510 Naxx matrix rows appended TODO in `coverage_cells()` order. Every participant of the 17 v1 Naxx archives was tried as an actor source: 178 of 191 contexts pass `actor_problems` (13 fail: 12 in two Druid archives whose subjects carry no ranking category, 1 name with two actor IDs). One source per cell, the subject first, registers 26 Naxx cells IN_PROGRESS (Patchwerk for eight class archives and five Druid trees, Balance for 15 bosses, Sapphiron Restoration, Four Horsemen Guardian); matrix rows mirror them. The two older provenance files had stale CRLF working copies; they were restored to the index LF bytes before pinning (the parked `tasks/raid-completion/research/naxx-reference.json` still records the old CRLF hash as history). Tests: pinned counts updated, per-raid counts asserted (illegal factions stay absent), unit suite 2105 passed, golden `test_real_actor_receipts_reject_wrong_configuration_or_variant` passed with all 133 records. `check_raid_coverage --inventory --raid naxxramas --staged`: 510 cells, 26 IN_PROGRESS, problems [].
2026-10-21 · 01.4 · `check_raid_coverage.py --raid SLUG` scopes `audit` and `--staged` to one raid; a record of another raid is skipped, an unknown cell is still reported (new unit test). Needed at once because the scope change made the parked MC batch stale (D010).
2026-10-21 · 01.5 (code; release pending) · `necropsy.raids.ENCOUNTER_CONTEXT_ZONES` (all four raids) and `ENCOUNTER_CONTEXT_PARTITIONS` ({1, 2}) replace the three hard-coded zone sets in `snapshot/v2.py`, `wcl/acquire.supports_encounter_context` and `analysis/encounters/duty.applies`. `duty.applies` itself requires `format == necropsy-live-snapshot-v2` for zone 2006, so class role inference upstream of the pages sees no change for v1 Naxx; `analysis_json.build_document` runs the encounter-context block for Naxx only on v2 (`snapshot/v2.FORMAT`). PM-1 check: `workspace/naxx-compat/naxx_outputs.py` hashed analysis.json, report.html and playbook.html for all 17 v1 Naxx archives and the Haplina subset at eb1d776 (`baseline-eb1d776.json`) and again with the change (`after-01.5.json`): 54 of 54 byte-identical. New tests: a synthetic Patchwerk capture in zone 2006 is v2 with encounter and critical scopes and gains `duty_context`; the same capture without encounter context is v1 and has none; partition 3 is still refused. The normal CLI now selects encounter scopes for Naxx partitions 1 and 2 (expectation updated). Unit and integration suites: 2494 passed, 29 skipped. Docs: architecture, raids, CHANGELOG. Box stays open until a release carries it (PM-2).
2026-10-21 · 01.2 · `encounter_strategy` no longer returns None for every Naxx call: Naxx uses the same `strategy` section and partition and class filters as the other raids. `naxxramas_guidance.yaml` has no `strategy` section, so it still returns None today (existing test) and serves sourced items once added (new test with a patched rules entry: Hunter item served, Mage none, partition 3 none). v1 Naxx never reaches the encounter block; v1 outputs still 54 of 54 byte-identical (`workspace/naxx-compat/after-01.2.json`). Open for content work: the existing Naxx guidance `encounters` section and future `strategy` items must not repeat or contradict each other (pre-mortem assumption); decide per boss when the first Naxx strategy items are written.
