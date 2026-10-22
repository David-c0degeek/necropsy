# 06 - Content, Receipts And Batches

## Goal
Sourced boss × class guidance for all 15 bosses and every configuration, a clean
receipt for every capture, and batch registrations that turn cells COMPLETE.

## Integration analysis
Reuse the existing strategy seam, `guidance_lint.py`, `render_parity.py` and
`raid_batch.py`. `analysis/encounters/strategy.py` now accepts an optional
comparison category, canonicalized by the existing ranking taxonomy. Restricted
rows require a known matching category; unknown does not broaden them. The
original general proposal still withholds its two tank-only profiles. Their
separate `research/naxx-category-strategy-proposal.yaml` is ready for review,
with six rows and ten applicable boss/configuration projections. No draft
content is activated by the seam change.

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

`research/class-loadout-path-audit-20261022.json` pins the existing presentation
and healer-note paths for all 34 configurations. The 32 non-Hunter categories
already share Weapons, Trinkets, Relic/Ranged and World buffs rows; Warlock also
has owned-pet/summon presentation. Two Hunter configurations retain the dedicated
playbook. Separate missing-data view probes check all 32 shared projections;
they are not actual-player, normal acquisition or visual acceptance. Reuse these
rows when reviewing 06.2; remaining work concerns source/class/category content
and eligible recorded loadouts, rather than duplicating slot presentation.

## Boxes
- [ ] **06.1** (agent) Content per boss, all classes at once: drafts by work order from 04.1 excerpts, lint-clean, Claude-verified against excerpts, then one content review per boss group.
- [ ] **06.2** (agent) Class notes and loadout rows for any class or spec that lacks them on Naxx.
- [ ] **06.3** (agent) Receipts for every capture at the batch commit; one sampled picture per capture inspected.
- [ ] **06.4** (agent) Batches per configuration group; `raid_batch write`, `check_raid_coverage --inventory --staged`, gate, pair review, push. Record elapsed time per batch.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log

2026-10-22 · Class/loadout path audit · All 34 legal configurations are mapped
to their existing render and class-note paths, with source hashes. Thirty-two
synthetic missing-data projections through `class_view.bosses` retain explicit
Unknown labels for all loadout lines. Hunter's separate Weapons, Trinkets, Pet,
Weaving, Rapid Fire and Refocus paths are inspected separately, without claiming
a new Hunter projection. Paladin, Priest and Shaman healing views already have
sourced healer notes; Druid's healer review is separate, and selecting Balance
HPS does not itself establish healing duty. No new class/rank/talent/duty advice,
production row, visual claim or completion tick is introduced. 06.2 remains
open for the source and actual-capture review described in the audit.

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

2026-10-22 · Category selection and author source review · Optional category
filtering is wired through each boss playbook/acquisition selection. General
rows retain legacy behavior; restricted rows require an explicit legal
class/category/metric combination. Existing class aliases are canonicalized,
without assigning encounter duty. Four normal synthetic acquisition/render
cases cover selected/unknown category and v1/v2. All 84 focused strategy/snapshot
tests pass, plus 44 guidance/work-order/proposal checks and 92 browser checks.
All 54 outputs from 18 v1 archives and the three full Haplina outputs are
byte-identical before/after. `research/category-strategy-compatibility-20261022.json`
records hashes and limits. Production strategy items are still unpopulated.

Author review of all 15 profile groups found an ambiguous Sapphiron instruction:
the third-Icebolt movement tip lacks context for the five-cast air phase. This
is not proof the statements are logically incompatible. The key is now blocked
in the current source ledger, and coordinator revision 2 withdraws that item
from 34 drafts without substituting another trigger. The revised source pin
is applied to all 510 current coordinator orders, which replay successfully.
Previous coordinator bytes remain in Git; the original model orders and trial
receipts are unchanged. `research/guidance-author-source-review-20261022.json`
binds all 50 remaining profiles and records each group's source boundaries.
This is author review, not independent approval. Class/loadout review, content
integration, capture receipts, formal review and completion remain open.

2026-10-22 · Coverage consumer follows category selection · The coverage
content audit now forwards the exact legal cell category to the same strategy
selector as the report path. A restricted Guardian-only three-section test
counts as available for Guardian and remains unavailable to Balance/Feral;
the independent ranking-policy requirement remains unvalidated in every case.
All 41 coverage tests pass. The real Naxx inventory still reports 26
IN_PROGRESS/484 TODO, no problems and no COMPLETE cells. This fixes a consumer
of the optional selector; no production source proposal or acceptance is added.
