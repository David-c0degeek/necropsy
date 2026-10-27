# NaxxCompletion-Plan.md — Complete Classic Era Naxxramas for every class, spec and faction

> **Status: IN_PROGRESS — subjects 00–01 complete; eight exact-cell DPS policies recorded; v3 target derivation verified in code; shared quota fix prepared; release/image rollout pending; local inference off.** Created 2026-10-21.
> **Purpose.** Bring Naxxramas (zone 2006, 15 bosses) to the layer-based
> completion bar that the parked raid work reached for Molten Core: every legal
> boss × configuration cell COMPLETE with real actor evidence, raw-first
> independent facts, sourced boss × class guidance, a validated ranking policy,
> a clean render receipt and a verified batch registration. MC, BWL and AQ40 are
> parked (D001), not abandoned.
>
> **Disposable.** The plan and its `tasks/naxx-completion/` folder are deleted (or
> archived out of the repo) once the subject ships. Deleting or archiving is
> human-owned and happens only after §8 sign-off. Shipped code, comments, tests,
> identifiers and commit messages must not reference them (§6.11). Commit the
> folder while the plan is live so it is resume-safe (§6.14).

> **Terms.** Subject, Box, Slice, Checkpoint and Collaboration mode mean what they
> mean in `tasks/RaidCompletion-Plan.md`. **Cell**: one Naxx encounter × one legal
> configuration (class, WCL category, metric, faction). **Work order**: one bounded,
> machine-checkable task for the local runner (§6.20).

## Collaboration model

| Field | Value |
|---|---|
| Mode | `coordinated` (Claude/Codex pairing restored 2026-10-26, D018) |
| Primary owner | Codex (shared-tree writer for the controller/release unit after handoff epoch 4) |
| Coordinator | Codex |
| Resume safety | required |
| Parallel branches | `no` — the local runner writes drafts outside the repository only |
| Notes | The pair session is active again under D018. **Codex** owns controller implementation, release preparation and UI/UX; **Claude** is the required reviewer and retains live Tower operations until fixed-image handover. Ownership moves only through explicit pair handoff. D013 records the historical solo interval, not current authority. **Local runner** remains OFF under D016 and is no dependency or reviewer. Future explicitly requested LocalBox use must select an available saved balanced tune and verify its effective launch arguments. Tower uses the reviewed queue; final Naxx product acceptance remains open. |

### Parallel work tracker

n/a in `coordinated` mode.

### Checkpoint gate

As in `tasks/RaidCompletion-Plan.md` (box, Progress log, §5 tracker, verification
or exact blocker, behaviour verification, doc-currency, commit and push, no
history rewrite, plan-agnostic commit text), plus:

- `uv run python scripts/pre_review.py --full` before every push to main, with the
  worker count recorded (§2).
- `uv run python scripts/check_raid_coverage.py --inventory --staged` before every
  register commit.
- A work-order result enters the tree only after its verifier passes and the
  writer has read it; the verifier output is cited in the Progress log.

---

## 1. Subject

Complete **Naxxramas, all 15 encounters** (Patchwerk, Grobbulus, Gluth, Thaddius,
Noth, Heigan, Loatheb, Anub'Rekhan, Faerlina, Maexxna, Razuvious, Gothik, Four
Horsemen, Sapphiron, Kel'Thuzad) for **all 34 legal configurations** (nine classes,
their WCL category pools, DPS/HPS metrics, legal factions: Paladin Alliance,
Shaman Horde), on the Era partition chosen in 00 (seed: partition 1). That is
15 × 34 = **510 cells** (recounted in 01). Each cell needs: real public actor
evidence; independent raw facts (actor, and recipients for HPS); sourced
boss × class guidance with race/faction limits; a validated ranking policy with a
raw-frozen oracle; a clean source-versus-installed render receipt; a batch
registration that `check_raid_coverage` verifies. Existing Naxx behaviour (saved
analyses, legacy pages, Hunter/Druid/class fixtures) is preserved.

**Out of scope:** MC, BWL, AQ40 (parked, D001); other raids, rulesets, Season of
Discovery, Anniversary; automatic talent diagnosis; universal quality scores;
promised gains.

### What FULLY implemented means

The D036 layers (see `scripts/raid_batch.py` and `tasks/RaidCompletion-Plan.md`
D036) applied to Naxx: **every applicable cell COMPLETE**. OPEN tracks progress
only; an OPEN cell (for example, scarce logs) is an explicit blocker to full
acceptance, never a reduced denominator. Partial delivery would need a separate,
explicit owner scope decision and could not be called full completion. Prior Naxx acceptance (AllClasses/ClassExpansion, 2026-10-15) is
**not inherited** (D005): its accepted limits (Holy Priest fixture without live
healing evidence, retired Druid SME review) are re-opened as cells. Lack of logs is
OPEN, never N/A; N/A needs ruleset illegality or demonstrated WCL unavailability
with a source.

### Risks and rollback

| Risk | Impact | Mitigation / rollback |
|---|---|---|
| Adding Naxx strategy and cells changes existing Naxx pages | Saved analyses and legacy views regress | Naxx legacy/live/browser/package controls in every gate (§2); additive rules; byte-compare saved-output replays; revert the module change. |
| Local runner output is wrong but plausible | Bad facts or advice enter the tree | Work orders produce drafts only; every field has a machine verifier; raw oracles are independent of the analyzer; Claude reads and Codex reviews every content diff. Revert the batch. |
| Content errors in class/race/faction capability | Misleading coaching | Capability source ledger per class; guidance_lint; review checks every claim against its excerpt. |
| PC memory instability corrupts evidence or gates | False failures, or worse, bad bytes | XMP off before start (owner); trusted baseline in 00.3 before any evidence work (D004); hashes and pins catch later bit flips but not corruption before hashing; Tower and CI provide second hosts. |
| WCL quota limits captures | Cells stay OPEN for want of logs | One reviewed queue on Tower using the whole quota; reuse existing archives; quota stops resume. |
| Naxx DPS ranking needs a policy family not built yet | DPS cells cannot validate | 05 builds the DPS generator first on one boss and proves it against raw before scaling. |

---

## 2. Authoritative inputs

| Source | Contribution |
|---|---|
| Owner instructions, 2026-10-21 | Park MC/BWL/AQ40; complete Naxx to the highest standard; use local AI where realistic; XMP off before starting |
| `tasks/RaidCompletion-Plan.md` (D034–D036), `tasks/raid-completion/lessons.md`, `review-checklist.md`, `naxx-reference.md` | Proven process, completion layers, review rules, lessons |
| `tasks/AllClasses-Plan.md`, `tasks/ClassExpansion-Plan.md`, `tasks/necropsy/05-naxx-encounters-and-recommendations.md` | Existing Naxx scope and its accepted limits (not inherited) |
| `src/necropsy/rules/classic_era/zones/naxxramas*.yaml`, `src/necropsy/raids/`, `analysis/encounters/strategy.py` | Current Naxx rules: facts for 15 bosses, guidance for 8, no `strategy` items; `encounter_strategy` returns None for Naxx |
| `tests/golden/haplina_naxx/`, `tests/golden/druid/`, `tests/golden/classes/` | Existing Naxx real fixtures and provenance |
| `scripts/raid_batch.py`, `check_raid_coverage.py`, `unit_preflight.py`, `render_parity.py`, `fact_freeze.py`, `freeze_hps_ranking.py`, `capture_queue.py`, `capture_runner.py`, `guidance_lint.py`, `pre_review.py` | Reused tooling |
| `D:/repos/LocalX/LocalPilot/docs/10-decisions.md`, LocalHub pair-seat baseline 2026-10-02 | Local model evidence: Qwen3.6 35B-A3B 22/24 agent tasks at 64k; clean-review false REVISE 1 in 3; Ornith 35B used project context 0/30 |
| `unraid-tower` changes/2026-10-21-necropsy-capture-parked.md | Tower state and restart path |
| [WCL API](https://www.warcraftlogs.com/api/docs), [Vanilla ranking guide](https://vanilla.warcraftlogs.com/help/ranks) | Primary contracts |

### Verification commands

| Purpose | Command | Notes |
|---|---|---|
| Locked setup | `uv sync --locked` | |
| Lint / format / types | `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy` | |
| Pre-review gate | `NECROPSY_GATE_WORKERS=N uv run python scripts/pre_review.py --full` | N recorded; 8 only after 00.3 passes |
| Ordinary suite | `uv run pytest -m "not golden and not live and not acceptance"` | |
| Golden | `uv run pytest -m golden` | Naxx fixtures included |
| Coverage register | `uv run python scripts/check_raid_coverage.py --inventory --staged`; `--require-complete` (Naxx scope, 01) | |
| Batch | `uv run python scripts/raid_batch.py write SPEC`; `digests CELL` | |
| Receipt | `uv run python scripts/render_parity.py ARCHIVE --entries E --commit REV --out DIR` | |
| Naxx compatibility | `uv run pytest -m golden --ignore tests/golden/test_raid_evidence.py -n 8 --dist worksteal -rfE` (Haplina, Druid and class replays, saved-output and browser checks); `uv run pytest -m browser -rfE`; `uv run pytest -m acceptance`; package: `tests/unit/test_rules_package.py`, `test_distribution_artifacts.py`, `test_release_bundle.py` (in the CI fast suite) | No gate runs the browser suite unless a browser test file changed; run it at every 01 checkpoint |
| Work-order verifiers | TBD in 02 | |
| Local runner | TBD in 00.4 (`localbox serve …`, LocalPilot headless invocation) | |

---

## 3. Subject file index

| # | File | Subject | Depends on |
|---|---|---|---|
| 00 | `tasks/naxx-completion/00-tooling-research-and-readiness.md` | Readiness: hardware, baseline, local runner trial, Naxx inventory, pre-mortem | — |
| 01 | `tasks/naxx-completion/01-naxx-register-and-strategy-seam.md` | Naxx cells in the coverage register; strategy layer for Naxx without regressions | 00 |
| 02 | `tasks/naxx-completion/02-local-work-orders.md` | Work-order format, drafts area, verifiers, LocalPilot runner | 00 |
| 03 | `tasks/naxx-completion/03-naxx-captures.md` | Naxx capture queue, Tower run, intake and provenance | 01 |
| 04 | `tasks/naxx-completion/04-boss-research-and-raw-facts.md` | Boss-major sources, raw discovery, frozen facts | 01, 02, 03 |
| 05 | `tasks/naxx-completion/05-ranking-oracles.md` | HPS and DPS ranking policies with raw-frozen oracles | 02, 03 |
| 06 | `tasks/naxx-completion/06-content-receipts-and-batches.md` | Boss × class content, receipts, batch registration | 04, 05 |
| 07 | `tasks/naxx-completion/07-product-acceptance.md` | Pages, installed build, Naxx controls, release, owner acceptance | 06 |

---

## 4. Decision log

| ID | Date | Title | Decision | Rationale | Refs |
|---|---|---|---|---|---|
| D025 | 2026-10-27 | Exclusion-neutral comparison admission at bosses with production exclusions | In the follow-up register, a comparison at a boss with production `ranking_exclusions` is admitted only when the DPS freezer admits it with the exact packaged exclusion list as explicit input AND its excluded damage is exactly 0. The ranked amount is then the same with or without the list. Positive excluded damage, or an arithmetic mismatch under the untested list, stays unverified (typed), never refused as poor quality and never admitted. Evidence or ownership failures stay refused. No other list is ever substituted. This neither validates the exclusion lists nor certifies a cell; cell policies for these bosses are separate. | Probe (research/exclusion-test-20261027/): 28 of 30 attempts admit with excluded damage 0 either way. Codex DESIGN_AGREED mailbox 133 | D022; D024; PM-51..53 |
| D024 | 2026-10-27 | Defer the targeted follow-up behind exclusion admission | D023 stays the agreed design but is not built now. Its first slice (supplement schema, writer, reader, freezer path, tests) is parked unmerged as a patch. Codex CHALLENGE (mailbox 131) showed that the reader does not yet strictly prove raw evidence; a shared raw-proof refactor of the strict reader is needed first. That makes D023 a multi-day build that today helps 2 cells. Next comes admission for the 5 bosses with production ranking exclusions, which every configuration needs. D019 stays not fully operational. | Owner, 2026-10-27, chose "Defer follow-up (Recommended)" | D019; D023 |
| D023 | 2026-10-27 | Targeted follow-up as a separate supplement archive | Cells short of admitted comparisons get a `necropsy.live-supplement` archive per cell. It has its own strict reader, and `open_snapshot` refuses it. It takes candidates one at a time from a fresh identity-based ranking ledger in unchanged rank order, admits each by the DPS freezer's real supplement path, and stops at the minimum, the attempt limit, exhaustion or quota. Every started deep attempt counts against the limit. Report generations are sealed per candidate. The detector re-admits the source and the whole chain from bytes. Offline first; runner and queue integration is a separate checkpoint, and the spending ceiling goes to the owner. | Codex CHALLENGE mailbox 129, DESIGN_AGREED mailbox 130; research/followup-supplement-design-20261027.md | D019; D022; PM-47..50 |
| D022 | 2026-10-27 | Fight-scoped catalog pets in DPS admission | A report-catalog pet owned by the comparison actor is out of scope for the selected fight only when it is absent from the fight's friendlyPets and has no source or target event in that fight's encounter-All pages. The DPS freezer certifies those pages itself. Anything else still refuses. Ownerless active guardians (Battle Chicken, Arcanite Dragonling, Summoned Skeleton) stay unresolved, and arithmetic fit never decides ownership. The old check is unchanged where the catalog and fight listings already agree. | Step-1 diagnosis (research/followup-pet-diagnosis-20261027/): 11 refusals came from catalog pets that never appeared in the fight. Codex DESIGN_AGREED C1 only (mailbox 125) | D019; PM-43..46 |
| D021 | 2026-10-27 | Tower verification substitutes for the replacement-memory baseline | Evidence and releases may proceed on work verified on Tower, which does not have the PC's memory fault. Work counts as verified when the exact tree is rebuilt there and passes the full gate, the golden suite and the browser suite. The PC still produces no evidence until its replacement memory passes the 00.3 baseline. The D020 receipt re-verification ran on Tower over every path changed in cc637a7..1951472 (766 paths). Its fail-closed manifest is in `research/receipt-reconciliation-20261027/`. No corruption is demonstrated in the reproduced subset; this does not verify every record. Four records could not be reproduced: the three `production-followup-20261024` records and the findings prose of `journal-conflict-followup-20261022.json`. They stay as unverified historical observations, and no acceptance decision may rest on them. D020 is otherwise unchanged. | Owner: "tower is on a different machine though, no memory issues there"; on 2026-10-27 the owner chose that Tower verification counts, and that the unresolved records are kept and flagged | D020; D004; D006 |
| D020 | 2026-10-26 | Known faulty PC memory: pause local evidence until replaced | A nondeterministic corrupted byte in a test's own temporary ingest file, under 8-worker load (golden bwl-holy-raid-context; it passed in the previous gate and 3 of 3 serial reruns), reopens D004. The owner reports the memory as known faulty, with an RMA on 2026-10-27. No new local evidence, commits of evidence-bearing work or releases until the replacement memory passes the 00.3 baseline. All research receipts committed since 2026-10-21 are then re-verified in check mode, and any that does not reproduce is regenerated. Tower and GitHub CI stay the independent hosts. The failure log is kept in workspace/corruption-20261026/. | Owner: "hardware issue is known and memory is getting RMAed tomorrow" | 00.3; D004; D006 |
| D019 | 2026-10-26 | Three comparisons per boss with a targeted follow-up | The live cohort depth drops from 5 to 3 comparison players per boss, for every Era raid. Selection stays top-ranked and same-faction; a wider rank window was declined. The reader accepts archives at the current depth 3 and the historical depth 5 only. A deterministic detector lists configuration and boss cells whose admitted comparisons, using the existing DPS and HPS admission, fall below the policy minimum of 3. A later targeted capture adds comparisons for exactly those cells, and A is not fully operational until that path exists. Released 0.7.0 readers reject depth-3 archives. | Owner: "A - approved. Mark bosses without enough valid comparisons for a followup - where we take more comparison players. B - Deny - we're trying for top". Leaderboard overlap measurement 1951472 found about 2.5% fight coincidence at comparison depth. | 03; 05; 06 |
| D018 | 2026-10-26 | Restore pairing and authorize operational follow-through | Claude/Codex pairing is active; after epoch 4 Codex owns the quota-controller fix and release preparation, Claude reviews and retains live Tower operations until fixed-image handover. Owner approved the fixes, release and Tower image rollout; normal artifact verification and state backups remain. After that, investigate fight-centric reuse combined with report batching, starting with a measured offline estimate. No WCL limit request and no local inference. | Owner decisions relayed in pair mailbox claude:42; previous code units independently reviewed and pushed as 7eb1a03, 96f728c and 3062569. Product acceptance is separate. | 03–07; manual-actions.md |
| D017 | 2026-10-23 | Independent Codex restart review | Use a separate Codex reviewer for the prepared queue/image and associated operational fix while Claude is unavailable. Root remains sole writer. Retain actual read-only verdicts and existing restart conditions; no content/cell/product acceptance is waived. | Owner answered "Use a separate Codex reviewer" to the explicit reviewer question. | 03; research/independent-queue-review-20261023.json |
| D016 | 2026-10-22 | Remove unproven local inference from active Naxx work | Keep local AI off and schedule no further local-model experiments for this plan. Codex continues implementation, source/content work and verification. Preserve failed trials and useful verifier tools; do not present local inference as a completion dependency or independent review. A future explicitly requested model use still requires the saved balanced tune and verified effective arguments. | Owner: "if the local AI gives no value, i dont see the point. next?" Both tested work kinds failed acceptance, current guidance drafts already exist and no critical-path task requires inference. | D009; D013; D015; 02–07 |
| D012 | 2026-10-21 | Codex accepts implementation ownership | Codex is the sole shared-tree writer and coordinator after pair handoff epoch 2 at 10ba2f2. Continue the owner-authorized 0.6.0 release, then measured Naxx v2 acquisition and remaining subjects. Claude remains required reviewer in the harness; LocalPilot remains advisory under D009. Tower restart and final acceptance remain owner gates. | Claude relayed owner instructions: "codex will take it from here with localpilot" and "Cut v0.6.0 release"; mailbox claude:14/15, handoff-2026-10-21-codex.md. | 01–07 |
| D013 | 2026-10-21 | Codex continues while Claude has no usage | Continue implementation solo as directed by the owner. Record Claude as rate-limited and park the existing pair session, retaining its pending reviews without manufacturing approval. This supersedes the requirement to await Claude before ordinary implementation; it does not promote LocalPilot to reviewer, waive capture validation or authorize final product acceptance. The conditional Tower restart prerequisites remain recorded and must be satisfied before production restart. | Owner: "since Claude has no more usage - you need to pick up where we left off". | 02–07 |
| D014 | 2026-10-21 | Freeze the guidance trial threshold before running it | Ten bounded Sapphiron guidance drafts use native tool-free LocalPilot `ask`, loopback-only provider configuration, 600 seconds and 4096 output tokens per order. At least 9/10 must pass the independent machine verifier; any fabricated/misattributed material claim on coordinator review, out-of-scope tree mutation or unreviewed promotion rejects the work kind. Usage counts stay unknown if the runtime does not expose them. Rejected drafts are not repaired into passes. | Codex coordinator implementation choice under the owner's autopilot direction; `02-local-work-orders.md`, PM-4 and the existing pre-trial proposal. | 02.1–02.4 |
| D015 | 2026-10-21 | Reject bounded guidance delegation after its frozen trial | Keep guidance drafting with Codex under D013: only 2/10 original machine passes, unsupported claims and a positioning-boundary miss on content review. Preserve all first attempts, no repaired retries and no production promotions. Always select available saved balanced LocalBox tunes as directed by the owner; mixed-profile trial results do not establish a tune comparison. | `naxx-completion/research/guidance-trial-results.json`; owner: "always use localbox balanced tunes if they exist - remember this". | 02.3; 04–06 |
| D001 | 2026-10-21 | Park MC/BWL/AQ40; Naxx first | MC/BWL/AQ40 work stops after the D036 (a)/(b) landing (main 2bc1a30, 821e67f). Their register, closures, batch and Tower archives stay as they are; nothing is deleted. The Tower runner is stopped and its watchdog disabled (unraid-tower c779d5b); it restarts only with a reviewed Naxx queue. | Owner: "Park MC, BWL and AQ40. Lets fully complete Naxx to the highest standard." Answered: stop Tower now and requeue Naxx; land D036 first. | RaidCompletion-Plan; 03 |
| D002 | 2026-10-21 | Completion bar | Naxx cells use the D036 layer model unchanged: engine digest, receipt per capture, content digest per boss × configuration, batch manifest. Extensions go into the same tools, not copies. | Proven on 17 MC cells; one bar for all raids. | 01; 06 |
| D003 | 2026-10-21 | Three-seat work split | Local runner (Qwen3.6 35B-A3B on LocalBox, LocalPilot) executes work orders and drafts; Claude specifies, verifies, extracts sources, writes the tree and reviews content; Codex reviews batches. Ornith 35B is not the runner (used injected project context 0/30). The local runner's review verdicts are advisory only. | Owner question and setup, 2026-10-21; LocalX evidence in §2. Expected: frontier use roughly halved, not removed. | 02 |
| D007 | 2026-10-21 | Autopilot split across three seats | Extends D003. One three-party pair session (`start --with codex,localpilot --advisers localpilot`): Claude owns and is the only tree writer; Codex is the required reviewer; LocalPilot joins natively (`localpilot mesh run --role localpilot`) as an adviser whose verdicts never count. Work by seat. **Claude:** 01 code (register, strategy seam, 01.5 encounter context), work-order specs and verifiers (02), intake and batch writes, content review. **Codex** (read-only on the tree, drafts outside it): reviews every request; builds the independent raw oracles PM-3 needs (Four Horsemen, Gothik, Thaddius, Loatheb, Kel'Thuzad) from raw archives without analyzer imports; owns the 00.7 partition evidence and the quota-cost estimate; leads UI/UX review of Naxx pages. **LocalPilot:** 00.4 trial, then bounded work orders into `workspace/naxx-drafts/` (raw-discovery counts, fact-freeze specs, guidance drafts with quoted excerpts); advisory pre-screens of requests. Owner gates stay owner gates (03.3 Tower restart, 07.4 acceptance). | Owner, 2026-10-21: "Autopilot as much as you can. Split the work logically between you, codex and localpilot." | 00–07 |
| D008 | 2026-10-21 | Partition 1 only; 510 cells | This plan's scope is partition 1 (S0), 15 bosses × 34 configurations = 510 cells, all of which must be COMPLETE. Partition 2 (S0 without world buffs) is a separate, unimplemented extension: it needs signed fight-ID semantics verified against the API, request/response fixtures, and the partition in the cell identity before any cell is added. It is not unavailable and not N/A. No quota throughput is promised from the probe. | Codex 00.7 probe (research/partition-recommendation.md, 319 pinned JSON files: 317 API request records plus 2 derived summaries; 285.4 of 3000 points): partition 1 has rows in all 20 Patchwerk pools; partition 2 in 18 (Protection Paladin and Enhancement Shaman empty), and every non-empty partition-2 sample uses negative `report.fightID` (e.g. -29 for public kill 29), which `cohort.py:390` and `acquire.py` reject. | 00.7; 01.1; 03.1 |
| D009 | 2026-10-21 | Raw discovery stays with Claude after the local-runner trial | Work-order kind (a), raw discovery counts, moves back to Claude: the 00.4 trial passed 0 of 3 attempts. LocalPilot keeps the guidance-draft kind (c) for one measured trial in 02.3 and stays an adviser in the pair session only if that trial passes; until then it does not join. Claude and Codex absorb its share (D007): Claude raw discovery and fact freezes, Codex independent oracles as planned. | 00.4: Qwen3.6 35B-A3B APEX-I-Quality on LocalBox, LocalPilot `print` in an isolated folder. Attempt 1 (no shell): guessed the archive layout, script fails. Attempt 2 (two exact script grants): hit LocalPilot's 600 s cap after 109 tool calls, never found `masterData`. Attempt 3 (layout excerpts in the order): ignored them, invented event fields, wrote `{}`. The repository tree was unchanged after every attempt. | 00.4; 02 |
| D010 | 2026-10-21 | Parked MC batch goes stale under Naxx engine changes | D036 is unchanged: any package change outside the zone files changes every raid's engine digest, so the 17 MC cells completed through batch mc-healers-1 (of 26 COMPLETE MC cells in all) report "stale engine verification" from 01.1 on. They are re-attested by a new batch when MC resumes (D037), not after each Naxx change. Naxx sign-off uses `check_raid_coverage.py --raid naxxramas` (01.4); the unscoped inventory keeps reporting the stale MC cells honestly. | Adding Naxx to `raid_scope.yaml` (a package file) made the MC batch stale at once; re-attesting a parked raid on every Naxx change would cost four fresh renders each time. | 01.1; 01.4; D036; D037 |
| D011 | 2026-10-21 | Ranking reconciliation is cell-scoped only | `check_raid_coverage.ranking_problem` no longer accepts a raid-wide ranking rule: a cell's ranking dimension needs a validated metric policy scoped to exactly that cell. Before this, Naxx's `naxx-ranking-exclusions-v1` (basis empirical, validated on one Hunter capture's damage) would have passed every Naxx cell's ranking check, HPS included. MC, BWL and AQ40 rules are `unvalidated`, so no existing result changes. | Found while running `unit_preflight` on a Naxx unit in 01.3: Naxx cells listed no ranking problem. Matches the §7 gate (reconciled ranking policies for every configuration) and plan 05. | 01.3; 05 |
| D004 | 2026-10-21 | Hardware precondition and trusted baseline | Owner disables XMP before 00 starts. No new Naxx evidence is generated or accepted until 00.3 establishes a trustworthy baseline on the selected host and settings. Failures are classified and all are kept: ordinary assertion failures (code defects) versus suspected corruption or native crashes (garbled bytes, access violations, stdout-less exits, nondeterministic subset failures). Fewer workers alone does not establish stability; a later pass never overrides an earlier failure. Hashes catch corruption only after hashing, so evidence produced on an unstable host is regenerated, not reused. | 2026-10-20 bit flip ("nuln") and access violations under 8-way load; 2026-10-21 serial `check_raid_coverage --inventory` at 83d1b1d: one run 9 unexplained, nondeterministic subset failures (cause and factual validity unestablished), one clean, one died without output (Codex #196). Root cause unconfirmed. | 00.3 |
| D006 | 2026-10-21 | Baseline trusted; gate workers stay 8 | The PC with XMP off (2133 MT/s JEDEC) is the trusted host for Naxx evidence. `NECROPSY_GATE_WORKERS` default stays 8. Any later suspected-corruption failure reopens D004. | 00.3 at cc637a7, all seven runs exit 0: three 8-worker seed gates (52 passed each, 4:56 to 5:19), three serial inventories (byte-identical logs, 26 COMPLETE, 0 problems), CI fast suite (2559 passed, 29 skipped). Logs in `workspace/naxx-baseline-20261021/` (summary.tsv). | 00.3 |
| D005 | 2026-10-21 | No inherited Naxx waiver | Prior Naxx acceptance does not complete any cell. Its limits become OPEN cells to close. | Highest-standard instruction. | 01 |

---

## 5. Master progress tracker

| Done | # | File | Status | Owner summary | Human actions mirrored? |
|---|---|---|---|---|---|
| [x] | 00 | `00-tooling-research-and-readiness.md` | DONE | agent; product-owner (XMP) | yes |
| [x] | 01 | `01-naxx-register-and-strategy-seam.md` | DONE | agent; released 0.6.0, close-out recorded | n/a |
| [ ] | 02 | `02-local-work-orders.md` | IN_PROGRESS — verifiers and510 drafts prepared; inference removed under D016; independent review open | agent; product-owner (local inference hold) | yes |
| [ ] | 03 | `03-naxx-captures.md` | IN_PROGRESS — real v2 smoke and independent queue/image review passed; production restarted, 34 quota-deferred; capture/intake open | agent; product-owner (Tower restart) | yes |
| [ ] | 04 | `04-boss-research-and-raw-facts.md` | IN_PROGRESS — new-v2 NPC and actor positive facts replay; semantic/source approval open | agent | n/a |
| [ ] | 05 | `05-ranking-oracles.md` | IN_PROGRESS — 49 new-v2 arithmetic matches/40 ownership refusals, separate 39 v1 matches; exact-cell/HPS policies open | agent | n/a |
| [ ] | 06 | `06-content-receipts-and-batches.md` | IN_PROGRESS —510 source-bound drafts and layout packet prepared; independent content approval/batches open | agent | n/a |
| [ ] | 07 | `07-product-acceptance.md` | IN_PROGRESS — legacy and real-v2 installed/visual controls pass; all-class final acceptance open | agent; product-owner | yes |

---

## 6. Cross-cutting principles

1–17 as in `tasks/RaidCompletion-Plan.md` §6 (same numbering; 2–4 struck), with
`tasks/naxx-completion/` and `NaxxCompletion-Plan.md` in place of the raid-completion
paths. Plan-specific:

18. **Independent module, shared engine.** Naxx policy lives in the Naxx zone files; class, event, coverage and rendering stay shared. No Naxx branches in class plugins.
19. **Full scope requires evidence.** Empty facts, generic advice and synthetic-only or budget-only snapshots cannot close a cell. Missing logs are OPEN.
20. **Work orders are bounded and checkable.** Each has an input bundle (paths, hashes, source excerpts), an exact output schema, a verifier command and a time cap. The runner writes only under `workspace/naxx-drafts/`. A draft without a passing verifier is discarded, not repaired by hand in the tree.
21. **Raw first, independent oracles.** Expected facts and ranking oracles are computed from raw events by scripts that do not import the analyzer, frozen before any policy uses them.
22. **Opportunity and assignment precede judgement.** Unknowns stay unknown; guidance only for unmeasured duties; recorded scores stay distinct from reconstructed totals.
23. **Throughput is a requirement.** Boss-major work is done once for every class; one review per batch; measure elapsed time per batch and report it.
24. **Pre-Mortem obligations live in `tasks/naxx-completion/pre-mortem.md`** (created in 00.6); every PM-* risk must have Plan refs and a non-Pending resolution before sign-off.

---

## 7. Gate review (run last; tick everything)

- [ ] All §5 subjects done or abandoned with a §4 row; subject 00 complete
- [ ] §2 commands pass, worker count recorded
- [ ] Behaviour verification recorded for every runtime change
- [ ] Risks-and-rollback reviewed; Integration analyses present; no undisclosed dead surface
- [ ] Every subject has Captain Hindsight verdict `CLOSE`
- [ ] Every ticked box has a Progress-log entry and a pushed checkpoint
- [ ] Durable decisions promoted to `docs/decisions/`
- [ ] Documentation-impact review done
- [ ] Plan-agnostic code, tests and commit messages (grep excluding `tasks/`)
- [ ] `manual-actions.md` resolved or deferred
- [ ] `cleanup-audit` run or waived; findings triaged
- [ ] Lessons migrated to `tasks/lessons.md`
- [ ] Every applicable Naxx cell (510, or the 01 recount) COMPLETE; `check_raid_coverage --require-complete` (Naxx scope) passes with no OPEN cell. Any OPEN cell blocks this gate unless a separate owner decision accepts partial delivery, which then cannot be called full completion
- [ ] Every boss has verified targets, sourced facts, boss × class guidance and reconciled ranking policies for every configuration
- [ ] Naxx legacy/live/saved-output, browser and package controls pass; intended changes reviewed
- [ ] Every PM-* risk has a terminal Resolution and Captain Hindsight calibration
- [ ] Owner product acceptance requested

---

## 8. Acceptance / sign-off

| Date | Reviewer | Result | Notes |
|---|---|---|---|
| | | | |

---

## Appendix: Captain Hindsight Prompt

> Embedded so the plan is self-standing.

```text
You are now Captain Hindsight.

Review the completed subject, phase, box, or major plan section with hindsight.
Assume the work is already done, then identify what is clearer now than it was
before the work started.

Check specifically for:
- Scope drift or missed requirements.
- If tasks/naxx-completion/pre-mortem.md exists, calibrate the PM-* risks relevant to this review target and append any unpredicted material failure as the next CH-MISS-*; do not rewrite the original prediction fields.
- Matrix closure without real actors/independent facts; generic-only advice; missing phase/assignment applicability; inherited Naxx waivers; ranking/variant contradictions and premature completion claims.
- Work-order output accepted without its verifier, or a local-runner verdict used as review.
- Regressions in existing Naxx pages or saved analyses.
- Spec deviations that need a Decision-log row (and whether the decision is
  durable enough to promote to the project's ADR / decision log).
- Lessons that should be recorded before context is lost.
- Tests that pin implementation details instead of observable behavior.
- Complexity, duplication, brittle design, or awkward naming that should be fixed now.
- Behaviour closed on a green build alone: a box marked done on a passing build/test exit code without the changed flow exercised end-to-end (observed-vs-expected output).
- Reuse missed or vision drift: new parallel code where existing code should have been extended, or a change that drifts from the project vision/ADRs (cross-check the subject's Integration analysis).
- Human-owned actions that need to be mirrored or resolved.
- Docs that drifted from shipped behaviour — user- and developer-facing alike (README, usage/HOWTO guides, CHANGELOG, API/command/config reference, architecture/onboarding docs, troubleshooting, examples, wiki, prompt/skill docs).
- Plan references that leaked into shipped code, tests, comments, identifiers,
  commit messages, branch names, PR titles, or PR descriptions.

Before returning a verdict, confirm the claimed verification against the
artefacts: rerun the relevant verification command or cite its recorded output.

Return exactly these sections:

1. Keep: what was correct and should remain.
2. Fix before closing: concrete issues, missing tests, spec drift, plan hygiene, or design problems — cite the file, test, or commit for each item.
3. Record: decisions or lessons that must be added to the plan files.
4. Risk: anything still uncertain after verification.
5. Verdict: CLOSE or DO NOT CLOSE.

If the verdict is DO NOT CLOSE, list the smallest concrete actions needed before
the work can be closed.
```
