# 02 — Shared encounter and class contracts

## Goal

Extend the existing engine so mechanics alter measurements and guidance for every class/role. Keep raid policies modular, event/class primitives shared and presentation a consumer of analytical truth.

## Integration analysis

- Existing seams under `src/necropsy/`: `analysis/encounters/`, `analysis/context.py`, `analysis/generic/targets.py`, `analysis/benchmark.py`, `analysis/classes/classic_era/`, `analysis/{gamedata,guidance,recommendations}.py`, `report/{analysis_json,combat,druid}.py` and the renderer.
- Preserve graded evidence/coverage/refs, class/category/build/duty distinctions, known-sample thresholds, recorded versus reconstructed scores, deterministic schema and old rendering. Current guidance is Hunter-oriented; extend typed advice for other roles rather than cloning a Hunter engine per raid.
- Raid modules own facts, targets, phase policies and applicability. Shared event/opportunity primitives use existing seams. No parallel renderer, duplicate metric engine or template-computed advice. Inspect versioned/optional compatibility before coding. PM-1/PM-2 apply.

## Boxes

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

TBD — no implementation or runtime acceptance is claimed at plan creation.
