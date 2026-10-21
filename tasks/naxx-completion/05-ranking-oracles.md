# 05 - Ranking Oracles

## Goal
A validated ranking metric policy for every Naxx boss × configuration, each with
a raw-frozen oracle of published rows, for both HPS and DPS.

## Integration analysis
The legacy Naxx `ranking_exclusions_rule` is empirical: its comment explicitly
describes fitting target sets to the historical Haplina cohort, and its standing
test calls production `ranking_damage`. It is not an independent raw oracle or
a per-configuration policy. The new `scripts/freeze_dps_ranking.py` imports only
standard-library code and the independent raw page validator in `fact_freeze`;
no analyzer, DuckDB or metric-policy imports. Specs bind a captured leaderboard
row, selected actor/fight/class/spec/role, explicit exclusion IDs and archive
hash. Ownership listings, request identities/page hashes and closed pagination
must qualify actor scopes. SOURCE/TARGET use maximum multiplicity. Damage to
owner/owned actors and explicit excluded game IDs is retained separately from
ranked damage; no exclusion search occurs. Published decimal tokens retain
lexical precision and are compared with exact Fractions. Result is a draft
actor-arithmetic oracle, not a validated configuration policy or full eligibility.

Reuse `scripts/freeze_hps_ranking.py`, the `ranking_metric_policies` schema and
`tests/golden/test_hps_ranking_policy.py` for HPS. Those helpers require actual
encounter-All evidence and frozen actor contexts; the available v1 pilots do not
satisfy that contract. Do not weaken the HPS verifier to accept them. Future
policy registration still needs the exact cell, reviewed scope and raw evidence.

## Boxes
- [x] **05.1** (agent) DPS oracle generator: raw re-enumeration of published DPS rows (damage done, pets/owned units, exclusions, duration), proven on one boss against published amounts with wrong-policy mutations rejected.
- [ ] **05.2** (agent) HPS oracles and policies for every HPS configuration × boss; contexts without owned-unit listings stay OPEN.
- [ ] **05.3** (agent) DPS oracles and policies for every DPS configuration × boss.
- [ ] **05.4** (agent) Golden policy tests cover every Naxx policy; mismatches investigated, never fitted.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log
2026-10-22 · 05.3 offline inventory · Exhausted the 102 supported DPS/tank participant rows in 12 deduplicated, pinned Naxx archives (116 selected fights including healer contexts), using an explicit empty exclusion set throughout. There are 39 arithmetic matches across 13 bosses and 63 refusals: 31 missing owned-unit listings, 28 disagreeing ownership listings, three without a unique published row and one without a unique name/realm actor. No exclusions were fitted. A separate stdlib ZIP/Counter enumeration reproduced all 2677 admitted damage occurrences, totals and exact Fraction residuals. All 39 full oracles then replayed byte-for-byte from the committed recipes and declared serialization; all 39 also pass the existing strict `actor_problems` checker. `research/offline-dps-inventory.json` pins inputs, recipes, raw multiset/member hashes and actor-source candidates. These are reusable v1 actor scopes, not new registrations, validated cell policies or complete encounter context. Full generated rows remain in ignored workspace. Loatheb and Maexxna have no admitted row in this inventory. 05.3 stays open.

2026-10-22 · 05.1 · Added `scripts/freeze_dps_ranking.py` with 15 synthetic/interface tests, including repeated observations, owned damage, self damage, explicit exclusions, hash/identity aliases, missing/foreign ownership, missing/noninteger amounts, out-of-bounds/unterminated streams, wrong published identity/duration/amount, duplicate/nonfinite JSON, output relocation, stale/tampered replay and refusal to overwrite. `research/dps-ranking-pilot/` retains two raw Patchwerk oracles and their review: Balance Haplina 68395 external damage versus published 535.273 DPS; Feral Hamtaro 163371 raw minus 1034 self = 162337 ranked, including 1256 Battle Chicken damage, versus published 1500 DPS at its integer lexical precision. Separate stdlib enumeration matches every raw occurrence and the manually recorded totals; real wrong-duration, dropped-owned-damage and included-self-damage mutations fail where applicable. Both frozen files replay with zero differences. Ten other sampled rows remain refused for missing/inconsistent ownership, without defaulting to zero pets or adjusting exclusions. No policy, actor-source or cell registration. PM-8/PM-9 are mitigated by these guards; 05.2–05.4 stay open.

Verification: targeted 15 tests, Ruff lint/format and mypy pass. Both committed draft paths replay with zero differences. Full checkpoint gate runs after commit with eight workers (`NECROPSY_GATE_WORKERS=8`, `PYTEST_ADDOPTS=-n 8 --dist worksteal`); receipt `workspace/codex-naxx/dps-oracle-full-gate.log`. No production engine/rule/render change, so no additional visual claim. Public WCL site fetches returned HTTP 403; maintenance status remains unknown and no authenticated API query was sent.
