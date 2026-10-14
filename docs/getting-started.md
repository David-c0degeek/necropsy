# Getting started

[Home](../README.md) · [Documentation](README.md) · [Next: reading results](reading-results.md)

Run the included sample first. It produces a real report, playbook and
`analysis.json` without WCL credentials and without downloading the full golden
fixture.

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

The command prints the boss and recommendation counts and every file it wrote:

| File | What it is |
|---|---|
| `report.html` | The full report: findings first, then execution, comparisons and evidence |
| `playbook.html` | A per-boss review list with local "Reviewed" checkboxes |
| `analysis.json` | The complete, versioned result the pages are built from |
| `necropsy-<character id>-<zone id>.zip` | A package: both pages, `analysis.json`, CSV tables, evidence files and a checksum manifest |

Open **`workspace/demo/report.html`** in your browser. The pages work straight from
disk and load nothing from the network automatically. They start in the reference's
dark theme; the Theme button offers light and system modes and remembers your choice.
Review marks in the playbook are saved only in that browser, for that exact
analysis. Use `--no-package` to skip the ZIP (an older package of the same name is
then removed so it never looks current). The package holds derived analysis of
real players' logs and is not anonymised: share it only where those logs may be
shared.

By default the analysis database is temporary and removed afterwards.
`workspace/` is ignored by Git, keeping generated results out of your changes.

## 3. Use your own supported export

Necropsy reads the **v6 Hunter deep-export ZIP** from the existing
`wcl_hunter_deep_export.py` exporter, plus its own fixture-subset and live
snapshot v1 formats.
A WCL page, a URL, and an arbitrary ZIP of log files are not that format.
The ZIP contains profile and manifest data, report bundles, and paginated event
streams; see the [database reference](database.md).

The exporter is separate tooling and is not shipped with this CLI. If you do
not already have a supported ZIP, use the included sample or
[acquire your own logs](#acquire-your-own-logs).

Assuming your export is saved as `export.zip`:

```sh
uv run necropsy offline export.zip --out workspace/my-analysis
```

Supported analysis is Classic Era Hunter in Naxxramas. You can now
[sign in to WCL and acquire logs from a character URL](warcraft-logs.md).
No WCL credentials are needed for this offline command.

## Repeat an analysis faster

Keep a database for repeat runs on the same archive:

```sh
uv run necropsy offline export.zip --out workspace/my-analysis --db workspace/analysis.duckdb
```

The archive is verified on every run. A database is reused when its archive hash
and schema version match; otherwise it is rebuilt under ingest's replacement
rules. If it belongs to another archive, choose a new database path or add
`--replace`. Keep the database closed during building or replacement.

Rebuild the pages and package from an existing `analysis.json`, without the
archive or a database:

```sh
uv run necropsy render workspace/my-analysis/analysis.json --out workspace/my-analysis
```

Build just the database for inspection with:

```sh
uv run necropsy ingest export.zip --db workspace/analysis.duckdb
```

## Acquire your own logs

For a Classic Era Hunter's Naxxramas logs, follow the
[WCL connection guide](warcraft-logs.md) to configure your personal client and
sign in, then run:

```sh
uv run necropsy analyze "YOUR_CHARACTER_URL" --cache workspace/wcl-cache --out workspace/my-run
```

Reuse the cache; use an output directory without earlier results. Acquisition
uses the network, saves a raw snapshot under `snapshot/`, and writes the same
report, playbook and package as offline analysis. Check the printed exit status:
`4` means a partial report was written; `2` needs a partition choice; `3` means
finalization stopped with no new snapshot or report. Other failures use `1`.
The CLI has synthetic integration tests and an observed authenticated Windows
run with explicit partial coverage; see [live validation](live-validation.md). [Read coverage and recovery details](warcraft-logs.md#acquire-an-analysis).

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
for preserved export bytes, `generated` for descriptors and wrappers, or
`acquired` for API event pages copied from the verified acquisition cache.
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

For `offline` and `render`, every output is built before anything in the output
folder changes. If building
fails, the folder is left exactly as it was. The new files then replace the old
ones one at a time; if a replacement fails, the old files are put back and the
command reports the error.

Two cases need your attention:

- **The error says the previous files could not all be restored.** The message
  names a `.necropsy-backup-*` folder inside the output folder; it holds the old
  versions of the files that were moved. Compare it with the output folder, copy
  back the old files you want, and delete the backup folder only once you have
  checked the result.
- **The process was killed while files were being replaced** (a crash, power
  loss, or closing the terminal). The output folder can hold a mix of old and new
  files until you recover it, and a `.necropsy-backup-*` folder may remain.
  Restore from the backup folder as above, or simply run the command again.

Those commands only replace `analysis.json`, `report.html`, `playbook.html` and their own
package file; it refuses to touch a folder or link that has one of those names.
Check the command's exit status and message before using the output.

[Read your results →](reading-results.md)

## Druids

Use `analyze URL --category Balance` (or `Feral`, `Guardian`, `Restoration`) with the existing cache/output options. Each category needs a separate output directory. Saved Druid snapshots use the same `offline` command. See [Druid analysis](druid-analysis.md) for evidence, override examples and validation limits.

Balance healing assignments can select `--category Balance --metric hps`; use a
separate output directory for each category/metric selection.
