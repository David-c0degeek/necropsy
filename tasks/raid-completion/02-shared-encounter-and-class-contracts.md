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
