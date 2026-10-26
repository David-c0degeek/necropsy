# C1 cell-scoped DPS policy matrix

`matrix.json` classifies all 89 retained real-v2 DPS attempts from
`../real-v2-dps-20261023/` for the Druid Balance DPS Alliance configuration,
per boss. For every attempt it records:

- the snapshot's faction verdict;
- the disposition (admitted arithmetic match or ownership refusal);
- for matches, how many target game IDs the ranked damage reaches, and the
  damage to production-excluded game IDs.

Every one of the 89 attempts has an observed Alliance faction verdict.

Decision rule, agreed with Codex (codex:47, codex:48):

- A boss with production `ranking_exclusions` stays OPEN. No admitted row
  damages an excluded ID, so the exclusions are untested. This applies to
  Anub'Rekhan, Gluth, Heigan, Faerlina and Razuvious.
- A boss stays OPEN with fewer than three admitted matches, with no non-subject
  match, or with any contradiction. Loatheb and Patchwerk have no admitted row.
- Every other boss gets one policy. Its dispositions satisfy n = k + r + c with
  c = 0. A refusal that is not ownership-based would abort the build rather
  than count as neutral.

The eight resulting evidence files are
`tests/golden/raids/dps-ranking-naxx-*-balance-druid.json`. Their policies are
in `src/necropsy/rules/classic_era/zones/naxxramas.yaml`.
`tests/golden/test_dps_ranking_policy.py` re-proves every row from raw pages
without the freezer, the analyzer or metric code.

```powershell
uv run python tasks/naxx-completion/research/c1-dps-policy-matrix/build.py
```

Check mode writes nothing and fails if a fresh build differs from the committed
files. `--write` creates them and refuses to overwrite. The archive needs Git LFS.

Limits:

- These policies explain published DPS from raw events for exactly this cell
  scope.
- The production engine still reports Druid ranking damage as unknown
  (`analysis/benchmark.py`). No engine emission, product score, grade or
  COMPLETE cell follows from this matrix.
- Kel'Thuzad has five in-scope attempts: the subject has no own fight with an
  observed faction.
- An empty exclusion set is positively exercised only where admitted rows
  damage more than one target game ID.
