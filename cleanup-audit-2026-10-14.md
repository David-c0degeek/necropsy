# Cleanup audit — 2026-10-14

Reviewed baseline: `8aa4988` and its existing application/test/configuration tree.
This is a whole-repository, report-only sweep. Generated `workspace/`, `.venv`,
Git/mailbox state, frozen raw/oracle fixtures and generated client tables are
excluded from removal candidates. Their consumers and provenance were checked.

## 1. Executive summary

No high-confidence application-code or dependency removal is recommended.
One documentation-currency finding requires a small correction. Two apparent
duplications are deliberately retained. Every candidate below is triaged.

The system was mapped through the installed CLI in `pyproject.toml`,
[command registration](src/necropsy/cli.py), authentication/acquisition,
snapshot readers, normalization, analysis, resource-loaded rule/template assets,
rendering and publication. Developer scripts, manual live acceptance, pytest
hooks, browser tests and both CI workflows were included. No server routes,
background scheduler or DI container is configured.

Existing tooling: ruff check/format and full mypy passed; the full suite passed
1,018 tests with one disabled live check and four expected failures before the
localized anonymous-ID guard, whose fetch/acquisition regression set passed 70.
No dedicated unused-dependency or license/advisory scanner is configured; this
audit makes no dependency-security or license-compliance claim.

Runtime dependencies have concrete consumers: DuckDB normalization/analysis,
HTTPX WCL requests, keyring credential storage, Jinja rendering, Pydantic schema
validation, PyYAML rule loading and Typer commands. Playwright is used by
[browser tests](tests/browser/test_report_browser.py); types-PyYAML supplies
mypy stubs, and uv_build is the configured build backend.

## 2. High-confidence safe cleanup

**C1 — stale implementation-status documentation.** Category: doc/comment drift.
Confidence: High. Change risk: Low.

Evidence: [CONTRIBUTING.md](CONTRIBUTING.md) describes the live marker as reserved
and acquisition/authentication as future work; the actual
[manual live entry point](tests/live/test_live_acceptance.py) is operational and
explicitly gated by `--run-live` plus a URL. Module introductions in
[acquire.py](src/necropsy/wcl/acquire.py) and
[cohort.py](src/necropsy/wcl/cohort.py) still say no CLI uses them, despite
[run_analyze](src/necropsy/wcl/analyze.py). Query comments in those modules and
[fetch.py](src/necropsy/wcl/fetch.py) also need wording consistent with real
authenticated attempts, without claiming a successful acceptance receipt.

Hidden-use checks: source imports, CLI registration, manual test and documentation
commands were checked. Module docstrings are documentation; no code or API
surface needs deletion. Correcting them removes misleading setup guidance.

Recommended action / triage: **fix now**, after this report is emitted, in a
documentation checkpoint. Preserve the personal-client distribution gate and
pending authenticated end-to-end acceptance. Before changing: compare commands
with `pytest --help`, the live test gate and current CLI help. After changing:
`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, relative-link
checks and the two opt-in/forbidden-factory tests. A full behavioral rerun is not
needed for prose-only corrections.

## 3. Medium-confidence cleanup requiring verification

**C2 — repeated strict integer helpers.** Category: duplicate small validation.
Confidence: High that repetition exists; Medium that consolidation helps.
Change risk: Medium.

Evidence: private `_int` helpers in
[acquire.py](src/necropsy/wcl/acquire.py),
[cohort.py](src/necropsy/wcl/cohort.py) and
[fetch.py](src/necropsy/wcl/fetch.py). Other parsing helpers, including legacy
normalization, have different coercion contracts and should not be assumed equal.

Hidden-use checks: direct callers, cache-key validation and malformed-input tests
were checked; these functions are not runtime plugin entry points. A future
consolidation would keep one strict helper and migrate only equivalent WCL
callers. It would save very little and introduce shared coupling.

Triage: **won't fix** in this milestone; short local validators are easier to
audit at their boundaries. Before any later consolidation: compare boolean,
null, numeric-string, float and integer behavior. Verification afterward:
`uv run pytest tests/unit/test_wcl_cohort.py tests/unit/test_wcl_fetch.py
tests/unit/test_wcl_acquire.py tests/unit/test_wcl_cache.py`.

## 4. Risky cleanup candidates

**C3 — historical reader and separate publication strategies.** Category:
apparent parallel/legacy surfaces. Confidence: High that they remain necessary.
Removal risk: High.

[V0Snapshot](src/necropsy/snapshot/v0.py) serves existing v6 exports and supplies
the shared lower-level layout to the live reader. The pre-generation live fixture
also proves backward compatibility. It is not abandoned code.

[Cache publication](src/necropsy/wcl/cache.py) is no-clobber, while
[derived output publication](src/necropsy/report/publish.py) intentionally replaces
files with backup/rollback. Their similarly named functions have different
observable contracts. A unified replacement helper would weaken evidence safety.

Hidden-use checks: `open_snapshot`, `ingest`, `write_snapshot`, `write_outputs`,
historical/live tests and public offline/render commands were checked.
Triage: **won't fix**; retain both readers and both contracts. Before any future
replacement: establish exact compatibility/no-clobber semantics and migration.
Verification would require archive/cache/publisher tests plus full historical
replay and old live-v1 replay.

## 5. Duplicate/parallel systems to consolidate

No further justified consolidation was found. C2 names the only small overlap;
if revisited, one strict WCL integer helper would survive and equivalent callers
would migrate. C3 is an intentional difference, not a consolidation target.

## 6. Over-engineered areas to simplify

No deletion recommendation supported by the available evidence. The declarative
schema, graded evidence model, resource-loaded rules and snapshot-reader seam
serve active behavior. Public exports, empty package initializers and pytest
hooks cannot be declared dead solely from ordinary text-reference counts.

The acceptance module is deliberately consumed by the documented manual pytest
workflow and its synthetic checks. It is not an undisclosed production route.

## 7. Stale documentation/tests/configuration

C1 is the only required currency fix. Historical source documents and oracle
files are provenance records, not current operational guides; keep them intact.
The former per-revision immutable-bundle test was intentionally replaced by
generation/coexistence regressions after live evidence disproved that assumption.

## 8. Phased cleanup plan

1. Correct C1 wording and record verification in a documentation checkpoint.
2. Retain C2/C3 for the reasons above. No runtime removal or dependency pruning.
3. Re-run a whole-repo sweep after adding further classes/raids or a desktop
   client; larger findings then belong in a new plan, not the closing disposable
   milestone plan.

## 9. Validation checklist

- CLI, manual diagnostics, resource/config activation and CI consumers mapped.
- All dependency categories checked for concrete usage.
- Current lint/type and recorded full/focused test results cited above.
- No removal proposed solely because a symbol lacked local references.
- All findings triaged. C1 was corrected after emitting this report, outside the
  report-only audit step; lint/format and documentation verification are recorded
  with its checkpoint. C2/C3 remain retained for the reasons above.
- Frozen evidence, derived artifacts, credentials and caches are not deleted.

## 10. Open questions / human confirmation

None needed for the recommended prose correction or retention decisions.
Authenticated receipt review, broader Hunter-mechanics review and the public PKCE
distribution gate remain separate acceptance obligations. This audit does not
complete those gates.
