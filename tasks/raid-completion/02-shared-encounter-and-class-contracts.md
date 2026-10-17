# 02 — Shared encounter and class contracts

## Goal

Extend the existing engine so mechanics alter measurements and guidance for every class/role. Keep raid policies modular, event/class primitives shared and presentation a consumer of analytical truth.

## Integration analysis

- Existing seams under `src/necropsy/`: `analysis/encounters/`, `analysis/context.py`, `analysis/generic/targets.py`, `analysis/benchmark.py`, `analysis/classes/classic_era/`, `analysis/{gamedata,guidance,recommendations}.py`, `report/{analysis_json,combat,druid}.py` and the renderer.
- Preserve graded evidence/coverage/refs, class/category/build/duty distinctions, known-sample thresholds, recorded versus reconstructed scores, deterministic schema and old rendering. Current guidance is Hunter-oriented; extend typed advice for other roles rather than cloning a Hunter engine per raid.
- Raid modules own facts, targets, phase policies and applicability. Shared event/opportunity primitives use existing seams. No parallel renderer, duplicate metric engine or template-computed advice. Inspect versioned/optional compatibility before coding. PM-1/PM-2 apply.

## Boxes

Readiness constraint (D003): current new-raid domain evidence applies only to
Era partitions 1/2. Guard applicability before new mechanics/ranking policies
run; never select SoM/Hardcore because the zone matches. Keep Naxx historical
and saved-live replay behavior. Live API schema is frozen in research/schema.json;
the older public schema additionally lists obsolete expansion arguments and
must not supersede current authenticated introspection.

- [ ] **02.1** (agent) Define the durable module contract: identity/variants, targets, facts/sources, observed phase/opportunity policies, ranking/metric windows, class/role applicability and guidance. Promote architecture decisions to an ADR; preserve registry and callers.

- [ ] **02.2** (agent) Implement target and phase/opportunity evidence with observed/inferred/static/unknown distinctions, actor/event refs, multiple targets, immunity/untargetable time and incomplete windows. Prove short, no-transition and partial-stream counterexamples.

- [ ] **02.3** (agent) Implement metric-policy reconciliation for ranking amount/duration, class/metric, pets/guardians, exclusions and variants. Keep WCL-recorded scores independent and unknown totals honest; test mismatched zones/partitions/variants and rule bases (PM-2).

- [ ] **02.4** (agent) Extend role/assignment/context evidence for damage, healing, tanking, utility and hybrids. Support encounter-restricted cadence and special duties without inferring assignment from category/build or inventing threat quality.

- [ ] **02.5** (agent) Extend structured preparation/loadout, execution, cooldown/resource/opportunity and coordination guidance to every class/role. Verify class-relevant items/set bonuses, enchants, ammunition/consumables, trinket/shared cooldowns and their ruleset/partition availability using sourced game data. Prevalence alone is not BIS or a causal gain. Retain rule IDs, applicability, confidence, controllability and source refs; wire outputs to actual analysis/render callers (PM-1).

- [ ] **02.6** (agent) Implement fair opportunity-aware comparisons beside labelled whole-fight values. Never silently normalize across incompatible assignments/phase definitions. Preserve same-faction/category/metric/duty eligibility, individual examples and the three-known-value median minimum.

- [ ] **02.7** (agent) Add negative tests for absent casts versus absent coverage, incoming versus actor-owned effects, owned pets versus unknown guardians, zero opportunity, mixed duty, guide timing without observed phase and conflicting ranking rules.

- [ ] **02.8** (agent) Update schema, serialization, docs and optional/versioned readers together. Verify old Naxx JSON and live-v1/legacy snapshots still produce both pages and packages; review intended semantic changes before updating baselines.

## Hindsight checkpoint

Use the master plan’s embedded prompt. Record Keep / Fix before closing / Record / Risk / Verdict; calibrate relevant PM predictions without rewriting them.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log

2026-10-18 / slice 27 / Genuine death and Feign Death checkpoint.
One shared raw death classifier distinguishes literal feigns, genuine deaths and unresolved flags across generic deaths, observed actor resets, effect identity validation and NPC windows. Unrelated recipient uncertainty does not taint personal state. No normalizer/schema change. Actual Geddon exposure corrected from0.480s to28.133s; end censoring and14.980s initial unknown preserved. ADR0015 extended.

Verification, observed-vs-expected behavior, uncertainty and interim Hindsight
are in research/feign-lifecycle-review.json. Keep shared seams and immutable
evidence; fix remaining full-domain/class/faction/phase/ranking/duty/product
and human obligations before closure. CH-MISS-3/4 and lasting lessons recorded.
Verdict DO NOT CLOSE. No full box or matrix cell closed.

2026-10-18 / slice 26 / Expanded Hunter comparison and guardian checkpoint.
Normal installed resume completes29 public selected actor/fights/all9 personal
bosses, with five comparisons each for Skeram/Royalty/Sartura/Fankriss. All58
player/54 pet/58 global directions complete; two guardian listings missing.
Native4 is the normal stopped acquisition after successful analysis/package;
107 requests reused,1196.82 account-wide points between readings. Neith's next
Viscidus candidate is absent. No quota/cache/revision/writer bypass. Original
archive remains immutable and stronger Viscidus primary evidence is preserved.

Added29 actor and29 owned-pet contexts:45 archives/525 actors/322 recipient
cases/41 owner contexts/38 units. All prior496 actor/322 recipient expectations
and12 earlier actor/context/pet measurements agree exactly. Four Sartura
contexts explicitly list no pet. Smcadogx retains Cat plus owned item summon
Vanquished Tentacle15901, with a separate ownerless Chicken in Fankriss. Final
actual source assertions keep the item summon outside trained-pet DPS and keep
confirmed trained-pet measurements despite unresolved guardian ownership.

Two real goldens pass/82.83s before final explicit guardian assertions; final
source29 actors/29 pet contexts/all9 bosses and package acceptance pass with
those exact assertions. Installed outside checkout matches all4 artifacts.
Four real browser cases pass. No production changes after9b69e70; Naxx all4
baseline hashes remain current.136 wheel members match checkout. Raw276716922
and output35264063 extracted bytes pass unlimited secret scans; research clean.
Ruff/format/mypy/docs pass.59 IN_PROGRESS/893 TODO/0 COMPLETE, no status closure.

Expanded independent ranking study retains83 records/64 distinct actor-fights,
with initial54 observations unchanged. Exact native API amount/duration binding
and residual candidates do not activate a ranking policy. SoD/Fresh/whole-raid
source scope is explicit; Royalty reset, Cthun instance/order, controlled-player
and guardian credit questions remain. Review: research/aq40-hunter-expanded-review.json.

Engineering Hindsight: Keep shared seams and independent immutable evidence;
fix remaining evidence/model/class/faction/duty/item/pet and human/domain/product
obligations before closure. Record that an overbroad research-script replacement
changed an Ignite filter; preservation guard rejected registration before any
write, then exact raw expectations agreed after correction. Numeric agreement
and selected actor aliases cannot certify eligibility. PM-1/2/3 reviewed;
verdict DO NOT CLOSE. Full subject boxes remain open.


2026-10-18 / slice 25 / Hunter owned-pet evidence and missing-reference
rendering checkpoint. Normal installed Marksmanship/DPS/Horde capture retains12 public actor/fights,
all9 personal bosses and3 Skeram comparisons;24 player,22 pet and24 global
directions complete. The stopped next candidate is absent from the native ZIP.
One missing guardian listing preserves the separately confirmed trained pet;
explicit no-pet and unknown-category owned units stay distinct. Added12 raw
actor cases and12 independent owner contexts/11 units through the existing
direction projector; prior484 actor/322 recipient expectations unchanged.
44 archives/496 actors/322 recipient cases;59 IN_PROGRESS/893 TODO/0 COMPLETE.
The stronger existing Viscidus primary source is retained.

Actual browser review found Hunter-only missing-comparator practice text and an
empty reference section. Corrected the existing renderer, preserving meaningful
comparisons and exact Naxx template whitespace.89 raw-fact units pass/2.30s;
3 real goldens pass/170.06s before render-only correction; final29 render tests
pass/15.51s. Source/installed12 actors/12 pet contexts/all9 bosses and four
artifacts match; four browser cases and desktop/mobile visual review pass.
All4 Naxx artifacts match30e89ce.136 wheel members match source; source
distribution excludes development data. Raw149843728/output18859101 extracted
bytes pass unlimited secret scans. Ruff/mypy/docs checks pass.

Research retains322 HPS records/173 unique actor-fights with exact native API
amount bindings and observed six-significant-digit rounding; no universal
precision/credit policy inferred. AQ40 Hunter target/control residual candidates
remain research, not enabled ranking rules. Normal comparison resume started
after reset; no new archive is counted here. Review:
research/aq40-hunter-pet-review.json. All full boxes stay open.

Engineering Hindsight: Keep shared seams, immutable raw facts and honest pet
scope. Fix all remaining phase/opportunity/ranking/class/faction/duty/loadout/pet
and human/domain/product gates before closure. Record the Hunter-specific
reference gap and exact newline preservation; risk remains that numeric
agreement or a known pet hides incomplete guardian credit. PM-1/2/3 reviewed;
verdict DO NOT CLOSE.


2026-10-17 / slice 24 / Cardinality-qualified AQ40 aura checkpoint follows
D018. Shared NPC state now retains Sartura Whirlwind/Enrage, separate Huhuran
Frenzy/Berserk, individual Twin teleport aura and Ouro Berserk; personal Sand
Blast uses actual26102 transitions. Unnumbered durations require exact fight
actor/gameID binding with integer instanceCount1. Positive transitions survive
unknown cardinality; numbered-add requirements and initial/lifecycle/censoring
rules remain intact. Explicit fight metadata refs accompany these state values.

Full normal capture now has54 public selected actors/all9 personal bosses and
five comparisons each,108 complete player directions/108 global scopes and four
missing pet owner listings. Original29 AQ40 dimensions agree.43 archives/484
actor cases/322 recipient cases; prior430/268 expectations and seven BWL exposure
contexts unchanged. All raw actor/recipient checks and nine strict upgraded
receipts pass.51 IN_PROGRESS/901 TODO/0 COMPLETE, no additional status closure.

Six NPC contexts/nine manual timelines froze before activation; actual page
inspection added a seventh raw countercase afterward: actor113/Ouro receives
Berserk but only109 is listed in the fight roster. Do not borrow109 cardinality;
113 durations remain unknown. Exact current golden assertions pass on source
and installed saved JSON. Eight separate actor contexts now bind16 manual
exposure timelines, including4.994s Sand Blast/48.997s initial unknown.

128 runtime tests pass/16.94s before metadata-ref addition; final81 window tests
pass/2.86s after it.62 independent-checker and16 strategy tests pass. Seven real
replay/register goldens pass/360.83s before explicit metadata refs/seventh raw
countercase; final source/installed artifact equality and current saved golden
assertions cover those additions. Four actual browser cases and Twin desktop/
Ouro mobile inspection pass. Naxx four artifacts remain byte-identical to30e89ce.
Raw468,825,813-byte/current extracted300,247,274-byte unlimited scans find no
secrets;136 wheel members match current source. Lint/types/docs clean.

One installed native analysis failure recovered unchanged in isolated offline
and actual CLI runs using a byte-identical archive,205 reused requests/0 new
points/expected exit4. Its cause remains recorded, not claimed fixed. See
research/aq40-observed-aura-review.json for Keep/Fix/Record/Risk/PM calibration.
DO NOT CLOSE: all full phase/opportunity/ranking/class/faction/duty and human
acceptance boxes remain open. Native stability needs further final-gate review.


2026-10-17 / slice 23 / Initial AQ40 checkpoint follows D017. Shared sourced
facts/static strategy now covers all28 catalog entries/952 legal configuration
paths; this is not full boss/class guidance or measured opportunity support.
Native first AQ40 capture retains29 public actors/all9 personal bosses,
58 complete player directions/58 global scopes and two missing pet listings.
Comparisons stop at Viscidus; a94-request zero-point resume produces24 actors
and does not replace stronger evidence.42 archives/430 actor/268 recipient cases,
original401/239 expectations preserved;51 IN_PROGRESS/901 TODO/0 COMPLETE.
Independent full registers pass; eight strict new actor receipts pass.46 focused
class-report/strategy tests pass/13.26s; new real golden1/59.87s before the final
missing-reference guidance refinement. Final source/installed four artifacts
match over all29 actors/all9 bosses; four browser cases and desktop/mobile
visual inspection pass. Naxx four artifacts match30e89ce. Raw194,914,329-byte and
current extracted112,121,485-byte unlimited scans find no secrets.136 wheel
members match source;227 formatted files/218 typed sources/291 docs links clean.
See research/aq40-initial-review.json for Keep/Fix/Record/Risk and PM calibration.
Hindsight verdict DO NOT CLOSE; all full boxes and human acceptance remain open.


2026-10-17 / slice 22 / BWL actor exposure reuses the shared observed-only
state and saved JSON/pages. Added Burning Adrenaline18173, logged Essence of
the Red23513, Flame Buffet23341, five Chromaggus afflictions and Nefarian fear/
curse/Priest-call policies. Priest-call exposure is class-qualified, not inferred
from a nominal timer. Saved cohort examples identify their player/report/fight
and cannot fill missing personal Nefarian context. Shared caveats render once.

Seven independent actor contexts/fifteen manually reviewed integer-ms timelines
were frozen before activation. Separate actor-effects raw checker and rehashed
mutation tests project transitions/lifecycles without calling production state
helpers.41 archives/401 actor/239 recipient/six NPC-control contexts unchanged;
43 IN_PROGRESS/909 TODO/0 COMPLETE. Raw available recipient/spell IDs must match
positive integer projections before excluding another actor. Unknown aura or
lifecycle identity retains unattributed evidence and stream coverage, withholding
durations and transitions. No actor0 or fabricated absence.

Focused153 checks pass/29.45 s; current final47 effect checks pass/13.04 s after
unknown-coverage metadata and cohort-caveat refinement. BWL golden2/90.34 s and
other42/317.85 s cover all41 archives plus overlapping control/effect registers;
do not sum them as44 distinct tests. Final source/fresh installed three-fixture
replay verifies65 actors/11 boss sections/12 byte-identical artifacts, including
original MC Holy/Hunter exposure. Twelve actual browser cases pass; mobile reviewed.
Current extracted273,808,943-byte unlimited scan found no secrets. Naxx four
artifacts remain byte-identical to30e89ce. Lint/types/docs and inventory pass.
Exact results and interim Hindsight:research/bwl-observed-effects-review.json.
Full phase/ranking/class/faction/duty and domain/product review remain open;
no full box or subject closes.

2026-10-17 / slice 21 / Incremental BWL work follows D015 alongside
unfinished01/02. Initial sourced facts and class-qualified static strategy now
cover all eight individual bosses plus the existing combined entry. Nine dossiers,
pinned primary addon revision and Classic tooltip review distinguish version,
removal type and actor/phase uncertainty. No guide timer supplies measured phases.

Normal full Holy CLI acquisition initially stopped on quota at38 actors; resume
reused178 requests and reached53 public selected actors/53 fights,106 complete
player directions and106 complete global scopes, with no quota stop. One Ebonroc
pet owner remains unresolved. Nefarian has five complete cohort actors and no
personal fight because factionID is absent; no subject, personal duty or zero is
fabricated. Combined and individual dragon comparisons remain separate.

Registered41 archives/401 actor cases/239 recipient cases plus six separate
control contexts; original348 actor/186 recipient expectations preserved.
Eight additional Holy Alliance evidence cells are IN_PROGRESS:43 partial /
909 TODO /0 COMPLETE. Independent401 actor and239 recipient checks pass.
Fourteen strategy checks cover all nine named classes, legal configurations,
removal-type boundaries and Nefarian responses. Source/installed/page/package,
privacy and final golden results are retained in research/bwl-initial-review.json.
Final full BWL golden passes1/87.04 s; all eight new actor receipts validate.
28 class Report integration checks and16 Druid view checks cover the additional
personal context attribution fix discovered in real page inspection. Final source/
installed saved-render artifacts match; Naxx analysis/pages/package remain
byte-identical to30e89ce. Unlimited raw381,908,872-byte and final extracted
255,984,054-byte scans found no secrets. Four browser cases pass; lint/types/docs
clean. Full phase/ranking/class/faction/duty and human acceptance gates remain open;
no full box or subject closes.

2026-10-17 / slice 20 / Normal installed full-MC context capture promoted
as a separate immutable fixture:40 archives/348 actor cases/186 recipient cases,
six separate NPC-control contexts. Original288 actor and126 recipient expectations
remain unchanged. Sixty independently enumerated actor cases exactly agree with
the earlier actor-only full raid; new All/critical context is separately frozen.
Eight existing Alliance Holy Priest receipts use the full format2 capture; stronger
Golemagg/Majordomo captures remain.120 player directions and114 encounter scopes
complete; two pet ownership listings remain unknown.35 IN_PROGRESS/917 TODO/
0 COMPLETE. Both full MC golden replays pass:2 passed/42 deselected/111.50 s.
Further source/installed artifact acceptance recorded in
research/mc-full-context-review.json. No box closed; phase, ranking, all-class
coverage and domain/product review remain open.

2026-10-17 / slice 19 / Class-qualified NPC control windows reuse the existing
observed-state/scope/saved-output path. Separate Garr710/18647 policies require
an unambiguous Player/Warlock caster, native Firesworn12099 and exact target
instance; keep NPC buff defaults and personal SOURCE-owned counters unchanged.
Raw source/target/spell IDs are checked before class/target exclusion, so bool/
fractional coercion cannot certify absence as a different actor. Unknown lifecycle
recipients carry event refs and withhold windows. No cross-rank union, timer
removal, physical attackability, lost DPS or assigned control inferred.

Frozen control-facts.json has six independent whole-fight contexts and four
manually reviewed positive instance intervals, separate from unchanged288 actor
and126 recipient cases.39 archives,35 IN_PROGRESS/917 TODO/0 COMPLETE remain.
Finia own yKBC4j3tzL8mDrNR/22 has zero applications personally and globally.
Forand cohort8Lt3zrD92h7Ty6xv/22 contains Greasecup11 effects:27.290 s known
active/24.404 s unknown, censored at end. Actor102 instances4/8 retain20.009 /
30.000 s; separate Rank2 example13.700 s, never a nominal-duration extension.
Three complete contexts have no applications, not proof of initial inactive state.
Both pages identify cohort target observations as being in that player's fight.

Current104 unit checks pass/2.99 s, including all nine named caster classes,
known wrong/unknown/ambiguous NPC/pet/player identity, spell/type/instance/scope,
raw coercion before exclusion and unresolved lifecycle ownership. Broader1445
passed/343 deselected/368.39 s before final malformed-ID tightening; current
focused checks cover that additional guard. Selected raw-control/legacy Garr/
Majordomo Holy/full MC golden checks pass, and current new Garr golden passes
1/6.20 s. Five source/fresh installed replays outside checkout verify84 actor
cases/14 boss sections,20 byte-identical JSON/Report/Playbook/package artifacts,
legacy unknown global counts and unchanged observed Majordomo buffs.20 desktop/
mobile checks pass; positive Garr mobile screenshot inspected. Final privacy/
Naxx/staged receipts are in research/control-windows-review.json.

Updated ADR0017, raid docs, changelog, raw checker/fixture guide, Garr dossier
and existing matrix receipt. Future full-context MC capture is independently
counted as ignored research only, not another seed. Interim Captain Hindsight:
Keep raw/manual independence, scope and separate source versus global effects;
fix full class/faction/duty/loadout, physical phases/opportunities, ranking and
human review. Record first archive fight is not necessarily the subject and
cohort player is not necessarily the effect caster. PM-1/PM-2/PM-3 full calibration
pending. DO NOT CLOSE; no full box or configuration accepted.

Final checkpoint audit caught CH-MISS-2: Git normalized SHA-bound JSON bytes
after local verification. Earlier pushed provenance references did not match
Git blobs. Fixed forward with canonical LF metadata, exact-byte Git attributes
for registers/native sidecars and recomputed reference digests; every frozen
measurement/provenance value remains unchanged. Eight real Git-filter regressions and eight staged Git/LFS countercases plus
seven existing coverage tests pass (23/6.53 s). New --staged checks actual index
metadata bytes and LFS OID/size, without replacing raw/domain checks. Fresh real
actor receipt recheck passes1/116.86 s after canonicalization. Staged verification
is recorded in the review.

Current full golden check:42 passed/423.77 s across all39 archives; frozen288
actor cases and126 recipient cases pass, including normalized raw owned sums
for every class. Ordinary1384 passed/401.79 s. Final installed CLI continuation
acquired all10 bosses/57 fights/60 actors with114 complete global scopes and
120 complete player directions;2 pet listings remain missing (native4), with
no quota stop.236 saved requests reused;60 original independent actor sums
verified. Three final installed replays match12 source artifacts. Naxx4 baseline
artifacts remain byte-identical and its frozen fixture tree unchanged. Actual
installed public51 report bundles and351,164,920 extracted raw/output bytes pass
unlimited secret scan. See research/normal-context-review.json and
normal-context-installed-cli.json. This new full context archive stays ignored
research, not a counted fixture or full domain certification.

2026-10-17 / slice 18 / Shared run_analyze now enables existing actorless All
and critical collection for MC/BWL/AQ40 Era partitions1/2. One applicability
predicate also guards explicit library acquisition. Low-level acquire remains
opt-in; Naxx/non-Era normal flows keep format1. No renderer, extra cache,
normalizer or downloader added. D013 and ADR0016 record the decision; sources,
pre-mortem and actual cross-raid immutable evidence precede normal activation.

Nine actual CLI cases verify three raids/both Era partitions and legacy
counterexamples. A quota interruption between All and critical leaves the
critical marker absent and no selected complete fight; resume reuses the All
scope, preserves the original archive and produces12 certified scopes. Broader
ordinary suite1384 passed/342 deselected/401.79 s. Ruff/format,218 typed sources
and291 doc links pass. Updated architecture, raid/API docs, changelog and
snapshot writer description. Three real source/installed replays retain exact
actor arithmetic and artifact bytes. Normal live MC continuation retained94
scopes/47 fights/50 cases, reused193 requests and stopped at the unchanged quota
reserve (native4); later comparison coverage remains partial.

See research/normal-context-review.json and normal-context-live-cli.json for
remaining final checks and receipts. Interim Hindsight Keep shared scope and
budget/revision/finalization/resume invariants; fix actual phase/opportunity,
ranking, class/faction/duty/loadout and complete product paths before closure.
Global presence never certifies another player's personal completeness. PM-1/
PM-2/PM-3 pending full calibration. DO NOT CLOSE; no full box accepted.

2026-10-17 / slice 17 / Full ten-boss MC capture independently registered,
without cutting or rewriting the normal CLI archive.60 actor cases in57 fights
and60 separate recipient-qualified support cases bring totals to36 archives,
270 actor cases and126 healing cases; all original210 actor expectations remain
unchanged. Added only missing Garr/Ragnaros Holy cells, preserving stronger
existing format2 receipts:35 IN_PROGRESS/917 TODO/0 COMPLETE.120 player streams
are complete; two unresolved pet discovery listings remain explicitly MISSING.
Nested original filenames retain ZIP/member/hash provenance and Git LFS coverage.

Added sourced initial Ragnaros recovery, conditional Hunter/Mage Sons control,
Paladin Aura19900 and Shaman Totem10538 party capability. All nine named classes
are checked; no assignment or successful effect inferred. Long372.315-second
public research has Sons but no20567 marker and null API phaseTransitions; do
not derive vulnerability/submerge boundaries from guide or addon timers.
Static facts and strategy remain separate from personal findings.

Shared existing golden assertions now run per actual boss for multi-boss
archives. Independent checks plus three representative replay cases pass5/90.29s;
current strategy and full golden pass12/43.72s, including exact missing pet
coverage. Source/fresh installed wheel outside checkout match all4 JSON/Report/
Playbook/package artifacts for10 bosses and60 actor/support cases. Both pages
pass desktop/mobile/no-network/errors/overflow/print checks; Ragnaros mobile
content visually inspected. Unlimited gitleaks:141,470,611 extracted raw bytes
and371,588,287 build/source/installed/package bytes, zero findings. Ruff, mypy and
291 local doc links pass. Updated raid docs, changelog, fixture guide and dossier.
No shared runtime or Naxx oracle changes. See research/mc-full-ragnaros-review.json.

Interim Captain Hindsight: Keep immutable multi-boss inputs and independent
actor/recipient arithmetic; fix remaining full class/faction/duty, phase,
ranking, loadout and human review obligations. Record60 cases/57 fights and
120 complete player plus2 missing pet-discovery streams; source arithmetic
never implies complete pets. PM-1/PM-2/PM-3 pending full calibration.
Verdict: DO NOT CLOSE. No full box or configuration accepted.

2026-10-17 / slice 16 / Recipient-qualified credited absorption and deeper MC
actor evidence. Added raw source, friendly, boss and unresolved absorption/rates,
plus combined friendly heal+absorption over whole-fight duration. Preserve
heal-only values and overheal denominators; no pet/guardian sum, WCL policy or
quality grade is inferred. Available raw source/recipient/amount scalars are
checked against normalized values: boolean or fractional coercion cannot certify
a contribution. Partial actor-source streams remain unknown even with globals.
Both pages show saved support examples, including Mage wards, through existing
combat/Druid metrics and shared playbook adapter. Old JSON gains no new analysis.

Primary WCL pins identify healing category as including absorbs. Independent66
retained HPS cases reproduce recorded two-decimal scores using source heals plus
absorption over recorded duration; separate healing-facts.json freezes recipient
expectations before production changes. This is observed precision, not a fitted
tolerance or universal ranking proof. Synthetic wrong owner/recipient, incoming
mitigation, hostile/unknown recipient, malformed amount, partial/zero and raw
scalar-coercion counterexamples pass. Original192 actor expectations unchanged.

Three finalized six-source Golemagg Fury / Majordomo Fire and Frost captures add
18 cases:35 archives/210 actor cases,33 IN_PROGRESS/919 TODO/0 COMPLETE. The18
participants span17 fights/34 global scopes: Frost has two Mages in one fight,
with distinct arithmetic and shared event normalization. Subject Magma13880
apply14.094 through39.333 s gives25.239 known affected/14.094 unknown; stack
refreshes do not become armor-loss, avoidance or assigned-tank judgements. No
selected Mage Polymorph application is invented. Dossiers/provenance record
exact sources and independent facts. Additional long Ragnaros public research
returns16576 events/2 terminal pages, same public revision34 before/after, no
20567 marker and null API phases. It remains uncounted research, not zero phases.

Verification: all35 retained archives pass38 goldens/282.54 s before final raw
scalar/render guards; current focused support checks48 pass/5.97 s and numeric/
missing/null event-copy rendering1 pass/1.03 s. Full ordinary regression1373
pass/338 deselected in384.02 s before final missing-index fallback;17 historical
class/Druid goldens pass/240.57 s. Four Naxx artifacts remain byte-identical.
Eight source and isolated installed real replays across all three raids preserve
48 independent actor totals, normal live acceptance and32 byte-identical JSON/
Report/Playbook/package artifacts.32 desktop/mobile/offline/no-error/overflow/
print checks pass; positive Magma and Mage-support mobile sections inspected.
Unlimited scans:96,870,342 raw bytes and530,494,953 build/source/installed/package
bytes, zero findings. Final missing/null fallback recheck passes in all8 installed
fixtures with32 artifact byte matches; targeted legacy Unknown test passes.

Interim Captain Hindsight: Keep independent recipient facts, preserved heal-only
measurements, explicit actor/source coverage and saved-only adapters. Fix full
class/pet/target/phase/ranking/opportunity/loadout coverage and human reviews
before closing. Record CH-MISS-1: installed byte comparison found Jinja resolving
dict.copy rather than the saved event index. Corrected all three class Report
locations, including legacy missing/null Unknown behavior; underlying JSON and
Naxx Hunter values unchanged, no baselines regenerated. Risk:66 score agreements
are bounded evidence, not universal HPS or quality approval. PM predictions stay
pending full calibration. Verdict: DO NOT CLOSE.


2026-10-17 / slice 15 / Golemagg/Majordomo initial strategy and shared instance
observations. Added two normal finalized format2 public six-source Holy captures
and12 independent cases:32 archives/192 cases,30 IN_PROGRESS/922 TODO/0 COMPLETE.
Original180 expectations unchanged; independent global facts also bind actual
Majordomo reflection/shield caster, recipient, instance and transition.

Shared observed three-state aura logic now serves exact NPC instances as well
as existing actor effects, preserving historical defaults. Global counts/windows
require unrestricted encounter coverage with explicit actorless role in saved
refs. Critical/player scope, ambiguous instances/catalog, partial pages and
multiplicity/boundary conflicts cannot certify absence or duration. Positive
transitions survive partial streams. Unknown initial state, simultaneous
contradiction, death reset and censored end stay explicit. No inferred phase,
attackability, immunity, assignment, quality or ranking denominator is added.
Existing saved JSON renders without current-policy injection.

Majordomo subject wjWt8JCzRKqV1gkG/21 Elite80/instance3 has5.464 s Reflection
active and30.445 s unknown. Independent JqLRy1GvDjMkPYp2/44 Elite78 instances1–4
have6.348/8.439/9.973/2.637 s active, proving actor-only merge invalid. Short
kills have zero recorded applications but unknown initial state. Primary Aegis
caster-self description contradicts the guide's ally-shield claim; nominal
timers/control thresholds and Golemagg add-completion contradictions are not
implemented as measured rules. All nine class names check Mage-only control
capability. Strategy now covers11 encounters/374 legal configuration paths.

123 focused/schema/historical checks pass/47.28 s; two new real goldens pass/
12.72 s; all192 independent raw cases pass. Installed wheel outside checkout
reproduces12 raw actor totals, exact subject/cohort instance states, both pages/
packages and normal live acceptance. Eight desktop/mobile/offline/no-error/
no-overflow/print checks pass; positive Golemagg Report and Majordomo Playbook
mobile sections visually inspected. Unlimited gitleaks8.30.1:66,558,304 raw bytes
and77,014,695 current build/source/installed/package bytes, zero findings. All
four Naxx artifacts remain byte-identical to30e89ce. All32 retained real archives pass34 golden checks/230.44 s,
including192 independent raw cases. Full ordinary regression excluding golden/live/acceptance/browser
passes1351 tests/334 deselected in368.52 s. New ADR0017, dossiers and research/mc-final-context-review.json retain
current contract, source conflicts, pre-mortem and exact acceptance limits.

Interim Captain Hindsight — Keep shared state/coverage/serialization/render
seams and independently frozen instance facts. Fix physical phase/opportunity,
ranked targets/denominators, positive control/interrupt/loadout/pet and remaining
class/role/faction evidence plus human reviews before closure. Record missing
serialized scope role caught by the focused test and repeated-instance ranking
limitation. Risk: local buff state does not prove attackability or assigned
behavior. PM-1/PM-2/PM-3 pending full calibration. Verdict: DO NOT CLOSE.


2026-10-17 / slice 14 / Representative finalized live format2 evidence. Normal
acquisition/finalization/writer produced six public Lucifron Mage sources,
12 global scopes,31,515 unrestricted events and1,485 critical damage events.
Promoted immutable raw archive/manifests/provenance and six independent context
facts; original174 expectations unchanged.30 archives/180 cases,28 IN_PROGRESS/
924 TODO/0 COMPLETE. Independent checker now proves terminal contiguous pages,
exact global scope/filter/digests and distinct raw critical/control/Ignite inputs.
Manual synthetic changes to ownership, school, Ignite, scope and pagination fail.
Version2 also rejects unrestricted actor-owned events missing from a captured
actor direction, preventing silent actor arithmetic changes. All12 real actor
directions independently match their unrestricted owned events exactly.

New real golden and all180 independent cases pass. Installed wheel outside
checkout reproduces all six raw actor totals,12 scopes, both pages/package and
normal acceptance; observed unselected Mage has no complete actor-source claim.
Four desktop/mobile browser/no-network/error/overflow/print checks pass; actual
mobile Report inspected. Unlimited gitleaks8.30.1 finds zero leaks in22,056,307
raw bytes and36,391,113 build/output/installed/package bytes. Ruff272 files,
mypy216 source files and maintained docs pass. Full ordinary suite excluding golden/live/acceptance/browser passes1320 tests
(332 deselected)/353.88 s;42 focused parser/checker tests pass/2.92 s.

Keep versioned scopes, independent inputs and shared existing pipeline. Fix
observed phase/opportunity, fully reconciled ranking, remaining evidence and
class/role advice before closure/default collection. Transport acceptance is
not domain-policy acceptance. Full MC Holy normal CLI run retained47 fights but
stopped at quota reserve; it remains unpromoted research, not a counted fixture.
Research source conflicts for Golemagg/Majordomo recorded without inventing
IDs, phase boundaries or shield attribution. PM-2/PM-3 pending full calibration.
Interim Captain Hindsight: DO NOT CLOSE.


2026-10-17 / slice13 / 02.1-02.3 and02.7 partial: explicit live format2 for
optional encounter context through the normal acquisition generation/finalization,
cache, writer, shared page decoder, normalizer and output/package path. No default
collection change. Both scopes are certified once per selected fight with exact
request, bounds, revision, endpoint, page digest and terminal pagination proofs.
Actor/pet and critical raw views must be subsets, including multiplicity, of All.
No actor0, filtered-as-All coverage, extra/missing page or unsupported version
fallback. Existing v0/v1 requests/writing and actor absence predicates preserved.

131 acquisition/live/raid integration checks pass/114.73 s before acceptance-helper
follow-up;22 new final v2 positive/tamper/ruleset checks pass/4.01 s, including the
normal live acceptance checker and both pages/package. Legacy reader/ingestion
plus new v2 checks56 pass/6.94 s before four additional ruleset guard negatives.
All29 existing real archives pass31 golden checks/188.56 s, including174 raw fact
cases. All four Naxx artifacts remain byte-identical to30e89ce. Fresh installed
wheel outside checkout replays the synthetic normal-acquisition v2 archive into
exact36 unique events/12 actorless scopes, both pages/package and live acceptance.
Unselected Mage17 has observed events but no complete actor-source certificate;
raw critical and actor overlaps do not double totals. Synthetic transport is not
real v2 capture acceptance. Fresh wheel/sdist/synthetic raw/cache/output/installed
extraction7,882,364 bytes (scanner7,866,228) passes unlimited gitleaks8.30.1.
Ruff272 files/mypy216 source files/maintained docs pass.

[ADR0016](../../docs/decisions/0016-encounter-event-scope.md) records current
optional support and live/default-collection limits. Keep versioning, shared
parser, raw identity and separate coverage; fix live finalized raw/independent/
installed acceptance and actual observed phase/metric/opportunity policies before
enabling defaults or closing contracts. Full MC Holy capture is waiting for its
observed reset through normal CLI. No new real fixture, complete cell or box is
counted. Interim Hindsight DO NOT CLOSE; PM-2/PM-3 pending full calibration.


2026-10-17 / slice12 / 02.1-02.3 and02.7 partial: encounter-scope cache/fetch
foundation under D010. Pre-mortem guardrails and versioned archive constraints
recorded before code in research/encounter-stream-contract.md. Independently
compared20 immutable actor streams against seven same-revision public terminal
whole-fight research payloads: exact subset and multiplicities match. Extend the
existing cache/client/pagination path with nullable actor and explicit all scope,
separate encounter/critical identities and a canonical critical-damage filter.
No actor0, substitute downloader, default collection or archive format change.
Wrong scope/filter/actor, revision drift, page-budget interruption, non-damage
critical responses and actor-cache preservation/reuse covered.118 focused cache/
fetch checks pass/1.53 s. Seven recorded payload pairs replay exactly through the
normal client/cache using synthetic offline transport/quota and no-network reuse;
research/encounter-cache-recorded-replay.json is not a live archive acceptance.

Keep current actor identities/names and coverage predicates; fix versioned raw
archive collection/reader/writer, full normal capture and independent normalized/
rendered/installed acceptance before enabling production encounter context. No
ranking reconstruction, boss phase or opportunity is certified. Shared subject
remains IN_PROGRESS; interim Hindsight DO NOT CLOSE; PM-2/PM-3 stay pending full
calibration. Broad ordinary regression in progress.


2026-10-17 / slice 11 / Sulfuron initial strategy and evidence. Promoted
public finalized six-source Holy/Rogue captures:29 archives/174 independent raw
actor cases,28 IN_PROGRESS/924 TODO/0 COMPLETE. Original162 expectations unchanged.
Guide and Classic spell record disagree on nominal Dark Mending cast time (2 s
versus2.5 s); no numeric timer, cast-opportunity or lockout model is implemented.
General add targets/interrupt backups and divided healer/magic-removal duties
use existing sourced static strategy. No personal successful interrupt/removal
counter or failed-duty diagnosis is inferred from absent selected events.

Verification:11 focused/new real golden checks pass/7.98 s; all174 independent
raw cases pass. Fresh wheel installed outside checkout reproduces both real
roles, both pages/packages and corrected Shazzrah applicability for all nine
named classes. Eight desktop/mobile/no-network/no-error/no-overflow/print checks
pass; positive Holy Report and Rogue Playbook mobile strategy inspected.
Unlimited gitleaks8.30.1:28,975,958 raw bytes and47,892,406 current source/installed/
package/build bytes (scanner47,563,511), zero findings. Dossier and
research/sulfuron-review.json retain exact limits.

Fury capture stopped during normal finalization:159 allowed points remain,
unknown-cost reserve162. Cache/journal retained; no archive or acceptance and no
quota ceiling change. Selected Rogue pages contain other actors' interrupts,
but none of six selected Rogues has a source-owned interrupt. This is not proof
of raid failure or universal Rogue non-applicability.

Interim Hindsight: Keep ownership/coverage/normal finalization and sourced advice;
fix actual positive interrupt/removal/hostile-heal/instance opportunity, all
class/faction/tank/ranking/loadout/pet and human domain/product obligations before
closure. Record source cast-time conflict and numeric-class-filter miss in
lessons. PM-1/PM-2/PM-3 remain pending full calibration. DO NOT CLOSE.


2026-10-17 · slice 10 · Shazzrah initial evidence/strategy · Two public
finalized six-source Holy/Hunter captures add12 independently enumerated actor
cases:27 archives/162 cases,26 IN_PROGRESS/926 TODO/0 COMPLETE. Original150
expectations preserved. Personal Curse19713 uses existing observed-only state;
active effects at fight end remain censored. Friendly curse removal and hostile
Deaden Magic removal are separate class capabilities, not inferred assignments.
No selected positive Deaden Magic removal or Counterspell interrupt is claimed.

Verification:40 focused checks/8.69 s; two new real goldens/6.61 s; all162 raw
fact cases pass. Fresh installed wheel outside checkout reproduces exact windows,
facts/strategy and both pages/packages for both roles. Eight desktop/mobile
checks pass offline/no-error/no-overflow/print; actual positive Holy Report and
Hunter Playbook mobile exposure sections visually inspected. Unlimited
gitleaks8.30.1 finds no leaks in21,559,194 raw bytes or22,198,662 current output/
package/build bytes (scanner21,870,352). See research/shazzrah-review.json and
[dossier](dossiers/shazzrah.md) for limits.

Interim Hindsight: **Keep** shared state/coverage, immutable evidence and honest
class capability. **Fix before closing** all class/faction/tank, actual interrupt/
removal/opportunity/pet/loadout/target/ranking evidence and domain/product review.
**Record** active-end observations do not mean dispel failure; no cast is not a
measured lockout. **Risk** PM-1/PM-2/PM-3 remain Pending full calibration.
**Verdict: DO NOT CLOSE.** No full subject box or matrix cell closes.


2026-10-17 · slice 9 · 02.4/02.5/02.7/02.8 partial · Existing aura-state contract
now carries Geddon Ignite Mana still active at fight end. No fabricated removal
at the boundary, mana-loss amount, assignment or avoidance grade. Static bomb /
Inferno/healer/magic-removal/Hunter pet strategy stays separate from observations.
Seven encounter strategies cover238 legal class/metric configuration paths;
39 focused checks and27 all-real golden checks pass. Fresh installed replay
outside checkout and both-page/mobile checks pass. No schema or shared Python
measurement change; full opportunity/duty/ranking and global-source contracts
remain open, including actual bomb and Ragnaros submerge evidence.

2026-10-17 · slice 8 · 02.4/02.5/02.7/02.8 partial · Reused shared observed aura
states for Gehennas Curse and added patient-specific healing context. Personal
healer exposure does not establish the state of all healing recipients or
support outgoing-HPS scaling. Six sourced strategies now cover 204 legal
configuration applicability paths; Mage/Druid removal and healer context have
separate class/metric guards. No Python engine change. Final 38 focused checks
and 24 real golden checks pass; installed raw replay, both pages/package,
representative mobile review and four byte-identical Naxx artifacts verified.
Complete phase/opportunity/ranking/duty/class contracts remain open.

2026-10-17 · slice 7 · 02.4/02.5/02.7/02.8 partial · Added source-owned control
applications via existing actor-event/coverage primitives. Positive application
evidence retains NPC actor/instance/spell/time; casts, removals and wrong targets
are distinct. Unknown required metadata/partial coverage prevents exact counts;
known mismatches exclude unrelated events. Garr supplies real positive/zero
sources,17 focused matching/coverage cases and static assignment-aware strategy.
Saved optional control data reaches both pages without adding rules to old JSON.
Shared full opportunity/duty/ranking/loadout contracts remain open. Current
five-encounter strategy applicability is verified across170 legal configuration
paths. Ordinary1308 checks pass; final focused22 checks pass after matching
refinement. Actual current real/installed/Naxx/render follow-up running. No full
shared box closes.

2026-10-17 · slice 1 · 02.1/02.5/02.8 partial under D006 · Shared sourced-static-strategy contract in analysis/encounters/strategy.py and existing per-raid guidance YAML; concrete Lucifron, combined-dragon and Viscidus strategies. Backend selects class/metric/Era-partition applicability and saves optional playbook data. Existing common pull-sheet adapters present preparation/execution/coordination and source links in both Report and Playbook, retaining explicit general-strategy limitations and no personal grading/observed-phase claim. No class plugin, role heuristic, metric, cohort or snapshot migration changed. Missing strategies remain absent; old saved JSON does not acquire current rules at render. Verified 102 legal seed configuration applicability paths; class-specific curse/magic removal, Viscidus HPS context, wrong-raid/seasonal/boolean partition negatives, old-document rendering. Real replay/content/source/package checks plus unit strategy checks: 16 passed/69.17 s. An earlier real-content run caught missing Report wiring despite passing transport tests; corrected with saved-content source disclosure in both adapters. Actual 12 page/viewport/no-network/no-overflow/print checks pass; two representative screenshots inspected, research/strategy-review.json records limits. All four original historical Naxx artifacts match 30e89ce byte for byte. Static checks/schema currency/docs pass; broad ordinary follow-up running. No subject or matrix cell closes; complete phases/metric reconciliation/duties/loadout/opportunity contracts remain open. Checkpoint pending.

## Interim review — not subject closure

2026-10-17 · slice 3 · 02.4/02.7 partial · Added shared direct-boss-melee context
and an ambiguity guard for action-based combat/Druid duties in new Era raids.
Three or more boss melee events without qualifying tank actions invalidate a
simple DPS/healer duty inference, retaining raw actions and unknown assignment.
No tank assignment is inferred from category or hits. Personal pressure remains
visible in both pages even when personal comparison eligibility fails. Partial
target streams preserve positive times while totals remain unknown; trash and
other actors do not count. Era/seasonal, real MC Fury-style and Druid counterexamples
are tested. Eight focused cases pass; broad ordinary suite 1255 passed/262
deselected/393.66 s (two subsequently added Druid cases additionally covered by
the focused run). Four historical Naxx artifacts again match 30e89ce exactly.
Remaining assignment/opportunity/ranking contracts stay open; no full box closes.

Verification follow-up: all 12 immutable raid replays pass, **14 golden checks /
99.75 s**, with all 72 independent raw actor cases. Eight actual page/viewport
checks for real MC Protection and BWL Guardian pass offline/no-network/no-error/
no-overflow/print visibility. Inspected MC Protection mobile Playbook screenshot:
nine boss melee events and the assignment limitation are visible with bounded
layout. Unlimited scans: 81,152,275 new raw bytes and 29,891,846 representative
generated output bytes, no findings. Research/duty-review.json records limits.
Keep shared bounded evidence and old Naxx behavior; remaining hybrid assignment,
physical phase/opportunity and recipient-aware healing policies need work.
Interim verdict remains DO NOT CLOSE for the whole subject.

2026-10-17 · slice 4 · 02.3/02.4/02.7/02.8 partial · Recipient-qualified healing
added through existing generic combat/Druid plugins for new Era raids. Raw
source sums are preserved; friendly support, boss healing and unclassified
recipients are separate, with source coverage and roster/actor/event refs.
Missing recipients/roster, conflicting boss/friendly identity and incomplete
source streams cannot manufacture a friendly-healing zero. Incoming heals are
excluded. Qualified overhealing also excludes boss effects. The three real
Ebonroc amounts (125,000/75,000/460,963) remain independently frozen raw facts;
real replay checks assert their separation from friendly support. Both pages
disclose the distinction. D007 and ADR 0014 document the intended new-raid
measurement semantics; original Naxx behavior and saved JSON remain unchanged.
Focused 17 checks and all 12 real replays (14 golden checks/112.88 s) pass;
broad ordinary follow-up running. Full WCL HPS/ranking reconciliation remains
open; no cell or shared box is complete.

Verification follow-up: full ordinary suite **1261 passed, 265 deselected,
377.13 s**. Four historical Naxx artifacts remain byte-identical to 30e89ce.
Fresh wheel raw replay outside checkout verifies all three Ebonroc boss-healing
amounts versus zero friendly support, both pages and package. Eight actual
source page/viewport checks pass; inspected the BWL Guardian mobile healing
section. Source output scan 29,928,344 bytes; installed output 24,997,156 bytes;
wheel/report packages 57,729,387 extracted bytes (scanner read 57,713,527),
unlimited gitleaks, no findings. Static checks/docs and all 72 raw facts pass.
Research/healing-review.json records representative limits. Keep raw/qualified
semantics and source refs; fix complete ranking, NPC recipient/opportunity and
domain coverage before closure. Interim verdict: DO NOT CLOSE for subject 02.

2026-10-17 · slice 5 · 02.1/02.2/02.7/02.8 partial · Added strict observed-only
actor debuff windows through the existing aura-state primitive and per-raid YAML
policies: Lucifron's Curse, Impending Doom and combined-entry Shadow of Ebonroc.
Missing initial state stays unknown; no-transition/short fights cannot invent
unaffected time. Partial target streams retain positive transitions but unknown
window durations. Wrong actor/kind, out-of-fight, conflicting refresh and
simultaneous apply/remove cases are exercised. Guide timing never supplies a
phase or lost-throughput denominator. Real Lucifron target-only arithmetic
independently fixes Curse known exposure 7.672 s / initial unknown 13.760 s and
Doom 14.059 s / unknown 12.141 s. Both pages show known and unknown time with
source/limitation. D008/ADR 0015 preserve Naxx/default aura semantics and separate
the optional shared contracts from full phase/opportunity acceptance. Twelve
adverse/behavior cases plus historical recovery cases pass (29 checks); all 12
real replays pass (14 golden checks/113.10 s). Broad follow-up and artifact
review running. No full box or cell closes.

Window verification follow-up: **1273 passed, 265 deselected / 372.44 s** ordinary;
all 12 then-current real sources replayed (14 golden checks / 113.10 s).
Fresh installed-wheel raw Lucifron replay outside checkout verifies exact
independent windows and both pages/package. Eight source viewport checks pass;
inspected MC Holy mobile window display. Four original Naxx artifacts remain
byte-identical. Unlimited scans: 29,946,830 source-output bytes, 4,945,036
installed-output bytes, 37,190,911 extracted wheel/report-package bytes
(scanner read 37,174,955); no findings. Research/effects-review.json records the
window-only review scope, preceding the next removal-effect addition.

2026-10-17 · slice 6 · 02.4/02.7 partial · Added source-owned successful mechanic
removal observations independently of casts: exact extraAbilityGameID and
isBuff=false identify Curse/Doom/Dominate Mind removals. Counts require source
coverage; positive effects survive partial coverage; absent or malformed mechanic/
debuff metadata cannot give a known zero. Personal and cohort source identities,
target/removing-spell/mechanic/time/event refs retained. Incoming effects, buff
purges, unrelated dispels and cast events are excluded. No assignment,
opportunity, reaction-time, causal downtime or utility score is inferred.
Real independently enumerated examples: Balance/HPS Truudee 5, Ragny 12, 海兰 1
Curse removals; Mage Benoii/Darkwizzardo one each; Priest Bluebeard one control
removal and Maoainai one Doom removal (unrelated ID11672 excluded). Seventeen
adverse/behavior tests pass; shared cross-raid/class/recovery follow-up 91 passed /
33.83 s. All 16 real fixture replays pass (18 golden checks / 126.98 s), with
post-metadata-guard focused real follow-up running. Full subject stays open.

Adverse follow-up: death/resurrection without a removal event cannot extend a
prior apply across that boundary; observed-only state resets to unknown, with
reset-event refs retained. Historical aura defaults are unchanged. Eighteen
effect/removal cases plus 17 prior recovery cases pass (35 total/5.62 s).
Post-metadata-guard real Lucifron healer/utility subset: 3 passed/10.84 s.
Installed Balance/HPS replay outside checkout and eight source viewport checks
pass, with useful utility content and source/limitation visible. Visual review
removed repeated long limitations while retaining individual counts. Full broad
follow-up running; no subject or full box closes.

Final slice verification: ordinary suite **1278 passed, 269 deselected /361.83 s**;
latest state-reset/view follow-up **51 passed /11.66 s**. Fresh installed-wheel
Balance/HPS raw replay passes outside checkout, preserving category/metric and
the independent removal counts in both pages/package. Eight source viewport
checks pass, and the grouped mobile utility section was inspected. Unlimited
scans cover 57,112,206 new raw bytes, representative source/installed output,
and 16,416,950 extracted final wheel/report-package bytes (scanner read16,400,994),
with no findings. Sdist excludes disposable tasks/workspace files. Full real
replay after the last state-reset guard is running; previous all-source run was
18 passed/126.98 s. No independent expected raw measurements were regenerated.

### Interim Captain Hindsight — observation and utility slice

**Keep:** Existing actor-event/aura primitives, strict coverage, per-raid policy
assets, saved analytical truth consumed by both pages, positive observations
under partial coverage, source/actor/target refs, and historical defaults.

**Fix before closing:** Global phase/immunity/targetability and fair opportunity
contracts, complete boss/class loadouts and personal coaching, recipient/ranking
reconciliation beyond the first supported cases, and all missing cell evidence.
This slice deliberately establishes local observations rather than claiming a
complete opportunity denominator.

**Record:** Simultaneous apply/remove event hash order is not semantics. Death/
resurrection needs a state boundary. Missing dispel metadata is distinct from
complete-stream absence; successful removal effects are distinct from casts.
Actual mobile review found repeated long limitations, which were grouped while
preserving individual facts. D008/ADR0015 retain these boundaries.

**Risk:** Actor-only data cannot prove dispel opportunities or downtime causes;
guide schedules and ranking categories cannot fill those gaps. PM-1/PM-2/PM-3
remain pending for the full subject and plan, with verified guardrails exercised
here rather than a final calibration or inherited acceptance.

**Verdict:** DO NOT CLOSE — complete the shared contracts and full domain/evidence
obligations before any whole box, subject or matrix cell is marked complete.

Final replay follow-up after the latest state-reset and malformed-metadata
guards: **18 passed/116.21 s**, all 16 immutable real captures. Four Naxx
artifacts again match the original source baseline exactly. Updated representative
page/viewport checks pass. Coverage remains 16 IN_PROGRESS/936 TODO/zero COMPLETE;
the strict completion command was explicitly checked to refuse with exit1.
These observations are a verified incremental implementation, not full subject
or per-cell acceptance. Magmadar research remains separate and unpromoted.

Verification follow-up: full ordinary suite **1248 passed, 262 deselected,
337.38 s**. After the independent checker's additional missing-amount guard,
22 focused cases and all 54 real raw actor facts pass; static checks remain
green. Schema currency passes. Current wheel/sdist build and isolated installed
strategy/scope imports pass; saved real JSON for all three raids renders both
pages/packages outside the checkout. Package/source and selected generated-output
secret scans pass. No task/workspace files are present in the sdist. New general
strategy is not a final release candidate or full evidence acceptance.

**Keep:** One existing analysis/render pipeline, per-raid rule ownership, static
strategy explicitly separate from observed facts, source links and class/metric
filters, old JSON unchanged on render, unchanged Naxx bytes.

**Fix before closing:** Complete all shared boxes, especially measured phase/
opportunity/ranking/duty contracts. Resolve the MC Fury-tank pressure counterexample
without silently changing Naxx or treating category as assignment. More source
and real-cell validation is required; current three strategies are initial scope.

**Record:** D006 sequences independent static work beside remaining evidence
contracts. PM-1's Report wiring risk was caught by actual content assertions;
successful transport/build tests alone did not detect it. Scope remains full.

**Risk:** Generic/class strategy is not complete loadout or personal coaching,
and no timing, immunity or assignment was inferred from a guide. Current ranking
policies remain unvalidated. Other boss strategy and real class cells are open.

**Verdict:** DO NOT CLOSE — this is an engineering checkpoint, not full subject,
raid, domain/product acceptance or publication.

2026-10-17 · slice 2 · checkpoint receipt · b25e8bb pushed, HEAD/origin/main matched and source tree clean. All verification above remains current; only documentation follows. Subject stays IN_PROGRESS with every full shared-contract box open, zero certified matrix cells, and no human sign-off inferred. Continue phase/opportunity/metric/duty work and the remaining evidence contracts.

Encounter-cache final checks:122 cache/fetch tests pass/1.58 s after adding
explicit null actor negatives in both legacy directions. Full ordinary suite
1333 passed/1 skipped/281 deselected in395.31 s before that test-only expansion.
Ruff/format/mypy/docs pass. All four Naxx artifacts again match30e89ce byte for
byte. Research receipts pass unlimited secret scan. Full MC Holy acquisition
is running through normal CLI with one observed-reset wait; currently quota
waiting, no archive or new evidence is counted. Checkpoint pushed separately.
