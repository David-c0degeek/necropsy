# Release 0.7.1 and Tower worker rollout

Owner-authorized under D021. Claude drives; Codex reviews. Main `463e489`
carries unit 7: three comparisons per boss, the comparison follow-up register,
and the reconciliation record. Codex agreed it in round 2 with blocking 0,
after a Tower gate, golden and browser run on its exact tree. This release only
stamps the ten version surfaces at 0.7.1 and dates the changelog. The PC
produces no evidence (D020/D021). Verification ran on Tower and GitHub CI.

## Pre-publication proof

- Candidate tree `aebde760` was verified on Tower: gate with 2807 fast tests
  passed and 9 skipped, golden 569 passed, browser 96 passed. Bundle
  `release-071-candidate.tgz` has SHA-256 `24a52c0e41d8`.
- Codex agreed in round 1. The commit is
  `af900ecf0e611267b34fa3fb9b001bdd6cc40a8c`.
- Exact-SHA workflow_dispatch runs
  [CI 40500974484](https://github.com/David-c0degeek/necropsy/actions/runs/40500974484)
  and [Desktop 40500978240](https://github.com/David-c0degeek/necropsy/actions/runs/40500978240)
  passed on all three CI operating systems and all four desktop platforms.
- On Tower, `check_assets.py` checked the four platform artifacts:
  - the shared wheel, sdist and installers are identical across platforms;
  - every per-platform checksum and all four bootstrap receipts pass;
  - all 148 wheel package files and both installers equal the Git blobs at
    `af900ec`.
  - The first run false-failed: it compared wheel directory entries with Git
    tree listings. That attempt is kept.
- All nine draft server digests and sizes matched the Tower-verified set.

## Publication

[v0.7.1](https://github.com/David-c0degeek/necropsy/releases/tag/v0.7.1) was
published at 12:27:11 UTC. Tower downloaded all nine files without
authentication at 12:27:35 UTC. Every hash matched, and `SHA256SUMS`
(`294338238e0c`) is byte-equal to the verified one. The tag and remote main
are both `af900ec`.

## Tower rollout (live observation, after publication)

- **Image.** The context was staged from the public assets, with the same queue
  and pin as 0.7.0 (`888b8d8d`). The runner (`de277bab`), Dockerfile,
  entrypoint, requirements and status page are unchanged; only the wheel
  differs. The image is
  `sha256:d72b207a2f9c7e50167a35ca6658972e814a1b2099c236ca179edaa281fe45dd`.
- **Network-none proof** as UID 99:100. All HTTP answers are synthetic; the
  bundle was generated on Tower from the integration fixtures at `af900ec`.
  - A fresh acquisition replays the 22-request depth-3 cassette in order, with
    12 event requests and no actor target request. It writes a strict v3
    archive at depth 3 with no issues.
  - A depth-3 resume over a depth-5 cache selects the depth-5 prefix, with no
    event request.
  - The strict reader opens the synthetic depth-5 archive. It also opens both
    real historical depth-5 archives (`caa19938`, `837485a9`, Tower originals
    with their entries), with no issues.
  - The first attempt failed only on unreadable empty lock files in the cache
    copy. They were removed and the bundle made world-readable; the attempt is
    kept.
- **State.** The 0.7.0 and 0.7.1 images loaded the same live state copy, which
  had a capture in flight, to byte-identical results.
- **Swap** at 12:36 UTC. `rollout_071.sh` waited for a waiting controller with
  no capture child, paused the watchdog cron, and re-checked. It then ran
  `rollout_071.py`, adapted from the reviewed 0.7.0 rollout, and restored the
  watchdog. Results:
  - new worker `2cc0cdcaea22` on 0.7.1, with identical mounts, UID 99:100, init
    and restart policy;
  - entry records unchanged and no state field added;
  - www container unchanged; watchdog exit 0.
  - The 0.7.0 worker is kept stopped as `necropsy-capture-before-071-20261027`.
    Afterwards the older `before-070` container, whose definition is backed up,
    and its image were removed.
  - The receipt is `rollout-receipt.json` in
    `/mnt/user/appdata/necropsy-naxx-release-071-20261027/`, SHA-256
    `4ebea3106b44`.
- The first wrapper attempt failed safe on a `docker top` field error and
  changed nothing. Its log is kept.

## Review after the swap (Codex #119)

Codex's STOP on the rollout scripts arrived after the swap. The capture had
already returned to an idle quota wait, so the armed wrapper ran at once; no
window to object was left. Codex raised four points about the executed
scripts:

- unchecked watchdog backup, pause and restore steps;
- an order-sensitive mounts comparison;
- restart policy and network not asserted;
- `quota_until_utc` and the controller excluded from the state comparison.

Each was checked against the actual result on Tower:

- the watchdog backup holds both files, the live files equal the pre-pause
  backup, and the effective cron has one entry;
- mounts are equal by destination and attributes, and in raw order;
- restart policy, network, UID, init, stop timeout and log config equal the old
  worker's;
- `quota_until_utc` is unchanged (13:34:27Z), the controller was waiting before
  and after, and the entries are equal with nothing in flight.

Codex's independent read-only checks at 12:39:05Z agree (mailbox 120). These
observations show that this swap succeeded. They do not show that the executed
scripts handle failures safely. Their error paths are untested: unchecked
backup, pause and restore steps, an order-sensitive mounts check, and missing
restart, network and quota assertions.

The executed `rollout_071.sh` (`cc7c98eec916`) and `rollout_071.py`
(`6a63b25133e4`) must not be reused unchanged. Corrected versions sit beside
them, not yet executed and pending review: `rollout_fixed.sh` (`abe92f6a9945`)
and `rollout_fixed.py` (`6be8fdfb309f`). Any future rollout needs reviewed
hardened scripts first. Arming a wrapper also needs an explicit hold, so that a
reviewer can act before the boundary is crossed.

Rollback: 0.7.0 cannot read archives captured at depth 3. Stop the worker and
preserve state before any rollback. The first real depth-3 archive still needs
strict reading and intake. The targeted follow-up capture that consumes
`followup-comparisons.json` is still unfinished.
