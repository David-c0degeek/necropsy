# 01 — Evidence, independent facts and complete scope

## Goal

Establish every boss/configuration obligation and a practical capture program. Freeze Naxx as the reference, acquire usable seed captures for each new raid, and expose remaining evidence gaps without blocking work on already evidenced bosses.

## Integration analysis

- Existing seams: `raids/`, `wcl/acquire.py`, `wcl/checkpoint.py`, `snapshot/v1_writer.py` under `src/necropsy/`; `tests/golden/*/PROVENANCE.md`, `tests/golden/haplina_naxx/facts.yaml`, `tests/fixture_paths.py`, `scripts/fixture_tools.py` and golden/acceptance markers.
- Preserve immutable revisions, ownership, stream/member digests, private fixture policy, user-endpoint auth, quota and resume. Reuse the client/cache/writer and fixture tools; no second downloader or raw parser.
- Durable fixtures/fact checkers belong at those seams; the plan CSV is tracking only. Confirm the detailed prior-art map after 00 before ticking boxes. PM-1/PM-3 apply.

## Boxes

- [x] **01.1** (agent) Reconcile all 28 new WCL entries, 27 canonical bosses, 34 legal category/metric/faction configurations and 27 declared trees against current metadata. Produce a durable supported-scope manifest and reconcile every seed matrix row, including combined dragons (PM-1/PM-3).

- [x] **01.2** (agent) Freeze the Naxx reference: definitive content inventory, existing facts, historical/live/legacy archives, all class fixtures, both pages and package expectations. List actual accepted gaps instead of claiming universal prior validation.

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

2026-10-17 · slice 1 · 01.1–01.8 · Added packaged scope (28 encounters × 34 legal configurations = 952), developer coverage register/checker with strict missing/illegal/duplicate/hash/content/actor guards, independent raw-fact checker and mutation tests. Frozen 101 Naxx rule/fixture/provenance/oracle files (153,207,138 bytes); current hashes unchanged. Fresh 60 first-page category/metric pools across all three raids expose real candidates, including sparse combined pools and misleading guild-faction metadata (not actor proof). Public complete-raid metadata identifies every MC/AQ boss and BWL combined variant; individual dragon sources remain a separate acquisition requirement. Captured/finalized three public six-actor seeds (Holy Lucifron, Holy combined dragons, Hunter Viscidus); 18 independent raw cases; raw/generation/member/owner provenance frozen, 113,744,740 extracted bytes scanned by unlimited gitleaks, no leaks. New golden checks: 5 passed/28.86 s including all three offline replays, both pages/packages and exact raw measurements. Structural/semantic negatives and raw checks: 17 passed; installed scope/rules 9 passed; static checks pass. Matrix 3 IN_PROGRESS/949 TODO; strict gate exits 1 as required. Additional damage/tank/healing-family seeds in progress; no cell/domain completion claimed. Full ordinary baseline rerun 1227 passed/418.57 s. Existing golden: 244 passed/4 xfailed/1 browser-test defect; D005 repairs real local cross-page navigation validation, targeted rerun pending. Checkpoint pending; subject remains open for remaining contracts/capture families/review.

Scope and independent-reference inventory are complete for 01.1; evidence/core
contracts remain in progress for other boxes. No runtime encounter changes or
new complete-support claim in this checkpoint. Maintained docs/raids and fixture
README/PROVENANCE describe the exact delivered validation limits.

2026-10-17 · slice 2 · 01.2–01.8 · Expanded to nine immutable public six-actor seeds and 54 frozen independent raw cases: damage, healing and Protection categories across all three raids. Real BWL/AQ Protection samples currently infer tank; MC samples instead expose repeated boss melee with Fury actions but a current DPS inference, retained as a duty counterexample rather than approved ground truth. Additional Guardian capture stopped at 80% quota during finalization; a retry under the existing standard 90% policy also stopped (159 points remaining versus 162 conservative unknown-cost reserve). No ZIP or acceptance is claimed for that attempt; preserve requests/cache and resume after reset. All nine archive/member manifests and public visibility verified; 301,461,037 extracted raw bytes scanned, no leaks. Initial installed raw replays outside checkout cover all three raids, matching zone IDs and both pages/packages. Current installed module/rule probe and saved-JSON renders also pass after strategy work. Both Naxx pages, JSON and package are byte-identical to source 30e89ce replay; 101 frozen Naxx hashes remain unchanged. Full baseline follow-up 1248 passed/262 deselected/337.38 s; current strategy units + all nine real replays/content/source/package checks 16 passed/69.17 s; raw mutation/coverage checks pass. Structural browser checks cover 12 page/viewport combinations with print/no-network/no-overflow; representative visual review is explicitly limited. Inventory remains 9 IN_PROGRESS/943 TODO, zero COMPLETE; strict gate correctly exits 1. Checkpoint pending. 01.3–01.8 remain open for the complete schedule, phase/duty/guidance fact contracts, fast subsets, exhaustive content gate and capture backlog. No blanket subject closure.

## Resume anchors

2026-10-17 · slice 4 · Guardian evidence and phase research · Resumed retained
MC capture after quota reset with the normal 90% policy; completed MC, combined
BWL and Viscidus Guardian captures, six usable sources each. Appended 18
direction-only independently enumerated actor cases without regenerating the
original 54; union checker verifies all 72. Inventory 12 IN_PROGRESS/940 TODO,
zero COMPLETE. All 81,152,275 extracted Guardian raw bytes scanned with unlimited
gitleaks 8.30.1, no findings. Live phase-schema/report probe records null phases
for every MC/AQ boss and only initial BWL Razorgore/Nefarian markers, not a usable
physical opportunity contract. See research/phase-observations.json. BWL Guardian
sources also expose Ebonroc healing attributed to tanks; recipient/ability
semantics must precede HPS reconciliation. Real replay follow-up running.

- Current normal-source evidence: tests/golden/raids/{provenance,facts,coverage}.json
  and raw/*.zip plus manifests; exact commands in master §2 and fixture README.
- Naxx reference and exact replay receipt: naxx-reference.md and
  research/naxx-foundation-replay.json. Source baseline is 30e89ce, not the older
  0.3.1 taxonomy-preview output (not comparable).
- Further investigations: domain-observations.md, research/candidate-inventory.json
  (60 category/metric first-page pools), research/raid-report-inventory.json.
- Pending Guardian retry: ignored workspace/raid-research/capture_guardian_seed.py,
  mc-guardian/requests and shared cache. This is acquisition-library/request-journal
  verification, not a substitute for the later actual GUI/CLI quota-resume gate.
- Continue shared measured phase/opportunity/metric/duty contracts and full
  evidence coverage. Initial static strategy is governed by D006; it does not
  close phase or per-cell guidance obligations.

2026-10-17 · slice 3 · durable checkpoint receipt · Evidence and initial strategy changes committed and pushed as b25e8bb (following 9ab2a29, a0b6553 and 9aded83). Local HEAD equals origin/main and working tree verified clean before this receipt. Latest targeted verification: 22 passed/3.63 s plus all 54 raw fact cases; strict completeness refusal explicitly verified at 9 IN_PROGRESS/943 TODO/0 COMPLETE. No additional acquisition, evidence waiver, acceptance or publication in this receipt. This documentation-only receipt is checkpointed separately.
