# Pre-Mortem — remaining Classic Era classes

## Failed future
A class expansion shipped with a familiar shell but wrong spec filters, falsely inferred duties and copied class mechanics. Green heading tests hid empty or misleading execution plans.

## Prediction register

| ID | Predicted severity | Failure | Basis | Predicted detection | Guardrail | Resolution | Plan refs |
|---|---|---|---|---|---|---|---|
| PM-1 | High | Talent labels sent as unsupported API filters silently remove leaders | Evidence: live gameData labels DPS/Healer differ from ranking Destruction/Holy; Combat/Affliction/Survival probes empty | Silent with class-only tests | Verified per-class catalog and aliases; assert filtered row spec and exact metric; disclose category grouping | Mitigated | 01.1; 01.2; 05.1 |
| PM-2 | High | Ranking label or incidental heal marks tank/healer duty and creates a false personal grade | Evidence: Druid Guardian-without-tank fixture and existing role thresholds | Silent with category-only checks | Repeated class actions and direct incoming hits; mixed/unknown separated; missing personal ungraded; unknown partial streams | Mitigated | 02.2; 03.1; 05.1 |
| PM-3 | High | Generic report retains Druid fields/advice or breaks old Hunter output | Evidence: two rounds of user feedback, Druid-only template and hardcoded snapshot/report class branches | Before production only with actual pages | Shared execution/loadout/ability views and generic combat key; preserve old saved documents, all-class actual rendering and source-aware content checks | Mitigated | 02.1; 04.1; 04.2; 05.1 |

## Captain Hindsight calibration

| PM ID | Outcome | Observed impact | Actual detection | Mitigation effectiveness | Severity calibration | Evidence |
|---|---|---|---|---|---|---|

## Misses

| ID | Failure | Observed impact | Actual detection | Why missed | Future lesson | Evidence |
|---|---|---|---|---|---|---|

## Solo calibration — 2026-10-15

| PM ID | Outcome | Observed impact | Actual detection | Mitigation effectiveness | Severity calibration | Evidence |
|---|---|---|---|---|---|---|
| PM-1 | Prevented Prediction | Unsupported categories excluded; HPS preserved | Live queries before coding, catalog tests | Verified catalog plus alias policy worked | High plausible; no production failure claimed | 18 catalog/query checks; ADR0006 |
| PM-2 | Prevented Prediction | DPS-duty Protection sources excluded, partial/mixed personal data ungraded | Raw real fixtures plus behavioral integration | Repeated actions/direct hits and trusted streams prevent category-only grading | High plausible; assignments still unapproved | 19 integration checks; warrior-protection facts |
| PM-3 | Prevented Prediction | Structured execution and class-aware pages; old Hunter bytes preserved | Real rendered pages and byte guard | Shared view and content/source assertions worked | High plausible; user product acceptance pending | 56 synthetic plus48 real page/viewports; four Hunter artifacts |

CH-MISS-1 · Dual-purpose Holy Shock was initially classified by its name in only the healing set. Solo review found the ability can also deal damage; matching source/target/name/time effect resolves duty, with two regression cases. No shipped user report failure is established. Future lesson: identify dual-purpose actions before selecting class role signals (c016c4b).

These resolutions cover observed development verification, not an unelapsed long-term production observation window. Domain acceptance remains inconclusive and human-owned.


## Terminal acceptance — 2026-10-15

PM-1/2/3 remain Mitigated / Prevented Prediction within observed development verification; original predictions are unchanged. David accepted the documented limits and instructed final completion. Prior pending product-acceptance statements are superseded. Independent assignment adjudication and an unelapsed production horizon remain unknown, not falsely validated. Holy Shock correction and its two regressions resolve CH-MISS-1. No remaining engineering obligation blocks this accepted scope.
