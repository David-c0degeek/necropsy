# Classic Era classes, builds, roles and Warcraft Logs

Research date: 2026-10-16. Scope: Classic Era / `vanilla.warcraftlogs.com`, Naxxramas zone 2006. This is research and a proposed model, not a claim that the redesign is implemented. Production behavior was not changed.

Subsequent implementation: [ADR0012](decisions/0012-game-build-and-wcl-category.md)
and [class selection](class-analysis.md) describe the delivered behavior. This
document retains the research-time findings and proposed model for provenance.

**Finding:** the game has 27 talent trees across nine classes, while WCL currently advertises 19 ranking categories. Its category display names, API slugs, talent distributions and encounter duties are different dimensions. Necropsy's current `spec` selector exposes the API categories, which prevents users from expressing all game specializations and makes labels such as Rogue Assassination misleading.

## Evidence and boundaries

Evidence grades follow the repository review rubric: **Confirmed** for direct source/API/code observations, **Strong inference** for conclusions supported by several observations, and **Open question / Unable to verify** for missing external rules. Historical statements are dated even when their original publication is confirmed.

- **Confirmed:** fresh authenticated, read-only requests through Necropsy's existing WCL client returned all class/category names, IDs and slugs, ranking schema and partitions. Twenty-eight first-page Patchwerk queries exercised all 19 advertised categories and nine additional talent-tree slugs, with partition explicitly set to 1. All 19 advertised categories returned rows; the other nine returned a nested JSON error: `Invalid class and spec specified.` Each populated page contained 100 rows except Paladin Tank, which contained 88. This is a bounded sample, not an exhaustive census.
- **Confirmed:** a fresh public report supplied 40 combatant events; their three numeric talent totals matched all 40 corresponding playerDetails records. This establishes data availability for that report, not universal coverage or the full allocation of individual talents.
- **Confirmed:** the sampled known character's `gameData` returned `{"error":"This game does not support cached game data."}`. A preceding name/realm lookup returned no character. Neither result proves race metadata is universally unavailable.
- **Confirmed:** independent inspection traced the selectors, acquisition, normalization, snapshot validation and reports. Focused existing tests passed: **147 passed**. Tests establish current contracts, not equivalence to WCL's unpublished classification rules.

Sanitized machine-readable observations are in [the research receipt](assets/class-taxonomy-2026-10-16.json). Full queries, timestamped responses, the probe script and verifier notes remain in ignored `workspace/taxonomy-research-2026-10-16/`. No authentication material is included. Raw public actor identities are omitted from the committed receipt.

## The game's catalog and WCL's catalog

Blizzard documents three talent trees per class and permits distributing points across them. A tree name therefore does not establish an exclusive specialization or encounter assignment. The names below form the proposed game catalog; aliases such as Beastmastery, BM, Marksman and MM can resolve to canonical names without becoming API filter strings. [Blizzard's Classic primer](https://news.blizzard.com/en-us/article/23090134/wow-classic-primer-for-new-players)

The WCL columns below are **Confirmed** by fresh `gameData.classes { id name slug specs { id name slug } }` responses. IDs are WCL identifiers, scoped by game/class; they must not become unqualified game identifiers. Notice that Priest Healer has ID 2, not 1, and Hunter's only category has ID 2. Do not manufacture missing categories from numeric gaps.

| Class (WCL ID) | Game talent trees | WCL category display name → slug (category ID) |
|---|---|---|
| Druid (2) | Balance, Feral Combat, Restoration | Balance → `Balance` (1); Feral → `Feral` (2); Tank → `Guardian` (3); Healer → `Restoration` (4) |
| Hunter (3) | Beast Mastery, Marksmanship, Survival | Marksmanship → `Marksmanship` (2) |
| Mage (4) | Arcane, Fire, Frost | Fire → `Fire` (2); Frost → `Frost` (3) |
| Paladin (6) | Holy, Protection, Retribution | Healer → `Holy` (1); Tank → `Protection` (2); DPS → `Retribution` (3) |
| Priest (7) | Discipline, Holy, Shadow | Healer → `Holy` (2); DPS → `Shadow` (3) |
| Rogue (8) | Assassination, Combat, Subtlety | DPS → `Assassination` (1) |
| Shaman (9) | Elemental, Enhancement, Restoration | Elemental → `Elemental` (1); Enhancement → `Enhancement` (2); Healer → `Restoration` (3) |
| Warlock (10) | Affliction, Demonology, Destruction | DPS → `Destruction` (3) |
| Warrior (11) | Arms, Fury, Protection | DPS → `Fury` (2); Tank → `Protection` (3) |

The [public Vanilla statistics page](https://vanilla.warcraftlogs.com/zone/statistics/2006) independently displays the role-oriented labels. The API supplies their slugs directly; no label-to-slug guesswork or HTML scraping is necessary. `Encounter.characterRankings.specName` expects the slug. [WCL encounter API](https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/encounter.doc.html)

The nine non-advertised slugs tested were Hunter `BeastMastery`/`Survival`, Mage `Arcane`, Priest `Discipline`, Rogue `Combat`/`Subtlety`, Warlock `Affliction`/`Demonology`, and Warrior `Arms`. All nine were explicitly rejected as invalid class/spec combinations by the tested endpoint. They were not valid zero-row leaderboards. Together with their absence from the live Vanilla catalog, this establishes that Necropsy should not currently offer them as independent Vanilla ranking pools. It should still allow their game talent identities. This result is scoped to the tested site/API, not other game families or future versions.

### Direct examples from one live fight

These are **Confirmed** API observations, with player identities omitted. Ordered numbers are the report's three talent-tree totals; category is reported independently by WCL.

| Class | Talent totals | WCL category slug | Consequence |
|---|---|---|---|
| Warrior | 0/33/18 | `Protection` | A Fury-heavy hybrid appears in the Tank category. |
| Warrior | 2/32/17 | `Protection` | Tank category does not mean most points are in Protection. |
| Warrior | 17/34/0 | `Fury` | WCL's DPS category happens to share a talent-tree name. |
| Rogue | 17/34/0 | `Assassination` | A Combat-heavy build appears in the generic Rogue DPS pool. |
| Rogue | 19/32/0 | `Assassination` | This is not an isolated tree distribution. |
| Warlock | 9/21/21 | `Destruction` | Tied/hybrid distributions cannot be reduced by a unique-largest-tree rule. |
| Hunter | 20/31/0 | `Marksmanship` | The category and recorded build are separate evidence, even where names align. |

These examples establish the mismatch directly. They do not validate the player's assigned duty, a specific individual talent, or a universal classification algorithm.

## What WCL's classification rules actually establish

### Historical primary evidence

WCL's author described Classic's initial approach in August 2019: identify healing from healing versus damage and broadly group class DPS, while tank classification needed separate heuristics. This is historical design discussion, not a current specification. [Kihra's original discussion](https://forums.combatlogforums.com/t/classic-wow-spec-detection/8369)

For Warrior/Druid tank classification, the historical record shows changing rules:

- January 2020: Kihra described melee-hit percentages and the possibility of encounter-specific thresholds. [January/February discussion](https://forums.combatlogforums.com/t/logs-are-ranking-me-as-a-fury-when-im-tanking/8459?page=4)
- March 2–3, 2020: a stance/form-duration approach was deployed with a 40% threshold. Kihra subsequently said the hit heuristic had been removed. [Deployment discussion](https://forums.combatlogforums.com/t/logs-are-ranking-me-as-a-fury-when-im-tanking/8459?page=5)
- March 18, 2020: Kihra stated a 35% Defensive Stance rule and explained that stance-restricted abilities could establish an otherwise unobserved stance. A Taunt cast supplied stance evidence; the classifier then evaluated uptime. [Razorgore explanation](https://forums.combatlogforums.com/t/classic-razorgore-tank-mis-logs-as-fury/9496)

**Open question:** current Vanilla thresholds, encounter exceptions, precedence and default behavior are not established by those old posts. In particular, neither 35% nor 40% is approved here as today's global rule. Off-tanking, tank swaps and stance visibility are reasons WCL's label can differ from actual duty.

For Mage, Kihra explained in October 2020 that Master of Elements was a principal Fire indicator and that ranked boss classification must be deterministic using that individual fight. A character could therefore receive different categories without changing talents. This is confirmed historical explanation; the current complete Fire/Frost decision tree remains unverified. [Mage classification discussion](https://forums.combatlogforums.com/t/bug-classic-wow-my-mage-is-misclassified-as-frost/10573)

WCL's later retrospective explicitly characterizes Vanilla Era detection as role-oriented, with Mage separation historically motivated by Ignite. The article concerns SoD changes; only its explanation of the Vanilla approach is relevant here. SoD and TBC thresholds must not be imported into Era. [WCL retrospective](https://www.archon.gg/classic-sod/articles/news/sod-phase-1-reflections-and-lessons-learned)

### Safe boundary for Necropsy

Preserve **WCL's observed classification** and **Necropsy's inferred encounter duty** independently. A disagreement is information, not a reason to overwrite either value. Record a declared assignment separately again. WCL's ranking pool remains authoritative for reproducing that leaderboard, while Necropsy's evidence determines whether a personal gameplay comparison is applicable.

Do not reproduce WCL's detection algorithm from a few examples. Today's API result can be used without claiming to know how WCL arrived at it. Exact algorithm parity requires a versioned primary rule or explicit verification across boundary cases.

## Ranking scope is part of the definition

WCL distinguishes a parse from a player's best ranking, rankings from a two-week parse comparison, historical from today's percentiles, and overall from bracket-specific results. Partitions preserve separate competitive contexts. A percentile is therefore not meaningful without its population and time basis. The ranking guide also notes that new historical scores can change before daily lock-in. [WCL ranking guide](https://vanilla.warcraftlogs.com/help/ranks)

Live schema confirms that character `encounterRankings`/`zoneRankings` expose `role`, `specName`, `metric`, `compare`, `timeframe` and bracket/partition options. In contrast, `Encounter.characterRankings` has class/spec/metric filters but **no dedicated `role` argument**. These are different API surfaces. Use the former's role enum only where that field supports it; do not add it to the leaderboard query. Advanced filters need their own evidence. [Character API](https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/character.doc.html), [Encounter API](https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/encounter.doc.html)

The live Naxxramas partition list includes S0, S0 Without World Buffs, Season of Mastery phases, and Hardcore variants. Hostname/zone alone do not identify the competitive rules. Keep site, game, zone, partition, encounter, difficulty, metric, category and any extra filters with the query and saved result. Keep faction/region scope explicit too.

Tank category plus DPS metric means damage ranking within that tank category; it does not measure tank quality, survivability or threat. HPS is throughput under a particular assignment/damage environment, not an overall healing-quality score. Necropsy already states these limitations in [shared combat analysis](../src/necropsy/analysis/classes/classic_era/combat.py).

### Saved ranking score versus reconstructed event throughput

Mage provides a concrete reason to retain both. WCL's author confirmed in 2021 that Ignite sharing required Fire critical strikes and deployed per-target distribution. That historical policy means credited ranking damage can differ from actor-owned raw damage. The exact current distribution formula is not verified by this research. [Ignite explanation and change](https://forums.combatlogforums.com/t/ignite-distribution-on-bosses-with-adds-gluth-in-particular/11194)

Do not recompute a WCL ranking from actor-only sums and silently replace it. Keep `ranking.category_score` and its metric/source separate from event DPS/HPS, pets, exclusions and any credited attribution. Existing [ranking metadata](../src/necropsy/report/rankings.py) and [shared report output](../src/necropsy/report/combat.py) already provide this separation; extend it.

## Talent evidence: inspect the source, not the field name

**Confirmed:** sampled leaderboard rows with `includeCombatantInfo:true` returned seven `talents` entries whose IDs were zero and names were Unknown Ability. They are not a valid three-tree distribution and must not become `0/0/0/0/0/0/0` or a known specialization.

**Confirmed:** the fresh report instead returned:

- Combatant events: three entries with point totals in `id`, e.g. 20/31/0.
- Fight-scoped playerDetails: the same three totals in `combatantInfo.talents[*].guid`.
- Misleading decorated names/icons on those point totals, e.g. a total of 31 displayed with an unrelated spell name. These strings do not identify the talents actually selected.

All 40 actors' point triples matched between the two report sources. The seven populated existing class fixtures also contain three-entry playerDetails talent arrays; the budget-only Holy Priest fixture supplies no such evidence. Availability must still be graded per actor and fight.

Existing [`environment.talents()`](../src/necropsy/analysis/generic/environment.py) combines actor/fight-scoped evidence and returns unknown on conflicts. The normalizer's [`_talent_points()`](../src/necropsy/normalize/ingest.py) is looser: it accepts arbitrary nonempty integer-ID lists. A future contract should validate length, integer types excluding booleans, ranges, total points, tree order and source semantics at the boundary. This is hardening, not evidence that the observed leaderboard placeholders currently enter combatant normalization.

A three-number distribution is not a full allocation. A primary-tree label may be derived under an explicit rule when the maximum is unique; ties must remain mixed/unknown. Preserve raw totals and hybrid descriptions. A dominant tree alone must never determine DPS/Tank/Healer duty or a guaranteed WCL category.

## Race, faction and valid combinations

Blizzard's Classic primer supplies the game-valid race/class matrix below. This validates possibilities; it is not evidence of an individual actor's race. [Blizzard source](https://news.blizzard.com/en-us/article/23090134/wow-classic-primer-for-new-players)

| Faction | Race | Valid classes |
|---|---|---|
| Alliance | Dwarf | Hunter, Paladin, Priest, Rogue, Warrior |
| Alliance | Gnome | Mage, Rogue, Warlock, Warrior |
| Alliance | Human | Mage, Paladin, Priest, Rogue, Warlock, Warrior |
| Alliance | Night Elf | Druid, Hunter, Priest, Rogue, Warrior |
| Horde | Orc | Hunter, Rogue, Shaman, Warlock, Warrior |
| Horde | Tauren | Druid, Hunter, Shaman, Warrior |
| Horde | Troll | Hunter, Mage, Priest, Rogue, Shaman, Warrior |
| Horde | Undead | Mage, Priest, Rogue, Warlock, Warrior |

**Confirmed implementation:** [`environment.race()`](../src/necropsy/analysis/generic/environment.py) requires the actor's own racial cast in that fight and keeps missing/conflicting evidence unknown. [`racials.yaml`](../src/necropsy/rules/classic_era/racials.yaml) is an evidence-spell catalog, not the matrix above. Faction has separate direct and inferred evidence paths.

Live schema inspection found no `GameRace` type, no race field in `ReportActor`, and no races field in `GameData`. Together with the sampled cached-game-data error, this leaves no verified dedicated race lookup in the inspected API paths. This is **Unable to verify** for a broader API source, not proof that no JSON response or future endpoint can carry race.

An Orc observation is compatible only with its valid faction/classes. A Druid known to be Alliance narrows the valid race to Night Elf, but that is a constraint-derived conclusion, not an observed racial cast. If implemented, retain the derivation and its ruleset; do not silently promote it to observed. User declarations also need their own provenance. Contradictions should remain visible.

## Intent versus implementation

Current intent comes from [class analysis](class-analysis.md), [ADR0005](decisions/0005-class-and-encounter-duties.md), [ADR0006](decisions/0006-shared-class-combat-evidence.md) and the user's clarified requirement in this research. Future catalog requirements are not scored as missing shipped features.

| Capability / intent classification | Actual wired behavior | Status / confidence | Evidence |
|---|---|---|---|
| All nine classes, verified WCL pools — documented-current | Catalog/policy routes through acquisition into shared or class-specific reports | Operational-with-limitations / Confirmed | `analysis/class_catalog.py`; `analysis/roles.py`; `wcl/cohort.py`; `report/combat.py` |
| Separate category, build and encounter duty — documented-current | Separate analysis evidence exists, but selection/metadata terminology still conflates dimensions | Partially-implemented / Confirmed | `CombatAnalysis`; `CharacterContext.ranking_category`; `CohortKey.role`; desktop selector |
| Observed duty qualifies comparisons — documented-current | Shared reports require exact inferred duty; Druid qualifies its comparison key separately | Operational-with-limitations / Confirmed | `report/combat.py:110`; `report/druid.py:419` |
| Talent provenance and unknowns — documented-current | Fight-scoped totals and conflicts preserved; shared build-match flag mishandles two unknowns | Operational-with-limitations / Confirmed | `environment.py:190`; `report/combat.py:80`; `report/druid.py:148` |
| Race evidence — documented-current | Own racial casts; missing/conflicting observations stay unknown | Operational-with-limitations / Confirmed | `environment.py:160`; `racials.yaml` |
| Full game specialization and race/class catalogs — planned/future | Current selector supplies WCL categories; no distinct game catalog in the inspected flow | Planned-only / Confirmed | `tui/service.py:269`; `desktop/engine.py:178`; `desktop/src/App.tsx:607` |
| Reproduce today's exact WCL classifier — no current implementation commitment | Available historical explanations do not establish full current rules | Impossible-to-verify / Open question | Historical sources above; current metadata provides categories, not algorithms |

### Findings, ordered by severity

| ID | Severity / gap type | Capability classification / confidence | Finding and minimal response |
|---|---|---|---|
| T-1 | Medium / Partial | documented-current / Confirmed | Category/build/duty separation does not extend consistently to user-facing terminology: `selected_spec()` resolves directly into WCL categories; desktop calls them specs. Clarify current category labels. For the separately requested future game-spec selector, separate intent from category routing before exposing extra trees; do not append unsupported slugs to `CATEGORIES`. Evidence: `roles.py:43`, `tui/service.py:269`, `desktop/engine.py:178`, `App.tsx:607`. |
| T-2 | Medium / Incorrect | documented-current / Confirmed | Acquisition labels role `enforced`, while the leaderboard query enforces class/category/metric and row validation checks class/spec/hardMode, not observed duty. Describe it as category policy and retain event qualification separately. This is not an absence of downstream duty checks. Evidence: `wcl/cohort.py:67`, `:182`, `:413`; `report/combat.py:110`. |
| T-3 | Medium / Incorrect | documented-current / Confirmed | Shared `build_matches` compares raw optional values: unknown equals unknown and becomes true. Use three-state semantics, following Druid's existing implementation. Evidence: `report/combat.py:80`; `report/druid.py:148`. |

The new game/race catalogs are requested future work, not retrospective defects against the earlier category-only contract. Current duty heuristics are explicitly conservative Necropsy rules, not claims of WCL parity. No Critical or High shipped defect is established in this scoped review; changing the meaning of archived `spec` would introduce a substantial compatibility risk.

## Proposed model and implementation guardrails

Extend the existing acquisition/normalization/report pipeline. Do not add another WCL client, credential path or analysis pipeline.

1. **Game identity:** game/ruleset, canonical class key, race evidence and faction evidence. Catalog validity is separate from observed identity. WCL class/category IDs stay namespaced.
2. **Build evidence:** encounter-scoped three tree totals; optional verified full allocation; derived primary tree/hybrid label; separate user-declared preference. The label's derivation must be inspectable.
3. **WCL classification:** site/ruleset, class/category IDs, API slug and display name, source report/fight, query metric and partition. Store the actual returned category, not one inferred from tree totals.
4. **Duty and assignment:** inferred DPS/Tank/Healer/mixed/unknown with confidence and supporting events; declared assignment and reason separately. Do not encode a Warrior's mutable duty as its class identity.
5. **Comparison request:** intended build/playstyle, eligible WCL pools and actual acquisition scope. Game tree → WCL pool is sometimes broad or one-to-many, not always a function. Fury-heavy Warrior tanking, Arcane/Frost hybrids, and healing hybrids must remain representable.
6. **Comparison result:** distinguish WCL category leader, event-qualified role comparison and locally build-qualified subset. “Best Combat Rogue” requires sufficient verified build evidence and search coverage. Filtering the first page/top five by talents cannot establish the global best for that build; disclose a bounded subset or acquire under an explicit search budget.

Examples of intended presentation:

- `Rogue · Combat-heavy 17/34/0 · DPS; comparison pool: WCL Rogue DPS`.
- `Warrior · Fury/Protection 0/33/18 · inferred Tank; WCL category: Tank`.
- `Mage · Arcane-heavy build; WCL category: Frost; category reason not independently verified`.

These examples illustrate representation, not automatic labels implemented by this research.

### Compatibility and acceptance checks for the redesign

- Preserve the old meaning of archived participant `spec`: it is a WCL category. Snapshot v1 recomputes ranking policy and validates category/metric/role, so changing `spec` to a talent tree in place can reject historical archives. Inspect `snapshot/v1.py:335`, `:358`, `:375` and `normalize/schema.py` before choosing additive fields versus a version bump.
- Keep current CLI `--spec`/`--category` behavior backward readable; design a distinct talent/build selection surface and explain legacy aliases. Preserve the legacy Hunter unfiltered policy.
- Preserve WCL ranking score versus actor/pet/event metrics, unknown versus zero, incomplete coverage, faction evidence and immutable raw snapshots.
- Test a Combat-heavy Rogue in `Assassination`, Fury-heavy tank in `Protection`, a tied Warlock build, Mage category disagreement, and missing talent evidence. Unknown/unknown must not count as a build match.
- Verify that selected tree intent never silently becomes an unsupported API `specName`, and broader comparisons are labeled honestly. Track search exhaustion, subset size and exclusion reasons.
- Add invalid race/class/faction cases plus unavailable and contradictory evidence. A validity constraint cannot become an observed race.
- Retain stored category names/slugs even if future WCL metadata changes, so old snapshots remain interpretable.

### Open questions before algorithm parity or narrower leader claims

- Current Vanilla tank and healer detection precedence, thresholds and encounter exceptions; current Mage Fire/Frost classification and Ignite credit formula.
- Exact tree-order/full-allocation evidence across old reports and current combat-log versions; data completeness per character/fight.
- Whether an appropriate supported advanced WCL filter can narrow a build, and whether it has identical semantics to the game tree catalog. No such filter was established here.
- A broader authoritative race source beyond inspected fields, including freshness and fight-time applicability.

These do not block modeling WCL's returned category faithfully. They do block claiming that Necropsy reproduces the WCL classifier or has acquired a global leader for an unranked talent specialization.

## Verification record

All commands ran from `C:\repos\necropsy` and were read-only with respect to production behavior. Generated research receipts are the only additions.

| Check | Result | What it establishes |
|---|---|---|
| `git status --short`; `rg`/file reads across catalog, selectors, acquisition, analysis, snapshots and reports | Initial worktree clean; inspected citations above | Wiring and existing contracts, not gameplay truth |
| Existing-client metadata/schema/partition probes and `workspace/taxonomy-research-2026-10-16/probe.py` | 28 bounded ranking attempts: 19 successful, nine nested class/spec errors | Live category availability, slug mappings, rejected filters and sampled rows |
| Existing-client report/event and character probes | Report/event request complete; first character name lookup null; known ID lookup returned cached-game-data unsupported error | Source-specific talent shapes and bounded API limitations |
| Read-only scan of eight `tests/golden/classes/raw/*.zip` report bundles | Seven populated fixtures supplied three-entry talent metadata; Holy Priest budget-only supplied none | Existing raw evidence shapes; archives unchanged |
| `.venv/Scripts/python.exe -m pytest tests/unit/test_class_catalog.py tests/unit/test_wcl_cohort.py tests/unit/test_druid.py tests/unit/test_druid_views.py tests/integration/test_class_reports.py -q` | 147 passed in 16.73s | Existing focused regression contracts; no new implementation validated |
| Exploratory `rg` against guessed paths/globs | Some returned missing-path errors; corrected to actual `normalize/` and file paths | Search misses, not failed product checks |
| Browser fetches of some WCL schema/help pages | Some 403/cache misses; live authenticated introspection succeeded; ranking guide available through indexed result | Do not imply every documentation page was directly accessible |
| Independent report review against raw JSON | Caught the initial probe summary treating missing rankings as empty lists; report/receipt corrected to preserve all nine nested errors | An HTTP/GraphQL success does not establish successful JSON-scalar ranking data |
| Local document links, receipt counts and SHA-256 checks; `git diff --check` | Passed; Git emitted a line-ending normalization notice for the existing guide | Report references resolve, evidence counts/hashes agree and tracked changes have no whitespace errors |

Independent verifier verdict: **Accept-with-caveats**. The reviewer independently checked code citations, all 17 raw-receipt hashes, the 19 successful/nine rejected query outcomes, 1,888 rows and the 40 matching talent triples. The initial rejection/empty-result error was corrected. Current classification thresholds and universal talent/race availability remain explicitly unverified. Production `page_items()` already rejects responses without a rankings list; the research summary error did not establish a production error-handling defect. Read-only notes and final verification are in `workspace/taxonomy-research-2026-10-16/code-verifier.md` and `report-verifier.md`.
