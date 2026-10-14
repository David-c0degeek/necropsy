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
