# 05 — Class-aware reports and playbooks

## Goal
Expose Druid roles and useful class-specific details through the existing report and package.

## Integration analysis
- **Existing code found:** `report/analysis_json.py, report/render/playbook_view.py, view.py, templates, assets, report/package.py`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [x] **05.1** (agent) Extend analysis JSON with explicitly versioned/compatible class-specific metrics; preserve legacy hunter fields/readers where required and synchronize the generated JSON schema.
- [x] **05.2** (agent) Reuse shared rendering and evidence components with class-aware labels, role-specific summaries, KISS cards and full supporting detail. Show talent/build versus observed role, overrides, hybrid phases and unknowns clearly.
- [x] **05.3** (agent) Extend package CSV/evidence exports and user/developer docs; verify old Hunter pages and desktop/mobile layouts remain complete without new class terms leaking into historical outputs.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

## Progress log
2026-10-14 · 1 · 05.1 05.2 05.3 · Shared report/package pipeline dispatches class sections and templates; legacy Hunter pages and bytes preserved. Druid practice notes, role-specific measurements, full source timeline, forms/resources/targets and all cohort detail exported as CSV/JSON. Browser inspection covered 16 real page/viewport combinations (1400/390), no overflow, remote requests or JS errors; dedicated synthetic browser cases additionally check escaping/search/theme. README, user/developer docs, schema, ADR and validation limits updated. Closing peer review pending. Checkpoint commit/push follows this record.

2026-10-14 · 2 · Scoped Claude core review AGREE round 1 / blocking 0; 86 independent tests passed. Addressed important incidental-duty finding with explicit 20% secondary cast-share heuristic and regression cases; preserved minor actions. Role taxonomy/domain gates remain open. Reporting/docs are requested in a separate bounded final review because the first review explicitly did not read those line by line.

2026-10-14 · 3 · Claude output review AGREE round 2 / blocking 0 / important 0 against 107e024; exact limitations of that review remain recorded. Added named actor catalog, faction/external context, graded resources, comparison CSV and optional detail compatibility; role raw catalog includes Swiftmend/Hurricane/Ravage/Pounce. Per-phase hybrid comparisons are not implemented: unsupported whole-fight aggregates are deliberately declined, with activity spans retained. Latest focused/browser/real replay checks pass; final guard/record review and updated CI follow.


2026-10-15 · final engineering checkpoint · Six real Druid replays pass, including Four Horsemen tank/hybrid and own Sapphiron healing. 855 fast pass; full initial golden/acceptance 233 pass / four retained xfails; expanded six-Druid replay six pass; browser suite 23 pass; all 24 real page/viewport checks plus six artifact checks/output scans pass. Ruff lint/format, strict mypy and wheel/sdist build pass. Hunter JSON/both pages/ZIP byte-identical after inline-heading whitespace correction. Linux/Windows CI b4fd2e8 passed; final changed-fixture/template checkpoint CI follows. Portable raw scans: 169,740,861 + 62,401,552 bytes, no leaks. Review packet names exact human questions. Final independent review remains pending; checkpoint commit/push covers this record.

## Captain Hindsight — 2026-10-15

### Keep

Retain shared document/assets/publisher and optional class detail compatibility. Existing acquisition, normalization, evidence and publication remain the runtime path. Behavior was exercised from saved raw evidence to package and browser, not inferred from compilation.

### Fix before closing

Final Claude review and current-tip CI passed. No engineering defect is currently known; never mark the remaining human-owned boxes accepted from agent checks.

### Record

ADR 0005 records class/metric/duty compatibility. Decisions D007–D011 cover tank evidence, bounded validation, secondary duty share, cleanup reuse and explicit metric selection. PM-1–PM-3 calibration and CH-MISS-1/2 are retained in pre-mortem.md; durable lessons are in tasks/lessons.md. No shipped-code plan reference was found by targeted search outside tasks.

### Risk

Role thresholds are provisional. Exact-build samples can be sparse; resource/form/overheal/threat/assignment gaps stay unknown. Selected fights across three bosses do not establish full-raid or final domain acceptance. No requested role was deferred.

### Verdict

CLOSE — all subject boxes and engineering checks pass. Cross-subject domain acceptance remains open in its explicitly owned boxes; no domain approval is inferred here.


2026-10-15 · engineering review receipt · Claude mail 180: AGREE round=3 blocking=0 important=0 at db89d3a; 92 independent focused tests pass. It reviewed the changed roles/cohort/acquire/analyze/snapshot-reader/document/Druid analyzer-report/base-template code, and explicitly excluded remaining views/offline/writer/CLI/export/schema/docs/plan/raw-fact surfaces from that round. Earlier scoped rounds plus lead inspection, six real artifact/package replays, schema tests and 24 browser cases cover those paths; no claim of blanket independent review is made. Optional CohortKey.metric storage nit retained as-is: the property preserves Hunter's serialized key bytes, all supported combinations are tested, and unsupported combinations fail canonical policy. Future categories must extend that policy and query tests together. Linux and Windows CI db89d3a passed: https://github.com/David-c0degeek/necropsy/actions/runs/38646145402. This is a record-only close-out; no runtime or test edits follow the reviewed code.


2026-10-15 · selected-spec correction · D012/D013 reopen the affected agent boxes.
User confirmed one selected spec view with all bosses visible, matching personal
data only, and separately labelled top-player examples when personal data is
missing. Implemented CLI aliases/conflict refusal, role eligibility, requested
empty bosses, exemplar/metadata separation, coverage/learning CSVs, personal-first
Druid acquisition and finalization reserve with policy restoration. Hunter26
recorded request bodies/endpoints and all four saved artifacts match72744c5.
Latest broad run:877 fast pass; subsequently added the multi-boss snapshot-order
regression (passes) and conflict checks. Native DuckDB failed during overlapping
large replays (malformed JSON/native access violation); isolated Guardian replay
passed. Serial full golden/acceptance rerun is pending; no normalizer change was
made without a reproducible cause. Tank-view real fixture and32,499,807 extracted
bytes passed arithmetic/secret checks. Full Balance run is waiting once on the
observed reset, after cancelling the old acquisition and retaining its cache.

## Captain Hindsight — selected-spec correction

### Keep
Keep spec/category/observed-duty separation, personal eligibility and explicitly
labelled learning examples. Retain all requested bosses and guard unknowns.

### Fix before closing
Finish latest serial golden/browser checks, current CI, independent scoped review
and actual multi-boss live view verification. Do not count the old close-out as
approval of these new behaviors.

### Record
D012/D013 and ADR0005 describe the clarified view and acquisition order. PM/CH
calibration records the missed view contract and budget-order issue. User's yes
confirms the view model only; domain heuristic/advice gates remain open.

### Risk
API budget limits comparison depth; native bulk-loader failures during concurrent
verification need a clean serial result before claiming latest replay success.
No source log or ranking category alone proves a selected encounter duty.

### Verdict
DO NOT CLOSE — latest verification, live capture and scoped review are pending.

2026-10-15 · selected-spec verification complete · All 15 Balance bosses are
visible, with 14 matching personal performances and no personal Sapphiron grade.
Alyrian's acquired #1 Balance Sapphiron fight is separately labelled learning
evidence. Snapshot SHA-256 934d7a43f50ad27af2966a3f4efb852a3c791e56926ae87548734e4960783078;
package SHA-256 efe380c6832a2873b1eb8b132738560c564827cc53423f9a3c213b18d4441656.
Eight portable immutable captures now cover all requested behavior cases.
Full serial golden/acceptance: 236 passed / four retained expected failures;
new full-view golden: one passed / seven deselected in 43.88 seconds, including
15 independently summed actor-damage facts and coverage/learning CSV checks.
Latest broad local run: 877 fast passes, with two subsequently added integration
cases also passing. Ruff lint/format, strict mypy (132 files) and build passed.
All eight real artifacts pass artifact/package/output checks and 32 browser
page/viewport cases (1400/390 pixels), with no overflow, JS errors or automatic
remote requests. Hunter JSON/both pages/ZIP and 26 recorded request bodies plus
endpoints match the saved baseline. Raw/output unlimited scans covered
266,125,045 / 35,283,900 additional bytes without findings.
The production run waited once for 1,712.99 seconds, retained all personal fights,
then stopped comparison acquisition under the finalization reserve; later boss
comparisons remain partial. Finalized raw evidence and all outputs were checked.
Native loader failures occurred during overlapping large replays; serial full
verification passed without recurrence. Cause remains unconfirmed; no speculative
normalizer change was made.
Claude mail 185: AGREE round=1 blocking=0 important=0 after the user clarification,
against c983993; 18 independent focused tests passed. Review covered selected-spec
eligibility, exact-key learning examples/metadata, acquisition order/reserve,
snapshot provenance, CLI and HTML escaping/CSV sanitizer paths. Explicit exclusions:
docs/ADR/plan/records, raw fixtures/manifests, most tests, template body beyond
escaping check, CSV columns, writer beyond fingerprint and broad/live/browser
receipts. Those are lead-verified, not blanket independently approved. Optional
docstring/local-copy nits were addressed at e8fed3e with focused checks passing.
Linux/Windows source CI e8fed3e passed:
https://github.com/David-c0degeek/necropsy/actions/runs/38704628831.
Only fixture/test and close-out records follow that source checkpoint.
Human taxonomy/findings/advice/product boxes remain open; no role is deferred.

## Captain Hindsight — verified selected-spec view

### Keep
Keep the existing pipeline, one selected spec per view, all requested bosses,
personal eligibility and separately sourced learning examples. Real full-view
replay and browser evidence confirm the clarified behavior, including missing
personal data and honest leaderboard positions.

### Fix before closing
None within this subject; no human acceptance is inferred for other subjects.

### Record
The verification receipt above supersedes earlier pending engineering receipts.
D012/D013, ADR 0005, PM calibration and permanent lessons capture the view model,
budget priority and compatibility guards. Eight immutable fixtures retain raw
provenance; domain approval is separate from fixture authorization.

### Risk
Comparison depth remains budget-limited; role thresholds and practical advice
await domain acceptance. The concurrent native loader failure has an unconfirmed
cause; serial verification passed. Missing signals remain unknown.

### Verdict
CLOSE — every subject-owned action is complete; cross-subject domain gates remain explicitly open.

2026-10-15 · user comparison correction · Reopened affected agent boxes.
The earlier receipts describe the prior behavior; they do not close the sparse
comparison and faction preselection changes. D014 records the corrected contract.
Live capture has 15 ranking references and 14 personal Balance fights; seven
personal bosses have five event sources. Current-code replay/browser, broad
regression, independent review and current CI remain under verification.

2026-10-15 · final faction/spec engineering verification · Runtime checkpoint
0b58043 retains the interactive legacy Hunter choice after independent review.
The product flow is character → faction/spec → faction leaders. Missing personal
encounters show no personal grade while retaining leader opener/ability practice.
Overall top is a closed optional disclosure with faction/race/buff caveats.
One/two event sources show individual comparisons and n; known builds are context.
The live Balance capture has 15 ranking references and 14 personal performances;
seven personal bosses have five event sources, later event sampling stays partial.
Raw SHA-256 1c670a28e56ddf98b7df7b3e003817519ec9514a52ef7374eaa07836953d6a57;
package 4222a515c171f04de83200da35f89e5583140af4eac828563dede65e6805de74.
Nine immutable raw fixtures replay. Full serial golden/acceptance: 238 passed,
four retained expected failures, 891 deselected, in 392.17 seconds. Ruff lint and
format, strict mypy (132 files), and uv build pass. Independently scoped Claude
review 189: AGREE round2 blocking0 important0 at 0b58043; 37 CLI tests pass,
following 114 focused independent passes in round1. Review exclusions remain
explicit: CSV column details, view/template bodies beyond dispatch, snapshot
metadata_order details, docs/ADR/plan/records, raw fixtures, most tests and broad
live/browser/scan/CI receipts are lead-owned. No blanket review is claimed.
Lead verified the new snapshot provenance roundtrip/tamper and prefetch identity,
sparse/unknown/zero/build/faction cases, Hunter missing-personal flow, and HTML
escaping. All four saved legacy Hunter artifacts are byte-identical. Explicit
selected Hunter lookup intentionally adds specName and staged acquisition;
legacy no-spec query remains unchanged. Faction preselection changes live report
checks intentionally for both classes; guild inference and unknowns stay explicit.
Actual Balance and no-personal Guardian outputs pass artifact/package checks and
eight latest real page/viewport cases (1400/390, both pages), zero remote requests,
overflow or JS errors. Balance theme/search and closed disclosures pass; Guardian
shows Harryjam #4 Alliance and recorded Maul/Swipe guidance without personal grade.
Raw scan: 268,170,221 extracted bytes, unlimited target size, no findings. The
full Balance output-directory scan covered 48,800,516 bytes including retained
snapshot files, also clean; this is not a claim that all bytes are derived output.
API typed schema/probes do not establish a faction query argument: local selection
is explicit rather than claiming an ignored filter worked. Optional review nits
(unknown earlier faction row counts and inferred-opposite-faction skip counts)
are deferred with conservative scope labels and limits. Current source CI receipt
is recorded below. No runtime changes follow these records; human taxonomy,
findings/advice and product acceptance remain open.
Linux/Windows source CI 0b58043 passed: https://github.com/David-c0degeek/necropsy/actions/runs/38717484080.

## Captain Hindsight — faction/spec comparison correction

### Keep
Keep faction/spec as the main lookup choice, leaders as practice references with
no personal grade when absent, sparse source counts and direct comparisons, and
the separate closed overall-top disclosure. Existing acquisition/evidence/render
and publication seams carry the behavior; no parallel pipeline was introduced.

### Fix before closing
None within this subject. Human decisions in other subjects remain separate.

### Record
D014, ADR0005 and permanent lessons capture the corrected user contract. PM-1
remains prevented, PM-2 was confirmed at whitespace level and repaired, and PM-3
is confirmed with domain acceptance inconclusive. CH-MISS-5 is mitigated by actual
individual comparisons and the 15-reference live capture. Independent review
caught the interactive legacy option regression, fixed and tested before closure.

### Risk
Deep event coverage remains partial, guild faction can be inferred, unknown
earlier players limit faction-rank claims, and role/advice acceptance remains
human-owned. No ignored server filter or unsupported class analyzer is claimed.

### Verdict
CLOSE — subject-owned engineering work and recorded verification are complete.


2026-10-15 · presentation parity correction · User identified that Druid was a visually and structurally inferior raw-detail view, and explicitly requested class-neutral Ability use vsX for Hunter and future classes. Reopened affected engineering boxes; existing user-facing components and gear resolver are reused. Generic source-qualified cast counts, optional entry evidence/schema and shared ability CSV/table are added. Old saved documents remain renderable; regenerated Hunter outputs intentionally add the requested section. Final shared desktop/mobile/raw checks, scoped review and CI remain pending.


2026-10-15 · shared presentation verification ·

Source ad833d8 is pushed. CI passed on Linux (867 passed, 27 skipped) and
Windows (868 passed, 26 skipped): https://github.com/David-c0degeek/necropsy/actions/runs/38727937515. Both deselected 243 tests.
Full serial golden/acceptance: 238 passed, four existing xfails, 895 deselected
in 386.84 s; the subsequent source-link-only correction passed all 27 report/
package integration checks. Latest raw replay and refreshed outputs for Balance,
Restoration, missing-personal Tank and Hunter passed all 16 desktop/mobile page
cases, artifact/package checks, theme/search/review persistence, no overflow,
remote requests or JS errors. All four saved legacy Hunter artifacts are byte
identical. New Hunter replays intentionally add ability evidence, table and CSV.
All existing shot counters match the generic counts across subset encounters.
Unlimited output-directory secret scans passed: Balance 50,093,915 bytes, Tank
53,215,139, Restoration 59,476,356, Hunter 3,398,300 (includes retained snapshots,
not only derived output). New commit-range scan also passed. Raw fixtures unchanged.
Claude190 agreed the design and191 supplied incorporated guardrails. Latest scoped
review request is still unread; no final independent verdict is claimed.
Human taxonomy/findings/product boxes remain open.

## Captain Hindsight — shared presentation and ability use

### Keep
Shared Value/plan/equipment/ability components and thin class evidence adapters.
Class-specific labels and actual recorded counts are visible in the established
product hierarchy. Existing guidance and pinned encounter facts retain caveats.

### Fix before closing
Obtain the outstanding scoped independent review; record actual findings/verdict.
For validation, also retain the separately owned product acceptance gate.

### Record
The first CI exposed a missing standard external-link attribute and an outdated
exact package member assertion; both fixed, 27 integration checks and latest CI
pass. No new domain mechanics were invented. Durable decisions and lessons are
updated. PM-1/2/3 calibration remains as previously recorded; CH-MISS-6 now has
actual shared page/data evidence, while human acceptance remains inconclusive.

### Risk
Cast coverage, assignments and available exemplars limit inference. Ability-use
rates describe recorded fights and cannot establish optimal play. Only Hunter
and Druid analyzers exist; shared components support future class adapters.

### Verdict
DO NOT CLOSE — scoped independent review is outstanding; human-owned gates are
also outstanding where applicable. Implementation and lead verification are complete.


2026-10-15 · user-ended pairing; solo execution correction · Replaced aggregate cooldown dump with shared structured execution rows for opener, core abilities, individual utility/cooldowns, targets and resources. Loadout rows now Weapons/Trinkets/Relic/World buffs. Source-qualified personal/leader values preserve incomplete/missing unknowns and distinguish incoming casts. 27 focused checks and 16 actual refreshed page cases passed; lint/types pass. Prior final Claude requirement is explicitly waived by the user, never represented as peer agreement. Human domain/product acceptance remains open.


## Solo Captain Hindsight — execution correction

### Keep
Shared Hunter plan hierarchy now includes actual opener, class ability cadence, first-use times, per-fight rates, target/resource context and recorded source links. The shared class view supports subsequent classes without a second report pipeline.

### Fix before closing
None for reporting. Human taxonomy/findings/product actions remain separately tracked. The user explicitly ended pairing; Claude review is superseded rather than completed.

### Record
Execution correction 8425ce5 preceded the remaining-class work. Nineteen latest category integration checks, 16 refreshed real Hunter/Druid page/viewports and four unchanged saved Hunter artifacts support the presentation contract. Actor-owned timing and incomplete stream regressions pass.

### Risk
Recorded examples cannot establish optimal play or assignments. Human acceptance is not implied by these checks.

### Verdict
CLOSE for reporting engineering. No independent peer approval is claimed.
