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

These match ordinary CI on Linux and Windows with Python 3.14. The fast suite
uses the committed subset without the full Git LFS export.
Try the user workflow in [Getting started](docs/getting-started.md).

## Choose the right validation

| Suite | Command | What it checks |
|---|---|---|
| Fast | `uv run pytest -m "not golden and not live and not acceptance"` | Unit and integration behavior with small fixtures |
| Golden | `uv run pytest -m golden` | Full export and registered facts against raw evidence |
| Acceptance | `uv run pytest -m acceptance` | The fact register's verification and resolution status |
| Live | `uv run pytest -m live` | Reserved marker for manual API checks; live acquisition is not implemented yet |

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
Live authentication and any distributed client remain future work; do not add
credential-sharing instructions.

## Make a change easy to review

Describe the trigger, resulting behavior, checks actually run, and relevant
limits. For a rule, include evidence and a regression that catches its failure.
For docs, run examples and check links. Templates provide prompts, not a
substitute for judgment. Leave historical source documents intact.
