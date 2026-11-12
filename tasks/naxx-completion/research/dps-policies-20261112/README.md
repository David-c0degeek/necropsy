# Naxx DPS policies for every captured configuration, 2026-11-12

`build.py` generalizes the C1 matrix (`../c1-dps-policy-matrix/`) from Druid
Balance DPS Alliance to every DPS configuration in the comparison follow-up
register (`../../followup-comparisons.json`, 26 configurations, 390 cells).

## Method

The admission is the register's own: `comparison_followup.cells` runs the DPS
freezer on each same-faction comparison's published row. The builder replays
that admission, checks it equals the committed register, and keeps each
admitted row's freezer result. Per cell it applies the C1 rule:

- A boss with production `ranking_exclusions` stays OPEN. Exclusion-neutral
  admission (D025) is for the register only and does not test the lists.
- The 8 committed C1 policies are kept as they are.
- A cell stays OPEN with any arithmetic contradiction ("published DPS
  contradicts raw"), with any refusal that is not about pet ownership, or with
  fewer than 3 distinct admitted players (`live_cohort.min_same_faction`).
- Every other cell gets one policy. Ownership refusals (pet listings disagree;
  unproven pet set, no `pets.json`, D026) are unknown, never matches.

Output:

- `matrix.json` has the decision for every cell;
- `policies.yaml` holds the policy entries, appended to
  `src/necropsy/rules/classic_era/zones/naxxramas.yaml`;
- one evidence file per policy, `tests/golden/raids/dps-ranking-naxx-<boss>-<spec>-<class>-<faction>.json`.

Check mode (the default) writes nothing and fails if a fresh build differs.
`--write` refuses to overwrite. A build takes about 9 minutes.

`tests/golden/test_dps_ranking_policy.py` re-proves every row of every policy
from raw pages with standard-library code, without freezer, analyzer or metric
code. It is now class- and spec-generic, and checks D022 catalog pets absent
from the fight against the encounter-All pages. All checks pass (1,195 with D027 and D028).

## Result

After D028 (fight-active catalog units such as Shaman totems), 161 new
policies; 169 at bosses without exclusions.

| Decision | Cells |
|---|---|
| New policy | 161 |
| Existing C1 policy | 8 |
| OPEN: production exclusions (handled by `../dps-exclusion-policies-20261112/`) | 130 |
| OPEN: fewer than 3 admitted players | 65 |
| OPEN: contradiction retained | 26 |

No other refusal type occurred. Contradictions concentrate in Mage Fire. The
first build (before D028) had 142 policies; the Shaman configurations then had
none because every totem-owning comparison was refused.

## Limits

- Each policy explains published DPS from raw events for exactly its cell
  scope: no engine emission, product score, grade or COMPLETE cell.
- An empty target-exclusion set is positively exercised only where admitted
  rows damage more than one target game ID.
- This unit had no independent Codex review (owner, 2026-11-12: work without
  Codex). The golden re-proof is the independent check.
