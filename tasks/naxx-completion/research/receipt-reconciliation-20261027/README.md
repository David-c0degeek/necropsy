# Receipt reconciliation on Tower, 2026-10-27

Question: after the PC's faulty memory (D020), do the records committed since
the trusted baseline still reproduce on a host without that fault?

Scope: every path touched by any commit in `cc637a7..1951472`, which is 766
paths. The 00.3 baseline ran at cc637a7. The paths come from the union of the
commit history, not only the endpoint diff. Every job ran on Tower in a
disposable clone of a verified Git bundle, at the commit or tool version each
record names. Inputs were the Tower originals wherever they exist. The PC ran
nothing.

`manifest.json` assigns one disposition per path, and assigns it fail-closed. A
claimed result needs every predicate to hold: an exact job exit, a byte
comparison, or a flag in a structured result file. Any missing or contradicting
evidence would make the row `UNVERIFIED`. No row is.

## Result

No corruption is demonstrated in the reproduced subset. This does not establish
every record as verified.

| Disposition | Rows | Meaning |
|---|---|---|
| PASS, PASS-after-input-fix | 52 | Reproduced at HEAD, by check mode or byte comparison |
| PASS at the recorded commit or version | 62 | Reproduced with the tool version the record names (53 DPS oracles, the real-v2 DPS records and others); some show release-version drift or a stale pin at HEAD |
| CONTENT-EQUAL, qualified | 5 | Equal except named fields: relative path depth, interpreter string, editorial fields, oracle list order, and one historical base-commit discrepancy |
| UNRESOLVED-FOR-OWNER | 4 | No producer or no as-of inputs. Kept as unverified observations (below) |
| PC-ORIGIN-PINNED | 319 | Raw WCL partition responses. Their pins verify, but no independent Tower copy exists |
| OBSERVATION | 68 | Operational or review records. Not recomputable; each cited digest is classed by key as a Tower original, Git, or unmatched |
| SOURCE, PROSE-OR-INPUT | 256 | Code verified by the Tower gate; prose and hand-written inputs |

Differences found, none of them a content change:

- **Release version.** Rendered pages and the layout manifest embed the
  version (0.6.1 then 0.7.0). Both reproduce exactly at their recorded commits
  (3062569 and 38eb4a5).
- **Path depth.** Regenerated facts sit in a different directory, so
  `spec.archive` is spelled differently. Both spellings resolve to the same
  pinned archive, and the payloads are equal without that field.
- **Interpreter string.** This differs in the offline DPS inventory only.
- **Listing order.** `real-v2-dps-20261023/independent-review.json` lists
  oracles in case-insensitive order, as the PC's file system did. The content
  is equal when keyed by oracle.
- **Dispel inventory provenance.** The record names `base_commit` fd6f271. Its
  `eligibility_checker_sha256` is the 4c2faca version of
  `check_raid_coverage.py`. A rerun with either checker gives identical rows.
  The discrepancy stays recorded.

## Unverified historical observations

The owner decided on 2026-10-27 (D021) that these stay in Git, flagged. No
acceptance decision may rest on them:

- `production-followup-20261024/journal-review.json`,
  `partial-inventory.json` and `summary.json`. No producer was recovered, and
  the as-of production inputs were not retained independently.
- The findings and positive groups of `journal-conflict-followup-20261022.json`.
  Its full survey does reproduce: the SHA-256 equals the recorded
  `full_survey_sha256`, with 3 encounters, 12 contexts and 5866 occurrences.

## Evidence on Tower

The run directories, logs, exits, result files, job scripts and the manifest
builder are under `/mnt/user/appdata/necropsy-verify-20261026/recon/`. They are
frozen in three bundles in `../bundles/`:

| Bundle | SHA-256 |
|---|---|
| `recon-evidence.tgz` | `c55f7c8323515e26fa8d2b56723cbcb48a9c8f82ddcd98a48206cf333edd80cc` |
| `recon-evidence-2.tgz` | `5c757390bd7862b39946f5e2299c113f62a3508ec0e26d49e6f4a468055d451c` |
| `recon-evidence-3.tgz` | `550d70d40edfbd66a6b40ab6ea958421246f92effd9c2ef698250ee49431c2ba` |

Failed first attempts are kept beside the runs that replaced them, and
`manifest.json` names both. Codex reviewed the report in three rounds and
agreed in the third. The review covered the report and its limits, not any
code change.
