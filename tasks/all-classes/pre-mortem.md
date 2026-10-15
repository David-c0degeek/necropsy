# Pre-Mortem — remaining Classic Era classes

## Failed future
A class expansion shipped with a familiar shell but wrong spec filters, falsely inferred duties and copied class mechanics. Green heading tests hid empty or misleading execution plans.

## Prediction register

| ID | Predicted severity | Failure | Basis | Predicted detection | Guardrail | Resolution | Plan refs |
|---|---|---|---|---|---|---|---|
| PM-1 | High | Talent labels sent as unsupported API filters silently remove leaders | Evidence: live gameData labels DPS/Healer differ from ranking Destruction/Holy; Combat/Affliction/Survival probes empty | Silent with class-only tests | Verified per-class catalog and aliases; assert filtered row spec and exact metric; disclose category grouping | Pending | 01.1; 01.2; 05.1 |
| PM-2 | High | Ranking label or incidental heal marks tank/healer duty and creates a false personal grade | Evidence: Druid Guardian-without-tank fixture and existing role thresholds | Silent with category-only checks | Repeated class actions and direct incoming hits; mixed/unknown separated; missing personal ungraded; unknown partial streams | Pending | 02.2; 03.1; 05.1 |
| PM-3 | High | Generic report retains Druid fields/advice or breaks old Hunter output | Evidence: two rounds of user feedback, Druid-only template and hardcoded snapshot/report class branches | Before production only with actual pages | Shared execution/loadout/ability views and generic combat key; preserve old saved documents, all-class actual rendering and source-aware content checks | Pending | 02.1; 04.1; 04.2; 05.1 |

## Captain Hindsight calibration

| PM ID | Outcome | Observed impact | Actual detection | Mitigation effectiveness | Severity calibration | Evidence |
|---|---|---|---|---|---|---|

## Misses

| ID | Failure | Observed impact | Actual detection | Why missed | Future lesson | Evidence |
|---|---|---|---|---|---|---|
