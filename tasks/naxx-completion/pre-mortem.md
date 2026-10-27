# Pre-Mortem: Naxxramas completion

> Durable, plan-scoped bridge between Pre-Mortem, implementation, and Captain
> Hindsight for `tasks/NaxxCompletion-Plan.md`. Keep it with the plan until sign-off;
> durable lessons still graduate to the project's normal ADR / lessons surfaces.
>
> **History rule.** Prediction fields describe what was believed *before*
> implementation. Once implementation begins, do not rewrite them to match what
> happened. Hindsight appends calibration alongside the prediction instead.

## Failed future and verdict

Naxx was declared complete, but the Tower spent weeks of WCL quota on captures that cannot
carry encounter context, and turning the context on for zone 2006 silently changed the
legacy Naxx pages and the acceptance gate. The encounter modules built on single-boss MC
fights then gave wrong duty and exposure results on the Four Horsemen and Gothik, and
golden checks generated from the same analyzer stayed green.

Verdict: **PROCEED WITH GUARDRAILS**. The plan's architecture is sound (Codex #197
DESIGN_AGREED), but 00.5 found a seam the plan did not name: Naxx has no encounter context
at all (`inventory.md` §Places that treat Naxx specially). 01 must add it before 03 queues
any capture. Reversibility: rule and analysis changes are reversible; spent WCL quota and
published Tower captures are not.

Scope: register and strategy seam, encounter context for zone 2006, local work orders,
capture queue. Hardware stability is D004 and is tracked here as PM-5 for calibration only.

## Prediction register

### Independent DPS oracle follow-up, 2026-10-22

Scope: offline raw ranking arithmetic only; no analyzer, metric rule, acquisition,
register or production behavior changes. Existing HPS raw helpers require v2
encounter-All and do not accept the available actor-only Naxx archives, so do
not weaken them. Reuse the standard-library fact-freeze page validator for
actor-page completion while independently measuring DPS and published rows.

**PM-8 — High — circular or fitted ranking validation.** A generator reads the
analyzer's totals or searches exclusions until published DPS matches. Basis:
the legacy Naxx exclusion rule documents empirical target-set fitting and the
legacy golden test calls production `ranking_damage`. Guardrail: explicit
reviewed exclusion IDs supplied before calculation; no search or automatic
policy adjustment, no production imports. Bind an actual published leaderboard
row by report/fight/name/realm/class/spec and retain its raw amount token and
duration. Compare exact rational arithmetic at publication precision; a mismatch
fails without changing the policy. Negative mutations must distinguish wrong
duration, self damage, excluded targets and dropped owned-unit damage where
the fixture has those contributions. Resolution: Mitigated by raw-only imports, explicit exclusions, exact publication comparison, two independently enumerated real rows and wrong-policy negatives.

**PM-9 — High — false precision from incomplete ownership or stream evidence.**
A class without permanent pets is assumed to have no owned damage; overlapping
SOURCE/TARGET rows are double-counted, or a truncated stream yields a plausible
published total. Basis: existing Druid feral archives list Battle Chicken as an
owned unit; actor streams repeat observations in both directions. Guardrail:
require explicit pet listing agreement with fight and actor catalogs, bound
request identities and hashes, progressive terminal pagination, strict integer
IDs/amounts and maximum multiplicity. Refuse missing listings, invalid rows or
unresolved targets. Preserve all contributing/excluded raw locators. An actor
oracle is not encounter-wide evidence, complete snapshot eligibility, a
validated configuration policy, opportunity or a player grade. Resolution: Mitigated by strict ownership/request/page validation, duplicate-preserving Counters, missing-data negatives and ten retained real refusals. Full snapshot eligibility remains outside this tool.

Verdict: PROCEED WITH GUARDRAILS. Detection: before promotion with constructed
adverse archives and a real Patchwerk arithmetic pilot. Retain failures and
unknowns; no legacy output or existing HPS contract changes. Reversibility:
discard the draft tool/evidence without editing production rules or registers.

> `PM-*` IDs are stable and plan-scoped. Never renumber or reuse an ID. If a later
> pre-mortem adds risks to the same plan, continue from the highest number.
>
> Resolution starts `Pending` and becomes exactly one of `Prevented`, `Mitigated`,
> `Disproven / Not Applicable`, or `Explicitly Accepted` before final sign-off.

| ID | Predicted severity | Failure | Basis | Predicted detection | Guardrail | Resolution | Plan refs |
|---|---|---|---|---|---|---|---|
| PM-1 | High | Enabling encounter context for zone 2006 changes the output of existing v1 Naxx archives: the legacy Hunter and Druid pages, saved analyses, the desktop demo and the Naxx-only acceptance gate gain empty or "unknown" encounter sections, or raise, because the block is keyed on the zone and not on the presence of encounter streams. | [evidence: report/analysis_json.py:819 gates the block on `zone != "naxxramas"`; duty.applies and acquire.supports_encounter_context gate on zone IDs; wcl/acceptance.py:230 is Naxx-only; all 17 Naxx archives are formatVersion 1 (inventory.md)] [inference: replacing a zone check with a broader one silently widens the block to archives without streams] | Before merge only if byte checks cover every v1 archive; otherwise silent | Gate encounter context on the archive's v2 encounter streams, never on the zone alone, including `duty.applies` itself, which class role inference calls upstream of the pages. Before the change, record analysis.json and both page bytes for all 17 v1 Naxx archives, the Haplina export and the demo subset (00.2 baseline); after it, every one is byte-identical. The acceptance gate and the legacy replays run unchanged. | Prevented | 00.2; 01.2; new 01 box for zone 2006 encounter context; 07 |
| PM-2 | High | The Tower queue captures Naxx entries with a wheel that cannot acquire zone 2006 encounter streams (or before the v2 reader accepts zone 2006). Every archive is v1-shaped, `actor_problems` or the content bar fails on intake, and the quota spent is lost. | [evidence: snapshot/v2.py:67 rejects zone 2006; acquire.py:1011 supports_encounter_context excludes 2006; 03.2 says "current release wheel (cut a release only if the runner needs a change)"] [inference: the existing smoke checks argv and exit, not encounter-stream presence] | Silent until intake | 03 starts only after the zone 2006 encounter-context change is released and on the Tower image. The 03.2 smoke asserts the produced archive is v2 with encounter and critical streams for the entry's fight. Estimate per-boss point cost for Naxx encounter streams (Horsemen, Gothik, Kel'Thuzad) on one capture before queueing all 34 configurations. | Mitigated | 01; 03.1; 03.2; 03.5 |
| PM-3 | High | Encounter modules designed on MC give wrong Naxx results: multi-boss (Four Horsemen, four boss game IDs), split-side waves (Gothik native targets), polarity (Thaddius) and healing restriction (Loatheb) break single-boss assumptions in duty, exposure and summon logic, and the expected values are generated by the same analyzer. | [evidence: naxxramas.yaml lists boss_game_ids [16062..16065] for 51121 and native targets for 51109 [correction 2026-10-21, Codex #7: nine entries including Gothik, not eleven; Spirit of Naxxramas 16449 is a separate `start_trash` entry]; duty.boss_melee builds a boss set from encounter rules; raid-completion pre-mortem PM-2 and PM-3 were confirmed several times on MC] [inference: Naxx has more non-standard fights than MC] | Silent | Raw-first oracles for the Four Horsemen, Gothik, Thaddius, Loatheb and Kel'Thuzad before any Naxx encounter module output is accepted (05 and 04). Independent raw scans, not analyzer output, set the expected values. Adverse tests for multi-boss and split-side cases. A module that cannot represent a boss shows an explicit unknown, never a grade. | Pending | 04; 05; 06; 07 |
| PM-4 | High | A local-runner draft enters the tree with a fabricated or misattributed claim, or the runner writes outside `workspace/naxx-drafts/`, and a verifier written from the same draft passes it. | [evidence: LocalPilot decisions: Qwen3.6 35B-A3B 22/24 agent tasks; false REVISE 1 in 3 on clean review; Ornith 35B used project context 0/30 (NaxxCompletion-Plan §2)] [inference: a weaker model plus a verifier derived from its output repeats one error twice] | Before merge only if the verifier is independent | Verifiers come from the work order and the raw data, never from the draft (02.2 negative tests with planted defects). Hash the repository tree before and after every run and refuse any change outside the drafts folder. The runner gets no WCL credentials and no git write. Claude remains the only tree writer and checks every draft against its quoted source (D032). | Pending | 02.1; 02.2; 02.3; 02.4; 00.4 |
| PM-5 | Medium | Naxx evidence or gate results produced on the PC before the host is stable carry corruption that later hashes freeze as truth. | [evidence: D004; 2026-10-20 bit flip and access violations; 2026-10-21 serial inventory failures] | Silent after hashing | D004: 00.3 trusted baseline after XMP off; every failure classified and kept; evidence from an unstable period is regenerated, not reused. | Pending | 00.1; 00.3; D004 |

## Assumptions that could betray us

- Existing v1 Naxx archives can supply some cell dimensions → they cannot supply encounter or
  critical streams, so every encounter-context dimension needs new v2 evidence; actor streams,
  ranking metadata, facts and replays stay reusable where their scope suffices → 01.1 decides
  per archive and cell with `actor_problems` and the D036 layers (`inventory.md`).
- WCL quota can cover 510 cells of v2 Naxx captures in a reasonable time → if Naxx encounter
  streams cost much more than MC, the capture phase dominates the schedule → measure on one
  capture before 03.1 (PM-2).
- The Naxx `encounters` guidance section and the MC `strategy` section can coexist → if both
  render, Naxx pages repeat or contradict advice → decide the single source in 01.2.

## Plan guardrails

- [PM-1] Gate encounter context on v2 encounter streams; byte-identical replays of all v1 Naxx archives, the Haplina export and the demo subset are recorded in 00.2 and required in 01.
- [PM-2] 03 waits for the released zone 2006 encounter-context change; the smoke asserts v2 encounter streams; one measured capture sets the quota estimate.
- [PM-3] Raw-first oracles for multi-boss, wave, polarity and restricted-healing fights before module output is accepted; unknown, never a grade, where a module cannot represent the boss.
- [PM-4] Verifiers independent of drafts; tree hash before and after each run; no credentials or git write for the runner.
- [PM-5] D004 and box 00.3 as written.

## Calibration

### Operational retry review before activation, 2026-10-22

**PM-10 — High — an isolated smoke stops making progress or overlaps another API owner.**
Observed failure: the one-attempt job correctly stopped at a database restriction,
but its coordinator treated that limit as the end of the wider autonomous task.
A second verified resume retained 623798 raw event rows, then stopped while
finalizing report sets. A successful checkpoint is not a certified snapshot.
Reusing output directories without binding the prior checkpoint, or running
candidate discovery concurrently, could turn useful retries into conflicting
acquisitions. The failure and regression risk are grounded in both outcome
receipts and the retained journal; the database restriction's cause remains unknown.

Guardrails: one checked entry and pinned released image/queue, unchanged normal
analyze arguments, source-controlled receipt validation and retry decisions from
`capture_runner`, one API owner, fresh numbered attempt/receipt paths, verified
prior checkpoint, default quota reserve, the runner's two-minute reset margin,
50 GiB floor before/during attempts, four further attempts within six hours and
two hours per child, owner-stop forwarding, no automatic candidate change,
notifications or evidence promotion. Missing/mismatched outcomes and unknown
resets require attention. Validate the seed with networking disabled before
activation; keep ordinary source/content work moving during external waits.
Rollback: stop only the isolated coordinator; retain receipts/cache/checkpoints,
leave the parked production runner and watchdog untouched. Verdict: PROCEED WITH
GUARDRAILS; actual retries/capture acceptance remain pending.

### Scoped queue follow-up, 2026-10-21

**PM-7 — High — scope and evidence bleed into a new queue.** A regenerated
queue schedules the parked raids, or omits Naxx captures because v1 actor
evidence was mistaken for whole-fight context. Evidence: `universe()` currently
enumerates 136 runs and `dispositions()` treats a registered actor source as
capture-ready without checking encounter streams. Shared global artifact paths
also point every command at the parked research. Inference: a Naxx run can
silently reuse the wrong scope despite successful pin verification.

Guardrails before implementation: pass one immutable context through planning,
resolution, emission and both verification modes; default to the original three
raids; require explicit research and queue paths for an explicit raid; reject
unknown/inconsistent scopes; filter other-raid records before identity lookup;
require strict v2 complete encounter/critical scope before Naxx capture reuse.
Keep owner exclusions, exact configuration/partition/metric checks and the
parked queue unchanged. Test contamination and v1 false-reuse negatives.
Detection: before merge and again with committed queue pins before deployment.
Rollback: discard only the new research/queue; no state migration or production
restart. Verdict: PROCEED WITH GUARDRAILS. Resolution: Mitigated by immutable
context plumbing, exact configuration checks, strict v2 scope reuse, pinned raw
archive inputs (including LFS), owner exclusions at mining and resolution, and
negative tests. Actual capture, image smoke and deployment remain pending.

### Capture staging follow-up, 2026-10-21

**Failed future:** the new release image silently bakes the parked MC/BWL/AQ
queue because staging always reads its global queue path. A successful build
and version check do not detect that the wrong acquisition work was selected.

**PM-6 — High — wrong queue in an otherwise valid image.**
Basis: `scripts/stage_capture_image.py:QUEUE` and `stage` hardcode the parked
queue; the read-only integration audit identified the same gap. The failure
story is an inference from that inspected implementation. Existing staging
tests cover only the default queue and its pin. Preserve that default for
existing callers, accept an explicit queue and pin only together, verify the
selected bytes before creating output, and bind those bytes and the selected
pin into the manifest and Docker build checks. Detection: before merge with
custom-queue and wrong-pin tests; before production with staged-manifest and
real archive checks. Rollback: discard the fresh context; the parked image,
queue, state and archives stay available. Verdict: PROCEED WITH GUARDRAILS.

Plan guardrail: [PM-6] pair queue selection with an explicit pin, retain legacy
defaults, reject missing pairs and mismatches without creating output, and
verify the staged queue hash. This prevents accidental fallback during staging;
it does not prove candidate eligibility, Naxx-only scope or real v2 acquisition.
Those checks remain in 03.1/03.2 before production use. Resolution: Mitigated
by explicit inputs and rejection checks; deployment validation remains pending.

| ID | Outcome | Severity | Detected | Guardrail | Prediction | Evidence |
|---|---|---|---|---|---|---|
| PM-5 | Inconclusive | None observed | Before production | Effective so far | Unestablished | Subject 00: with XMP off, seven baseline runs (three 8-worker seed gates, three byte-identical serial inventories, CI fast suite) and two later full gates passed at cc637a7 and 61cdb30 (`workspace/naxx-baseline-20261021/`). Root cause and long-horizon stability remain unproven; evidence work may proceed under D006. |
| PM-4 | Prevented Prediction | Low | Before merge | Effective | Accurate | 00.4 trial: three local-runner drafts failed the independent verifier (`workspace/naxx-drafts/verify_00_4.py`) and 0 outputs were accepted; no tracked-tree change was observed (not proof of filesystem confinement). Scope: one work-order kind; 02 must keep both guards. |
| CH-MISS-1 | Miss (pre-existing) | Low | Before production (00.2 run) | n/a | Not predicted | The Paladin browser fixture was stale since 7930e66 because no gate runs the browser suite when only rules change. Missed because the pre-mortem looked at Naxx seams, not at gate selection. Lesson recorded; §2 requires the browser suite at checkpoints. |
| PM-1 | Prevented Prediction | High potential; no regression observed | Before release, including reviewer detection of the omitted full-export compatibility case | Effective | Accurate | Subject 01: upstream duty and rendering both require v2 for Naxx; 54 actor-only/demo outputs plus three full Haplina outputs match exactly across the engine/strategy changes. The release bump separately changes intentional version stamps. Synthetic v1/v2 Patchwerk behavior, 92 browser checks and all-platform release CI passed. |
| PM-2 | Inconclusive | No quota spent on new Naxx captures at this checkpoint | Release prerequisite verified before queueing | Partial guardrail complete | Observation horizon open | 0.6.0 is published from 65b1154; wheel and public asset hashes verified. Tower image, real v2 smoke, quota measurement and Naxx-only queue remain 03 prerequisites. Conditional restart approval does not establish their completion. |
| PM-3 | Inconclusive | No new boss-specific measured policy accepted | Before content promotion | Raw-oracle draft remains unpromoted | Observation horizon open | The independent stdlib prototype has 23 synthetic checks and five raw v1 smoke cases with independently matched Counters. It always reports incomplete scope; no real v2 fixture, mechanic family or full eligibility certificate has been accepted. Multi-boss/phase/healing risks remain open for 04–06. |
| PM-5 | Inconclusive | No new corruption observed | Local and independent CI hosts before release | Effective so far | Root cause and long horizon unestablished | 65b1154 full local gate and browser suite passed; three-OS CI and four native packaging/bootstrap jobs passed. This supports the operational baseline, not a permanent memory-stability claim or a proven cause of the earlier failures. |
| CH-MISS-2 | Miss (pre-existing) | High potential; no false Naxx completion accepted | 01.3 preflight and review, before cell validation | Exact-cell policy gate added | Not predicted specifically | Raid-wide empirical Hunter damage exclusions would have passed every Naxx ranking dimension, including HPS. The pre-mortem focused on event semantics rather than validation-scope leakage. D011 removes the fallback; all 510 Naxx cells remain unvalidated until their exact policy is proved. Lesson recorded. |

### Exhausted leaderboard pools, 2026-10-22

**PM-11 — Medium — rejected leaderboard candidates permanently fill discovery.**
Failed future: an unfilled configuration exhausts a first-page pool, but
`leaderboard()` counts the same 30 cached names toward its stopping limit and
never reaches the next boss. `build_plan()` then caps the board pool before
any newer candidate can enter it. Evidence: both callers use the unqualified
length of `leaderboard_pool()`, whose first-page deduplication caps at 30
without consulting the existing per-configuration `check()` verdict. Current
Naxx evidence has five empty/exhausted pools; the exact 30-row dead end is
reproduced with a synthetic cached first page before changing implementation.

Guardrails: reuse `check()` with the same scoped resolution/ranking caches and
owner exclusions before counting/truncating board candidates. Remove only
explicit False verdicts for that configuration; None remains eligible for
normal resolution. Apply the same filtering in network discovery and offline
plan merge. Do not change `MAX_CANDIDATES`, live budgets, queue emission,
identity/faction/metric requirements, cached answers, snapshots or the parked
queue. Emitted queues already pin their plan and both verification caches;
existing snapshot replay must remain valid. Test a later-boss candidate after
30 rejected rows, unknown rows, opposite-faction applicability, owners and the
unchanged live-call ceiling. Detection: targeted tests and full gate before
push; actual missing-pool discovery waits for the isolated capture to release
API ownership. Rollback: revert this planning-only filter; keep all raw board
and resolution evidence. Verdict: PROCEED WITH GUARDRAILS.

PM-11 implementation: the original reproduction failed with zero fetches where the second boss was required. Shared board filtering now uses exact cached `check()` verdicts before truncation; the three focused discovery/merge/applicability regressions pass. No WCL call, queue emission or production deployment is inferred. Full gate and live discovery remain separate.

### Category-scoped static strategy, 2026-10-22

**PM-12 — High — a missing category broadens tank-only guidance.** Failed
future: a Druid Balance DPS page receives Guardian preparation because both
use class 2 and metric dps, or an old saved page gains new advice during render.
Evidence: `encounter_strategy()` currently accepts only class/metric filters;
all 510 proposal projections explicitly withhold two tank-category profiles.
`analysis_json` already retains the selected category in combat/Druid playbooks;
`with_strategy()` consumes saved context without looking up current rules.
Inference: treating a missing category as a wildcard would recreate this gap.

Guardrails before implementation: optional keyword-only category selector;
category-restricted rows require an explicit matching, legal class/category/
metric combination through `ranking_policy`. General rows retain current
behavior when no category is available. Pass the selected comparison category
from each boss playbook/acquisition, never infer duty from it or from talents.
Do not activate any draft content, rewrite frozen trials or alter saved render
lookup. Capture same-version baseline outputs before editing runtime code,
then compare all 54 v1 outputs plus the full Haplina export byte-for-byte.
Use synthetic normal v2 acquisition to prove the category reaches the selector,
with missing/mismatched-category and invalid-selection tests. Run browser
checks at the engine checkpoint. Rollback is a code revert; no archive or
saved-document migration. Source/content and independent review remain open.
Verdict: PROCEED WITH GUARDRAILS.

PM-12 implementation evidence: all 34 legal configuration selections and
unknown/mismatched-category cases are covered. Canonical role aliases use the
existing class-aware taxonomy. Normal synthetic acquisition proves the selected
category reaches rendering only on the v2 Naxx path. All 57 legacy outputs are
byte-identical; 92 browser checks pass. Content remains unpromoted. Full gate
follows commit. Author review also caught the Sapphiron timing ambiguity that
mechanical quotation checks do not detect; the current key is blocked and the
34 affected coordinator drafts were revised explicitly, preserving old Git
bytes and original model trials. Independent content approval stays pending.

### Explicit dispel facts, 2026-10-22

**PM-13 — High — a removal freeze invents recipient identity or double-counts.**
Failed future: six personal dispels become twelve because SOURCE and TARGET
are added; an absent removed-spell/recipient field becomes zero; or a same-time
cast is paired with a dispel and treated as a response opportunity. Evidence:
the committed Sapphiron pilot independently records six explicit dispel rows,
each in both directions, with 2782/28542 and six recipient IDs. Existing
`fact_freeze.actor_stream()` already implements maximum multiplicity; its query
kinds do not yet expose dispels. No new stream reader or event matching is needed.

Guardrails before implementation: add an opt-in `dispels` query using existing
bound streams and clocks. Select only explicit `type=dispel`, source actor and
numeric requested removal ability; retain removed ability, recipient, isBuff
and raw instances. Require exact positive removed/recipient IDs, explicit
boolean isBuff and one numeric recipient catalog binding. Missing/malformed
fields refuse, not partial results. Missing instances stay null, never 1.
Do not assert friendliness, successful aura lifetime, paired casts, response
time, eligible opportunity, absence or grading. No new analyzer import or
production mechanic policy. Test repeated occurrences, scope, timestamps,
identity aliases/missing/duplicate recipients and malformed removed IDs/flags.
Replay existing frozen files byte-for-byte and compare the real six rows with
the earlier independently frozen observations. New file remains a draft,
without registering a cell or completing encounter proof. Rollback: revert the
new optional query kind; old specs/outputs remain unchanged. Verdict: PROCEED
WITH GUARDRAILS.

PM-13 verification: 70 fact-freeze tests pass. The real six casts and six
explicit dispel rows match the earlier independent values and all raw witness
locators. Old Lucifron/Geddon specs remain byte-identical across the extension.
Dependency check found DPS oracles pin the entire helper source: 39 complete
outputs are identical apart from that intentional provenance hash. Original
files/check strictness are preserved; two fresh draft oracles pass current
strict checks. No analyzer policy, aura reconstruction, registration or full
scope acceptance is introduced. Full unchanged-tree gate follows commit.

PM-12 consumer follow-up: the coverage audit also has an explicit cell category.
It now passes that category to the selector, so future restricted rows are
judged in the same view as rendering. The regression distinguishes Guardian
from other Druid DPS categories while preserving unvalidated ranking policy.
41 tests pass; current real inventory remains 26 IN_PROGRESS/484 TODO with no
problems. No content is activated or completed by this caller correction.

## Resume finalization priority — 2026-10-22

Failed future: the resume change either spends quota during its supposed
saved-data pass, or publishes a saved partial selection as if acquisition had
finished. Existing resume tests cover cached requests and partial finalization
reuse, but not a separate exhausted database allowance with hourly headroom.
The new offline reproduction fails because its first resumed HTTP request is
an acquisition event rather than an independent report finalization.

**PM-14 — High — Replay leaks new requests or leaves live acquisition disabled.**
Basis: `[evidence: WclClient.query; acquire._acquire_spec_view; analyze._run]`.
Add a client replay-only guard after verified journal lookup and before HTTP or
token access. A miss exhausts this pass's zero-new-request budget through the
existing controlled acquisition stop. Enable it only around the preliminary
resume acquisition, restore it in `finally`, and test missing/cached/no-journal
cases and exception restoration. Detection: before merge. Resolution target:
Prevented by the client guard and scope/flag restoration.

**PM-15 — High — Saved acquisition replaces independent finalization or completion.**
Basis: `[evidence: finalize_reports; snapshot.v1_writer; test_resume_reuses_reports_finalized_before_a_quota_stop]`.
The preliminary pass only reconstructs complete saved entries, then uses the
existing finalization scope, exact fight set, revision/actor/pet checks and
report cache. It publishes nothing. Normal acquisition and normal finalization
still follow before the unchanged writer, completeness and cohort checks.
Never copy acquisition data into finalization or repair checkpoint pins.
Test partial completion, finalization quota, mixed revisions and cached-prefix
reuse. Detection: before merge. Resolution target: Mitigated by unchanged
validation plus targeted integration checks.

**PM-16 — Medium — Extra report sets increase cost or alter unrelated fresh runs.**
Basis: `[evidence: finalize_reports groups exact fight IDs; Journal.identity includes scope and variables]`;
`[inference]` newly acquired fights can enlarge a report set, requiring a
different finalization answer. Apply the preliminary pass only to resume.
Reuse exact successful finalization requests; retain their historical answer
semantics. Preserve fresh-run order/defaults and existing archived outputs.
Do not claim this proves the real account's database refill/capacity or removes
every quota stop. Verify offline ordering/continuation and compatibility, then
require a separately built/released image and real smoke before deployment.
Detection: before merge and before production. Resolution target: Mitigated;
incremental report-set cost remains a measured rollout concern.

Plan guardrails: [PM-14] no HTTP in the preliminary acquisition, guaranteed
restoration; [PM-15] no preliminary publication or validation bypass;
[PM-16] resume-only scheduling, exact-query reuse and real deployment checks.
No persisted schema/options change is needed. Rollback is the code revert;
existing checkpoints and captured answers remain readable. The current Tower
0.6.0 measurement is unchanged. Verdict: PROCEED WITH GUARDRAILS.

Verification before the full checkpoint gate: PM-14 Prevented by the guarded
journal-miss path and tested flag/scope restoration. PM-15 Mitigated by the
unchanged finalizer plus legacy/v2 quota regressions, structural archive checks,
explicit partial coverage and changed-revision invalidation. PM-16 Mitigated
offline: all 57 retained legacy outputs are byte-identical; the 45-test replay
and failure group passes. Real incremental report-set cost and deployment
remain separate checks. `research/resume-finalization-priority-20261022.json`
records source/output hashes and limitations. Existing pending independent
reviews are not replaced by this author verification.

## 2026-10-23: mobile pull-section navigation

A draft-layout screenshot exposed a shared navigation defect: direct fragments
and keyboard jumps place Before/During/Raid headings at about21px, beneath the
42px sticky boss picker. Hunter and shared class layouts reproduce it.

PM-17: a broad scroll-offset correction moves desktop/print content or changes
saved analysis semantics while fixing mobile. Evidence: the picker and existing
anchor offsets are scoped to max-width1050px in report.css; report.js uses the
fragment target for scrollIntoView and transfers focus separately. Guardrail:
add only pull-step to that existing media-scoped selector; leave JS, analysis,
rules, capture and persisted schemas unchanged. Test direct-fragment and keyboard
navigation at320/390/768/1050/1400px, plus class paths and print controls. HTML
CSS bytes intentionally change; saved analysis values must not. Source and
installed render parity remain required before receipts, not silently reattested.
Rollback is the one-selector revert. Verdict: PROCEED WITH GUARDRAILS.

PM-17 calibration, 2026-10-23: Prevented Prediction. The media-scoped selector
fixes the reproduced mobile occlusion while all nine desktop and nine print-CSS
sample screenshots remain byte-identical. The 19-archive saved-document control
changes only the intended CSS in 38 HTML pages; the full export's four tests and
all 96 browser tests pass. Isolated installed/source outputs and all 147 package
files match commit6fcf509. Actual fragment/keyboard regression failed before the
fix at320/390/768/1050px and passes after, including1400px desktop. Guardrail was
effective for the tested layouts; this is bounded author verification, not final
content/physical-print/live acceptance. Detection was actual viewport navigation
after draft screenshots suggested a problem. No additional material miss found.

## 2026-10-23: first real v2 archive intake

PM-18: after intake, the partial capture is treated as complete, suppressing
needed comparisons or replacing earlier actor evidence with an ineligible scope.
Evidence: the strict archive contains14 subject fights,10 complete boss cohorts,
four unresolved pet-ownership cohorts and no eligible Kel'Thuzad subject.
actor_problems proves personal source/target streams but does not certify owned
damage, cohort completeness or policy. Guardrails: keep all records IN_PROGRESS;
replace only14 exact Balance/DPS/Alliance subject references after strict checks,
preserve their previous typed sources in an intake receipt and portable prior
archive/entries/provenance references, leave Kel'Thuzad and every other cell
unchanged. Retain missing pet-discovery scopes, with no inferred owners or zeros.
Use a separate capture provenance file so107 unrelated existing provenance pins
are not rewritten. Require all 917 member hashes, per-stream inventory, selected
short/complex smoke and source/installed parity; queue suppression still needs
its independent complete-cohort gate. Rollback restores the14 prior sources and
removes only new intake artifacts; no production state changes. Verdict:
PROCEED WITH GUARDRAILS. Observation horizon is intake/queue projection, not
future capture or domain acceptance.

PM-19: queue planning trusts a supplemental provenance file without its pin or
matches a different archive, then skips an unsupported capture. Evidence:
build_plan currently supplies only the shared raid provenance catalog, while
ActorSource already pins each capture's own provenance. Adding the new capture
to that old shared file would invalidate107 unrelated reference hashes.
Guardrail: load only registered, portable, hash-matching provenance references;
merge only the fixture matching that source's exact archive digest; reject
ambiguous matching fixtures; pin supplemental provenance in generated plan inputs.
Leave dispositions' identity, complete-cohort and strict v2 checks unchanged.
Test correct matching, wrong archive, stale hash, escape and duplicate fixtures;
verify real reuse recognizes only the10 complete cohorts. Existing main catalog
and parked records stay unchanged. Rollback is the lookup helper/wiring revert;
the capture remains valid evidence but needs another queue review. Verdict:
PROCEED WITH GUARDRAILS.

2026-10-23 intake refinement and calibration (PM-18/PM-19): the first real reuse
assertion expected five bosses still needing capture, but returned four. Inspection
confirmed the existing deliberate contract: complete comparison cohorts may be
reused even when the original subject is unavailable. Kel'Thuzad has five complete
comparison actors, each with observed Alliance faction and known empty pet lists.
Before updating that cell, separately validated Hotsndots's identity and complete
streams with actor_problems, preserved its old v1 source and explicitly retained
Teris's unavailable own fight. This is a refinement to the original leave-KT
guardrail, not an inferred faction or a silent change to dispositions/_cohort_met.
Actual projection registers11 bosses and retains four ownership-limited bosses.

PM-18: Prevented Prediction, resolution Mitigated for intake. All26 statuses stay
IN_PROGRESS,484 TODO; all 917 member hashes and all89 encounter/critical scopes
pass, with14 missing pet-discovery scopes preserved. The15 replaced references
(14 subject and one separately observed comparison actor) pass strict actor
checks; prior typed records are retained in a portable intake file. Every other
record is unchanged. No ranking policy, source/content approval or COMPLETE cell.
PM-19: Prevented Prediction, resolution Mitigated for queue projection. Seven
new catalog cases cover valid matching, another archive, stale digest, escape,
absolute path, duplicate and conflicting fixtures. All75 queue tests and41
coverage tests pass; actual reuse is11 supported bosses/four still needed. All
four real provenance catalogs load without changing the shared catalog. Full
checkpoint gate and independent/domain review remain separate horizons.

PM-2 calibration at real capture: Prevented Prediction for the released-image
and scope shape. Published0.6.1 actually produced v2,917 digest-verified members,
89 complete encounter and89 critical streams. Selected25.598s Sapphiron and
303.964s Gothik smoke checks pass, including three-page All scope. All147 private
wheel files and source/installed outputs match the pinned renderer. The original
bulk-cost prediction remains Inconclusive: account-wide readings across failed
windows/cache replay do not establish a cold-capture tariff or34-run forecast.
Retain PM-2 as Mitigated overall while full queue/review remains open.

2026-10-23 · Controlled Naxx production promotion pre-mortem · Independent
Codex queue/image review passes at5dc4b9a under explicit owner authorization.
Failed future: a new queue is attached to old MC state, or its status/watchdog
still reports the parked run; capture either refuses immediately or silently
loses supervision. Existing reviewed image and normal capture evidence remain
unchanged. No model or unrelated server change is in scope.

PM-20 (High, state mismatch/lost rollback): [evidence: capture_runner.py queue
state guard; Tower parked record2026-10-21 and private20:31UTC definition/state
backup] old state belongs to another queue. Mitigation: isolated fresh Naxx
state/out/cache/www, copied verified measured cache and independent protected
credentials, with all old paths/images preserved. Archive exact old definitions,
logs and affected settings before replacement; refuse removal of unexpected or
nonempty writable layers. Validate candidate image ID/queue before launch.
Detection: before production. Resolution path: Mitigated by guarded deployment.

PM-21 (High, false supervision): [evidence: entrypoint status directory binding;
Tower disabled watchdog schedule and its old base path] new worker can run while
www/cron reads old MC status. Mitigation: bind new www directory at the same LAN
endpoint, update watchdog base and helper to the reviewed runner bytes, restore
only its15-minute schedule preserving other entries, verify heartbeat, queueSHA,
new bind paths, observed UID/GID and no competing API worker. Preserve/reverify
private rollback settings and status definition first. Existing notification
settings are copied without a manual test message. Detection: before production
and fresh post-start status/watchdog inspection. Resolution path: Mitigated.

Guardrails: [PM-20] fresh state and preserved data/definitions; [PM-21] aligned
www/watchdog with independent heartbeat verification. Root's live20:30UTC check
finds two old containers, no capture/cron and316432904KiB available. Old data,
measured journals and general verified recovery20261006T210950Z remain distinct;
new runtime backups are not claimed cloud-backed up. Rollback stops only the new
worker, restores old definitions/www/watchdog settings and keeps both data trees.
Verdict: PROCEED WITH GUARDRAILS, after retaining actual independent PASS.

PM-21 prelaunch review correction: independent reviewer identified that a fresh
attention status would pass the initial queue/container check and a watchdog
exit0 (attention is deliberately quiet). Before execution, tightened readiness
to exact34 persisted entry IDs/queueSHA, fresh postlaunch heartbeat, running or
expected quota waiting, and both exact new container IDs/images/mounts/UID/GID.
Schedule/parked-cron prerequisites now validate before handover. This is a
Prevented Prediction; no production operation had run when found. Watchdog
success alone remains insufficient evidence of capture health.

2026-10-23 · PM-22 (Medium, alert retries delayed by active capture) · Actual
start notification failed once and was delivered on a later attempt transition.
[evidence: capture_runner.supervise only calls heartbeat; idle/wait call flush;
actual pending then delivered start outbox] a due alert during a six-hour child
can otherwise wait until that child finishes. Existing wait/idle retry tests do
not detect it. Independent Codex reviewer confirmed the gap. Mitigation: optional
flush max_attempts preserving default behavior, count only actual send attempts,
skip future-dated alerts, stop sends once stopping is set, and call max1 flush
from the supervision loop after stop/deadline/floor checks. Preserve durable
outbox ordering/delays and all child cleanup. Focused tests cover running-child
retry, one-send bound and stop during send. Nominal one30s request+1s poll+20s
child grace+30s drain fits existing90s stop budget; urllib timeout is not a hard
whole-operation wall-clock guarantee. Existing limitation is retained, not
misrepresented as strict timing proof. Resolution path Mitigated; verdict
PROCEED WITH GUARDRAILS. Rollout only during observed quota wait/no live child,
with a separate reviewed runner image and unchanged queue/wheel/state schema.

PM-20 calibration: Mitigated / Prevented Prediction. Fresh Naxx state has the
exact 34 queue entries; old MC state/status bytes remain identical to private
backup. Original definitions/logs and all data/images retained; only exact exited
predecessors retired after private manifest/layer checks. New worker rollout
preserved every deferred entry/inflight record and left www running.

PM-21 calibration: Mitigated / Prevented Prediction for the independently caught
attention-state readiness gap. Live queue SHA/heartbeat/new binds and restored
15-minute watchdog verified against new paths. Deployment misses were host shell
execution (explicit bash required), Docker top requiring a PID column and mixed
heartbeat/launch timestamp precision. Failed guards/logs retained. The timestamp
false failure was resolved using actual Docker start and newer status-file mtime
plus fresh heartbeat, while retaining readiness/state checks. These were harness
issues, not evidence of a failed capture; no data was reset or policy approved.

PM-22 calibration: Mitigated / Confirmed Prediction at source review. The original
start alert failed once, then delivered on a later transition. Four new cases
fail against the old runner; 74 runner tests and 2714 full fast tests pass for the
fix. Independent source review and actual network-disabled image/child tests
pass. Reviewed image 372d7ecc deployed during no-child quota wait; all 34 entry
records unchanged, exact runner hash and host watchdog verified. Nominal network
timeout limitation remains explicit. No manual notification or local AI used.

## 2026-10-26: first cell-scoped DPS ranking policies (C1)

Scope: eight Druid Balance DPS Alliance policies (Gothik, Grobbulus,
Kel'Thuzad, Maexxna, Noth, Sapphiron, Thaddius, Four Horsemen), metric-specific
policy conditions in `check_raid_coverage`, and a DPS golden. No analyzer,
acquisition, render or capture change. Codex DESIGN_AGREED (codex:48) after one
CHALLENGE round that removed an engine-reconciliation overclaim and five
exclusion bosses.

Failed future: the coverage checker accepts a DPS policy for a boss whose
production rules later gain target exclusions, so a raw explanation that never
tested those exclusions keeps clearing the ranking dimension. Or the condition
change silently loosens the existing HPS contract. Or the policies are
"validated" from the same per-row drafts without an independent re-enumeration,
or from rows whose faction, scope or ownership was never established.

**PM-23 — High — the metric-specific condition change weakens HPS or malformed
refusals.** Basis: [evidence: `_policy_scope` compares conditions to one
metric-agnostic set; test_raid_coverage parametrizes ten malformed mutations
against the MC HPS pilot]. Guardrail: keep the HPS set byte-for-byte and select
the set from the policy's own scope metric. An unknown metric fails closed before
conditions are read. Existing malformed cases still refuse, and new cases cover a
DPS policy carrying the HPS set, an HPS policy carrying the DPS set and an
unknown metric. Detection: before merge. Rollback: revert the checker; no
receipts change.

**PM-24 — High — an added production exclusion still clears an untested DPS
policy.** Basis: [evidence: all 49 admitted rows have zero ranked damage to
production-excluded game IDs; `ranking_problem` returned on scope match alone].
Guardrail: the DPS condition `encounter-has-no-production-ranking-exclusions` is
enforced in `ranking_problem` against the live zone rules, not just stated, and
the golden asserts it as well. A synthetic mutation that adds an exclusion to a
covered encounter must reopen the ranking problem. Detection: before merge, and
on every inventory run. Rollback: revert the checker; policies become inert.

**PM-25 — High — validation counts are circular or overstated.** Basis:
[evidence: the per-row oracles come from `freeze_dps_ranking.py`; 40 of 89
attempts were refused for ownership; the Kel'Thuzad subject has unknown faction].
Guardrail: the golden re-enumerates raw pages with standard-library code only
(no freezer, analyzer or metric imports) and recomputes totals, duration,
published token and exact Fraction residual. Each policy records dispositions
n = k + r + c with c = 0, k ≥ 3 distinct report/fight/actor samples, at least one
non-subject actor, and every row's faction verdict `observed`. Refused rows stay
listed as unknown, never as matches. Wrong-duration, self-damage and
added-exclusion mutations must fail where the row exercises them. The single
positive owned-unit witness (Maexxna g8f9nGyRTpNLMqWm fight 9, 442 damage) proves
dropped-owned failure, and non-exercisable mutations are marked as such.
Detection: before merge. Rollback: delete the eight policies and evidence files.

Verdict: PROCEED WITH GUARDRAILS. Reversibility: full; this unit changes no
analysis output, saved document, capture or published asset. `engine_digest`
already excludes `ranking_metric_policies`, so v1 output byte-compatibility (PM-1)
is not touched; the full gate confirms it.

C1 calibration before the full gate, 2026-10-26:
- PM-23 Prevented Prediction. The HPS condition set is unchanged, and all ten
  existing malformed-policy cases still refuse. Four new cases refuse
  cross-metric condition sets, a dropped DPS condition and an unknown metric;
  67 coverage/batch unit tests pass.
- PM-24 Prevented Prediction. A synthetic Gothik exclusion reopens that cell's
  ranking problem through `ranking_problem` itself, while Grobbulus stays clear.
  The golden separately asserts that every policy's encounter has no production
  exclusions.
- PM-25 Mitigated. The golden passes 43 cases with standard-library raw
  enumeration only. Wrong duration fails on all 34 rows, self damage on 15,
  removing the largest non-boss target on 14, and dropped owned damage on the
  single Maexxna witness. The builder aborts on any non-ownership refusal.
- Horizon: independent review and the full gate. Engine emission and product
  acceptance remain separate.

## 2026-10-26: derived actor target streams (snapshot v3)

Scope: for Naxx captures with encounter context, stop requesting per-actor and
per-pet `target` event streams. Record each one as a byte copy of the same
fight's certified encounter-All stream, with explicit derivation provenance, in
a new snapshot formatVersion 3. Evidence: the 96f728c receipt shows all 189
target responses equal All, and the page digests are identical in 97 of 97
streams. Codex DESIGN_AGREED after two CHALLENGE rounds (codex:54, codex:55).
No Tower, image or release change is in scope.

Failed future: a Naxx capture skips its target requests and saves archives that
claim requests nobody made. Or analysis silently drops Naxx encounter context
because a v2-only gate does not know v3. Or an old archive now reads
differently. Or a resumed attempt mixes a stale target cache with a new All
stream.

**PM-26 — High — a derived stream masquerades as an acquired request.** Basis:
[evidence: cache.py check_identity accepts exactly IDENTITY_FIELDS; v1.py
_check_stream_identity certifies "fetched with the supported request";
freeze_dps_ranking.py:316-345 requires actor request fields]. Guardrail: a
derived stream has `identity: null` and a sibling `derivation` (versioned rule,
the parent's exact encounter-All identity and its page digests). Its members are
GENERATED in the entries manifest. No cache entry, journal record, account
reading or completion marker is created. The reader validates the parent
identity through the unchanged strict request contract and check_pages over the
derived pages themselves, then requires byte equality with the parent pages.
Mixed identity and derivation, unknown rules, non-encounter parents, source or
critical derivations, and cross-fight or cross-actor bindings are refused.

**PM-27 — High — a v3 archive silently loses capability.** Basis: [evidence:
duty.py:36 and analysis_json.py:820 enable Naxx encounter context only for the
v2 FORMAT; check_raid_facts.py:184, capture_queue.py:557,
check_capture_archive.py:33 and freeze_dps_ranking.py:147 accept fixed versions].
Guardrail: one ENCOUNTER_FORMATS set ({v2, v3}) replaces the v2-only capability
gates, while v1 and unknown formats stay refused. A v3 fixture proves that
duty, analysis encounter context, raid facts, the intake check, queue reuse and
DPS freezing still work.

**PM-28 — High — existing archives change bytes or meaning.** Basis: [evidence:
the writer derives formatVersion from encounter_context; 57 legacy outputs, the
Haplina export and the measurement archive are pinned]. Guardrail: v1/v2 schemas
and paths stay strict and unchanged, and formatVersion 3 is written only when a
derived stream exists. Every old archive replays byte-identically under the new
code. Released 0.6.1 refuses a v3 archive at marker validation, and a test
proves it. The rewritten v3 measurement copy matches its v2 analysis after an
enumerated whitelist only: snapshot archive_sha256 and format, and the rendered
hash/format labels.

**PM-29 — Medium — order, quota and resume mix sources.** Basis: [evidence:
acquire._generation fetches actor streams before encounter scopes; the shared
Tower cache keeps old actor-target entries]. Guardrail: for derived zones, fetch
encounter-All before any actor stream. If All fails or stops on quota, the
existing stop path runs and nothing is derived. The writer reads derived bytes
only from the verified All cache key; legacy target cache entries stay unused.
A revision change invalidates through the parent identity. Finalization keeps
its independent report re-reads. MC, BWL and AQ40 keep requesting targets
(DERIVED_TARGET_ZONES = {2006}).

**PM-30 — Medium — server behaviour changes.** Basis: [inference: the equality
is observed server behaviour on one corpus]. If WCL starts honouring targetID,
fetched target streams would shrink, while derived ones still equal All. That
is what current archives already contain, and the v2 containment and owned-event
proofs still hold. Explicitly accepted, and recorded in the ADR with a
re-verify trigger. A cheap periodic comparison can be planned separately.

Verdict: PROCEED WITH GUARDRAILS. Reversibility: code revert; v3 archives would
then be unreadable by the reverted code, so none is produced before review, and
release and rollout are separate, owner-gated steps.

Derived-target calibration before independent review, 2026-10-26:
- PM-26 Prevented Prediction. Derived streams carry `identity: null` and a
  derivation record, and their entries are GENERATED. Fourteen reader refusal
  cases pass. The DPS freezer refuses seven wrong-parent cases and gives
  identical totals for a valid derived case.
- PM-27 Prevented Prediction. Six v2-only gates now accept ENCOUNTER_FORMATS.
  The intake check, queue reuse, analysis encounter context and Naxx duty run on
  v3 captures; raid facts accept formats 2 and 3 and refuse 1 and 4.
- PM-28 Prevented Prediction. All 18 legacy archives (54 outputs), the full
  Haplina export and the v2 measurement archive replay byte-identically. The v3
  rewrite matches on 1,860,033 analysis paths, except the two whitelisted
  fields. Released 0.6.1 refuses v3 with SnapshotError.
- PM-29 Mitigated offline after review (codex:57). A points-limit stop on the
  whole-fight request is followed by no actor request and no derivation.
  Legacy actor-target cache entries never feed a derived stream. A revision
  change refetches the bundle (generation 2), and every derived parent then
  carries the new revision. Real Tower behaviour remains a rollout check.
- PM-30 Explicitly Accepted, with the re-verify trigger in ADR 0024.
- Gates: pre_review --full PASS (2748 fast), all goldens 569 passed plus 4
  xfailed, browser 96 passed.
- Review round 1 (codex:57) also tightened the independent DPS check. The parent
  envelope and its exact request fields, the parent's complete member set, and
  the derived zone and partition are now required. The comparison now uses exact
  structural equality after masking only the two provenance fields, with planted
  self-tests. The freezer change adds only `/tool_sha256` to the strict check of
  all 53 committed DPS oracles (oracle-compat.json).

## 2026-10-26: shared quota deadline in the capture controller

Failed future: one entry correctly waits for a known reset, but a different
entry immediately spends against the same account and receives a reset-less
429. Or deployment/restart forgets the shared wait and recreates the incident.
The October 24 and 26 incident receipts support this failure; `Runner.apply`
currently updates only the stopping entry, and `next_entry` considers only each
entry's own retry time. Claude retains live Tower operations during this work.

**PM-31 — High — restart or a partial commit loses the account wait.**
Basis: [evidence: `capture_runner.Runner.load`, `apply`, `save`, existing
crash-before/after-commit tests; live state has historical mixed deferrals].
Guardrail: persist the optional `quota_until_utc` in the same atomic state write
as the verified outcome and inflight clearing. Keep state version 2, preserve
every entry/attempt/archive record, and derive legacy waits only from exact
known quota-stop reasons with a still-future parsed retry time. Refuse malformed
new gate timestamps. Test restart, both commit crash boundaries, mixed/expired
legacy retries and a hash-pinned copy of the real pre-clear state. Rollback
keeps the additive field readable by old code, but old code does not enforce it:
stop the worker and preserve state before any rollback. Detection: before merge.

**PM-32 — High — a shared wait hides genuine attention or invents a reset.**
Basis: [evidence: `decide` pauses unknown resets, authentication failures and
unverified receipts; the quota gate is not a database-readiness guarantee].
Guardrail: a verified quota receipt may reuse an existing gate only while that
deadline is future, without extending it. Unknown resets without that evidence,
expired gates, authentication and corrupt receipts retain attention. Never
clear a saved incident during migration. Test the October 24 three-minute
ordering, known/unknown reset pairs, expiry and nonquota failures. The gate is
shared across this one runner's configured identity, not a lock across unrelated
processes/accounts. Detection: before merge; live readiness remains observed.

**PM-33 — Medium — scheduling or status waits forever or raises a false alert.**
Basis: [evidence: `next_entry` also identifies terminal completion, `status`
publishes retry time, and `run`/watchdog consume the waiting state].
Guardrail: terminal queues finish even with a future gate; runnable work cannot
start before the gate, while later individual retry delays still hold. Publish
the actual earliest gated retry using the existing status fields. Gate waits
remain `waiting`, with heartbeats and alert retries, and create no attention
incident. Test terminal/expiry/later-transient cases and status/outbox behavior.
Detection: before merge.

Verdict: PROCEED WITH GUARDRAILS. Persist these deadlines only from verified
outcomes or existing known quota deferrals. No API query, WCL limit request,
credential change, capture-content change or incident auto-clear is involved.
Code review and the eight-worker full gate precede commit/push; the approved
release and image rollout use verified artifacts and separate state backups.

Shared-quota checkpoint calibration, 2026-10-26:
- PM-31 Prevented Prediction at the offline horizon. Existing before/after
  commit crash tests now assert the same persisted account deadline on both
  reconciliations. The hash-pinned real-state proof preserves every field except
  the expected additive deadline, including all 34 entries and attention incident
  2. Legacy expired waits do not become a new gate; malformed deadlines refuse.
  Live deployment/rollback behavior remains a rollout horizon.
- PM-32 Prevented Prediction for receipt handling. Both incident orderings fail
  on the old scheduler and pass with the gate. Unknown-reset in-flight receipts
  reuse a future gate without extending it; expiry, authentication and invalid
  receipts still require attention. This prevents the premature second child,
  not arbitrary database-quota exhaustion after the observed deadline.
- PM-33 Confirmed Prediction during pre-merge verification. The first revision
  briefly published `running` at startup before entering a gate wait, which could
  make the watchdog treat historical progress as stalled. A publication-level
  regression caught it; startup now chooses `waiting` before its first write.
  Terminal work finishes, expiry releases pending work, later transient delays
  hold, and every gate-wait publication stays quiet with no watchdog alert.
- Resolution: all three are Mitigated pending independent review and the
  approved deployment. No new material miss was found; the shared-budget lesson
  is appended to lessons.md. The code checkpoint does not close 03.4/03.5 or
  imply any COMPLETE cell.

## 2026-10-26: release and fixed-image handover

Failed future: public installers point at assets that are missing or combine
different candidate versions. Or the new image loses mounted progress or creates
format 3 archives before the matching reader is available. The owner approved
this release/rollout (D018); approval is not evidence that the artifacts or live
handover have passed. Claude retains live Tower operations.

**PM-34 — High — release assets or public pointers disagree.** Basis:
[evidence: `stage_capture_image` verifies a public wheel checksum; installers,
Python and native desktop packages all carry versions; Desktop CI builds four
platform bundles]. Guardrail: prepare 0.7.0 on its own release branch, commit
before the full gate, and build CI artifacts from the exact candidate SHA through
workflow dispatch. Verify every platform manifest/bootstrap receipt, refuse
conflicting shared bytes, compare the wheel payload to Git blobs, and publish a
complete draft only after review/checks. Download/hash public artifacts before
advancing main's installers. Never overwrite old release assets or retag.
Detection: before publication and public-pointer advancement. Rollback: preserve
the existing public release/main pointer until the new release is verified.

**PM-35 — High — rollout loses progress or leaves incompatible evidence.**
Basis: [evidence: current image 372d7ecc cannot read v3; preserved state has
34 entries, candidate checkpoints and legacy target cache; state schema remains
readable by old code but its gate is ignored]. Guardrail: hand over only the
published wheel, exact reviewed runner and explicit Naxx queue/pin with a context
manifest. Run network-disabled image acquisition/reader/migration checks before
live deployment. Claude preserves private definitions/logs/state/watchdog and
rolls only at a controlled no-child boundary, preserving mounts/UID/web/cron and
entry/checkpoint bytes. First real resumed output needs a strict reader/intake
check and journal confirmation that actor target requests are absent. Keep
v3 archives with a compatible reader; rollback to the old image cannot consume
them and does not enforce the shared gate. Detection: image preflight and live
handover; later quota readiness remains observational. No WCL limit request.

Verdict: PROCEED WITH GUARDRAILS. Publication and image changes are already
authorized, but require concrete peer-reviewed artifacts and observed handover
results. No cell completion or final Naxx product acceptance is inferred.

### Release calibration, 2026-10-26

- PM-34: Mitigated. Candidate e0e2ad2 passed its committed eight-worker gate,
  Claude's round2 review, all three exact-SHA CI jobs and four native builds.
  Four manifests, bootstrap/failed-upgrade receipts, identical shared bytes,
  all148 Git-bound wheel files and both Git-bound installers verify. The complete
  draft's nine server hashes matched. All nine public files were freshly
  downloaded unauthenticated and verified before main/tag alignment.
- The earlier b58a5a8 macOS CI job failed to acquire a hosted runner because of
  reported capacity constraints, not code failure; Windows/Linux passed. That
  incomplete baseline was not accepted as release coverage. The candidate's
  independent macOS job acquired a runner and passed. No source workaround or
  skipped-platform release was introduced; the existing all-platform guardrail
  caught the infrastructure gap, so this is not a new unpredicted product miss.
- PM-35: Mitigated for the deployed-image checkpoint, with03.4 monitoring
  retained. Claude deployed image2123ec9c at15:23:05UTC after network-none
  installed acquisition/v3 reader and copied-live-state migration checks as
  UID99:100. The operator receipt records unchanged entry records/mounts/web,
  preserved stopped predecessor/private backups and watchdog0; Codex retrieved
  it read-only, matched the remote/local hash and compared its fields to the
  reviewed handover. The ordered-mount comparison initially stopped safely;
  all remaining checks reran against mounts keyed by destination. No product
  regression or guardrail bypass is inferred from that verification correction.
  The first gated attempt resumed the old checkpoint and ended15:49:07UTC in
  finalization quota-reset; the whole queue waits until16:48:15UTC, with no
  second entry or attention. Claude checked82 new journal records, including
  zero target requests (Tower a70fb39). No new archive exists, so its strict v3
  provenance/reader/intake remains open under Claude. New request absence does
  not certify archive derivation or quota recovery. The predecessor's v3 reader/
  gate limitations are recorded. No COMPLETE cell or acceptance follows.

## 2026-10-26: live leaderboard overlap window (owner option C)

Scope: one bounded read of the first leaderboard page for each Naxx boss across
the 20 distinct class, spec and metric leaderboards behind the 34
configurations, 300 requests in all (510 was the earlier planning count). It runs
as the sole WCL owner with production stopped. The analysis is offline
afterwards. There is no standards change; reducing comparisons from 5 to 3 is a
later unit. Codex DESIGN_AGREED (codex:95) with guardrails.

**PM-36 — High — a competing API owner, or lost production state.** Guardrail:
`window.py` starts only when the controller is waiting with no inflight attempt,
a quota gate at least 10 minutes in the future, and only docker-init plus the
controller running in the worker. It then stops the worker and snapshots the
state hash. The fetch runs in a separate `--rm` container of the same released
image, with secrets mounted read-only. A `finally` block restarts the worker
whatever the fetch did. State bytes must match the post-stop snapshot at the end
of the window. After the restart, entries and inflight are compared rather than
timestamp bytes. If the gate has elapsed by the end of the window, production
may legitimately run straight away.

**PM-37 — High — quota overrun.** Guardrail: the client makes one attempt per
request, with no retry and no reset wait. A fresh rate reading is taken before
the first page, and each later decision uses the previous response's rate data.
The run stops before a request when the remaining points are at or below 600.
Query cost is unknown in advance, so this limits spending but is not a hard
bound. Any error stops the run and is logged. A partial run resumes later from
a frozen worklist and hash-verified pages, never in a retry loop.

**PM-38 — High — false overlap claims.** Guardrail: coincidence is counted only
on exact (report code, fightID) pairs taken from leaderboard rows, after
filtering to the page's actual class, spec and metric. Ranking rows carry only a
guild faction number, so faction stays inferred. Unobserved or failed pages are
missing, never zero coincidence. Denominators (rows, distinct fights, pairs)
and duplicate or missing identity counts are reported. A coincidence is not
cohort eligibility.

Verdict: PROCEED WITH GUARDRAILS. Reversibility: the read has no persistent
effect beyond quota spent. Production resumes from its preserved state.

Leaderboard window calibration, 2026-10-26:
- PM-36 Prevented Prediction.
  - Window 1 stopped production, fetched nothing, and restarted it with
    byte-identical state, in the waiting state with unchanged entries and
    counts.
  - Window 2 waited for the gate with production stopped, then restarted it with
    the state unchanged during the window.
  - Both windows' receipts and state snapshots are preserved under distinct
    identifiers.
- PM-37 Confirmed Prediction, guardrail effective.
  - Window 1's single request found "no database points remaining" while hourly
    points read 1654/3000, so the visible floor does not protect the hidden
    allowance. The run stopped on that first error, with no retry.
  - The guardrail was adjusted, after review, to wait for the gate.
  - Window 2 then fetched all 300 pages just after the reset, ending with about
    2494 hourly points remaining.
  - Production as the consumer of the database allowance remains a hypothesis.
- PM-38 Mitigated. Coincidence is counted on exact (report, fight) pairs after
  class and spec filtering, is faction-blind as stated, has explicit
  denominators, and is not treated as cohort eligibility.

## 2026-10-26: depth 3 with targeted follow-up (owner decision A, D019)

Scope: the live cohort depth goes from 5 to 3 for every Era raid. The reader
accepts depth 3 or 5 only. A detector writes a follow-up register. Release and
rollout come afterwards. Codex DESIGN_AGREED (codex:102) with guardrails.

**PM-39 — High — existing archives become unreadable or change.** Basis:
[evidence: v1.py refused any top_n other than the current depth; every live
archive records top_n 5]. Guardrail: an explicit `accepted_deep` set of {3, 5}.
Depth 4 and any other value are refused, and a test proves it. Markers,
reasons, participant order and outputs of existing archives are byte-identical:
the 54 legacy outputs, Haplina, the measurement archive and all MC/BWL/AQ/Naxx
goldens. No golden is regenerated to fit.

**PM-40 — High — a resumed depth-5 partial mixes cohorts.** Basis: [evidence:
checkpoints key on CLI options, not depth; production holds depth-5 partial
checkpoints]. Guardrail: an offline fixture resumes a depth-5 partial at depth
3. It proves that the selected comparisons are the first 3 by the unchanged
ordering, that subject, faction, category, metric, order and strict actor and
ownership bindings stay intact including dropped or inaccessible comparisons,
and that the new archive says top_n 3. Cached extra requests stay in the
journal and are never presented as selected.

**PM-41 — High — the detector overstates or understates comparisons.** Basis:
[inference: a separate counting rule would drift from the freezers].
Guardrail: count distinct admitted comparison players per configuration, boss
and metric with the subject excluded, by reusing the existing DPS and HPS
admission. Missing or unverified evidence is kept apart from zero valid
players. Archive and receipt provenance and typed refusal reasons are kept.
The minimum of 3 comes from the packaged rule, never from an archive's
historical target. Meeting the minimum never makes a cell complete.

**PM-42 — Medium — depth 3 ships without the follow-up path.** Guardrail: A is
tracked as not fully operational until a targeted capture consumes the
register and rechecks admission. No all-boss recapture or wider-rank fallback.
Old 0.7.0 readers reject depth-3 archives, and the image rollback note says so.

Verdict: PROCEED WITH GUARDRAILS. Reversibility: reverting the rule restores
depth 5. Depth-3 archives then need a reader from this or a later release.

## 2026-10-27: fight-scoped catalog pets in DPS admission (D022)

Scope: the DPS freezer's pet-listing check, for report-catalog pets that the
selected fight does not list. Basis: [evidence: the step-1 diagnosis receipt
(research/followup-pet-diagnosis-20261027/, Tower, caa19938). 11 refused
comparisons fail only "pet listings disagree". All 39 catalog-only pets
across 27 rows are absent from their fight listing and have no source or target
event in the certified encounter-All scope.] Codex DESIGN_AGREED C1 only
(mailbox 125).

**PM-43 — High — a real owned pet is scoped out and its damage is lost.**
Guardrail: an extra is scoped out only when it is absent from the selected
fight's friendlyPets and absent as both source and target in that fight's
encounter-All pages. The pages are certified by the freezer itself: unique
proof, exact identity and bounds, report revision, exactly the listed page
digests, and the raw page validator's completion and cursor checks. Any
listing presence, any activity, or a missing, partial, wrong-identity or
unterminated scope refuses. Mutation tests cover each case.

**PM-44 — High — old oracles or receipts change.** Guardrail: when the
catalog and fight listings already agree, the code path and output bytes are
unchanged. The new scoped-out record appears only on rows that use it. Every
committed oracle replays with the same difference keys under the new
freezer as under the current one. The oracle-compat check compares the two. The
existing differences are recorded, not treated as new: `tool_sha256` for all,
and also `page_validator_sha256` for the two pilot oracles.

**PM-45 — High — ownerless guardians get admitted by arithmetic fit.**
Guardrail: unresolved fight pet ownership still refuses (C2 unchanged).
Published residuals never select pets or exclusions. Owned guardians that are
listed, such as an owned Battle Chicken, stay counted.

**PM-46 — Medium — the register overstates recovery.** Guardrail: the
register is regenerated on Tower and each newly admitted row's arithmetic is
reviewed. Rows that later checks refuse keep those reasons. Exclusion cells
stay unverified. The diagnosis is not an exhaustive ownership audit: it reads
the combined catalog, not every report generation.

Verdict: PROCEED WITH GUARDRAILS. Reversibility: reverting the freezer change
restores the strict report-wide equality. Rows admitted under D022 then refuse
again, and nothing else changes.

## 2026-10-27: targeted follow-up supplements (D023)

Scope: a new supplement archive kind, writer, strict reader, an offline
orchestrator, freezer support and a chain-aware detector. No runner, queue or
live use in this checkpoint.

**PM-47 — High — a supplement is read as a normal cohort.** Guardrail: a
distinct kind and its own reader. `open_snapshot`, the analyzer and the pages
refuse it, and tests prove it. Normal archives and their outputs are
byte-identical.

**PM-48 — High — the follow-up spends more than its bound.** Guardrail: every
started deep attempt reserves a slot before it begins. Failures, partial
attempts and quota stops keep their slot. Resuming the same attempt does not
charge again. Ranking rows examined have a separate bound. Tests cover resume.

**PM-49 — High — the wrong players are taken.** Guardrail: a fresh pinned
ranking and an identity-based ledger in unchanged rank order. Identities in the
source and earlier supplements are excluded; old raw positions never are. A
moved-rank test proves it.

**PM-50 — High — admission is overstated.** Guardrail: per-candidate admission
through the freezer's real supplement path. The detector re-admits the source
and the chain from bytes and refuses forks, cycles, missing parents,
duplicates and configuration mismatches. Generations are sealed, so a later
finalization cannot change an admitted candidate's evidence.

Verdict: PROCEED WITH GUARDRAILS (offline checkpoint). Reversibility: the
supplement kind is additive; removing it leaves every normal archive untouched.

Calibration, 2026-10-27: deferred by D024 before any merge. The first checkpoint confirmed PM-50's risk: the reader
accepted emptied pages, duplicated candidates and a wrong cell (Codex, mailbox 131). That happened before any
consumer relied on it.

## 2026-10-27: exclusion-neutral admission in the follow-up register (D025)

Scope: `comparison_followup.py` admits comparisons at the five bosses with
production `ranking_exclusions` when their excluded damage is exactly 0. It
adds a typed arithmetic-mismatch exception to the DPS freezer. No cell policy,
exclusion-list validation or live use.

**PM-51 — High — an untested exclusion list decides a row.** Guardrail: admit
only with excluded damage exactly 0, so the ranked amount does not depend on the
list. Positive excluded damage stays unverified with the measured amount. An
arithmetic mismatch under the list stays unverified: it is a typed freezer
exception, never inferred from message text. The list is always the exact
packaged one; there is no fallback list and no per-row choice between results.

**PM-52 — Medium — neutral rows are read as a validated list.** Guardrail: each
row records the applied list and "exclusion-neutral". The records say this
neither validates the list nor certifies a cell. Zero excluded amount does not
prove the excluded NPCs had no activity. Rows the freezer stopped before
measuring excluded damage claim nothing about it.

**PM-53 — Medium — refusal classes blur.** Guardrail: evidence and ownership
failures stay refused with their reason. Policy-dependent arithmetic failures
are unverified. Subject rows never count. HPS stays unverified. Tests cover each
class.

Verdict: PROCEED WITH GUARDRAILS. Reversibility: reverting the detector and the
freezer exception restores the blanket "unverified" for these bosses.
