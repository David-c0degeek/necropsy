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

`uv run pytest -m "golden or acceptance" -q`: 246 passed, 986 deselected,
4 known xfailed in 545.12s. The same four accepted exceptions are recorded
in the previous milestone; no new failure or altered fixture.
`uv run pytest -m browser -q`: 41 passed, 1195 deselected in 177.28s.
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

Browser suite completed: `uv run pytest -m browser -q`: 41 passed,
1195 deselected in 177.28s. Golden/acceptance continues. Tools: uv0.11.21,
gitleaks8.30.1; no new tool or dependency installed.


Engineering implementation checkpoint: 0cfdab0, pushed to origin/main.
GitHub run https://github.com/David-c0degeek/necropsy/actions/runs/38773124443
passed Ubuntu lint/format/types/build and the complete final fast suite, including
installed-wheel public/replay checks. Windows CI is still running at this record;
local Windows regression and installed WinVault evidence above are complete.
Linux CI does not certify its real credential backend or independent-account use.
Final follow-up is documentation/review evidence only, with no package-code change.

## Final solo review

Keep: one auth/store/client/acquisition/offline pipeline; separate public/personal
records and explicit user endpoint; immutable evidence, fixed cohorts and all
nine class contracts; installed package and real OS-store evidence.

Fix before closing: `01-public-auth-contract.md` 01.1/01.3 need an actually
registered public ID/callback and observed contract; `03-authorized-acquisition.md`
03.1 needs real public ranking/report/archive permission evidence;
`05-independent-user-acceptance.md` 05.2/05.4 need another person/account/machine
and explicit publication approval. Master §7/§8 stay open. No engineering code
fix remains from the tests/review; none of those human/live obligations is waived.

Record: ADR0007, D004–D007, package-receipt.json, original PM predictions with
terminal engineering resolutions and honest live-horizon calibration, permanent
lessons and docs updated. Source README is separate from generic package metadata.
Whole-repo cleanup waived; changed modules reviewed for reuse, sanitization,
callback lifetime, staged writes, old-record readability and installed behavior.
No new store/cache/normalizer/publisher/report pipeline. Code remains in the
existing cohesive auth module to retain one lifecycle and callback contract.

Risk: no public app ID supplied; live refresh/scopes/archive permission and
independent Windows public-account flow are unobserved. Real macOS/Linux stores
unverified. Windows local proof and Ubuntu synthetic CI do not replace those gates.

Verdict: DO NOT CLOSE the whole plan. Engineering is implemented and verified;
remaining registration/live/independent/publication obligations are explicit.
