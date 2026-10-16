# 01 — Evidence, independent facts and complete scope

## Goal

Establish every boss/configuration obligation and a practical capture program. Freeze Naxx as the reference, acquire usable seed captures for each new raid, and expose remaining evidence gaps without blocking work on already evidenced bosses.

## Integration analysis

- Existing seams: `raids/`, `wcl/acquire.py`, `wcl/checkpoint.py`, `snapshot/v1_writer.py` under `src/necropsy/`; `tests/golden/*/PROVENANCE.md`, `tests/golden/haplina_naxx/facts.yaml`, `tests/fixture_paths.py`, `scripts/fixture_tools.py` and golden/acceptance markers.
- Preserve immutable revisions, ownership, stream/member digests, private fixture policy, user-endpoint auth, quota and resume. Reuse the client/cache/writer and fixture tools; no second downloader or raw parser.
- Durable fixtures/fact checkers belong at those seams; the plan CSV is tracking only. Confirm the detailed prior-art map after 00 before ticking boxes. PM-1/PM-3 apply.

## Boxes

- [ ] **01.1** (agent) Reconcile all 28 new WCL entries, 27 canonical bosses, 34 legal category/metric/faction configurations and 27 declared trees against current metadata. Produce a durable supported-scope manifest and reconcile every seed matrix row, including combined dragons (PM-1/PM-3).

- [ ] **01.2** (agent) Freeze the Naxx reference: definitive content inventory, existing facts, historical/live/legacy archives, all class fixtures, both pages and package expectations. List actual accepted gaps instead of claiming universal prior validation.

- [ ] **01.3** (agent) Inventory authorized real reports across all three raids, factions, categories and duties. Create a deduplicated roster-based capture schedule prioritizing every boss and rare healing/tank categories; record quota bounds, permissions, missing sources and exact resume commands.

- [ ] **01.4** (agent) Acquire usable seed fights for each raid and role family through existing client/cache/checkpoints. Record source dates, partition/revision, selection, actor source/target streams and ownership. Budget-only snapshots do not satisfy this box.

- [ ] **01.5** (agent) Create frozen per-raid fixtures, provenance/member-hash manifests and permitted fast subsets with an independent boss fact check per raid. Keep full captures in authorized storage; verify installed/offline reading and scan raw/generated data under existing privacy/secret policy.

- [ ] **01.6** (agent) Implement independent fact-register/checker contracts for amounts, durations, targets, casts/timings, phases, duties and guidance conclusions. Expected values must not call production analyzers; demonstrate that deliberately wrong inputs fail (PM-3).

- [ ] **01.7** (agent) Implement a durable coverage/content checker mapping matrix obligations to actual rule/source/test/review refs. Distinguish implementation, synthetic verification, real verification and acceptance; empty/generic-only raids cannot pass and sparse samples cannot be fabricated (PM-1).

- [ ] **01.8** (agent) Populate exact capture, matrix, oracle, integrity and acceptance commands in the master table. Publish the evidence backlog and safe capture order; later raid/class subjects own completing all their rows.

## Hindsight checkpoint

Use the master plan’s embedded prompt. Record Keep / Fix before closing / Record / Risk / Verdict; calibrate relevant PM predictions without rewriting them.

- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log

TBD — no implementation or runtime acceptance is claimed at plan creation.
