# Check an authenticated live run

[Documentation](README.md) · [WCL connection](warcraft-logs.md) · [Reading results](reading-results.md)

This manual check acquires real WCL data and verifies the saved snapshot, analysis
and package. Preparing and testing the harness with synthetic data does not
complete authenticated acceptance. A partial acquisition can pass artifact checks;
it still requires review of its coverage notes. This check does not validate game
mechanics or prove every recommendation correct.

## Before the run

Register `http://localhost:8765/callback` for your personal confidential WCL client
and complete `uv run necropsy auth login` interactively. Follow the
[sign-in guide](warcraft-logs.md); do not put secrets in environment variables,
commands or the receipt. Public-client PKCE remains required before distribution.

Choose a supported Classic Era Hunter character URL, a reusable cache and an output
directory without prior results. An optional historical comparison requires a saved
historical `analysis.json` for the same character, Naxxramas and selected partition.
Do not substitute a historical report HTML or arbitrary JSON file. Without a
baseline, the receipt says the comparison was not performed.

## Run deliberately

From the repository root, in PowerShell:

```powershell
$env:NECROPSY_LIVE_URL = 'YOUR_CHARACTER_URL'
$env:NECROPSY_LIVE_CACHE = 'workspace/wcl-cache'
$env:NECROPSY_LIVE_OUT = 'workspace/live-check'
uv run pytest -m live --run-live -s tests/live/test_live_acceptance.py
```

Replace `YOUR_CHARACTER_URL` with the intended WCL character URL. Both `--run-live`
and a nonempty URL are required. A normal test run stays offline even if the URL
variable remains set. The explicit manual command uses credentials and the network.

Optional settings:

| Variable | Meaning |
|---|---|
| `NECROPSY_LIVE_ENDPOINT` | `client` by default, or `user` for the entire run |
| `NECROPSY_LIVE_PARTITION` | A positive partition ID when the choice is ambiguous |
| `NECROPSY_LIVE_HISTORY` | Path to matching historical `analysis.json` |
| `NECROPSY_LIVE_WAIT_FOR_RESET` | Set exactly `1` to allow one bounded observed reset wait |

Set optional values before running, for example:

```powershell
$env:NECROPSY_LIVE_PARTITION = 'YOUR_PARTITION_ID'
$env:NECROPSY_LIVE_HISTORY = 'workspace/historical/analysis.json'
```

Replace `YOUR_PARTITION_ID` with a numeric ID returned by `necropsy resolve`.
Use a new output directory for each acquisition. Missing or mismatched explicitly
supplied history is an error. If partition resolution needs a choice, resolve the
URL first and use one of the returned partition IDs. Keep permission failures on
the selected endpoint; do not treat an endpoint change as a successful retry.

If an older cache format is refused, set `NECROPSY_LIVE_CACHE` to a new directory
and retain the old cache. Archived content may require
`$env:NECROPSY_LIVE_ENDPOINT = 'user'` and subscription archive access; this is a
deliberate configuration choice, not an automatic fallback. Choose a new output
directory for that attempt too.

## Read the result

For a run whose fresh acquisition and finalization span an hourly budget,
set `NECROPSY_LIVE_WAIT_FOR_RESET=1` explicitly. This uses the same option as
`necropsy analyze --wait-for-reset`: one observed reset wait, at most one hour,
with cancellation available. The same selection stays in memory and combined
reports are still finalized fresh. The output lock remains held during the wait;
another run targeting that output is refused. Stream locks are held only during
their own fetch, so a wait inside a fetch can keep that stream locked. No second
wait is allowed; another budget stop retains the cache and needs a fresh output.
The default remains immediate stopping. The receipt records the opt-in, whether
a wait occurred, its observed countdown, reading age and elapsed duration. An
assumed post-reset counter is not an observed reading or an exact accounting bill.

If either opt-in requirement is missing, the test skips before using credentials.
The cache/output defaults are `necropsy-live-cache` and `necropsy-live-out`; set
the paths above to keep generated files under the ignored `workspace/` directory.

The receipt is `live-acceptance.json` in the output directory. It is not replaced.
It records complete or partial acquisition coverage, the original analyze exit
code, endpoint and partition, snapshot/package hashes, the actual run summary,
scanner status and historical comparisons when available.

Artifact checks cover the live snapshot and its companions, live analysis identity
and requested scope, nonempty pages, and package checksums. Complete acquisition
coverage can still produce unknown analysis values. When history lacks a requested
boss, that comparison is unavailable, not a measured difference. Differences in
selected fights and cohort players are expected because historical exports contain
the recorded overall top five and live acquisition selects same-faction samples;
rankings can also change over time. Review unexplained differences separately.

The points line is an account-wide change between observed readings and may
include other activity. It stays unknown when the accounting period cannot be
proved. It is not an exact bill for the analysis or a sum of cached stream costs.

Secret scanning reports passed, findings, unavailable or failed. If gitleaks is
missing, the receipt says unavailable; that is not a clean scan. A pattern scan
with no findings does not prove no secrets exist. Findings or scanner failures
need investigation before sharing results. Structural credential-field checks
also do not establish complete absence of credentials.

## Report back

Provide the test result, receipt's acquisition/scan/comparison statuses, selected
endpoint and partition, and any partial-boss reasons or unexplained differences.
Share the receipt only after reviewing it: it contains player names and paths.
Never send client secrets, tokens or credential-store exports. The raw snapshot
and analysis may contain private player data; keep them local unless needed for
an authorized investigation.

A successful manual run is evidence for authenticated acquisition and artifact
integrity. Sign-in prerequisites and domain review are tracked separately; the
harness does not silently close them. If report generation fails after the raw
snapshot is saved, follow the printed offline recovery command and retain its
member manifest. Read the error before rerunning acquisition.
