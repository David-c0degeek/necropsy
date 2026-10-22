# 04 - Boss Research And Raw Facts

## Goal
For each of the 15 bosses, once for every class: sourced mechanics with verbatim
excerpts, raw discovery of what the logs actually show (removals, presence,
targets, phases), and frozen independent actor and recipient facts for every
registered actor source.

## Integration analysis
Reuse the MC source-ledger shape, `fact_freeze.py` specs, removal/presence fact
registers, existing Naxx facts (`naxxramas_facts.yaml`, 15 bosses sourced) and
the Naxx golden fact checks. Do not duplicate existing Naxx fact registers.
The capability catalog is pinned from the boss ledger and linked by source IDs;
these are coordinator research references, not additional allowed draft support
keys. Existing `guidance_lint` deliberately does not resolve them. Each future
guidance item still needs class/faction applicability, its actual citation and
claim review; raw removal/control policies need independently observed identities.
The completed guidance trial retains its original input revision in Git; never
update its old order hashes or receipts to fit later source research.

## Boxes
- [ ] **04.1** (agent) Source ledger `naxx-boss-source-review.json`: per boss, verbatim excerpts, retrieval method, conflicts; class/race/faction capability notes per class.
- [ ] **04.2** (agent) Raw discovery per boss via work orders (02): removable effects and who removed them, boss presence and add windows, target sets; verified counts committed as boss mechanics files.
- [ ] **04.3** (agent) Frozen actor facts (and recipient facts for HPS) for every registered Naxx actor source, raw-first, reviewed.
- [ ] **04.4** (agent) Zone rules for Naxx (targets, removals, presence) only where 04.2 evidence supports them, with positive and negative tests.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-22 · 04.1 continued capability review · Catalog expanded from 25 to 42 sources, separating Druid and Shaman Nature's Swiftness, talent-only capabilities, Druid/Priest healing spells, defensive/stealth abilities, Mage control and Classic Warlock channels. The mixed Maexxna `druid_priest_heals` fragment is explicitly blocked: Regrowth cannot be attributed to Priests. Positive class attribution does not prove an actual build, immunity, assigned duty or opportunity. `research/edited-source-timing-audit.json` compares the three edited source pages with the frozen facts: Faerlina needs a Nature-school qualifier before a future content revision; Maexxna timings and Razuvious guide interval/line-of-sight statements remain guide descriptions. No production text changed, preserving the v1 compatibility baseline. Full omitted passages, diagrams, race exclusivity and conflicts remain open.

2026-10-21 · 04.1 (first pass) · `tests/golden/raids/naxx-boss-source-review.json`, same shape as `mc-boss-source-review.json` (version, subject, retrieval, sources, open): 15 bosses, 420 verbatim excerpts from the 15 warcraft.wiki.gg Classic pages that `naxxramas_facts.yaml` already cites (URLs asserted equal), each with its page-last-edited line. Limits recorded in the file: the fetch tool caps quotes at 125 characters, so some excerpts are fragments; three pages omitted their longest sentences and Kel'Thuzad came back as a selection; level 70, Wrath, Season and loot lines excluded. Box stays open: capability sources (race, faction and class spell availability) and second fetches for Kel'Thuzad, Heigan, Anub'Rekhan and Gothik are listed under `open`.
2026-10-21 · 04.1 (Codex #18, #19) · Codex AGREE on the ledger as first-pass storage only. Absorbed: per-source `conflicts` with a conservative rule each (Noth Wrath of the Plaguebringer school and tick, where spell 29214's own page also disagrees; Maexxna Web Spray avoidance list vs Vanish and Ice Block; Maexxna `warrior_shield_wall` naming Web Wrap in Web Spray context), the Maexxna `phase_web_wrap` fragment those rules cite, and five more open items (Grobbulus fragment without subject, Heigan diagram-dependent positions, Faerlina and Maexxna multi-class sentences needing per-class capability proof, fragments never supporting categorical advice, conflict keys blocked until resolved). 421 excerpts. 04.1 stays open.
2026-10-21 · 04.1 follow-up · Added `tests/golden/raids/naxx-capability-source-review.json`: 19 primary tooltip/database/official sources with short exact excerpts, class-ID namespace, rank/level and explicit limits. The boss ledger pins it and references it without enabling capability support keys in the existing linter. Captured Paladin Cleanse, Shaman Cure Poison, poison-totem cast 8166/effect 8168, Mage/Druid curse removal, Druid Abolish Poison, Priest Shackle/Mind Control/Fear Ward/Dispel Magic, Hunter Tranquilizing Shot/Aspect of the Wild and Paladin/Shaman resistance buffs. Official original-Classic faction restrictions and a positive Dwarf Fear Ward quest source are separate. Earlier scratchpad ID 8170 is Disease Cleansing Totem, not poison. No exhaustive absence matrix, racial exclusivity, raw ownership, measured opportunity or player loadout is inferred.
2026-10-21 · Targeted cached page follow-up · Recovered Grobbulus tip subjects (rendered image/link labels retained) and Anub'Rekhan Impale targeting/falling fragments. Added source conflicts for Gothik Harvest Soul cadence (15 versus about 20 seconds) and Kel'Thuzad Frost Blast damage (104% versus 130%); both conflicting keys are excluded by existing `_keys` handling. Full omitted add/mechanic passages, Heigan diagram context, further class spells and independent resolution of conflicts remain open. Direct wiki.gg and Blizzard opens returned HTTP 403, Wowhead returned a robot challenge; methods honestly record expanded cached search text where used. No WCL request, analyzer/rule change or completion claim.

Verification: the 19-source catalog hash, all capability references and WCL class IDs match; conflict keys remain excluded, and capability refs do not become allowed support keys. All 27 guidance tests pass. Full checkpoint gate follows commit with `NECROPSY_GATE_WORKERS=8` and eight fast-suite workers; log `workspace/codex-naxx/offline-source-full-gate.log`. Source research changes no analyzer/rule/render behavior.

2026-10-21 · Continued offline capability review · Catalog now has 25 sources: added Warrior Demoralizing Shout, Paladin Consecration (explicit Classic talent boundary), Priest Cure/Abolish Disease and Shaman Cure Disease/Disease Cleansing Totem. Heigan references the disease capabilities without claiming observed removals. Faerlina `strat_cleansers` and Maexxna `warrior_taunt` are now explicitly excluded by conflicts, closing the gap between prose warnings and usable support keys. Neither mixed-class sentence may be copied into guidance; separate class attribution and talent applicability remain required. No production rule or content item changed.
2026-10-21 · 04.3 pilot, not registration · Existing v1 Sapphiron Restoration archive, report `arYtVP9kgnjBJp7K`, fight 48, Druid actor 22 Haplina: `fact_freeze` actor-stream query found six spell-2782 cast times at 37202, 38720, 112566, 114135, 131290 and 174485 ms from the fight start (duration 174912 ms). A separate standard-library ZIP/event Counter enumeration reproduced all six timestamps and raw locators without the fact-freeze event parser or analyzer. SOURCE and TARGET each contain the six casts; max multiplicity gives six, not twelve. `research/sapphiron-actor-cast-pilot.json` retains raw events, locators, archive/tool hashes, interpreter and limits. A cast is not a successful removal or a removed-debuff identity. No actor-source registration, new frozen-fact register, ranking policy or COMPLETE cell is claimed; full eligibility and fact review remain open.
2026-10-21 · 04.2 positive removal pilot · Same selected actor/fight has six explicit `dispel` rows, separately from its six cast rows: `abilityGameID=2782`, `extraAbilityGameID=28542`, `isBuff=false`, recipients 8, 41, 39, 11, 27 and 34. Exact integer IDs bind to the report catalog and selected friendly-player list. SOURCE and TARGET each contain the six rows; maximum-multiplicity union remains six. Independent direct ZIP enumeration and the separate scanner parser agree on every raw row. `research/sapphiron-actor-dispel-pilot.json` retains raw rows, all locators/page hashes, query, tool/interpreter provenance and Classic Life Drain name/Curse source. These are positive personal dispel observations only. No encounter-wide absence/completeness, application-to-removal response time, assignment, missed opportunity, grade or completion is inferred; cast/dispel rows are not paired by nearest timestamp. Both 04.2 and 04.3 remain open.

2026-10-22 · Source follow-up and positive raw evidence ·
`research/boss-source-followup-20261022.json` recovers authored Classic guide
context for Anub'Rekhan, Heigan, Gothik and Kel'Thuzad. It retains retrieval,
short quotations and limits separately from the frozen source ledger. Heigan's
diagram, Gothik cadence and Kel'Thuzad conflicting damage claims remain open;
no blocked support key is enabled.

`research/journal-positive-observations.json` independently binds retained
successful request data to report revision, fight bounds and numeric NPC
catalog identities. The fixed journal archive contains 191 successful requests
and 623798 rows across responses, including overlap; these are not unique raid
events. Maximum raw multiplicity yields 8276 positive NPC-source occurrences
across nine selected fight contexts. Four Horsemen source identities/marks,
Thaddius Polarity Shift, Loatheb and Gothik casts and Kel'Thuzad casts are
positive observations only. All scopes remain incomplete. Upstream spell names
include reused labels, so names do not override numeric identities or certify
Classic mechanics. Kel'Thuzad boss-source events near the recorded fight start
also prevent blindly applying a full-pull guide timer. No absence, phase,
spawn-lifetime, assignment, opportunity, grading policy, actor registration or
certified v2 capture follows from this unfinished journal. 04.1–04.4 stay open.

2026-10-22 · Priest racial applicability follow-up · Direct authored Classic
guide body now supplies the complete five-race table and an explicit statement
that only Desperate Prayer is shared. This supports Dwarf-only Fear Ward for
the guide's Classic Era ruleset, closing that specific source gap beyond the
older positive Dwarf quest. `research/priest-racial-source-followup-20261022.json`
retains the short quote, table, derivation and variant limits. It does not prove
any captured player knew the spell or had an opportunity. No original source
pin, trial, rule, capability support key or completion tick changes.

2026-10-22 · Sapphiron movement ambiguity · The retained ability excerpt says
five Icebolts per air phase, while a separate tip prescribes moving after the
third. A direct authored Classic guide also describes five. Count alone does
not establish a safe movement trigger or explain the remaining casts; the two
statements are not declared logically incompatible. Added an explicit source
conflict for `tip_iceblock_timing` with a no-replacement-by-inference rule.
Current coordinator drafts withdraw the prescription; original model trials
and their historical pins stay unchanged. The author review binds the new
ledger/current draft revision. No raw movement or observed timing is inferred.

2026-10-22 · Portable positive actor facts · The existing independent
`fact_freeze.py` now supports an opt-in `dispels` query. It reuses the bound
All or actor stream and maximum-multiplicity merge, retains explicit removed
ability/recipient/flag/instance fields and refuses malformed or ambiguous
bindings. It neither pairs casts nor infers an aura lifetime, friendliness,
response time, assignment or opportunity. Seventy tests pass, including 15
new multiplicity, scope, missing/type-alias and catalog-binding cases.

`research/fact-specs/sapphiron-druid-actor.spec.json` freezes the prior personal
Sapphiron pilot into `research/sapphiron-druid-actor-facts.json`: six casts and
six explicit 2782/28542 dispel rows. Every value and locator matches the earlier
independently committed pilot. Fresh-checkout `fact_freeze check` reports zero
differences. `research/sapphiron-actor-freeze-review-20261022.json` binds the
inputs and limitations. The fact file remains a draft; no cell registration,
full encounter certificate or 04 completion is claimed.

2026-10-22 · Registered actor dispel inventory · All 26 current Naxx actor
references pass the strict actor-source checker. Separate stdlib ZIP/Counter
enumeration finds positive source-actor dispel rows only in the Sapphiron case
already frozen above; all six values and raw witnesses match. The other 25
selected actor streams have no positive rows for this query; they are not
frozen as zero opportunities, missing capabilities or raid-wide absence.
`research/registered-actor-dispel-inventory-20261022.json` retains source/page
pins, exact scope, result classifications and the one portable fact reference.
This exhausts this bounded query over registered sources, not all comparison
actors or all mechanic families. Further complete encounter discovery and
actor/recipient fact coverage remain open.

2026-10-22 · Exact capability-ID cast inventory · All 26 registered actor
references were separately checked against the 42-source class catalog's
exact spell IDs. Two contexts have positive matches: one Druid 2893 cast on
Maexxna at 36974 ms, and six 2782 casts plus one 17116 cast at 96968 ms on
Sapphiron. Independent raw maximum-multiplicity enumeration reproduces every
named time and witness locator. Two portable specs/fact files in
`research/actor-cast-facts-20261022/` replay with zero differences; the inventory
binds source/page/tool/catalog hashes. The other 24 selections have no positive
match to these exact IDs, which are not exhaustive rank families. No zero-use,
missing-capability, talent-build, removal-success, cooldown or opportunity
claim is inferred. These are drafts, not registrations or encounter proof.

2026-10-22 · Positive personal debuff transitions · Independent raw
ZIP/JSON/Counter enumeration of all 26 strictly eligible registered actor
references found 120 explicit actor-target debuff transitions in 14 contexts.
Fourteen portable specs/fact files in `research/actor-debuff-facts-20261022/`
match the complete independently enumerated multiset and every retained raw
locator; each strict replay reports zero differences. The inventory pins the
coverage register, source/page/tool digests and observed numeric IDs. IDs are
discovered from raw rows, without using analyzer/rule mechanic assumptions.

These include stack and refresh observations where explicitly present, without
pairing them into aura lifetimes. They may include player-caused debuffs;
neither their presence nor an API name attributes a mechanic to the boss.
The 12 empty selections are not absence or zero opportunity. No dispeller,
source ownership, phase, uptime, assignment, opportunity or grade is inferred.
`research/registered-actor-debuff-inventory-20261022.json` records the precise
scope and limits. The files remain drafts, with no cell/source registration,
rule activation, encounter-All certificate or completion tick.

2026-10-22 · Targeted source/raw conflict follow-up ·
`research/boss-source-mitigation-followup-20261022.json` retains an independently
authored Classic Maexxna instruction explicitly naming Shield Wall for enraged
Web Spray. It supplies a conditional warrior-tank replacement candidate; the
original Web Wrap key remains blocked and unchanged. An inspected independent
Heigan image depicts four floor divisions, but is not the missing red-square
wiki diagram and supplies no observed path. The third-party image stays outside
Git. Noth 29214's Classic page itself repeats the summary/effect-field conflict.

`research/journal-conflict-followup-20261022.json` checks the newer 693-request
journal without API calls. Twelve Noth/Gothik/Kel'Thuzad contexts supply 5866
positive NPC-source occurrences. Four metadata answers from other raids are
explicitly excluded; the old scanner's all-Naxx assertion failed before output,
and that failed log is retained. One positive Gothik 28679 cast pair is 19445 ms
apart, which does not establish a fixed cadence or complete phase. Five
Kel'Thuzad contexts distinguish 27808 cast/aura rows from 29879 damage; normalized
health/absorbed rows do not settle the 104%/130% disagreement. No positive Noth
29214 row in six surveyed contexts is not absence. All source keys remain
blocked; no certified scope, actor registration, grading rule or completed cell.
