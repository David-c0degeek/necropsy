# Haplina Naxxramas golden fixture — provenance

Machine-readable record: [`provenance.json`](provenance.json). Fast tests check
every digest listed there; the golden suite checks the full archive.

## Raw export

| Field | Value |
|---|---|
| File | `raw/wcl_hunter_deep_export_20261012_145328.zip` (Git LFS) |
| SHA-256 | `f249c944ed1c604eff4382f8e4041102d47a5d53c928c88affafcd7f7db39d95` |
| Size | 80,829,461 bytes; 1,407 members; ~1.82 GB uncompressed |
| Origin | `D:\repos\wcl_access_test\exports\wcl_hunter_deep_export_20261012_145328.zip`, byte-identical copy |
| Exporter | WCL Classic Era Naxx Hunter deep exporter v6 (`wcl_hunter_deep_export.py`) |
| Exported | 2026-10-12 12:53–13:09 UTC (`manifest.json` `createdUTC` / `completedUTC`) |
| Auth | `effectiveAuthMode=user` against `https://vanilla.warcraftlogs.com/api/v2/user`; `clientSecretIncludedInExport=false`, `userAccessTokenIncludedInExport=false` |
| Subject | Haplina (character 86583560), Ashbringer EU, Hunter; zone 2006 Naxxramas, partition 1 (S0) |
| Cohort | Overall top 5 Hunters per boss by DPS (75 rows) plus Haplina's best ranking per boss (15 rows): 89 fights in 85 reports; `errors=[]` |
| Member manifest | `raw/entries.sha256` — SHA-256, size and origin of every member; its own digest is recorded in `provenance.json` |

The cohort is the **overall** top five, not a same-faction top five. Facts
derived from it are historical-mode facts.

## Secret scan

`gitleaks 8.30.1`, `gitleaks dir <extracted copy> --redact --max-target-megabytes 0`
over all 1,407 extracted members (1.82 GB), 2026-10-13: **no leaks found**.
gitleaks is heuristic; this is a gate, not proof of absence.

## Fast-test subset

`tests/fixtures/haplina_naxx_subset.zip` (plain Git, 13.6 MB) holds 12 fights:
every recorded Patchwerk fight (Haplina + overall top 5) and Haplina + rank 1 on
Grobbulus, Gothik the Harvester and Kel'Thuzad.

- Every member except `subset.json` is a byte-identical copy of a full-export
  member (`origin=source` in `tests/fixtures/haplina_naxx_subset.sha256`).
- `subset.json` (`origin=generated`) defines the subset scope. The included
  `selection.json` and `manifest.json` are the unmodified full-export originals
  and describe 89 fights; they do not describe the subset.
- Built by `uv run python scripts/fixture_tools.py subset …`; deterministic
  (sorted members, fixed timestamps). Zip bytes also depend on the zlib build
  (`1.3.1.zlib-ng` here); the member manifest does not.

## Oracle

`oracle/definitive/` holds the definitive playbook and its tables — the only
report oracle. `oracle/historical/` holds superseded outputs (forensic pack,
playbook v1, Alliance-normalized v2) kept for traceability. Origins and digests
for all 36 files are in `provenance.json`. Oracle values are expectations to
triage against raw data, not ground truth; see `facts.yaml`.
