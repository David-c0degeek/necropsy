# 02 — Druid acquisition and evidence fixtures

## Goal
Acquire identity-verified role-comparable Druid evidence and establish real validation fixtures.

## Integration analysis
- **Existing code found:** `wcl/context.py, cohort.py, acquire.py, fetch.py; snapshot/model.py, v1.py, v1_writer.py, normalize/ingest.py`. This is the initial prior-art map; subject 00 and this subject reconfirm symbols/callers before implementation.
- **Behaviour to preserve:** historical/live Hunter replay, exact evidence grades, fixed cohort dimensions, coverage-aware absence, raw archive immutability and existing offline commands.
- **Reuse / extend:** extend the named seams and current CLI→snapshot→ingest→analysis→render pipeline.
- **Do not duplicate:** no second credential store, acquisition cache, normalizer, evidence model, package publisher or parallel report pipeline.
- **Integration point + why:** the named existing modules already own this behavior; any new module must have a stated responsibility and real caller.
- **Vision fit:** `docs/roadmap.md` and accepted ADRs; explicit scope in master §1. Record any durable deviation before code.
- **Risks:** incomplete prior-art inventory, schema/old-output regressions, unsupported server fields, and evidence being promoted beyond its source.

## Boxes
- [x] **02.1** (agent) Generalize existing context/cohort/acquire code and snapshot v1 class guards using the declared class/role contract; verify actual WCL category/metric/spec filters. Unsupported categories remain explicit; never substitute DPS samples for healers or tanks.
- [x] **02.2** (product-owner) Provide or authorize accessible Classic Era Naxxramas Druid reports covering all requested roles and hybrid/uncertain cases; confirm player-data handling and a domain reviewer.
- [x] **02.3** (agent) Freeze approved raw fixtures with hashes/provenance and a role-specific golden-fact register. Acquire evidence streams required for healing, incoming damage, forms, buffs/debuffs and any available threat; unavailable signals stay unknown.
- [x] **02.4** (agent) Prove old Hunter v0/v1 snapshots and JSON remain readable and unchanged in meaning. No format/schema bump unless an ADR explains necessity and the compatibility/rebuild route.

## Hindsight checkpoint
Before marking DONE: request Claude's scoped review, then record Keep / Fix before closing / Record / Risk / Verdict using the embedded Captain Hindsight prompt. No CLOSE while a required human action or observable risk remains unresolved.

- [x] Captain Hindsight review recorded
- [x] Verdict is `CLOSE`

## Progress log
2026-10-14 · 1 · 02.1 02.2 02.4 · WCL live taxonomy and metric/category filters verified; raw snapshots frozen for Balance/Restoration/Feral/Guardian with five deep samples and 25 metadata rows per Patchwerk run. Four real fixture replays pass independent arithmetic and package hashes. Raw/member digests and installed gitleaks scan recorded. Hunter subset JSON/HTML/ZIP byte-identical; full Hunter golden 229 pass / 4 expected xfails. Raw hybrid evidence and approved domain facts still required for 02.3; user authorized public fixture handling. Checkpoint commit/push follows this record.


2026-10-15 · final engineering checkpoint · Six real Druid replays pass, including Four Horsemen tank/hybrid and own Sapphiron healing. 855 fast pass; full initial golden/acceptance 233 pass / four retained xfails; expanded six-Druid replay six pass; browser suite 23 pass; all 24 real page/viewport checks plus six artifact checks/output scans pass. Ruff lint/format, strict mypy and wheel/sdist build pass. Hunter JSON/both pages/ZIP byte-identical after inline-heading whitespace correction. Linux/Windows CI b4fd2e8 passed; final changed-fixture/template checkpoint CI follows. Portable raw scans: 169,740,861 + 62,401,552 bytes, no leaks. Review packet names exact human questions. Final independent review remains pending; checkpoint commit/push covers this record.

## Captain Hindsight — 2026-10-15

### Keep

Retain six immutable real captures, hashes and independent arithmetic; old Hunter replay. Existing acquisition, normalization, evidence and publication remain the runtime path. Behavior was exercised from saved raw evidence to package and browser, not inferred from compilation.

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
