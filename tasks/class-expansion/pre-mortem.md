# Druid expansion pre-mortem

2026-10-14; Codex lead, Claude design review agreed (mail 177).

## Failed future

A restoration player receives damage advice because the report query and benchmark
builder still assume Hunter DPS. A partial cast stream appears to prove a role,
and synthetic examples are mistaken for validated mechanics.

## Retained predictions and guardrails

| ID | Prediction and evidence | Owner / obligations | Resolution |
|---|---|---|---|
| PM-1 | HPS and DPS or tank categories mix silently. Evidence: `wcl/cohort.py::LEADERBOARD_QUERY`, `wcl/fetch.py::REPORT_QUERY`, `analysis/benchmark.py::analyze_entry` hard-code Hunter/damage. Existing Hunter tests cannot detect healer contamination. | agent; 01.3/02.1: explicit category/metric policy, reject unsupported categories, exact role/build/category cohort equality; negative mixing tests. | Mitigated; residual evidence limits accepted at closure |
| PM-2 | Shared changes break archived Hunter JSON or render fabricated Hunter details for Druids. Evidence: `report/analysis_json.py::EntrySection`, `_entry`, `_boss`, renderer and package require Hunter fields. | agent; 02.4/05.1: optional class additions, preserved legacy serialization; compare saved baseline bytes and full Hunter replay. | Mitigated; residual evidence limits accepted at closure |
| PM-3 | Bear form or talents are mistaken for assigned tank duty; overheal/HPS becomes a quality score; unvalidated roles get marked shipped. Evidence: form/assignment distinction in product specification; no approved Druid fixtures in repository. | agent/domain-sme/product-owner; 01.2/03.4/04.4/06.1–06.3: role inference with source events, explicit uncertainty, mixed duties, no invented threat, approved raw facts and human review before closure. | Mitigated; residual evidence limits accepted at closure |

## Invariants and rollback

Raw archives, cache identity, stream proofs, multiplicity and unknown evidence stay
intact. Use the existing plugin, normalization and output pipeline. No auth or
distribution changes. Revert code commits and rebuild derived databases/outputs;
never rewrite raw fixtures. No database migration is required for reading existing
raw JSON fields. Additive analysis fields stay optional for older documents.

## Assumptions checked

Authenticated resolution of the user's supplied character 110733843 returned
Haplina, Dragonfang, Alliance, WCL class ID **2**, partition **1**. WCL class IDs
are not Blizzard class IDs. User states balance and restoration logs exist; that
does not establish feral/tank coverage or domain acceptance.

## Verdict

PROCEED WITH GUARDRAILS. Calibrate each original prediction at final Hindsight;
leave real-evidence and human gates open until actually satisfied.

## Interim calibration

| Risk | Outcome / detection | Current disposition |
|---|---|---|
| PM-1 | Prevented Prediction: real Restoration HPS and Guardian DPS queries/category checks plus negative row tests; no role/metric pooling. | Mitigated by canonical policy and exact comparison keys; domain review remains separate. |
| PM-2 | Prevented Prediction: Hunter subset JSON/both pages/ZIP remain byte-identical; 229 Hunter golden checks pass with four retained expected failures. | Mitigated; latest CI and final replay still required after remaining changes. |
| PM-3 | Confirmed Prediction: top Guardian rows have no tank hits; actual tank Harryjam has no usable form aura interval. Scoped peer review also caught incidental three-cast signals forcing hybrid. | Mitigated by direct-hit/action evidence, explicit unknown intervals and secondary cast-share guard; real mixed-duty evidence and human review remain open. |

CH-MISS-1: an additive Druid detail field can be missing from a saved document
while the class section still passes the free-form evidence envelope. Renderer
optional access and an older-detail regression now preserve readability. The
broad test caught this during concurrent code/template verification; run the final
suite only after sources stabilize, and never count a previous run for later edits.

## Final engineering calibration (2026-10-15; domain horizon remains open)

| Risk | Outcome, impact and detection | Mitigation and severity |
|---|---|---|
| PM-1 | Prevented Prediction for cross-role/metric pooling: actual HPS Balance rows preserve metric and decline incompatible observed duties. User's Sapphiron clarification exposed an over-restrictive category→metric default; explicit Balance/HPS now survives production acquisition and replay. | Exact keys plus strict reader conflicts are effective. High severity remains justified; human taxonomy review pending. |
| PM-2 | Confirmed Prediction at formatting level: final byte replay detected a Jinja block trimming the Hunter brand newline. JSON was unchanged; fixed with an expression and all four artifacts now match baseline bytes. | Golden suite plus byte comparison caught the gap before closure. Medium realized impact; compatibility guard effective after correction. |
| PM-3 | Confirmed Prediction: actual Guardian category without tank hits; tank actions without form intervals; real hybrid 24 cat/92 bear casts; incidental actions requiring the share guard. Own Sapphiron log agrees with user-stated healing assignment. | Six real fixtures and coverage-aware inference are effective engineering guards. Human findings/advice/threshold acceptance remains inconclusive; high severity still justified. |

CH-MISS-2: shared-template control blocks can break promised byte compatibility
through whitespace alone. JSON equality and semantic browser tests missed it;
the final four-artifact comparison detected it. Use expressions for inline labels
and retain rendered/package byte checks at the compatibility boundary. This is
also the concrete realization of PM-2; recorded separately because the mechanism
was not predicted.

## Selected-spec correction — 2026-10-15

CH-MISS-3: validating one example per role did not establish the intended selected
spec view. The user clarified that every boss stays visible, only matching
personal spec/duty is graded, and absent personal data gets separately labelled
top-player learning examples. A Guardian ranking with feral actions must not be
personal Tank analysis. D012 and ADR 0005 now state that contract; new empty-view,
role-mismatch, partial-coverage and reference-only tests pin it. The brief
mixed-category/pinned-raid proposal was removed before shipping.

PM-3 remains Confirmed Prediction: the new personal eligibility filter closes
another category-as-duty path; neither learning examples nor rank-one metadata
become personal baselines. Domain review of heuristics/advice remains separate.
PM-1 remains Prevented Prediction: selected spec aliases canonicalize before
querying and conflicting flags are refused before credentials are read.
PM-2 remains mitigated: Hunter four-artifact bytes and all 26 recorded mock HTTP
request bodies/endpoints match the 72744c5 baseline; the two-boss ordering test
also keeps Hunter's original personal/comparison interleaving.

Acquisition-order miss: fetching a deep cohort boss by boss exhausted the live
budget before personal raid coverage. D013 records personal-first ordering,
subject-less comparison priority, planned-order provenance and a conservative
finalization reserve restored in finally. Pagination still pays against each
request's guarded allowance. The replacement live run retains one bounded,
observed reset wait; unacquired comparisons remain explicit.

## Final live calibration — 2026-10-15

The real replacement run confirms the acquisition-order mitigation: all 15 bosses
remain visible and 14 personal Balance fights are retained before comparison
depth. Sapphiron uses Alyrian #1 without personal grading. The bounded wait was
1,712.99 seconds; finalization succeeded with comparisons explicitly partial.
PM-1 remains Prevented Prediction, PM-2 mitigated/Confirmed Prediction and PM-3
Confirmed Prediction with human threshold/advice acceptance still inconclusive.
CH-MISS-3 is closed at the engineering level by full-view raw replay, independent
facts, CSV and actual browser checks; human acceptance remains separate.

CH-MISS-4: concurrent large verification replays produced a native loader failure
and malformed-NDJSON error. Isolated replay and a complete serial golden run
passed without recurrence. The cause is unconfirmed; avoid overlapping heavy
native-loader checks when collecting acceptance receipts and retain failures
without inventing a library or memory diagnosis. Durable lessons are promoted.

## Sparse comparison pre-mortem — 2026-10-15

Failed future: a one-source score gap is presented as a reliable population
benchmark; a guild inference is labelled faction #1; a zero or unknown denominator
produces a fabricated percentage; prefetched rankings from the wrong spec or
endpoint enter the snapshot; Hunter historical output changes through a shared
template. Repository evidence: median_of's minimum3, exact-build Druid key,
select_boss's deep verification and the existing first-row metadata path.

Guardrails owned by Codex: individual values and n for sparse samples, no median
recommendation below3; per-source builds/differing counts; exact non-build key;
metadata and event arithmetic separate; unknown/zero percentage tests; explicit
global versus best-recorded-faction labels; complete prefetch key+endpoint check,
validated optional metadata_order; reserve/finally policy; Hunter replay bytes.
Claude186 agreed the Druid design; user subsequently broadened faction priority
to Hunter and Claude was notified. No speculative API filter ships: authenticated
schema plus live equal/dot filter probes were inspected, and all returned mixed
factions. Local faction filtering is explicit. Outcomes remain under verification.

CH-MISS-5: strict exact-build equality and a three-member median threshold hid
useful comparisons in a product that must teach from one top player. The user
found this by reading the actual playbook. Favor explicit sample size, individual
source comparisons and context differences over withholding useful observations.
The UI's faction filter is not proof of an equivalent API argument.

## Faction/spec selection review calibration

PM-1 remains Prevented Prediction: WCL-score differences and event differences
are separate, unknowns and zero reference percentages are guarded, and known
non-build dimensions remain exact. Sparse comparisons have explicit source n;
the aggregate recommendation still needs three. PM-2 remains Confirmed Prediction:
the lead byte guard caught another conditional-template newline trim; 421c15e
restores all four saved Hunter artifacts byte for byte. New selected Hunter query
shape changes intentionally, while legacy no-spec queries remain unchanged.
PM-3 remains Confirmed Prediction; main Guardian learning requires evidenced
tank duty and selected faction, not category DPS. Domain advice acceptance stays
separate and inconclusive. No claimed faction-specific rank is fabricated from
unknown earlier ranking identities. CH-MISS-5 is addressed by direct values,
spell counts/rates, source n, per-build context and a fresh 15-reference raid capture.

Independent review 188 found the new interactive prompt had blocked legacy
all-spec Hunter lookup. The prompt now defaults to `all`, explicit `--spec all`
maps to the original policy, and a tty regression passes. Claude 189 agrees
round 2 with zero blocking/important findings after 37 independent CLI passes.
Optional unknown-earlier-row counts and inferred-opposite-faction counts are
deferred: conservative scope labels, evidence levels and caveats already disclose
the limits. A future API filter requires proved behavior and distinct provenance;
no ignored faction filter is shipped. Final verification receipts follow.

Final verification: nine immutable fixtures replay in the complete serial
238-pass/four-known-xfail suite; no native loader failure recurred. Actual final
Balance/Guardian browser and artifact checks pass. Linux/Windows source CI and
scoped independent review passed. PM-1/2/3 calibration above remains accurate;
CH-MISS-5 has concrete runtime evidence. Required human decisions remain open.


## Shared presentation and ability use — pre-implementation guardrails

The design huddle and source reads identified these failed futures: visual parity
is superficial while Druid data stays buried; a shared cast counter inflates uses
with damage ticks/pets; partial absence becomes zero; gear names are invented;
new panels lose source context or leak Hunter-only advice; old optional JSON
breaks or unchanged old Hunter documents reformat. Evidence: class-report's raw
serialization, existing Hunter gear/plan components, generic source coverage,
normalized cast identities and package/schema rules.

Codex owns detection: shared plan/gear and ability components; no new domain
advice; actor-only cast query with complete_or_unknown and refs; partial/zero
unit cases; actual Balance/Restoration/Tank/Hunter replay and 16 browser cases;
review marks/theme/search/overflow/escaping; old-document byte guard; source
schema currency and ability CSV sanitization. Claude190 agreed the design, then
was notified of the user-requested shared ability extension. New Hunter analysis
bytes are intentionally additive; old saved documents retain compatibility.

CH-MISS-6: the Druid implementation passed data/replay checks while presenting a
raw detail dump instead of the established product. The user detected the gap.
Future class expansion needs a real side-by-side page/data inventory, shared
visual components, prominent meaningful comparisons and parity checks before
engineering closure. Existing whole-repo cleanup reuse still applies; no new
pipeline or dependency is introduced.


Latest presentation verification:

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

CH-MISS-6 is mitigated by the actual paired class pages and shared components, with independent review still pending. Two integration misses were caught by CI and fixed before this handoff; no root cause beyond the observed omissions is inferred.


## Execution parity correction — before implementation

PM-4 · High · It shipped with identical headings but a cooldown dump instead of
an execution plan; tests checked headings and missed the user-visible content gap.
Evidence: render/druid_view.py cooldown aggregation versus playbook_view.py's
Opener/Rapid Fire/Refocus rows; actual user feedback. Predicted detection: silent
under heading-only tests. Guardrail: structured per-ability rows, personal and
leader counts/rates/first-use timings with source links, opener and target/resource
context; actual row-content checks on real Balance/Restoration/Tank pages.
Owner: Codex; Plan refs: 05.2/06.1/06.4. Resolution: Mitigated.

PM-5 · Medium · Shared rows invent timing/absence for incomplete streams or imply
an optimal rotation. Evidence: complete_or_unknown ability counts and Druid timeline
can retain partial events. Guardrail: count and first-use unknown without trusted
cast evidence; no personal values for missing selected-spec encounters; label
recorded examples and assignment uncertainty. Owner: Codex; Plan refs: 05.2/06.1.
Resolution: Mitigated. Rollback: revert presentation-only change, immutable raw unchanged.


## Solo execution correction calibration

PM-4: Confirmed Prediction in the preceding presentation; corrected by structured per-ability execution rows, then guarded by actual row-content checks and refreshed 16page/viewports. No heading-only parity claim remains. PM-5: Prevented Prediction in this correction; actor-owned first-use, unknown incomplete counts and missing-personal tests prevent invented timing or grades. Source 8425ce5 and latest shared class changes retain these invariants. Observation is development verification, not human gameplay approval. CH-MISS-6 no longer waits on Claude after explicit user cancellation; product acceptance remains human-owned.


## Terminal close-out calibration — 2026-10-15

PM-1 remains Prevented Prediction for incompatible pooling, with metric/category corrections and exact eligible keys verified. PM-2 remains Confirmed Prediction at formatting level, repaired and guarded by four saved Hunter artifacts. PM-3 remains Confirmed Prediction: category/form did not establish assignment; direct-hit/action evidence, mixed/partial exclusions and stated unknowns mitigate it. PM-4 is Confirmed Prediction, repaired by substantive execution rows and source-aware page checks. PM-5 is Prevented Prediction through actor ownership and complete-stream unknowns. All engineering resolutions are terminal; residual domain limits are accepted by the product owner under D017/D018. Additional SME adjudication is waived, not performed. Future production/optimal-play horizons remain Inconclusive, not False Positive. CH-MISS-1 through CH-MISS-6 retain their documented fixes and lessons; none leaves an undisclosed required engineering action.
