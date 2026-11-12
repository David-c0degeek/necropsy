# Naxx DPS policies at bosses with production exclusions (D027), 2026-11-12

`../dps-policies-20261112/` left the five bosses with production
`ranking_exclusions` open: Anub'Rekhan, Gluth, Grand Widow Faerlina, Heigan
the Unclean and Instructor Razuvious (130 cells). `build.py` closes that gap
under decision D027.

## Rule

A production exclusion list names target game IDs and does not depend on the
attacker's class, so it is tested per boss. Its **list witnesses** are register
rows, from any configuration, whose published DPS the freezer matches with the
exact production list while they have positive damage to excluded targets.
A boss needs at least 3 witnesses. A cell at that boss gets a policy when it has:

- at least 3 distinct players matched with the list (excluded damage zero or
  positive);
- no contradiction, with or without the list;
- only ownership refusals.

The policy carries the condition `production-ranking-exclusions-exercised` and
`tested_exclusions`, the exact list it tested. `check_raid_coverage.ranking_problem`
reopens it when the production list differs.

## Result

| Boss | Witnesses | Policies |
|---|---|---|
| Anub'Rekhan | 5 | 10 |
| Gluth | 3 | 20 |
| Grand Widow Faerlina | 34 | 20 |
| Heigan the Unclean | 4 | 21 |
| Instructor Razuvious | 24 | 16 |

87 policies; 237 Naxx DPS policies in total. Open: 32 cells below 3 matched
players and 11 with contradictions (9 Mage Fire, 1 Rogue Assassination at
Heigan, 1 Mage Frost at Faerlina).

`tests/golden/test_dps_ranking_policy.py` re-proves every row, including the
excluded damage, from raw pages without freezer code. It also checks each
witness: matched with the list, contradicted without it. All 1,060 checks pass.

Check mode (the default) writes nothing and fails if a fresh build differs.
`--write` refuses to overwrite. A build takes about 9 minutes.

## Limits

- The list is tested per boss across configurations, not per cell. Gluth rests
  on the minimum of 3 witnesses.
- No engine emission, product score, grade or COMPLETE cell follows.
- No independent Codex review (owner, 2026-11-12). The golden re-proof is the
  independent check.
