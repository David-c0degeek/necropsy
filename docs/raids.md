# Raid modules

Necropsy supports Naxxramas, Temple of Ahn'Qiraj (AQ40), Blackwing Lair (BWL)
and Molten Core (MC), for all nine Classic Era classes.

Choose **Raid** before **Find my character** in the desktop or terminal app.
Each analysis belongs to exactly one raid and produces its own snapshot,
`analysis.json`, Report, Playbook and package. In **Your analyses**, use the raid
filter to view saved runs for that raid. Continuing a saved run retains its raid.
Opening an existing report does not contact WCL.

Advanced CLI users can select a module explicitly:

```sh
necropsy analyze "https://vanilla.warcraftlogs.com/character/id/123" --raid aq40 --cache ./cache --out ./aq40-run --endpoint user
```

The values are `naxxramas`, `aq40`, `bwl` and `mc`. Character URLs with
`?zone=2005`, `?zone=2002` or `?zone=2000` also select AQ40, BWL or MC respectively.
A URL without a zone retains the historical Naxxramas default. Use a separate
output directory per analysis. Resume with the same command plus `--resume`.

| Module | WCL zone | Encounters |
|---|---|---|
| Naxxramas | 2006 | 15 |
| AQ40 | 2005 | 9 |
| BWL | 2002 | 8 individual bosses plus the combined Ebonroc / Flamegor entry |
| MC | 2000 | 10 |

The encounter catalog was checked against the WCL Vanilla `worldData` API on
2026-10-16. BWL retains both individual and combined dragon encounters so that
recorded rankings from either form can be acquired; absent personal rankings
remain missing coverage.

The shared class analysis, gear, ability usage, same-faction comparison and
evidence rules apply to each module. Naxxramas retains its fixture-validated
ranking exclusions and authored boss guidance. AQ40, BWL and MC have synthetic
acquisition → snapshot → offline replay → rendering coverage. Their ranked-damage
exclusions have not yet been reconciled against real logs, and their modules
have initial sourced general strategy for Lucifron, Magmadar, Gehennas, Garr,
Baron Geddon, Shazzrah, combined Ebonroc / Flamegor,
and Viscidus. Other boss strategy, observed phase/opportunity analysis and
ranking-policy reconciliation remain incomplete. Missing facts remain
unknown. Hunter comparisons use recorded WCL scores; the engine does not claim
that an unvalidated event sum is ranked damage or reconstruct ranked target
shares from it. General class and cooldown guidance remains available.

The initial strategy appears under preparation, execution and raid coordination
in both pages. Lucifron distinguishes class-specific curse/magic removal;
Magmadar distinguishes Frenzy-removal casts from successful effects and local
Panic exposure; Gehennas separates personal Curse exposure from healing received
by other patients; Baron Geddon keeps Ignite Mana exposure separate from actual
resource loss, and bomb guidance separate from observed handling; Shazzrah
separates personal Curse exposure, friendly curse removal and hostile Magic
removal without diagnosing Counterspell from gaps in casts;
Garr retains individual Firesworn Banish applications without
assuming every Warlock was assigned control; Viscidus distinguishes freezing and healing context. Local
debuff windows retain unknown state and do not define global phases or damage
opportunity. These are general plans,
not proof of your assignment, phase or a personal mistake. They apply only to
Era partitions 1/2. Older saved JSON keeps its recorded advice on render/refresh;
offline analysis of the original snapshot can create a new derived analysis
with current strategy. Originals remain untouched.

For developers, each raid has its own definition under `src/necropsy/raids/`
and separate encounter, facts and guidance YAML under
`src/necropsy/rules/classic_era/zones/`. The registry is shared by acquisition,
snapshot validation, analysis and application selectors. Neither the desktop
nor the renderer computes new analytical facts.

The durable validation inventory is available to checkout contributors:

```sh
uv run python scripts/check_raid_coverage.py --inventory
uv run python scripts/check_raid_coverage.py --require-complete
```

The first command reports progress; the second refuses incomplete evidence.
Current domain completion remains open for all 952 configurations. See the
[evidence register](../tests/golden/raids/README.md) for receipt requirements.
This inventory is developer tooling; report generation does not read development
tracking files. The packaged scope enumerates Era partitions 1/2; other partitions
returned by WCL are not evidence that Era mechanics apply there.
