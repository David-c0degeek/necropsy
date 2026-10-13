# Necropsy

Local-first Warcraft Logs forensics. Paste a WCL character URL; get a same-faction,
class/spec/role-aware benchmark analysis and an offline boss-by-boss playbook.

Status: early development (Milestone A — headless Hunter/Naxxramas analysis).
The CLI can normalize a raw snapshot into a DuckDB analysis database
(`necropsy ingest`); analysis and reports come next. Plan: `tasks/Necropsy-Plan.md`.
Roadmap: `docs/roadmap.md`. Source specification and the investigation that led
here: `docs/origin/`.

## Development

Requirements: [uv](https://docs.astral.sh/uv/), Git LFS (only for the golden suite).

```sh
uv sync --locked
uv run necropsy --version
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest -m "not golden and not live and not acceptance"   # fast suite
```

## Usage

```sh
uv run necropsy ingest tests/fixtures/haplina_naxx_subset.zip --db work/subset.duckdb
uv run necropsy ingest <export.zip> --db work/full.duckdb --sha256 <expected> --replace
```

`ingest` verifies the archive, merges overlapping event streams without losing
genuine duplicate events, records how complete every stream is, and replaces the
database only if the build succeeds. Database layout and the event-identity
rules: [`docs/database.md`](docs/database.md). How every reported value states its
evidence: [`docs/evidence-model.md`](docs/evidence-model.md). Hunter analysis:
[`docs/hunter-analysis.md`](docs/hunter-analysis.md).

### Test suites

| Marker | What it needs | Command |
|---|---|---|
| *(none)* | nothing beyond the clone | `uv run pytest -m "not golden and not live and not acceptance"` |
| `golden` | the full raw export from Git LFS | `git lfs pull && uv run pytest -m golden` |
| `acceptance` | the golden-fact register; fails until every mandatory fact is verified | `uv run pytest -m acceptance` |
| `live` | WCL credentials in the OS keyring | `uv run pytest -m live` (manual only) |

### Clean-clone replay of the golden fixture

```sh
git clone https://github.com/David-c0degeek/necropsy.git
cd necropsy
git lfs pull
uv sync --locked
uv run pytest -m golden
```

### Fixtures

`tests/golden/haplina_naxx/` holds the frozen Haplina export, its oracle outputs
and the golden-fact register; `PROVENANCE.md` there explains each file.
`scripts/fixture_tools.py` is developer tooling (not part of the CLI) that writes
member manifests and rebuilds the fast-test subset `tests/fixtures/haplina_naxx_subset.zip`.
