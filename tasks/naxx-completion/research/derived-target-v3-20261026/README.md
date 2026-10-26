# Derived target streams: v2-to-v3 comparison, 2026-10-26

`convert_and_compare.py` rewrites the registered v2 measurement archive as
snapshot format 3. Each of its 97 actor target streams becomes a derived stream
(ADR 0024), and the script compares the analysis of both archives:

- The new reader accepts the v3 copy with no issues.
- Of 1,860,033 compared `analysis.json` leaf paths, exactly two differ:
  `snapshot.archive_sha256` and `snapshot.format`. They honestly describe a
  different file.
- `report.html` and `playbook.html` are equal after substituting exactly the
  labels that follow from those two fields: the analysis digest (full and its
  12-character prefix), the archive digest (its 12-character prefix) and the
  format. The receipt counts each label's occurrences on both sides.

```powershell
uv run python tasks/naxx-completion/research/derived-target-v3-20261026/convert_and_compare.py
```

Check mode writes nothing and fails if a fresh run differs from `receipt.json`.
The v3 copy is built in a temporary directory, so its own digest is not pinned.

Separate checks, recorded in the review request:

- Every old archive replays byte-identically under the new code: 18 legacy
  archives (54 outputs), the full Haplina export and this measurement archive.
- Released 0.6.1 refuses a v3 archive with `SnapshotError` at marker
  validation.

`oracle-compat.json` covers the freezer's own provenance. The freezer gained an
independent derived-parent check, so its `tool_sha256` changed. All 53 committed
DPS oracles were recomputed with the prior freezer (96f728c) and the current
one, using `oracle_compat.py`. Under the current freezer, each oracle has exactly
one added strict-check difference, `/tool_sha256`. Arithmetic, raw rows and
residuals are unchanged. Strict check is not weakened.
