# Contributing

[Home](README.md) · [Documentation](docs/README.md) · [Changelog](CHANGELOG.md)

Build from reproducible inputs, keep uncertainty visible, and describe behavior
a reader can verify. These instructions assume authorized repository access.

## Set up and check a change

Run from the repository root:

```sh
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -m "not golden and not live and not acceptance"
```

These match ordinary CI on Linux, Windows and macOS with Python 3.14. The fast suite
uses the committed subset without the full Git LFS export.
Try the user workflow in [Getting started](docs/getting-started.md).

## Choose the right validation

| Suite | Command | What it checks |
|---|---|---|
| Fast | `uv run pytest -m "not golden and not live and not acceptance"` | Unit and integration behavior with small fixtures |
| Golden | `uv run pytest -m golden` | Full export and registered facts against raw evidence |
| Acceptance | `uv run pytest -m acceptance` | The fact register's verification and resolution status |
| Browser | `uv run playwright install chromium` once, then `uv run pytest -m browser` | The rendered report and playbook in headless Chromium: navigation, keyboard, themes, review marks, print, narrow screens, no network requests; skipped when Chromium is not installed |
| Live | `uv run pytest -m live --run-live -s tests/live/test_live_acceptance.py` | Deliberate authenticated acquisition and artifact checks; requires the environment settings in [live acceptance](docs/live-acceptance.md) |

Before the golden suite:

```sh
git lfs pull
uv run pytest -m golden
```

The raw export is about 80 MB and requires authorized LFS access. The golden
CI workflow is manual, avoiding that download on every push. Acceptance checks
the register rather than replaying raw events; run golden verification too when
changing facts or rules.

## Protect the evidence contract

- Preserve `observed`, `derived`, `inferred`, and `unknown` in JSON. Missing is
  `null`, not an invented zero.
- Preserve coverage and provenance for whole-fight and absence claims.
  Inferred membership stays inferred through calculations.
- Use named, versioned rules for heuristics; explain thresholds and limitations.
- Test meaningful failure cases. Avoid tests that only repeat the implementation.
- Keep docs accurate for commands that exist. Label proposed features as planned.

Read [Evidence](docs/evidence-model.md), [Hunter rules](docs/hunter-analysis.md),
and [the JSON contract](docs/analysis-json.md) before changing analysis behavior.

## Desktop GUI

The [desktop guide](docs/desktop.md) covers Tauri/React prerequisites, engine
bundling, native launch and installer builds. Use `npm ci` in `desktop`,
`npm run build` for TypeScript/Vite verification, and `cargo fmt --check` plus
`cargo clippy --locked -- -D warnings` in `desktop/src-tauri` for Rust checks.
The desktop workflow builds and checks the frozen engine on each target OS.
`scripts/check_desktop_window.py` exercises the actual Windows WebView2 window
offline with an isolated profile/library. Report review marks are stored only
in the parent shell and are restricted to keys from the displayed analysis.

## Handle fixtures carefully

The frozen raw export and oracle files are historical evidence. Do not edit them
to make a test pass. Investigate disagreements and record a resolution; the
oracle is not automatically right.

[Fixture provenance](tests/golden/haplina_naxx/PROVENANCE.md) explains the files
and hashes. `scripts/fixture_tools.py` is developer tooling for member manifests
and subset rebuilding, separate from the CLI.

Keep credentials, tokens, private exports, and identifying player details out
of issues and attachments. Use a sanitized reproduction or reference the
authorized fixture. Put generated analyses in Git-ignored `workspace/`.
Personal live authentication is implemented; see [authentication](docs/auth.md).
Full live acceptance is recorded separately from offline tests. The guided app and public installers use the registered PKCE client; never add
shared-secret or credential-sharing instructions.

## Make a change easy to review

Describe the trigger, resulting behavior, checks actually run, and relevant
limits. For a rule, include evidence and a regression that catches its failure.
For docs, run examples and check links. Templates provide prompts, not a
substitute for judgment. Leave historical source documents intact.

Druid contracts are documented in [Druid analysis](docs/druid-analysis.md). Extend the existing class registry and shared output pipeline; do not apply Hunter ranking rules to another class. Keep real fixture provenance and independently checked facts distinct from synthetic tests. Role inference and raw HPS/DPS do not replace domain review.

## Verify distribution artifacts

Follow [the isolated package check](docs/installation.md#verification-and-removal).
Build the installer bundle with `uv run python scripts/build_release.py --out workspace/release`.
Run `scripts/check_bootstrap.py` on each target OS with a fresh managed-Python path.
Build through the sdist, scan all extracted members with unlimited-size gitleaks,
and test the installed entry point, public flow and offline replay outside the
checkout. A real OS-store probe uses disposable synthetic credentials. CI does
not establish independent-user acceptance or approval to publish.
