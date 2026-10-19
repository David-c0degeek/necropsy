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

New MC/BWL/AQ40 analyses for Era partitions 1/2 also collect whole-fight and
critical-damage context through the normal quota-controlled acquisition path.
These scopes support encounter observations; they do not establish every
player's assignment, personal stream coverage or a validated ranking policy.
Resuming an older actor-only run acquires missing context and writes a new
immutable snapshot. Original archives remain available; old saved analyses
continue to render their recorded results. Naxx acquisition stays actor-only.

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
Baron Geddon, Shazzrah, Sulfuron Harbinger, Golemagg, Majordomo, Ragnaros,
all eight individual BWL bosses and combined Ebonroc / Flamegor,
and all nine AQ40 bosses. Complete class/duty guidance, observed phase/opportunity analysis and
ranking-policy reconciliation remain incomplete. Missing facts remain
unknown. Hunter comparisons use recorded WCL scores; the engine does not claim
that an unvalidated event sum is ranked damage or reconstruct ranked target
shares from it. General class and cooldown guidance remains available.

Retained public full-MC Holy Paladin evidence covers all ten personal bosses and
five comparisons each. Independent raw checks qualify60 actor/context cases and
58 recipient cases; two comparison enemy rosters are empty and one guardian
owner is unresolved. These limits remain separate from the usable healing
events. Encounter utility, assignments and complete class/faction acceptance
are still being developed.

Full-MC Horde Restoration Shaman evidence adds60 actor/context and60 recipient
cases, with17 owned Healing Stream Totem units independently retained in59
owner contexts. One Magmadar pet owner remains unknown. Both pages retain
individually verified summon healing and credited absorption separately from
actor support, with whole-fight rates and explicit listing/quality limits.
These observations do not reconcile WCL HPS or complete summon-specific guidance.

Sulfuron Shaman reports show raid-roster interruptions of Dark Mending with actual
sources and Priest target instances. Four independently verified effects occur
in two of six Restoration-context fights. They remain separate from selected
player credit, ranking category and interrupt opportunities. Incomplete coverage
withholds an exact count while retaining qualified positive observations.

Initial Elemental/Horde/DPS evidence is partial:25 comparison actors cover five
bosses, while five personal ranking-selected contexts have unknown duty and remain
excluded from personal assessment. Known individual damage totems remain visible
beside unresolved ownership; missing sources and the quota stop are explicit.

A later normal resume completes acquisition of five Elemental comparison actors
per boss,50 overall. Forty-nine qualify for DPS comparisons; Pythón's Golemagg
duty remains unresolved under repeated boss melee despite positive damage, so
that baseline has four eligible examples. No personal DPS assessment becomes
available. Forty individually bound damage totems and one incomplete owner list
remain explicit. Two additional raid-roster Dark Mending interruptions belong to
Enoset and Shocknlawl, separately from selected-player utility. No quota stop
remains; full class/phase/ranking/domain/product acceptance is still open.

Shadow/Alliance/DPS comparison evidence is complete for collection: five
acquired Shadow Priest peers per MC boss, 40 eligible for DPS comparison. The
subject played Holy throughout, so personal Shadow assessment is absent on every
boss. Holy-Nova-heavy add fights on Garr and Majordomo keep unknown duty, and
one actor with conflicting Priest/Warrior evidence is excluded; Garr has no
eligible Shadow peer.

Priest reports also show friendly credited absorption by ability and recipient,
separating Power Word: Shield from Persistent Shield and other recorded effects.
The shield review prompt asks for coordination with tanks and healers; absorption
effects do not establish casts, prevented damage, equipment causes or quality.
Complete amounts require verified player SOURCE and encounter coverage; partial
evidence retains observations with unknown totals. Initial real acceptance covers
60 full-MC contexts, with the prompt limited to observed shield rank10901.

The initial strategy appears under preparation, execution and raid coordination
in both pages. Geddon additionally retains recorded Priest Dispel Magic and
Paladin Cleanse removals of Ignite Mana
and exact exposure endpoints alongside unambiguous self-dispels, with self-clear
and backup-coverage coordination. This supplies no reaction or saved-mana grade.
Lucifron distinguishes class-specific curse/magic removal;
Magmadar distinguishes Frenzy-removal casts from successful effects and local
Panic exposure; Gehennas separates personal Curse exposure from healing received
by other patients; Baron Geddon keeps Ignite Mana exposure separate from actual
resource loss, and bomb guidance separate from observed handling; Shazzrah
separates personal Curse exposure, friendly curse removal and hostile Magic
removal without diagnosing Counterspell from gaps in casts; Sulfuron separates
add interruption, friendly magic removal and divided healing assignments;
Golemagg retains observed Magma Splash exposure without assigning tank duty;
Majordomo keeps observed shield states separate for each add instance;
Ragnaros distinguishes conditional Sons control and party fire-resistance
support from measured phases or successful control.
BWL strategy distinguishes Razorgore controller preparation from recorded boss
execution, Vaelastrasz resource and Burning Adrenaline context, Broodlord threat
and Mortal Strike recovery, and Firemaw line-of-sight recovery. Ebonroc tank
handoffs remain separate from Flamegor Frenzy removal. Chromaggus separates
curse, magic, disease, poison and Hourglass Sand capabilities.
Priest Blue-affliction counters retain actual Dispel Magic effects and distinguish
other players' removals from personal utility. A zero is not a failed assignment.
Nefarian provides one guarded response per Era class; missing personal data or call markers stay
unknown. These additions do not establish measured phases or ranked totals.
AQ40 strategy distinguishes Skeram control recovery, Royalty kill order and
poison removal, Sartura guard control, Fankriss worm and trapped-player duties,
Viscidus participation, Huhuran soak/recovery, Twin Emperor targets and tank
pickups, Ouro threat recovery, and C'Thun tentacle/stomach coordination.
Huhuran Frenzy removal is Hunter-specific; Berserk and poison-themed effects
are separate. Wyvern Sting removal needs coordinated damage recovery.
These are conditional raid plans, not observed assignments or personal grades.
AQ40 also retains observed Sartura Whirlwind/Enrage, separate Huhuran Frenzy
and Berserk, individual Twin Emperor teleport auras and Ouro Berserk state.
Unnumbered NPC duration evidence requires the exact fight roster to identify
one instance of that NPC. Missing or ambiguous cardinality withholds durations;
numbered repeated adds retain separate windows. Personal Sand Blast exposure
is separate from physical attackability, tank assignment or avoidability.
Missing C'Thun vulnerability transitions do not establish that no weakening
occurred, and no nominal weakening timer supplies an observed window.
Skeram retains separate numbered image summons and elapsed event bounds to a
recorded positive-overkill marker. Groups can overlap; missing endpoints stay
unknown. These observations do not prove lifetime, attackability, target access
or available damage time, and do not supply a phase or performance grade.
Real Hunter replay also distinguishes confirmed pet absence from unknown pet
classification and unresolved guardian ownership. A known trained pet remains
measured when a separate guardian has no owner. A recommendation to bring a pet
requires at least three known same-faction trained-pet measurements and a
positive median. Known absence remains visible in Report and Playbook when that
comparison is missing or zero; the comparison does not establish pet safety or
raid assignments.
No-comparison boss sections keep
opening guidance unknown and omit an unavailable reference ability comparison.
BWL also retains observed Burning Adrenaline, Essence of the Red, Flame Buffet,
Chromaggus affliction and Nefarian fear/curse/Priest-call exposure. These are
recipient aura observations; Bronze exposure is not stun uptime, and a resource
aura's presence is not a measured resource quantity. Other players' observations
are labelled cohort examples and do not fill a missing personal fight.
Available raw identity fields must agree with normalized recipient/spell IDs;
unresolved aura or lifecycle identity withholds durations rather than creating
known absence. Historical whole-fight aura inference stays unchanged.
Recorded Feign Death does not count as a genuine death or reset measured aura
state. Malformed death flags stay uncertain; real deaths and resurrections
retain their state-reset behavior. Raw events are preserved.
When a personal fight is unavailable, its Report context keeps personal build
and duty unknown. A reference player's measurements remain labelled examples.
Garr retains individual SOURCE-owned Firesworn Banish applications separately
from encounter-wide, class-qualified target-instance observations. Ranks and
add instances stay separate; another Warlock’s effect is not personal uptime.
Complete Banish counts require strict player SOURCE plus encounter event-set
proof; older snapshots without it keep recorded applications with an unknown
count. A recorded application with an instance asks you to confirm control and
backup on that add, never implying an assignment.
Recorded Garr Warlock Curse of Recklessness, Curse of the Elements and Curse
of Shadow applications are listed separately with the same evidence rules;
other curses are outside the count. They ask which curse your raid assigned; they are not uptime, benefit
or a reason to change curses.
Neither view assumes every Warlock was assigned control; Viscidus distinguishes freezing and healing context. Local
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
