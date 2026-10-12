# Necropsy

Local-first Warcraft Logs forensics. Paste a WCL character URL; get a same-faction,
class/spec/role-aware benchmark analysis and an offline boss-by-boss playbook.

Status: early development (Milestone A — headless Hunter/Naxxramas analysis).
The CLI currently only reports its version. Plan: `tasks/Necropsy-Plan.md`.
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
