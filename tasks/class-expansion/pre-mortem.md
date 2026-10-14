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
