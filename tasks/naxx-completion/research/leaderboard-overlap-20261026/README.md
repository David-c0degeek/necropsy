# Live leaderboard overlap, 2026-10-26 (owner option C)

Question: how often do the top fights of different Naxx leaderboards coincide,
that is, could one captured fight serve several configurations' comparisons?

The 34 configurations use 20 distinct class, spec and metric leaderboards
(configurations that differ only by faction share one). One sole-owner window
read the first page of each for all 15 bosses: 300 requests.

```powershell
uv run python tasks/naxx-completion/research/leaderboard-overlap-20261026/analyze.py
```

Check mode writes nothing and fails if a fresh run differs from `receipt.json`.
The pinned input is the compressed bundle in the ignored workspace
(`workspace/leaderboard-overlap-20261026/leaderboard-overlap-bundle.tar.gz`, SHA-256
in the receipt). It holds the raw pages, worklist, readings, failures and both
windows' receipts and state snapshots. A copy stays on Tower under
`/mnt/user/appdata/necropsy-naxx-leaderboard-overlap-20261026/`. A clean checkout
needs the bundle restored at the workspace path before replay.

## Windows

| Window | Start (UTC) | Outcome |
|---|---|---|
| 1 | 17:54 | 0 pages. Hourly points read 1654/3000, but the first request failed with "no database points remaining". Production was restarted with its state unchanged; the failure is kept as evidence. |
| 2 | 17:57 | Waited, production stopped, until the saved quota gate (18:52:20). All 300 pages were fetched by 18:54, ending with about 2494 hourly points remaining. Production restarted with its state unchanged during the window, and then ran its own entry. |

Production is the likely consumer of the hourly database allowance, but this
is not proved. Window 2 only shows that requests made right after the reset
succeeded.

## Findings

A slot is one leaderboard's distinct fight among its top N ranked rows on one
boss. A slot is shared when the same exact (report code, fightID) also appears
among another leaderboard's top N rows for that boss. A fight that several
leaderboards share is counted once per leaderboard. The number of captures that
could merge is therefore slots minus the distinct fights across leaderboards,
not the shared-slot count.

Primary view, top N ranked rows:

| Top N | Slots | Shared | Share | Distinct fights | Could merge |
|---|---|---|---|---|---|
| 3 | 874 | 22 | 2.5% | 861 | 13 |
| 5 | 1449 | 38 | 2.6% | 1428 | 21 |
| 20 | 5784 | 336 | 5.8% | 5610 | 174 |
| 100 | 28445 | 3404 | 12.0% | 26624 | 1821 |

The receipt also gives a secondary view, the first N distinct fights on each
page, which for top 5 is 1500 slots and 42 shared. The most-shared pairs are
natural raid partners: Shadow Priest and Destruction Warlock, Fury and
Protection Warrior, and Holy Paladin and Holy Priest. Of the 29691 rows read,
1246 repeat a fight already in the same leaderboard, meaning several players of
one spec in one raid.

## What this establishes

At comparison depth (top 3 to 5), top fights of different leaderboards
coincide for about 2.5% of slots. That is at most 13 to 21 mergeable fight
captures across all leaderboards and bosses. Going from 5 to 3 comparisons per
boss cuts the nominal comparison slots by 40%.

Neither figure is a measured saving in requests, database points or time.
Cohort selection, faction verification, metadata reads, finalization and
per-actor streams all remain, and their costs here are unmeasured.

## Limits

- First pages only, read once (18:52–18:54 UTC).
- Leaderboard rows carry no faction here, so the coincidence ignores faction.
- A shared fight is not an eligible comparison for either configuration. Faction,
  ownership, the configuration's own ranking row and stream completeness are
  not established.
