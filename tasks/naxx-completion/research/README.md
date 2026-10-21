# Naxx completion research

Evidence for subject 00 of the Naxx completion plan. Codex produced these drafts
under D007 (read-only on the tree); Claude verified and promoted them unchanged.

Later solo continuation under D013 also retains these bounded offline audits:

| File | Content |
|---|---|
| [offline-dps-inventory.json](offline-dps-inventory.json) | 102 supported rows attempted; 39 independently re-enumerated matches, 63 refusals; pinned recipes and actor-source checks, no validated cell policies |
| [edited-source-timing-audit.json](edited-source-timing-audit.json) | Three edited Classic encounter pages compared with static facts; guide claims and unresolved qualifiers, no observed mechanic or production change |

| File | Content |
|---|---|
| [partition-recommendation.md](partition-recommendation.md) | 00.7 partition evidence and recommendation |
| [partition-configurations.csv](partition-configurations.csv) | Per-configuration Patchwerk page-1 rows for partitions 1 and 2 |
| [partition-evidence-manifest.json](partition-evidence-manifest.json) | SHA-256 of the 319 JSON files in `partition-probe/`: 317 API request records plus 2 derived summaries (`availability-summary.json`, `validated-pools.json`) |
| [quota-estimate.md](quota-estimate.md), [quota-estimate.json](quota-estimate.json) | MC-based quota scenario for v2 Naxx captures (not a bound) |
| [oracle-design.md](oracle-design.md) | PM-3 independent raw-oracle contract for five Naxx bosses |

The probe scripts that produced `partition-probe/` stay outside the tree because
they are exploratory drafts, not maintained code. Their SHA-256 values:

```text
1166852dafdb1f6acd694149e097d47a9fb9b541a1ec2c372de2408b8086ee46 *naxx_partition_probe.py
93989c5dcf461d4c5eab69ab1241e01c2748402f341ea2cc4a45d4e70d3cf365 *naxx_candidate_probe.py
```

Verification on promotion (2026-10-21): all 319 manifest hashes match; gitleaks
found no leaks; partition-2 rows carry negative `fightID` values (for example
-29 in `partition-probe/patchwerk-p2-10-destruction-dps.json`), and
`src/necropsy/wcl/cohort.py` accepts only `fight > 0`.
