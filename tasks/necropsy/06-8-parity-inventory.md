# Definitive playbook parity inventory

Inventory agreed by both participants, 2026-10-13 (peer mail 67-69). Reference read-only: D:/Parsing/Results/Playbook/Haplina_Naxx_Definitive_Playbook.html. Its structure and content categories are the minimum; reference-specific conclusions must be regenerated from the selected snapshot and named rules. Nothing below authorizes copying oracle values or confident prose. All gap owners are Claude (analysis/rules/schema) or Codex (presentation/docs). Gaps must resolve before 06.8 closes.

## Evidence and integration

Existing seams: report/analysis_json.py::_entry, _boss, build_document; report/render/view.py::_boss, _cohort, value_of; templates/base.html.j2, report.html.j2, playbook.html.j2, macros.html.j2; assets/report.css, report.js. Extend these, no parallel renderer. Package/publish API and analysis-only rendering remain unchanged.

Paths below are relative to a boss: S=subject; C=overall_cohort[] for the full recorded top-five presentation (cohort[] remains the same-faction comparison unless explicitly expanded); B=benchmarks.baseline; K=benchmarks.ceiling; E=encounter. Evidence objects keep value/level/claim/refs/coverage/note. Cast lengths and formatting may use the current view helpers; new cohort statistics and advice belong in analysis output, never templates. MIN_BASELINE=3 remains; low sample must be explicit. Inferred membership never becomes calculated/confirmed.

Reference DOM audit: 15 boss sections in raid order; every boss has Benchmark context, Loadout plan (Weapons/Trinkets/Pet/Weaving), Execution plan (Opener/Rapid Fire/Refocus), Do not, Raid ask, three gear/cohort disclosures. Every cohort table has 13 columns. Overview includes hero, Global setup, Corrections, Truth model, raid sheet; footer and sidebar retained.

## Global and interaction inventory

| Element | Source or named rule | Owner / gap |
|---|---|---|
| Fixed 285px sidebar, brand, character/zone/faction subtitle | top-level subject/zone; faction from boss evidence | Codex; preserve evidence qualification |
| Filter bosses, 00 Overview, star Truth model, numbered 01-15 links | bosses[] order and names; static truth anchor | Codex; labels, keyboard focus, active link, escaped text |
| Gradient hero, title, explanatory paragraph | subject.name, zone.name, mode, cohort.limitations | Codex |
| Badges: parse-row count, Alliance/Horde count, normalized shot targets, faction-aware weave, WF events, offline | top-level cohort plus C.environment.faction and outputs below | G03 Claude summary; qualify coverage/unknown and never claim all rows observed |
| Global setup: Spec, World buff, Core ranged gear, Armor pattern, Pet, Ammo, Engineering, Renataki, Faction rule | talent-build/darkmoon-faire/trinket/explosives-unused and per-entry environment/hunter facts partially exist | G03/G04/G07 Claude; all nine bullets retained, rules/evidence for each |
| Corrections that matter after faction normalization | K/B membership, C faction/race/WF/melee, B.weave, B.trinkets | G03/G04 Claude; summary must be dataset-derived, not Haplina-specific constants |
| Truth model: What is directly observed; What is deliberately NOT overclaimed | schema evidence contracts, cohort.limitations, rules.ranking_exclusion_rule | Codex; preserve comparator scope, WF non-observation, pet-family uncertainty, projected-shot limits; add empirical ranking/coverage caveats |
| At-a-glance raid sheet: Boss, Your %, Your DPS, Your kill, Overall #1, same-faction comparator inside overall top five, A/H, normalized Auto/Aimed/Multi target, Weave verdict | same sources as boss metrics and context below | Codex plus G01/G04/G05; preserve all nine columns |
| Footer dataset/provenance | snapshot, schema/version, archive hash, mode | Codex; retain offline/no-network notice |
| Boss reviewed checkbox in header; persistence; search; details | snapshot/analysis hash + boss ID keys | Codex; storage failure must not break page; keep per-finding marks as an addition |
| Dark reference palette, gradient, tiles, two-column cards, sticky/bounded tables, full gear cards | reference CSS structural measurements | Codex; add light theme/print, accessible labels, narrow-screen layout without removing content |

## Boss metrics, context, and all cohort columns

| Element | Existing analysis source | Owner / gap |
|---|---|---|
| Eyebrow Boss NN / name, heading, reviewed control | encounter_id, boss, index | Codex |
| Your DPS / Your kill | S.ranking.ranked_dps / S.kill_duration_s | Codex; ranked/raw distinction retained |
| Current % / Your % | user_rankings raw rankPercent, currently not in EntrySection | G01 Claude: report/fight-matched historical percentile, total parses and bracket with provenance; never recompute from top five |
| Overall #1 DPS | C leaderboard_position=1 and ranking.ranked_dps | Codex; unknown if rank1 absent; no assumption first recorded row is #1 |
| Same-faction comparator rank/name/DPS | K.leaderboard_position/player/ranked_dps/membership | Codex; comparator inside recorded sample, not dedicated faction leaderboard |
| Faction mix | C.environment.faction | G05 Claude aggregation/provenance for A/H/unknown counts |
| Current Auto/Aimed/Multi | S.hunter.shots.{auto_shot,aimed_shot,multi_shot}.casts | Codex; complete coverage required for whole-fight counts |
| Normalized shot targets | B.shot_targets.{auto,aimed,multi}; explicit Tauren-fill detail | Codex; fill remains separate and low confidence |
| Pet DPS versus faction median | S.hunter.hunter_pets[].dps, pets_listed; B.medians.pet_dps | Codex; aggregate pet DPS supplied by analysis, no lost listing/absence distinction |
| Benchmark context paragraph | K.membership, B.membership/entries, C faction/race/WF, exclusions | G04/G05 Claude; count/selection rules then Codex wording |
| Table # / Hunter + faction-comparator note | C.leaderboard_position/player, membership versus subject | Codex |
| Faction / Race evidence | C.environment.faction; C.environment.race.race/status/refs | Codex; racial-cast source text + evidence; unknown stays unknown |
| WF procs | C.environment.windfury.procs/status_evidence/extra_attacks | Codex; observed count versus non-observation, not inferred totem absence |
| DPS / Spec | C.ranking.ranked_dps / C.environment.talents | Codex |
| Trinkets | C.hunter.gear.trinkets + C.environment.gear.value names | Codex/G02; item-ID lookup, preserve uncertainty |
| Weapons (ranged/main/offhand) | C.hunter.gear.{ranged,main_hand,off_hand} + environment gear names | Codex/G02; occupied versus unknown slots distinguished |
| Raptor / White | C.hunter.shots.raptor_strike.casts / C.hunter.white_melee_swings | Codex; whole-fight evidence, boss/nonboss added alongside |
| Pet (name/family/abilities) / Pet DPS | C.pets_listed, hunter.pets/hunter_pets.{name,family,family_candidates,abilities,dps} | Codex; family ambiguous/inferred qualification preserved; non-Hunter guardians separate |
| Subject full logged gear disclosure | S.environment.gear.value, slot IDs, item IDs/names/enchant IDs | Codex/G02; all seventeen equipment positions, unknown/empty explicit; extras shirt/tabard allowed |
| Cohort full 17-slot cards and mini-badges | C.environment.gear plus rank/name/faction/talents/DPS/Raptor/White/WF | Codex/G02; colored faction border, unknown neutral, every recorded hunter |

## Advice sentence types: analysis owns decisions, Codex owns wording

| Sentence type | Available evidence / rules | Missing decision/output |
|---|---|---|
| Weapons: ranged set, pure-ranged stat sticks, alternate weave set, other-faction comparison warning | hunter.gear; B.items; B.weave; environment faction/race/WF | G04: slot-specific ranked usage and conditional loadout rule; never prescribe absolute BIS from prevalence |
| Trinkets: preferred/alternative combinations, no-loot fallback, Mark eligibility, Renataki prevalence and optionality | hunter.gear.trinkets/renataki_at_pull; B.trinkets; trinket recommendation | G04/G07: pair prevalence, encounter target-type applicability and conditional alternatives; population correlation not causal benefit |
| Pet: profile, DPS target/comparison, absent/dead/early stop, recall/resend and survival training | pets_listed; hunter_pets family/abilities/dps/activity/deaths; pet-* rules | G04/G07: complete aggregate and boss context; ambiguous abilities never become certain Cat; training suggestion needs sourced named rule |
| Weaving: YES/NO/opportunistic/conditional, number adopting, heavy five+ count, boss/add/trash role, cross-faction contamination warning | B.weave; raptor_roles; race/WF; weave-adoption | G04: graded decision using existing threshold rules; Gothik nonboss weaving kept distinct from boss; never promote 2/5 to majority |
| Opener: actual first sequence/times, proposed sequence, first Aimed delay, pre-cast, reset after specials, transitions | hunter.opener and shot/RF/Refocus casts; gear.renataki_at_pull | G04/G07: early-window analysis, comparator observations, conditional named execution rules; no template computation |
| Rapid Fire: early/hold/useful phase window, subject timing, rank1 timing, faction/overall medians, no-use versus unknown | hunter.rapid_fire; B.medians.first_rapid_fire_s; rapid-fire-unused | G04/G07: timing comparison and encounter windows. Preserve logged subline; reconcile contradictions in reference via evidence |
| Refocus: gear-dependent optionality, consumed-special state, rank1/comparator reset time, reset adoption/median, window too late | hunter.refocus; opener; gear.renataki_at_pull | G04: cohort reset statistics and state-sequence rule; observed reset is distinct from assumed cooldown eligibility |
| Do not: other-faction melee/WF expectation, petless/dead/inactive behavior, late/bad-phase RF, delayed special, invalid item, movement loss, padding comparison, conflicting utility | existing recommendations + race/WF/melee, pet, auto_gap, target integrity, raid utility | G04/G07: structured prevention output; do not invent lost ranged cycles, causal deaths, or exact WF damage attribution |
| Raid ask: no structural gap, positioning/pet safety, remove kite/MC assignment, transition/polarity, teleport/dance/spore/boss-window planning, trash-overlap visibility, route, speedkill | raid_speed; raid_utility; target_integrity; recommendations controllability | G04/G07: encounter context and conditional asks; never promise huge improvement or recommend padding as default |

## All fifteen boss-specific variants inspected

Every row retains all common sections/columns above. These are content categories to regenerate, not oracle conclusions to copy.

| Boss | Additional sentence variants requiring named rule/data |
|---|---|
| 01 Patchwerk | same-faction heavy weave versus pure ranged; nonmandatory Renataki; rank1 racial/WF white-melee attribution limits; no raid-speed gap |
| 02 Grobbulus | faction-dependent weaving; pet death and cloud recall; first Aimed delay; optional reset; stable range |
| 03 Gluth | absent pet, kiting assignment cost, ranged opener and early reset, no RF use |
| 04 Thaddius | opportunistic versus heavy weave; add-to-boss transition/polarity RF hold and reset usefulness |
| 05 Noth | pre-cast suggestion, RF before teleport, early/late reset comparison, minimal phase disruption |
| 06 Heigan | single Raptor versus heavy weaving, absent pet, first Aimed delay, RF timing, dance downtime |
| 07 Loatheb | spore-aligned burst window and assignment, pet DPS, RF timing, movement/Auto safeguards |
| 08 Anub'Rekhan | main-hand prevalence, no pet, early RF/reset and first Aimed, initial range |
| 09 Faerlina | Eye as stat stick without weaving; Mark target eligibility; no-loot trinket alternate; pet stopped early; reset adoption and delayed first Aimed |
| 10 Maexxna | Mark target eligibility; fallback pair; pet DPS; reset adoption and too-late reset/web-window caution |
| 11 Razuvious | pet DPS; acceptable RF window; optional reset; stable range and tank/MC execution |
| 12 Gothik | native/start-trash/foreign ranking scope; target-dense opener/RF; long Aimed gap; add-role weave; pet death; contextual trash-overlap/side assignment (not default padding advice) |
| 13 Four Horsemen | pet inactivity without death, late RF, optional early reset, movement/route planning |
| 14 Sapphiron | same-faction sample2 versus overall sample5; raid-speed ceiling; missing pet; sourced survival-training profile; early RF/reset versus kill duration |
| 15 Kel'Thuzad | defensive-trinket opportunity; pet DPS; boss-phase uptime; observed friendly crowd-control assignment and raid-speed gap |

## Gap register and closure

- G01 Claude: selected user_rankings rankPercent matched by report/fight; total parses/bracket and evidence.
- G02 Claude: read the existing raw leaderboard/user-ranking gear names at analysis time (229 IDs found by peer scan), with provenance wcl-rankings-gear; existing catalog fallback covers only 51 of 73 fixture IDs. Resolve every non-tabard item, reject conflicting labels, and classify zero/missing/cosmetic slots explicitly. Codex joins names by ID and formats all seventeen equipment slots (raw slots 0-17 excluding shirt); shirt/tabard may be additional. Enchant and armor-set names belong to G07.
- G03 Claude: dataset-wide counts/setup/corrections summaries (all nine global bullets), evidence and named rules.
- G04 Claude: structured complete per-boss playbook decisions/output, including every seven dl rows, benchmark context, Do not and Raid ask; conditional rules and cohort statistics. Proposed new rule names require agreement, not silently invented output.
- G05 Claude: explicit overall #1 benchmark always available without --cross-faction; expose evidence-bearing pet totals where needed. Faction mix and existing race/WF/white/shot/pet/opener data are already sufficient: reuse current fields rather than duplicate analysis.
- G06 Claude: preserve empirical and inferred limits: actual WF proc observations versus guessed totem presence; matched swing damage never stated as exact caused damage; ranked/raw/external and target shares remain distinct. Existing evidence sufficient for conservative wording, oracle overclaims need corrected decisions.
- G07 Claude: verified static encounter/item/pet-training knowledge and enchant/set names. Explicit public source, named rule and compatible existing evidence grade. Do not add a new evidence level named rule to the four-level schema. User clarified Ammo: preserve sourced general Doomshot advice with ranged-weapon compatibility, and keep actual logged ammo visibly not recorded because it is absent from this export. Public sources are explicitly requested for every static entry. Unsourced static advice remains an open gap.
- U01 Codex: shared reference layout/style/typography, 15-boss navigation/search, reviewed header controls, dense full tables/cards, every section retained. Report adds analytical drilldowns; playbook adds review workflow without displacing template elements.
- U02 Codex: auth guide, matching CLI wording and docs navigation; completed 07.1-07.3 only, live acceptance pending.

Release gate: every gap has implemented data/rule/output and tests or an explicitly agreed evidence limitation visible in the retained section; no silently dropped advice category. Browser full-fixture desktop/mobile screenshots, every section/column/slot check, keyboard/theme/print/storage-blocked behavior, deterministic package/rerender/escaping checks. Human comparison records still distinguish completed comparison from acceptance of the new implementation.
## Agreed implementation checkpoints

1. Claude: G01/G02/G05 data and schema, including overall #1; preserve raw/oracle bytes and reuse existing ingest/ranking seams.
2. Claude: G04 complete per-boss structured decisions, G06 qualification, benchmark context, Do not and Raid ask.
3. Claude: G03 global summaries/corrections and hero statistics.
4. Claude: G07 sourced encounter/item/pet-training/enchant/set guidance.
5. Codex: all presentation, generated wording, reference appearance and behavioral verification. The auth guide can land with the inventory. Each write-ownership transition uses the pair harness; no concurrent project edits.

Pre-mortem guardrails for new data: schema/database version and cached DB invalidation must include any new ingest table; report/fight percentile matching must reject mismatches/ambiguity; conflicting item names never become a confident name; tables preserve source provenance and the item catalog stays fallback. Extra data is optional or explicitly migrated for old analysis JSON. Statistical sample minima and evidence grades remain unchanged. Exact WF-caused damage is not established by matched candidates. Preserve these limits in new advice.

## Implementation status (2026-10-13)

- G01/G02/G05: implemented selected historical/today percentile with duplicate consistency and provenance; complete name/source/note and enchant labels; optional overall_top/faction_mix/overall_cohort and pet family grades/accounting. Existing rankings raw reused; database format unchanged; older analysis JSON remains renderable.
- G04/G06: implemented playbook-v1 context, weapon sets and trinket pairs, pet plans, role-specific weave, actual opener sequences/first-Aimed timing, cooldown comparisons, Do not and Raid ask. Timing/pet aggregates need three values and retain inferred membership. Inferred matched-WF damage is neither exact caused damage nor a bound. Source-based naxx-execution-v1 guidance remains distinct from observed cast timing; conditions show applies/otherwise/inapplicable/conditional and unknown alternatives stay visible.
- G03: overview-v1 includes all nine setup bullets, badges, every boss's faction correction context and the raid sheet. Armor slots are counted separately from the set ring; 7-piece armor and ring-inclusive set totals remain distinguishable.
- G07: sourced ammo compatibility, creature-type bonus eligibility, encounter timings (including source disagreements), client item/enchant/set/cooldown facts and set modifiers, pet family guides and training profiles. The original Great Stamina10/Claw8/Dash3/Frost Resistance3 profile totals280/300 under cited guide costs; rank4 variant totals325 and is labeled over budget. Guide-derived TP values are not client-verified server costs; actual ammo/training remain unrecorded. No unverified guide value is presented as an observed log fact.
- U01: faithful shared reference default-dark palette/285px sidebar/numbered filter navigation/hero/panels/metric tiles/context strip, seven advice rows, Do not/Raid ask, all thirteen cohort columns, seventeen equipment slots per subject/cohort Hunter, standalone Truth model, global setup/corrections/raid sheet. Extra findings, target shares, raid-speed/evidence and review controls remain alongside. Sources are safe HTTPS links followed only by reader action; no automatic network. Older JSON shows explicit missing-enrichment notes.
- U02: auth guide authored and peer accuracy-reviewed; local documentation links checked and source-link/percentile semantics documented.
- Verification: initial full suite727 passed,4 known xfailed; round-1 peer independently reran it and confirmed the visual frame and content inventory. Review requested fixes for known cooldown non-use and source-link precision. After data fixes the peer ran728 tests,4 known xfailed. Codex verified all five returned data-file fingerprints and ran62 focused data/view/render/browser checks after the presentation fixes; ruff, format and mypy pass. Rank-one known non-use now says "not cast", while unavailable casts remain unknown; low-sample timing reasons count known non-users. Pet-profile citations appear once per section with specific labels, and guidance links follow its declared dependencies. Round-2 peer review pending. Actual full15boss pages/package and desktop/mobile screenshots: ignored workspace/parity-full.
- Pair recovery: the last intended peer write window was not accepted due to a CLI flag error; peer disclosed its16 data paths. Codex verified fingerprints and retained existing ownership, withdrew the pending offer, and reviewed/integrated the intended edits. Future writes require a successful guard; no ownership ambiguity remains.

Evidence limits are retained content, not replacements for sections. Subject06.8 stays open until independent peer review confirms both the inventory and actual generated pages.
