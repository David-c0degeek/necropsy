# 04 - Boss Research And Raw Facts

## Goal
For each of the 15 bosses, once for every class: sourced mechanics with verbatim
excerpts, raw discovery of what the logs actually show (removals, presence,
targets, phases), and frozen independent actor and recipient facts for every
registered actor source.

## Integration analysis
To be completed before 04.1. Reuse the MC pattern: `mc-boss-source-review.json`
ledger shape, `fact_freeze.py` specs, removal/presence fact registers, existing
Naxx facts (`naxxramas_facts.yaml`, 15 bosses sourced) and the Naxx golden
fact checks. Do not duplicate existing Naxx fact registers; extend them.

## Boxes
- [ ] **04.1** (agent) Source ledger `naxx-boss-source-review.json`: per boss, verbatim excerpts, retrieval method, conflicts; class/race/faction capability notes per class.
- [ ] **04.2** (agent) Raw discovery per boss via work orders (02): removable effects and who removed them, boss presence and add windows, target sets; verified counts committed as boss mechanics files.
- [ ] **04.3** (agent) Frozen actor facts (and recipient facts for HPS) for every registered Naxx actor source, raw-first, reviewed.
- [ ] **04.4** (agent) Zone rules for Naxx (targets, removals, presence) only where 04.2 evidence supports them, with positive and negative tests.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-21 · 04.1 (first pass) · `tests/golden/raids/naxx-boss-source-review.json`, same shape as `mc-boss-source-review.json` (version, subject, retrieval, sources, open): 15 bosses, 420 verbatim excerpts from the 15 warcraft.wiki.gg Classic pages that `naxxramas_facts.yaml` already cites (URLs asserted equal), each with its page-last-edited line. Limits recorded in the file: the fetch tool caps quotes at 125 characters, so some excerpts are fragments; three pages omitted their longest sentences and Kel'Thuzad came back as a selection; level 70, Wrath, Season and loot lines excluded. Box stays open: capability sources (race, faction and class spell availability) and second fetches for Kel'Thuzad, Heigan, Anub'Rekhan and Gothik are listed under `open`.
2026-10-21 · 04.1 (Codex #18, #19) · Codex AGREE on the ledger as first-pass storage only. Absorbed: per-source `conflicts` with a conservative rule each (Noth Wrath of the Plaguebringer school and tick, where spell 29214's own page also disagrees; Maexxna Web Spray avoidance list vs Vanish and Ice Block; Maexxna `warrior_shield_wall` naming Web Wrap in Web Spray context), the Maexxna `phase_web_wrap` fragment those rules cite, and five more open items (Grobbulus fragment without subject, Heigan diagram-dependent positions, Faerlina and Maexxna multi-class sentences needing per-class capability proof, fragments never supporting categorical advice, conflict keys blocked until resolved). 421 excerpts. 04.1 stays open.
