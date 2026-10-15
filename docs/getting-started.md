# Getting started

[Home](../README.md) · [Documentation](README.md) · [Next: reading results](reading-results.md)

Your first success is an offline analysis of four Naxxramas bosses. No Warcraft
Logs account or credentials are needed for the demo.

## 1. Prerequisites and install

You need [uv](https://docs.astral.sh/uv/), Git and access to this repository.
Necropsy requires Python 3.14 or newer; uv can provision the project's Python.
From a checkout of the repository, run:

```sh
uv sync --locked
uv run necropsy --version
```

Dependency installation may use the network. If you want the released CLI
outside a checkout, follow [installation](installation.md). The included sample
lives in the repository, not in the installed wheel.

## 2. Run the included offline demo

```sh
uv run necropsy offline tests/fixtures/haplina_naxx_subset.zip --out workspace/demo
```

The sample includes Patchwerk, Grobbulus, Gothik and Kel'Thuzad for a Hunter.
It demonstrates actual output with small comparison samples and some unknown
benchmarks. It does not require the full Git LFS fixture.

## 3. Open the result

Open **`workspace/demo/playbook.html`** in your browser. Start with the raid's
priorities, choose a boss and read its actions and next-pull plan.
Switch to **Report** to inspect comparisons and supporting evidence.

| Output | Purpose |
|---|---|
| `playbook.html` | What to work on next, with practical boss guidance and local review marks |
| `report.html` | Investigate what happened, compare players and verify the evidence |
| `analysis.json` | The complete, versioned analytical source of truth |
| `necropsy-<character id>-<zone id>.zip` | Both pages, analysis JSON, CSV tables, evidence and checksum manifest |

Both pages work directly from disk with no server and no automatic network
requests. WCL source links need a connection only when you follow them.
Use the theme control for dark, light or system preference. Review marks belong
to this browser and this exact analysis; they do not change the findings.

The default analysis database is temporary. `workspace/` is ignored by Git.
Add `--no-package` to skip the ZIP; a prior ZIP with the same generated name is
removed to prevent presenting it as current. Packages contain player identities
and are not anonymized.

[Learn how to read your results →](reading-results.md)

## 4. Analyze your own character

Necropsy supports all nine Classic Era classes in **Naxxramas**. Use a character
URL on `vanilla.warcraftlogs.com`, for example the URL format
`https://vanilla.warcraftlogs.com/character/eu/REALM/CHARACTER`.

Sign in once, then acquire into a fresh output directory:

```sh
uv run necropsy auth login
uv run necropsy analyze "YOUR_CHARACTER_URL" --endpoint user --cache workspace/wcl-cache --out workspace/my-run
```

Replace `YOUR_CHARACTER_URL` with the actual character URL. Keep the terminal
open while authorizing Necropsy in the browser. Public sign-in is built in and
needs no shared client secret. It requires `--endpoint user` for acquisition.

An interactive terminal asks for faction and spec/category. For scripts, supply
the actual faction and supported selection explicitly, for example:

```sh
uv run necropsy analyze "YOUR_CHARACTER_URL" --faction Horde --spec Marksmanship --endpoint user --cache workspace/wcl-cache --out workspace/hunter
```

Use [class analysis](class-analysis.md) to choose another class/category.
Druids can use `--spec Balance`, `Feral`, `Restoration` or `Tank`.
Each category/metric selection needs its own output directory. A selected view
keeps missing personal encounters visible; learning examples are not personal
grades.

Acquisition uses the network, saves a snapshot under `snapshot/`, and writes
the same offline outputs as the demo. Reuse the cache across runs and choose a
fresh result directory each time.

| Exit status | Meaning |
|---|---|
| `0` | Outputs written with complete requested acquisition coverage |
| `4` | Outputs written with partial coverage; read the coverage notes |
| `2` | Choose one of the listed partitions and repeat with `--partition ID` |
| `3` | Finalization stopped without new outputs; retain the cache for another run |
| `1` | Follow the printed input, authentication, acquisition or output error |

Complete acquisition can still leave individual measurements unknown.
[Warcraft Logs connection](warcraft-logs.md) covers permissions, endpoint
selection, quota stops, saved snapshots and recovery.

## 5. Reuse a saved snapshot

Replay a Necropsy live snapshot, the included fixture subset, or a supported
**v6 Hunter deep-export ZIP** without login or network access:

```sh
uv run necropsy offline snapshot.zip --out workspace/replayed
```

An arbitrary ZIP or downloaded WCL page is not a supported snapshot.
The historical `wcl_hunter_deep_export.py` exporter is separate tooling and is
not shipped in this CLI. New users should acquire through `analyze`.

Rebuild only the pages and package from existing analytical output:

```sh
uv run necropsy render workspace/replayed/analysis.json --out workspace/replayed
```

Rendering uses saved values; it does not refresh rankings or fetch missing events.

## Common problems

| What you see | What to do |
|---|---|
| Archive not found | Check the ZIP path and current directory; quote paths containing spaces |
| `necropsy` is not recognized | In a checkout use `uv run necropsy`; after tool installation run `uv tool update-shell` and reopen the terminal |
| Public login with the wrong endpoint | Include `--endpoint user` on `analyze` and `resolve` |
| Results already exist | Use a new directory for `analyze`; offline/render intentionally replace their own outputs |
| An unknown or limited comparison | Read the coverage and sample notes; missing evidence is not zero |
| Golden export is a tiny pointer file | The small demo needs no LFS download; for the full fixture see [Contributing](../CONTRIBUTING.md) |
| Sign-in, permissions or quota failure | Follow [connection troubleshooting](warcraft-logs.md#when-sign-in-needs-attention) |

## Advanced reuse and integrity

Keep a database to speed up repeat analysis:

```sh
uv run necropsy offline snapshot.zip --out workspace/replayed --db workspace/analysis.duckdb
```

The archive is verified each time. The database is reused only when its archive
hash and schema match; otherwise it is rebuilt under the ingest replacement
rules. For a different archive, use a new database path or explicitly
`--replace`. Keep the database closed during replacement. A leftover
`.duckdb.wal` requires recovery and closure in the program using it.

`--cross-faction` adds separate context without replacing the same-faction
baseline. `--sha256 DIGEST` verifies a whole archive; `--entries MANIFEST`
verifies individual members. These integrity options also apply to `ingest`.
The member manifest uses `SHA256  BYTE_COUNT  ORIGIN  MEMBER_NAME` with two spaces
between fields, distinct from the export's internal `manifest.json`.
See [database and provenance](database.md) for the detailed formats.

```sh
uv run necropsy ingest snapshot.zip --db workspace/analysis.duckdb
uv run necropsy offline --help
```

## Output recovery

For `offline` and `render`, all outputs are built before existing files change.
A build failure leaves the output folder unchanged. Publication then replaces
files one at a time and attempts to restore previous versions on failure.

If restoration fails, the error names a `.necropsy-backup-*` directory holding
previous files. Compare it with the output folder and restore the files you need
before deleting that backup. A crash during replacement can also leave mixed
versions; restore the backup or rerun the command.

Only `analysis.json`, `report.html`, `playbook.html` and the command's own ZIP
are replaced. A folder or link occupying one of those paths is refused.
Check the exit status before treating results as current.

[Read your results](reading-results.md) · [Documentation home](README.md)
