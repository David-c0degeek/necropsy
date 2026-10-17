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
