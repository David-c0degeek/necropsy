# Unattended Tower capture — design

Status: design, revision 2 (after Codex CHALLENGE #85). Nothing has been
deployed or captured. Owner: Claude; status-page UX and alert wording: Codex.

## Why

The user's order (2026-10-19): prove one full cell, then capture every
remaining raid configuration on the Unraid server (Tower) without either agent
watching. Capture spends Warcraft Logs API points (1440 per hour on the user's
account), not AI usage. The pilot cell closed at f0d8c78.

## Decisions already made by the user

- **Credentials:** an opt-in token-file mode. Necropsy otherwise stores
  credentials only in an OS store, so this is a recorded policy change (ADR
  0023, proposed), not a fallback.
- **Alerts:** through Notifiarr. A test alert must reach the user, who confirms
  receipt, before any capture starts.

## Tower facts (read-only survey, 2026-10-19 11:06 UTC)

- 44 threads, 125 GiB RAM (108 GiB available), Docker 29.5.3, 38 containers.
- Free space: cache 326 GiB, `/mnt/fast` 1.3 TiB, array 22 TiB.
- The daily appdata backup runs at 03:00 and stops and starts containers
  (`appdata.backup` config); the capture container must tolerate this.
- The Notifiarr container runs in `vpnstack` network mode and listens on 5454.
  Passthrough notifications are a notifiarr.com website API
  (`POST https://notifiarr.com/api/v1/notification/passthrough/<api key>`,
  JSON with `notification.name` and `discord.ids.channel`). The local
  container does not offer a documented relay, so alerts go to the website API
  directly. This needs the user's Notifiarr API key and a Discord channel ID,
  both stored like the WCL token.
- Known unrelated open item: array `mdNumDisabled=1` (Tower issue #4).

## Queue

- Universe: 34 legal configurations × 3 raids = 102 raid/configuration runs.
- 25 already have registered real captures (from `coverage.json` actor
  sources). Each must be classified as usable, partial-resumable or partial
  final before it is excluded. The remaining runs (about 77) form the queue.
  The exact list is generated and reviewed, never assumed.
- Entry fields: stable `entry_id`, raid, zone, partition, class_id, category,
  metric, expected faction, an ordered list of reviewed public subject
  candidates (character URL, resolved faction, evidence of raid participation),
  and the queue version hash.
- Subject policy, as used in earlier units: a public player of that class and
  spec whose faction resolves (for example Paracetalol, Rumpldoc). Never the
  user's private characters unless the user says so. Alternate candidates are
  used only after a recorded refusal of the previous one, with a bound of
  three per entry. Refused and partial evidence is kept.
- The queue is built on the PC with a small resolve budget, reviewed by Codex,
  and shipped as a versioned JSON file.

## State machine (PM-4)

`analyze` gains `--outcome-json PATH`, which writes atomically after every
attempt:

- native exit code
- `stop_class`: `none` | `quota-reset` | `quota-reserve` | `source-limit` |
  `refused` | `auth` | `error`
- the observed reset or reserve boundary (UTC)
- checkpoint identity (options digest)
- snapshot archive path and SHA-256 when finalized
- incomplete-entry count and reasons

Runner states per entry:

| State | Entered when | Next |
|---|---|---|
| pending | queue load | running |
| running | attempt starts | per outcome |
| quota-deferred | `quota-reset` or `quota-reserve` | resume (`--resume`, same checkpoint) at boundary + margin |
| finalized-complete | exit 0 | done |
| finalized-partial | exit 4 with `source-limit` only | done (counted separately) |
| refused | `refused` (private, permission, schema, no faction) | next candidate, else done-refused |
| auth-paused | `auth` (token invalid or refresh save failed) | whole queue pauses, Needs attention |
| transient-retry | network or 5xx, bounded (3, with backoff) | running, else Needs attention |

- The first attempt never passes `--resume`. Resume is used only when a
  checkpoint with matching options exists.
- No budget bypass: the runner only schedules after the boundary that
  `analyze` reported.
- Tests use a fake `analyze` that writes structured outcomes. They cover an
  initial quota stop, a reserve stop, a final partial without quota, a
  permission refusal, an auth pause and a restart during a wait.

## Credentials (PM-5)

- New `NECROPSY_CREDENTIAL_FILE` selector. The default OS-store path and its
  errors are unchanged. Setting both this and `NECROPSY_KEYRING_BACKEND` is a
  deterministic error.
- POSIX checks: the file is a regular file (not a symlink), mode exactly 0600,
  owned by the process UID; the parent directory is 0700 and owned by the
  same UID. Any failure refuses, with no fallback.
- Rotation: write a 0600 temp file in the same directory, fsync, `os.replace`,
  then fsync the directory. A failed save raises, and the runner pauses the
  queue as auth-paused.
- The protected directory is mounted, not a single file, so atomic rename
  works.
- Secrets never appear in argv, environment variables, `docker inspect`, logs,
  status, the queue or image layers. The Notifiarr key and channel live in the
  same protected directory.
- Transfer: the user signs in on the PC; a one-time export command writes the
  token file locally (0600), and it is copied over SSH straight into the
  directory. Never through chat or the clipboard.
- Tests: wrong mode, wrong owner, symlink, interrupted rotation, write failure
  (ENOSPC), and an unchanged OS-store default.
- Rollback: unset the selector. Captures stay; OS-stored secrets are never
  migrated.

## Liveness and status (PM-6)

- The runner holds an OS file lock (single instance). It writes `status.json`
  atomically with `heartbeat_utc` (every 60 s), `last_progress_utc` (last
  finalized or changed checkpoint), and `next_retry_utc` during quota waits.
- Restart reconciliation: before advancing, compare the outputs on disk with
  the state. A finalized archive missing from the state is adopted after its
  hash is verified. Archives are never overwritten; each retry writes a new
  attempt directory.
- Independent watchdog: a Tower User Scripts cron job every 15 minutes reads
  `status.json` and alerts if the heartbeat is older than 10 minutes while the
  container should be running, or if progress is older than 2 hours outside a
  planned quota wait. Limit: a full Tower outage cannot alert from Tower
  itself; this is documented, not promised.
- 03:00 backup: the container restart policy is `unless-stopped`; the runner
  resumes from state after the backup restarts it. The watchdog ignores
  03:00–03:45.
- Free-space floor: the runner pauses with Needs attention when the
  destination has less than 50 GiB free, so other Tower apps are not
  affected.
- Capacity: earlier captures are about 280 MB raw each, plus the cache,
  analysis, pages, packages and bounded logs (rotated, 100 MB cap). The
  estimate is under 60 GB in total; the floor still applies.

## Status page (UX lead: Codex)

- Static, sanitized `www/` directory holding only `index.html` and a redacted
  `status.json`, served read-only on Tower's LAN address on a fixed port. No
  Cloudflared route, no Docker socket, no host-wide mounts.
- Headline: Running / Waiting for quota / Needs attention / Finished, plus the
  heartbeat age. When the heartbeat is stale the page shows "Offline since…"
  and drops any live claim.
- Current entry (raid, class, category, metric, faction), next retry in UTC,
  and disjoint counts: complete, partial, refused, pending, deferred. Usable
  archives are counted separately. A per-entry table shows the result, reason
  and retry time. No ETA.
- "Finished" means queue attempts ended. It never means all 952 cells are
  proved.

## Alerts

Start, per-entry refusal, auth pause, Needs attention, watchdog stale or dead,
and finish. Alerts are deduplicated per entry and state, with bounded retries.
Delivery failures are recorded in the status. A `--test-alert` is sent, and
the user confirms receipt, before go-live.

## Deployment

- The image is built from the reviewed release wheel (python slim), with the
  wheel and queue version pinned. Unraid autostart is off.
- Paths: `/mnt/user/appdata/necropsy-capture/{secrets(0700),queue,state,out,www,logs}`.
- Before deploying: follow the Tower maintenance skill. Find a verified
  recovery reference and write a dated `changes/` record. No change to other
  containers, the VPN or parity.
- Smoke test on the PC first, with a fake queue and no live API; then one real
  entry on Tower after the alert test.
- Import: after Finished, copy the outputs to the PC, verify archive hashes,
  then register the evidence through the normal review.

## Implementation slices

1. ADR 0023 plus token-file mode and its tests.
2. `--outcome-json` structured outcome and its tests.
3. Runner state machine, status writer and watchdog script, with fake-clock
   and crash tests.
4. Queue generation and review.
5. Image, status page and smoke test.
6. Tower deploy, alert test and user confirmation, then go.

## Acceptance details (from DESIGN_AGREED #86)

1. A missing or malformed outcome, an unknown quota boundary, or an exit code
   that disagrees with its outcome fails closed to Needs attention. Only a
   genuinely classified transient gets a bounded retry. The runner never
   infers complete or refused, and never invents a quota timestamp. Checkpoint
   lineage carries across immutable attempt directories: `--resume` receives
   the matching checkpoint explicitly. Tests use real `analyze` outcomes as
   well as runner fakes.
2. The controller persists an explicit terminal state. A Finished queue may
   stop its heartbeat; the page and the watchdog show Finished with its
   recorded time, not "dead". A failed fetch shows "connection unavailable"
   plus the last-known status and time. Backup alerts are suppressed only
   inside 03:00–03:45; a worker that hasn't returned after 03:45 alerts.
   Verify the actual backup inclusion and restart behavior before go-live,
   because `unless-stopped` doesn't restart a deliberately stopped container.
3. Subprocess supervision includes a timeout, cancel and graceful SIGTERM,
   with the kill-between-finalize-and-state, lock, disk-full and alert-failure
   tests. On Windows the export path can't promise POSIX 0600, so local
   staging and export use an owner-restricted ACL. UID and 0600 are then
   established and verified on Tower. No broadly accessible temporary token
   file.
