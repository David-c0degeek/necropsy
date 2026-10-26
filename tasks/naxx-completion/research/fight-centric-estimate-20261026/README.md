# Fight-centric capture: offline opportunity estimate, 2026-10-26

Question: could fights captured for one configuration also serve the others, so
that the 34 configurations need fewer captures? And what does the measured
capture cost per kind of request?

```powershell
uv run python tasks/naxx-completion/research/fight-centric-estimate-20261026/estimate.py
```

Check mode writes nothing. It fails if a fresh run differs from `receipt.json`.

## Inputs and their bias

The script reads two pinned inputs, and no WCL call is made:

- **Measurement archive.** The registered archive (Git LFS): 89 fights in 73
  reports, all captured for Druid Balance DPS Alliance (its subject and its
  comparisons).
- **Request journal.** The same capture's 916-request journal, stored in the
  ignored workspace and pinned by SHA-256. It remains on Tower, as recorded in
  `../capture-cost-20261026/`. A clean checkout needs it restored before
  replay.

Every figure below is an observation of this biased sample, or a conditional
opportunity built from it. None of it is a measured requirement for the other
33 configurations.

### Identity

- A character is the rankings row's global WCL character `id`. Its name, server,
  region and class must agree on every row with that id; none of the 1249 ids
  conflicts.
- Within each report, the row binds to playerDetails by name, server and region,
  with a strict class check. Faction comes only from that
  `combatantInfo.factionID`.
- Report-local actor IDs are never merged across reports.
- 885 rows are excluded, not guessed: 801 without an observed faction or
  identity, and 84 without a unique global id and class-checked binding. The
  counts below therefore cover observed eligible presence only, not every player
  in the fight.
- Every fight is bound to its boss from its own rankings block, so the sample
  covers all 89 fights over all 15 bosses. 20 of the 89 have no observed eligible
  configuration at all; they stay in the sample and count as 0 in the per-fight
  figures.

### Sessions

A report is one uploaded log, kept with its start and end. It is not a proven
calendar raid, and guilds are context only.

### Ranks

Ranks come from the DPS-metric rankings query, so HPS configurations count as
present only. Rank text is kept as published: 168 kept DPS rows have exact
ranks and 1798 have approximate ones (such as `~1` or `~5003`). Exact-only
figures are the primary result. Figures that include approximate ranks are a
separate conditional point estimate, not a bound: `~1001` could lie inside rank
1000 and `~999` outside it.

Exact ranks are scarce and unevenly spread. Balance has 46 exact and 27
approximate retained rows, Fury 14 and 961, Fire 29 and 213. The exact-only
tables therefore measure the exact evidence available. They do not prove that
other configurations seldom share high-ranked fights, and the real overlap
stays unresolved.

## Findings

### Observed eligible configurations per fight

Each fight shows 0–12 configurations with an observed, eligible player (median
10). Configurations per fight, median (max), at a DPS global rank of at most:

| Rank | Exact only | Including approximate |
|---|---|---|
| 5 | 0 (2) | 0 (2) |
| 20 | 1 (2) | 1 (2) |
| 100 | 1 (5) | 1 (5) |
| 1000 | 1 (7) | 3 (7) |

### Comparison-slot presence

A cell is a DPS configuration-boss pair; there are 390. Counted here are
distinct same-configuration characters other than the measurement subject,
present in a captured fight for that boss within the rank bucket. This is a
presence threshold, not eligibility. Selection, a faction-qualified ranking row,
ownership, metric and stream completeness are not proved for any of them.

| Rank | Cells with 5 or more | Share of the 1950 comparison slots |
|---|---|---|
| Exact, 100 | 1 | 3.6% |
| Exact, 1000 | 9 | 7.4% |
| Including approximate, 100 | 4 | 4.9% |
| Including approximate, 1000 | 20 | 13.4% |

### Subject reuse

Subject reuse cannot be judged from this archive. Each report bundle holds only
its selected fights: 59 reports have 1, 12 have 2 and 2 have 3. The best
coverage by one global character id across separate reports is 10 of 15 bosses,
which is not one session.

### Coverage and scale

15 of the 34 configurations are observed, all of them Alliance. 34 × (1 subject
+ 5 comparisons) × 15 bosses = 3060 nominal actor-boss slots. These are slots,
not fights or requests.

## Measured costs of this capture

From the journal, 916 successful requests:

| Requests | Count |
|---|---|
| Report, acquisition | 248 |
| Report, finalization | 74 |
| Event, encounter-All | 179 |
| Event, actor target | 189 |
| Event, actor source | 97 |
| Event, critical | 89 |
| Leaderboard | 15 |
| Subject | 15 |
| Combatant context and prelude | 5 each |

- The 189 actor-target requests are the ones 0.7.0 no longer makes.
- **Report grouping.** Grouped by scope and full request context (site, endpoint,
  query and every variable except the fight list), plus the revision each answer
  reported, the report queries collapse to 190 groups in acquisition and 73 in
  finalization, 59 fewer in all. Acquisition and finalization stay independent.
  A merged answer is not proved equivalent to the separate ones, so this is an
  opportunity, not a measured saving.
- Points are not modelled. The readings are account-wide, and the database
  allowance that stops finalization is hidden.
- Report cost is not just the subject and 5 comparisons. Cohort selection reads
  25 metadata rows per boss (`live_cohort`: deep 5, metadata 25, minimum
  same-faction 3, up to 10 pages) and verifies their factions. The 248
  acquisition report requests covered 190 reports, while the archive kept 73.

## Conditional counterfactual, one configuration's capture

This assumes the same operations, paging and selection as the measured
capture:

- Requests start at 916.
- Without the target requests (0.7.0), the capture would have needed 727.
- If report grouping applies, it would need 668. That figure holds only if
  merged report answers are proved acceptable.

Savings across configurations from reusing comparison fights are unknown. The
slot-presence shares above are presence statistics, not bounds on requests or
pages. Pages differ in size, and metadata reads and finalization would remain.

## What this establishes, and what it does not

In this sample, the exactly ranked evidence shows few top-ranked players of other
configurations in fights captured for one configuration. Given how scarce exact
ranks are, this does not establish how much reuse is possible.

This sample cannot show:

- how often the top fights of different configurations coincide in their own
  leaderboards;
- whether single raid sessions cover all 15 bosses for subjects.

Standards choices, such as comparison depth or the rank window, would change the
count of slots; this estimate does not decide them.

## Retained leaderboard inventory (operator-reported observation)

A read-only Tower inventory on 2026-10-26 checked
`/mnt/user/appdata/necropsy-naxx-capture-20261023/out/*/candidate-0/.necropsy-run/requests`.
These inputs are not pinned by this receipt. Only 3 of the 34 production
entries held leaderboard responses:

| Entry | Leaderboard pages | Bosses |
|---|---|---|
| Balance DPS Alliance | 15 | 15 |
| Balance DPS Horde | 16 | 15 |
| Balance HPS Alliance | 15 | 15 |

The other 31 entries had no journal records. The committed
`../capture-leaderboard-pages.json` has name, server and amount only, with no
report or fight. Coverage for the other configurations is unknown.

From those retained responses, the top-100 (report, fight) sets of Balance DPS
Alliance and Balance HPS Alliance coincided for 46 of 1499 rows (3.1%). This is
one dated observation of two views, on different metrics and possibly
different capture times. It is not a most-favourable case. It does not show
that measuring the other configurations is of little value.

## Proposed live measurement, not run

A separate sole-owner window, with production paused, would read the first
leaderboard page for each of the 34 × 15 configuration-boss pairs: 510
first-page requests as a planning count. Pagination, faction and identity gaps
and report validation may need more requests, and the quota cost is unknown. It
would measure leaderboard fight coincidence directly.
