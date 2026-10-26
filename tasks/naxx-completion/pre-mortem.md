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
