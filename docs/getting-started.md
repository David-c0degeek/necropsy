# Your first Necropsy analysis

[Home](../README.md) · [Install](installation.md) · [Read your results](reading-results.md)

## Install and open

Copy the [one install command for your computer](installation.md#one-command).
Setup handles the runtime and opens Necropsy. You do not need to learn Python,
uv, Git, command flags or output folders.

Next time, open the Necropsy shortcut/launcher or type `necropsy`.

## Analyze your character

![The graphical app with guided character setup and an offline example](images/desktop.png)

1. Copy your character's Warcraft Logs link from your browser.
2. Paste it into **Warcraft Logs character link** and choose **Find my character**.
3. Sign in through your browser when asked, then return to Necropsy.
4. Choose the raid partition if asked. Optionally declare your talent tree,
   then choose the WCL comparison category you want to inspect.
5. Choose **Analyze my character**. Activity and the current boss stay visible.
6. The Playbook opens when ready. Start with its priorities and next-pull plan;
   use Report to inspect comparisons and supporting evidence.

Necropsy handles your faction, endpoint, cache and output folder automatically.
It supports all nine Classic Era classes in Naxxramas. Healing/tank categories
keep their own analysis context; unknown evidence remains unknown.

## Stop, close and continue

When Warcraft Logs reaches its hourly allowance, the app saves its progress and
shows how long until it can continue. It sleeps and retries automatically.
Choose **Stop and save** if you prefer to return later. You can then quit.

Your runs remain under **Your analyses**. Select the run and choose
**Continue analysis** to carry on. **Open Playbook** opens a saved report offline.
The app preserves earlier snapshots when it updates a partial report.

An older CLI run can be added with **Add folder** in Your analyses.
Choose its containing folder. Runs with checkpoints resume in place. Runs from
before 0.1.1 recover their completed cached data into a new run while preserving
their old files. Keep both the cache and run folders.

Partial coverage caused by missing/inaccessible logs is explained in the report;
it does not mean you should wait for another quota window. Subscription-gated
archived/private reports still depend on your WCL account permissions.

## Common problems

| What you see | What to do |
|---|---|
| Password vault unavailable | Unlock your OS password vault; Linux needs a desktop Secret Service/KWallet and user D-Bus session. See [installation](installation.md#sign-in-and-analyze). |
| Browser did not open | Choose **Open sign-in** in the app. |
| Hourly allowance reached | Let Necropsy sleep, or **Stop and save** and continue later. |
| Saved output was edited | Preserve your edits; resume refuses to overwrite modified outputs. Start a new run for a fresh analysis. |
| A run saved elsewhere is missing | Use **Add folder** in Your analyses. |
| An unknown or limited comparison | Read the coverage/sample notes; missing evidence is not zero. |
| An old report design | Update Necropsy and regenerate from saved JSON/snapshot using the advanced commands below. |

## Developers and existing CLI users

The [contributor guide](../CONTRIBUTING.md) explains checkout setup and tests.
To try the included four-boss Hunter sample without WCL credentials:

```sh
uv sync --locked
uv run necropsy offline tests/fixtures/haplina_naxx_subset.zip --out workspace/demo
```

Open `workspace/demo/playbook.html`. The same limited sample is bundled in the
GUI under **Try the example**. The full golden export requires Git LFS; see
[fixture provenance](../tests/golden/haplina_naxx/PROVENANCE.md).

Advanced commands remain compatible:

```sh
necropsy analyze "CHARACTER_URL" --endpoint user --spec Balance --faction Alliance --cache ./cache --out ./analysis
necropsy analyze "CHARACTER_URL" --endpoint user --cache ./cache --out ./analysis --resume
necropsy offline snapshot.zip --out ./replayed
necropsy render ./replayed/analysis.json --out ./replayed
```

CLI `analyze` exit codes are 0 complete, 4 partial output, 3 finalization stopped,
2 choose a partition and 1 failure. The GUI and explicit `necropsy tui` handle these states for you.

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
