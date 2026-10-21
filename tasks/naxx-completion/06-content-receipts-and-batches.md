# 06 - Content, Receipts And Batches

## Goal
Sourced boss × class guidance for all 15 bosses and every configuration, a clean
receipt for every capture, and batch registrations that turn cells COMPLETE.

## Integration analysis
To be completed before 06.1. Reuse the 01.2 strategy seam, `guidance_lint.py`,
class notes (`healer_notes.yaml` and DPS equivalents if any), `render_parity.py`,
`raid_batch.py`. Existing Naxx `encounters` guidance (8 bosses) is either migrated
into strategy items or kept, by decision; no duplicate rendering.

## Boxes
- [ ] **06.1** (agent) Content per boss, all classes at once: drafts by work order from 04.1 excerpts, lint-clean, Claude-verified against excerpts, then one content review per boss group.
- [ ] **06.2** (agent) Class notes and loadout rows for any class or spec that lacks them on Naxx.
- [ ] **06.3** (agent) Receipts for every capture at the batch commit; one sampled picture per capture inspected.
- [ ] **06.4** (agent) Batches per configuration group; `raid_batch write`, `check_raid_coverage --inventory --staged`, gate, pair review, push. Record elapsed time per batch.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
