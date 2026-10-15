# Engineering verification — 2026-10-15

Starting commit b5b0915; Windows, Python 3.14.6. Full baseline 948 passed,
251 deselected. Existing class/raw fixtures untouched; no analysis/schema change.

## Observed commands and outcomes

- `uv run pytest tests/unit/test_wcl_auth.py tests/unit/test_wcl_pkce.py -q`:
  53 pass, including real callback handling, wrong state/denial/timeouts,
  public secret-free exchange and mode compatibility.
- Focused auth/PKCE/store/acquisition/offline acceptance run: 130 pass.
  Public Auth→CLI analyze→shared snapshot/report flow succeeds with synthetic
  user endpoint; client request refuses before HTTP. Failed switch preserves
  personal data. Permission denial never falls back. Schema remains unchanged.
- `uv run pytest -m "not golden and not live and not acceptance" -q`:
  974 pass, 251 deselected, 339.50s. Collection preceded the separate artifact
  test file; `uv run pytest tests/unit/test_distribution_artifacts.py -q`:
  11 pass. Windows ZIP normalization corrected in that test before its final run.
- `uv run ruff check .`: pass; `uv run ruff format --check .`: 191 files;
  `uv run mypy`: 151 files; `uv lock --check`: 49 locked packages, no drift.
- `uv build`: succeeds through sdist. Independent `uv build --out-dir
  workspace/repro-dist` produces byte-identical wheel AND sdist (SHA-256 compared).
- `uv run python scripts/check_distribution.py --snapshot
  tests/fixtures/haplina_naxx_subset.zip --receipt workspace/distribution-check.json
  --probe-os-store`: passes. Safe receipt copied to `package-receipt.json`.
  Clean environment outside repo, actual installed command version/help,
  installed public CLI + mock token/user API, Hunter replay and its source digest,
  package manifest and byte equality with the emitted JSON/HTML all pass.
- Real `keyring.backends.Windows.WinVaultKeyring` probe: synthetic chunked value
  write/read, replace/read, delete/read pass under a unique service; no actual
  WCL record read or modified. macOS/Linux unverified.
- Unlimited-size gitleaks scans of every extracted wheel/sdist member and replay
  output pass. No fixtures/workspace/cache/plans included; package metadata uses
  generic commands in PACKAGE.md. Pattern scan is not proof of absence.
- `git diff --check`: pass. Code/doc search for plan names, IDs and slice terms:
  only pre-existing JavaScript .slice operations and original design-history
  wording; no new disposable-plan references in shipped code/tests/docs.

## Final suites

Golden/acceptance and browser commands are running; results appended when complete.
An early overlapping golden attempt was cancelled and restarted after fast
checks, keeping large replay suites serialized. Never count that cancellation
as a pass. Browser suite includes small-fixture rendering only.

## Release boundary

No real public app, refresh lifecycle or full query permission matrix observed.
User confirms registration is absent and has creation instructions. No second
account/person/machine receipt and no release approval. Public ID remains unset
in package configuration; explicit ID/env input works. No publishing performed.
Subjects 01/03/05 and master §7/§8 remain open for their recorded obligations.
Cleanup sweep waived by D007; changed surfaces reviewed directly.
