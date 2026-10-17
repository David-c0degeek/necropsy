# analysis.json

[Home](../README.md) · [Documentation](README.md) · [Reading results](reading-results.md)

`necropsy offline` and `necropsy analyze` write one `analysis.json` per run. It is the only input the
report and playbook renderers use, so everything they show must be in it.

```sh
uv run necropsy offline <snapshot.zip> --out out/            # temporary database
uv run necropsy offline <snapshot.zip> --out out/ --db work/full.duckdb   # keep and reuse it
uv run necropsy offline <snapshot.zip> --out out/ --cross-faction        # add the cross-faction view
```

The archive is always verified first: whole-file digest (against `--sha256` when
given), member safety, and, with `--entries`, every member against the manifest.
With `--db`, an existing database is then reused only when it was built by the
current database schema from that verified archive (same SHA-256); otherwise it is rebuilt under
the usual `ingest` safety rules (`--replace` is needed to overwrite a database built
from another snapshot). Without `--db`, a temporary database is created and removed
afterwards. The file is written atomically: a failed run leaves no partial file.

## From the interface to the exact value

Open **Why this was flagged** on a finding, then its evidence disclosure. Paths
refer to the containing boss in `analysis.json`. The overview is a presentation
summary of saved recommendations, ordered by severity with one representative
per rule; it adds no analytical field or score. Boss review marks, navigation
filters and theme preferences are browser state and are never written to JSON.

The HTML can change independently of the analytical schema. Rendering the same
JSON with the same Necropsy version remains deterministic. See
[reading results](reading-results.md) for the player-facing vocabulary.

## Guarantees

New analyses may include `bosses[].playbook.encounter_strategy`. Each saved item
has a versioned rule, preparation/execution/coordination section, text, source
URL, retrieval date and `kind: general-strategy`. It is static guidance with
explicit class/metric/ruleset applicability, not observed phase or assignment
evidence and not a personal finding. Missing items remain absent in older JSON;
rendering or refreshing a saved analysis does not consult current strategy rules.
Current encounter coverage and limits are listed in [raid modules](raids.md).

For live Hunter DPS analyses, `ranking.ranked_dps` falls back to the recorded WCL
score when event reconstruction is unavailable. The row must match the player,
report, fight, encounter and acquired category; conflicting scores stay unknown.
`ranking.ranked_dps_evidence` records this source and its limitation (also on a
ceiling or overall-top entry that uses it). Event damage totals, pet attribution
and coverage remain independently evidenced: a known WCL DPS score does not
make missing pet events complete. Historical snapshot calculations are unchanged.

Hunter entries also expose `hunter.pet_roster_complete` and
`hunter.total_pet_dps`, separate from the completeness of all pet-linked actors
(`pets_listed`). Confirmed non-Hunter guardians cannot invalidate an otherwise
proven Hunter-pet roster. Complete absence gives zero Hunter-pet DPS; unidentified
possible Hunter pets retain uncertainty. Family inference may cite another
acquired fight of the same report actor and owner, without importing its metrics.

Recovered starting auras carry `combatant-prelude-auras-v1` with references to the
raw earlier snapshot and complete intervening recipient buff pages. These pages
are outside ranked event totals. Recorded metadata talent points use only
validated single-fight scope. Conflicting sources remain unknown.

- **Deterministic.** The same snapshot and options give byte-identical output: no
  wall-clock time, keys sorted, floats rounded to 6 digits, every list in a defined
  order (chronological lists stay chronological).
- **Every value carries its evidence.** Values are evidence objects as described in
  [`evidence-model.md`](evidence-model.md): `value`, `level`
  (`observed`/`derived`/`inferred`/`unknown`), `claim` (`value`/`complete`), and
  optional `rule`, `params`, `note`, `refs`, `coverage`. An `unknown` value has
  `value: null` and a `note` saying why.
- **Event references are capped.** Each reference lists at most 10 event
  occurrences (`uid`, `copy`) and always gives the full `event_count`. The database
  holds the rest.
- **Validated shape.** The document is the pydantic model
  `necropsy.report.analysis_json.AnalysisDocument`, validated before it is
  written; its JSON Schema is committed as
  [`analysis-json.schema.json`](analysis-json.schema.json), and a test fails if the
  two drift. Typed: the envelope (literal `schema_id`, `schema_version`, `mode`),
  options, snapshot, subject, zone, cohort, coverage, boss rules, entry headers,
  ceiling, exclusion counts, encounter findings and recommendations (enumerated
  controllability, severity and confidence; at least one evidence path). The
  analysis sections inside an entry (`environment`, `ranking`, `hunter`), the
  baseline and the findings keep free-form keys, but every evidence object nested
  anywhere in them is validated against the `Evidence` model (known level and
  claim, null value exactly when unknown, typed references). That nested check is
  done by the pydantic model (`EvidenceTree`) when Necropsy writes or a consumer
  validates with it; the exported JSON Schema cannot express it and shows those
  sections as plain objects. A consumer relying only on the JSON Schema gets the
  typed parts, not the nested evidence check.

## Top level (`schema_version` 1)

| Key | Content |
|---|---|
| `schema_id`, `schema_version`, `necropsy_version` | document identity |
| `mode` | `historical` for a recorded export; `live` for a snapshot Necropsy acquired (`cohort.limitations` then holds the live description and every acquisition coverage line) |
| `acquisition` | live snapshots only: every requested boss (including ones with no acquired fight or not attempted after a stop) with its coverage, the cohort key, subject pick, entries, dropped and metadata rows, plus the run's endpoint, opt-in cross-faction choice and stop reason |
| `options` | `cross_faction` |
| `snapshot` | archive SHA-256, export format, scope (`full`/`subset`), fight counts, database schema version |
| `subject` | the analyzed character (name, server, region, class) |
| `zone` | zone id, name, partition |
| `cohort` | how the comparison cohort was formed, and its `limitations` |
| `coverage` | stream, anomaly and snapshot-issue counts |
| `bosses` | one section per boss, in zone order |
| `overview` | zone-wide summaries (rule set `overview-v1`): recorded entries by faction (and how many factions are inferred), the global setup of every same-faction entry across bosses — talents, Darkmoon Faire buff, ranged weapon and enchant, armor set pattern (armor-slot pieces only) and the set's other members worn with it (`set_extras`), hands, pet families, engineering pets, explosive use, Renataki's Charm per boss — each as counts with `known`/`unknown` totals, general pet facts (`pet_facts`: training-point budget, per-rank costs with their guide sources, example builds totalled against the 300-point budget, family health/armor/damage modifiers — never the subject's own pet training, which logs do not show), the subject's faction with its evidence level, ammunition advice for the subject's ranged weapon, and per-boss corrections: rank 1 (player, faction, race with whether it is proven, Windfury), same-faction weavers with their Raptor Strike counts, the best pure-ranged same-faction entry, and the weave verdict on same-faction entries versus all entries |
| `game_data` | where static item, set and enchant data comes from: the game client tables (`product`, `build`, tables) exported by wago.tools — rule data, never an observation |

## Boss section

| Key | Content |
|---|---|
| `encounter_id`, `boss` | the encounter |
| `rules` | encounter rules applied: ranking exclusions with the rule's `basis` (`empirical` — found from recorded rankings, not documented by WCL) and validation, and native targets |
| `subject` | the subject's selected kill: ranking damage (with `rank_percent` for the subject: WCL's historical `percent` and `today_percent` at export time, total parses and bracket, observed from the matching ranking row or unknown; and `by_target`: every damaged target as `counted`, `excluded`, `own` or `unclassifiable` — no target ID, or no game ID while encounter exclusions apply, which also makes the ranked total unknown), gear with display names (`name_source`: `wcl-rankings-gear` from the snapshot's ranking rows, `game-client-data` from the pinned client tables, `rules-items` fallback, `conflict` when ranking rows disagree, with the reason in `name_note`, or `none`; permanent and temporary enchant names from the client tables; `set_pieces`: item sets worn with two or more pieces; `set_armor`: the same sets split into armor-slot pieces and other members such as the set ring, with their slots), whether the export listed the Hunter's pets (`pets_listed`; missing or null means unknown, so "no pet took part" is never assumed), Raptor Strike casts by target role (`raptor_roles`; a cast on anything but a proven hostile NPC makes it unknown), environment profile, Hunter analysis |
| `cohort` | the same structure for each comparison entry (same faction only, unless `--cross-faction`) |
| `benchmarks.baseline` | same-faction medians (Auto/Aimed/Multi per minute, Hunter-pet DPS, kill time, first Rapid Fire), shot-target ranges, weave adoption, talent / Darkmoon / item / trinket distributions, explosive and Rapid Fire use |
| `benchmarks.ceiling` | best-ranked same-faction entry inside the acquired sample (historical exports: recorded top five), with its `membership` evidence |
| `benchmarks.raid_speed` | the subject's kill time against the same-faction median kill time (`vs_median`) and the fastest same-faction kill (`vs_fastest`), both always reported; `basis` names which one decides `flagged` (median at 1.5x when at least 3 kill times are known, else fastest at 2.0x) |
| `benchmarks.baseline.tauren_fill` | only when a same-faction median has too few values: the same metrics recomputed with other-faction entries proven Tauren with Windfury proven absent (`eligible`, `excluded` with reasons, `needed_for`). Separate from the same-faction baseline and from `--cross-faction`; kill time and weave adoption are never filled |
| `benchmarks.overall_top` | recorded rank 1 of any faction; an acquired event calculation when available, otherwise observed scalar context from the verified saved leaderboard. Metadata fallback carries `ranked_dps_evidence`, `basis`, `source_member`, optional `captured_at`, and an `event_sample_acquired` flag. Its score does not enter event medians or advice; an already-acquired matching entry retains its faction/kill evidence. `null` when rank-one identity is missing, invalid or ambiguous |
| `benchmarks.overall_top_unavailable_reason` | optional explicit explanation when the acquired rank-one entry conflicts with the saved leaderboard identity; the headline stays unknown instead of choosing one source |
| `benchmarks.faction_mix` | recorded entries by faction, how many factions are inferred, and the same/other/unknown split |
| `benchmarks.cross_faction` | `null` unless `--cross-faction`; never merged into the baseline |
| `benchmarks.excluded` | entries left out of the baseline, by reason |
| `encounter` | target integrity (native, start-trash and foreign damage; foreign share = foreign / all three; unknown while any damaged target is unclassifiable, listed in `unclassified_targets`), raid utility findings, and `ranked_target_shares`: which targets make up ranked damage on this boss — one row per NPC (by game ID, with the most common name as label and other names as `aliases`) and one category row each for players and pets (different people in different raids are not compared one by one), the same-faction median share (`n_known`, and `n_unknown` entries whose ranked damage is unknown and never counted as 0), the subject's share (COMPLETE, so a 0 is a proven absence), and the targets the encounter rule excludes |
| `overall_cohort` | every recorded leaderboard row of any faction, as context (baselines and advice still use the same-faction `cohort`) |
| `playbook` | structured playbook decisions (rule set `playbook-v1`): benchmark context, same-faction weapon sets and trinket pairs, other-faction melee packages (Windfury damage counts the swings uniquely matched to Windfury procs: inferred, neither proof nor a bound), pet plan, weaving by role with named entries, opener, Rapid Fire and Refocus timings against rank 1 (`rank_one.used`: `false` when its casts are complete and empty, `null` when unknown) and the same-faction median (each aggregate carries `n_values`, `n_without` — known entries that never cast it — and `n_unknown`, with a `reason` when there are too few timings), Do-not items and raid asks, and `static`: cited encounter facts (creature type, timings, source page, retrieval date; unknown where no source gives them), creature-type trinkets with whether they apply to this boss (`null` while the boss's creature type is unknown) ammunition advice, and `guidance` (rule `naxx-execution-v1`): Rapid Fire as the subject's worn sets leave it (duration, cooldown, set bonuses applied, from the client data) and general-advice items, each with the facts it rests on (`based_on`) and, where it depends on the snapshot, a `condition` (`true`/`false`/`unknown` with the numbers that decided it and its evidence level); `status` is `applies`, `otherwise` (the alternative text applies), `inapplicable`, or `conditional` when the condition is unknown — data for the playbook's sections, worded by the renderer |
| `recommendations` | see below |

A median needs at least 3 known values; with fewer it is `unknown`, and nothing
built on it (shot targets, weave verdict, recommendations) is emitted as a
number. `benchmarks.baseline.membership` grades the same-faction selection: when
any faction in it is inferred, every median, shot-target range and the ceiling
are `inferred` too (see [`evidence-model.md`](evidence-model.md)).

Weave adoption (`benchmarks.baseline.weave`) is judged per target role (rule
`weave-verdict-v2`): `boss` (the encounter's boss units) and `non_boss` (every
other hostile NPC: adds, start trash, pulled-in trash). Each role has its own
counts and verdict; the top-level counts are descriptive totals over any target.
A Raptor Strike whose target has no resolved hostile identity makes that entry's
roles unknown, never zero.

## Recommendations

Each recommendation has `rule`, `category`, `controllability` (`player`,
`gear-build`, `pet`, `raid-assignment`, `raid-speed-environment`,
`faction-racial-external`, `rng-low-confidence`), `severity` and `confidence`
(`high`/`medium`/`low` — a heuristic evidence-quality tier, not a probability),
`finding`, `recommendation`, `observed`, `benchmark` (which view and how many known
values; empty for findings about the subject alone), `limitations`, and `evidence`: dotted paths into the same boss section,
for example `subject.hunter.shots.aimed_shot`. A recommendation never estimates a
DPS gain, and a rule whose inputs are unknown emits nothing.

## Historical mode limitations

A snapshot replay can only use what was recorded: the cohort is the overall top
five per boss, the same-faction ceiling is the best entry of the subject's faction
inside it, and medians come from at most five entries. `cohort.limitations` states
this in every document.

## Live snapshot limitations

A Necropsy snapshot v1 replays through the same offline commands as a v6 export.
`mode: live` describes its acquisition origin; it does not make rendering contact
Warcraft Logs. `acquisition.bosses` preserves requested scope, including bosses
with no acquired fight, whereas `bosses` contains detailed analyses for acquired
fights. Use both fields when presenting coverage.

Live event comparisons use acquired fights, with a target of five verified
same-faction samples. The metadata target is 25 and includes the deep sample;
metadata-only entries do not contribute to event medians. A median still needs
three known values. Raw leaderboard positions remain overall positions, and
overall rank-one event context is unknown if its fight is absent; its saved
leaderboard DPS may still be displayed as observed metadata. Old archives without
leaderboard capture times explicitly report that time as unavailable. Missing pet discovery remains
unknown rather than establishing that no pet participated.

Acquisition entries can carry a `bundle_generation` digest identifying the cached
report used to verify that entry. Live snapshot report sets can carry an optional
`cache_sha256` for the exact endpoint/fight-set/content record. These additions do
not change the analysis schema version or prevent replay of older v1 archives.

## Druid entry sections

Schema 1 adds optional `druid` entry data; `hunter` remains unchanged for Hunter documents and may be absent for other classes. Druid data includes separate class/build/category/role/assignment evidence, an optional reasoned override, selected role, role-specific metrics, forms, activity spans, resources and full event timelines. `ranking.category_score` is saved metadata with an explicit metric; it is distinct from event DPS/HPS. Baseline keys include exact comparison dimensions and remain null for inapplicable duties. Existing Hunter JSON continues to validate/render. See [the class contract](decisions/0005-class-and-encounter-duties.md).

Druid details also retain a source-referenced actor catalog for readable target/source names. Saved ranking category scores have their own metadata evidence; event metrics and comparison medians remain separate. Resource readings display their evidence grade, and a zero/missing capacity stays unknown even when the raw payload is retained.

Selected Druid views retain `acquisition.selected_category`/`selected_metric` and
optional planned `comparison_order`. Boss `playbook.personal_data` distinguishes
available, insufficient-data and not-assessed. An incompatible acquired subject
is retained as `playbook.excluded_subject` for audit and is absent from personal
grading. `playbook.reference` is an eligible learning example; it never fills a
missing subject or baseline. `benchmarks.overall_top` is separately scoped saved
category metadata. Older documents may omit these optional nested details.
Packages add `tables/personal-coverage.csv` and `tables/learning-examples.csv`.

Druid `playbook.comparisons` retains individual same-spec/faction event sources,
builds, fight lengths, measurements and signed differences, including samples of
one or two. `spells` contains cast counts and casts per minute. Baseline
`build_policy` records that talent points are context rather than an equality
filter; `builds_differing` and source counts disclose variation. Aggregate medians
still require three known values. `playbook.ranking_comparison` compares saved
WCL scores separately, with scope, faction evidence, source and sample count;
`same_faction_top` retains the best recorded same-faction score. No metadata score
enters event metrics. Packages add `tables/individual-comparisons.csv` and
`tables/ranking-comparisons.csv`. New snapshot `metadata_order` records completed
first-page prefetches; older archives omit it and remain readable.

Explicit selected-spec Hunter snapshots also retain `selected_category` and
`selected_metric`, enforce participant category, and use the same optional
prefetch/comparison order provenance for multi-boss lookup. Unselected historical
Hunter archives retain their original behavior. `playbook.overall_reference` and
`overall_comparison` are optional Druid event context, shown in a closed disclosure;
`reference` is the main same-faction learning example. Neither fills a missing
subject. Interactive faction/spec choices are CLI inputs, not inferred duties.

Every class entry may carry optional `ability_use` evidence: recorded actor cast
counts keyed by ability name. Counts require complete actor-source coverage;
unknown input never supplies zeros. Rendering compares each count and uses per
minute with the same-faction reference through a shared component. Passive damage
ticks, cast-less swings and pet actions do not become actor ability uses. New
class packages add `tables/ability-use.csv`, retaining evidence grade
and source identity. Older documents omit the field and remain valid; replay raw
snapshots to populate it. Existing analysis schema version stays 1 with the
optional addition reflected in the committed generated JSON schema.

Druid gear now uses the same item/enchant name resolver as Hunter. Catalog
conflicts and unavailable names remain explicit with IDs. These are presentation
additions; raw archives, event multiplicity and role eligibility are unchanged.

Schema1 also adds optional `combat` entry evidence for Mage, Paladin, Priest, Rogue, Shaman, Warlock and Warrior. It retains class/build/category/duty, metrics, actor casts/opener/cooldowns/timeline, targets, resources, deaths and separate pet evidence. Existing `hunter` and `druid` contracts remain. All supported classes use the shared ability comparison and CSV; non-Hunter class metrics/roles/timeline and source comparisons share exports. See [class analysis](class-analysis.md).

New Era raid analyses may add `bosses[].playbook.duty_context` for an acquired
subject, including one excluded from comparisons. It identifies report/fight/
actor and contains coverage-qualified `melee_events`, positive
`observed_melee_times_s` evidence and an assignment limitation. Partial incoming
streams leave the total unknown while preserving positive observations. Both
pages present the saved context; rendering old JSON never creates it.

MC/BWL/AQ40 Era partition 1/2 combat and Druid metrics now use recipient-qualified
`effective_healing`, its rate and overhealing. Additive `raw_source_healing` and
`raw_source_healing_per_second` retain the original source-event sums.
`healing_to_bosses` and `unclassified_healing` (with rates) separate mechanic
healing and unresolved recipients. The optional `playbook.healing_context`
discloses this policy and boss-healing examples in both pages. These fields do
not reconstruct WCL HPS or include absorption events. Historical Naxx, seasonal
analysis and previously saved JSON retain their prior semantics. See
[the recipient contract](decisions/0014-recipient-qualified-healing.md).

Optional `playbook.encounter_effects` saves local actor-debuff observations:
source/rule/ability IDs, `transitions`, three-state `windows`, `known_affected_s`,
`unknown_state_s` and a limitation. Window times are seconds relative to pull;
state is true/false/null. Positive transitions may survive partial target
coverage while window durations remain unknown. Missing initial state stays
unknown; simultaneous contradictory events do not receive an invented order.
These are exposure descriptions, not boss phases, dispel opportunities or a DPS
normalization. See [encounter evidence](decisions/0015-encounter-observations-and-strategy.md).

Optional `playbook.mechanic_removals` and `cohort_mechanic_removals` retain
personal/cohort source-owned removal effects independently of casts. Counts
require source coverage; positive observations identify relative time, target,
removing ability and removed mechanic IDs. These are successful effects, not
opportunity counts or a utility grade. Both pages show the saved observations.

Schema1 adds optional top-level `taxonomy` in new live and non-Hunter class
outputs. It contains the canonical tree names, WCL-namespaced comparison pool
(class/category IDs, display label and API slug), optional user declaration,
explicit broad-pool scope and per-entry tree totals, derived primary tree,
recorded category, inferred duty, declared assignment, race/faction evidence and
catalog-consistency evidence. A consistency value does not establish identity.
Historical Hunter output and older documents may omit it.

Live snapshots optionally retain `subject.talent_tree`; acquisition JSON exposes
it as `declared_talent_tree`. This is user intent, not observed evidence or a WCL
filter. Existing participant `spec` keys remain WCL categories. The optional
saved-run option is bound by existing resume checks. Existing snapshots and
checkpoints without the field remain readable by the updated application.

The legacy comparison `build_matches` field is three-state: true/false for two
valid three-tree totals, null if either is unknown or malformed. Matching totals
do not prove identical individual talents. See [the durable contract](decisions/0012-game-build-and-wcl-category.md).
