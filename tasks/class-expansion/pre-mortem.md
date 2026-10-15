# Druid expansion pre-mortem

2026-10-14; Codex lead, Claude design review agreed (mail 177).

## Failed future

A restoration player receives damage advice because the report query and benchmark
builder still assume Hunter DPS. A partial cast stream appears to prove a role,
and synthetic examples are mistaken for validated mechanics.

## Retained predictions and guardrails

| ID | Prediction and evidence | Owner / obligations | Resolution |
|---|---|---|---|
| PM-1 | HPS and DPS or tank categories mix silently. Evidence: `wcl/cohort.py::LEADERBOARD_QUERY`, `wcl/fetch.py::REPORT_QUERY`, `analysis/benchmark.py::analyze_entry` hard-code Hunter/damage. Existing Hunter tests cannot detect healer contamination. | agent; 01.3/02.1: explicit category/metric policy, reject unsupported categories, exact role/build/category cohort equality; negative mixing tests. | Open |
| PM-2 | Shared changes break archived Hunter JSON or render fabricated Hunter details for Druids. Evidence: `report/analysis_json.py::EntrySection`, `_entry`, `_boss`, renderer and package require Hunter fields. | agent; 02.4/05.1: optional class additions, preserved legacy serialization; compare saved baseline bytes and full Hunter replay. | Open |
| PM-3 | Bear form or talents are mistaken for assigned tank duty; overheal/HPS becomes a quality score; unvalidated roles get marked shipped. Evidence: form/assignment distinction in product specification; no approved Druid fixtures in repository. | agent/domain-sme/product-owner; 01.2/03.4/04.4/06.1–06.3: role inference with source events, explicit uncertainty, mixed duties, no invented threat, approved raw facts and human review before closure. | Open |

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
