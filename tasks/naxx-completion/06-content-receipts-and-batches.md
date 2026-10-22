# 06 - Content, Receipts And Batches

## Goal
Sourced boss × class guidance for all 15 bosses and every configuration, a clean
receipt for every capture, and batch registrations that turn cells COMPLETE.

## Integration analysis
Reuse the existing strategy seam, `guidance_lint.py`, `render_parity.py` and
`raid_batch.py`. `analysis/encounters/strategy.py` selects items by class and
metric, not ranking category. Keep the two tank-category-only draft profiles
out of the proposed YAML: class/metric selection would broaden them to DPS.
Any future category-aware seam needs its own implementation review and tests.

The eight existing Hunter `encounters` blocks stay in place for this proposal.
Do not repeat their Rapid Fire/Refocus instructions in new strategy items.
`report/combat.py` renders healer class notes only for the healer role;
`rules/classic_era/healer_notes.yaml` currently covers Paladin, Priest and Shaman.
Druid healer review is separate in `report/druid.py`. Recorded gear/build
presentation already shares `report/equipment.py`; source applicability and
actual captured loadouts still need review before 06.2 can close.

The proposed strategy file is research, not a production rule file. Mechanical
verifier success does not replace semantic source review, independent review,
rendering checks or per-capture receipts.

## Boxes
- [ ] **06.1** (agent) Content per boss, all classes at once: drafts by work order from 04.1 excerpts, lint-clean, Claude-verified against excerpts, then one content review per boss group.
- [ ] **06.2** (agent) Class notes and loadout rows for any class or spec that lacks them on Naxx.
- [ ] **06.3** (agent) Receipts for every capture at the batch commit; one sampled picture per capture inspected.
- [ ] **06.4** (agent) Batches per configuration group; `raid_batch write`, `check_raid_coverage --inventory --staged`, gate, pair review, push. Record elapsed time per batch.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log

2026-10-22 · Coordinator drafts prepared without local inference ·
`research/coordinator-guidance-drafts.json` records finite source-bound profiles
and 510 boss/configuration recipes (15 bosses × 34 legal configurations).
Every draft passes the existing work-order verifier. A separate reconstruction
reproduces all 510 orders and drafts byte for byte, checks source/tool hashes and
matches each projected section against `research/naxx-strategy-proposal.yaml`.
All eight work-order categories are accounted for; unsupported categories stay
explicitly unknown. The proposal contains before/during/raid sections for every
legal projection. Patchwerk hateful-tank loadout and Sapphiron tank duty remain
withheld because their category restriction is not expressible by the current
strategy selector. Existing Hunter guidance and all production rules are
unchanged. This is draft preparation, not 510 completed cells or approval.
Semantic/source review, capability/loadout coverage, independent review,
integration, visual checks, receipts and batches remain open. Historical local
model trial scores and frozen source-ledger pins are unchanged.

Verification: all 510 independent reconstructions pass; 119 existing guidance, queue, staging and archive checks pass. The docs checker passes 297 maintained links, and the research secret scan finds no leaks. Full unchanged-tree gate follows commit.

2026-10-22 · Portable proposal verification ·
`uv run python scripts/check_guidance_proposal.py tasks/naxx-completion/research/coordinator-guidance-drafts.json`
now reconstructs all 510 frozen drafts from a fresh checkout and reuses the
existing work-order verifier. It compares the complete proposed YAML with the
verified projections, including exact class/metric scope, citations, text,
support and section mapping; duplicate JSON/YAML keys, orphan rows, missing or
duplicate legal cells and tank-only leakage are refused. It is read-only,
starts no model and leaves content review pending. Sixteen tests cover the real
bundle and planted coverage, source/digest, applicability and projection defects.
This replaces dependence on the ignored replay helper for future verification;
the historical replay receipt and its script digest remain unchanged.
