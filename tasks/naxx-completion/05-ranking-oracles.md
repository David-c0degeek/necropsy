# 05 - Ranking Oracles

## Goal
A validated ranking metric policy for every Naxx boss × configuration, each with
a raw-frozen oracle of published rows, for both HPS and DPS.

## Integration analysis
To be completed before 05.1. Reuse `scripts/freeze_hps_ranking.py`, the
`ranking_metric_policies` schema and `tests/golden/test_hps_ranking_policy.py`.
Naxx has an empirical `ranking_exclusions_rule` already; determine what it covers
versus per-cell policies. DPS needs a generator that does not exist yet.

## Boxes
- [ ] **05.1** (agent) DPS oracle generator: raw re-enumeration of published DPS rows (damage done, pets/owned units, exclusions, duration), proven on one boss against published amounts with wrong-policy mutations rejected.
- [ ] **05.2** (agent) HPS oracles and policies for every HPS configuration × boss; contexts without owned-unit listings stay OPEN.
- [ ] **05.3** (agent) DPS oracles and policies for every DPS configuration × boss.
- [ ] **05.4** (agent) Golden policy tests cover every Naxx policy; mismatches investigated, never fitted.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
