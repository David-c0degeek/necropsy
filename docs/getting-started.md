# Getting started

[Home](../README.md) · [Documentation](README.md) · [Next: reading results](reading-results.md)

Run the included sample first. It produces a real `analysis.json` without WCL
credentials and without downloading the full golden fixture.

## 1. Set up the project

You need a repository checkout and [uv](https://docs.astral.sh/uv/).
The project requires Python 3.14 or newer; the tested baseline is Python 3.14.
Run from the repository root:

```sh
uv sync --locked
uv run necropsy --version
```

Dependency setup may use the network. Analyzing a saved archive is offline.
Authorized access is required to clone this private repository.

## 2. Try the sample

```sh
uv run necropsy offline tests/fixtures/haplina_naxx_subset.zip --out workspace/demo
```

The subset includes selected fights for Patchwerk, Grobbulus, Gothik, and
Kel'Thuzad. It demonstrates the workflow, rather than a full Naxxramas run.
Expect smaller comparison samples and more unknown benchmarks than in the full
fixture.

The command prints the result path and the boss and recommendation counts.
Open **`workspace/demo/analysis.json`** in your editor. The output is JSON today;
a browsable HTML report and playbook are planned.

By default the analysis database is temporary and removed afterwards.
`workspace/` is ignored by Git, keeping generated results out of your changes.

## 3. Use your own supported export

Necropsy reads the **v6 Hunter deep-export ZIP** from the existing
`wcl_hunter_deep_export.py` exporter, plus its own fixture-subset format.
A WCL page, a URL, and an arbitrary ZIP of log files are not that format.
The ZIP contains profile and manifest data, report bundles, and paginated event
streams; see the [database reference](database.md).

The exporter is separate tooling and is not shipped with this CLI. If you do
not already have a supported ZIP, use the included sample; acquiring an export
from a character URL inside Necropsy is planned.

Assuming your export is saved as `export.zip`:

```sh
uv run necropsy offline export.zip --out workspace/my-analysis
```

Supported analysis is Classic Era Hunter in Naxxramas. Live fetching,
authentication, and other classes or raids are future work. No WCL credentials
are needed for this offline command.

## Repeat an analysis faster

Keep a database for repeat runs on the same archive:

```sh
uv run necropsy offline export.zip --out workspace/my-analysis --db workspace/analysis.duckdb
```

The archive is verified on every run. A database is reused when its archive hash
and schema version match; otherwise it is rebuilt under ingest's replacement
rules. If it belongs to another archive, choose a new database path or add
`--replace`. Keep the database closed during building or replacement.

Build just the database for inspection with:

```sh
uv run necropsy ingest export.zip --db workspace/analysis.duckdb
```

## Choose your context and integrity checks

| Option | Use it for |
|---|---|
| `--cross-faction` | A separate view of all recorded cohort entries; the same-faction baseline stays separate |
| `--sha256 DIGEST` | Refusing an archive whose SHA-256 differs from your expected digest |
| `--entries MANIFEST` | Checking every archive member against a member manifest |
| `--replace` | Explicitly replacing a database associated with another archive |

Integrity and replacement options apply to both `ingest` and `offline`.
The member manifest is a text file with one member per line and two spaces
between fields: `SHA256  BYTE_COUNT  ORIGIN  MEMBER_NAME`. `ORIGIN` is `source`
for preserved export bytes or `generated` for a generated subset descriptor.
The fixture's [provenance record](../tests/golden/haplina_naxx/PROVENANCE.md)
lists the provided manifests. This is different from the export's internal
`manifest.json`.

```sh
uv run necropsy --help
uv run necropsy offline --help
uv run necropsy ingest --help
```

## When something goes wrong

| What you see | What to do |
|---|---|
| Archive not found | Check the ZIP path and current directory; quote paths containing spaces |
| Digest or member mismatch | Confirm the archive and manifest belong together; investigate the failed check |
| Database belongs to another snapshot | Use a new database path, or `--replace` if replacement is intended |
| A `.duckdb.wal` blocks ingest | Close the database in the program using it; after a crash, recover and close it there before retrying |
| Golden export is a tiny pointer file | Run `git lfs pull` with authorized access; see [Contributing](../CONTRIBUTING.md) |
| A benchmark is `unknown` | Read its `note` and cohort size; missing evidence or fewer than three known values may explain it |

A failed run exits with an error and does not write a partial `analysis.json`.
A previous successful file in that output directory can remain; check the
command's exit status and result message before using it.

[Read your results →](reading-results.md)
