# Haplina — Classic Era Naxxramas Hunter Parse Forensics

Dataset: Haplina’s selected best Naxx parse for each of 15 bosses plus the current top five Hunter parses per boss (75 leaderboard parses), with raw actor event streams, gear, combatant data, pets, buffs and timelines from the supplied WCL export.

## Executive findings

* **Pet data is recoverable much more deeply than the first pass suggested.** We can identify the actual pet actor, name, damage, uptime/death, and every active pet skill/spell ID. What WCL does **not** expose is the pet’s uncast/passive training-point allocation (Great Stamina, Natural Armor, resistance ranks). Classic pets do not have a Retail-style talent “spec”; they have family + trained abilities/passives.
* **Snape is not under-ranked on active skills:** the logs show Bite 8 (17261), Dive 3 (23148), and Lightning Breath 6 (25012), i.e. the top ranks of those active abilities. The problem is the Wind Serpent package, 12/33/6 hunter spec, uptime/deaths, and encounter handling—not a missing Lightning Breath/Bite rank.
* Across the 75 top-five parses, a hunter pet is present in **74/75**. **Claw appears in 65/74** pet logs; **Lightning Breath appears in 0/74**. At least 42 pets show the uniquely Cat-compatible observed combination **Claw + Dash**; additional named cats increase that count. The leaderboard is overwhelmingly physical/cat-oriented rather than Wind Serpent-oriented.
* **20/31/0 has a major pet-output signature:** across top parses with that spec the median pet output is ~158 DPS overall; excluding the pet-hostile/odd Gothik, 4HM and Sapphiron fights it is ~164 DPS. This is association, not a controlled simulation, but it lines up with the BM investment and the actual logs.
* **The top gear “set” is extremely stable:** median is **7 Cryptstalker armor pieces** (usually everything except gloves), with PvP Multi-Shot gloves, Prestor’s, Fallen God cloak, Cryptstalker/Reanimation rings, and Slavemaker. Nerubian Slavemaker is present in **70/75** top parses.
* **Melee weaving does not replace Slavemaker.** On Patchwerk, all top five use Nerubian Slavemaker. Four of five weave. Three of those four use **Eye of Nerub** as the melee weapon; rank 1 uses **Dark Edge of Insanity**. The pure-ranged top parse uses **Kingsfall + Harbinger**. Ranged weapon and melee-weave weapon are independent choices.
* **Gothik’s leaderboard is heavily strategy/padding-driven.** Haplina has 0 damage to non-Gothik trash in the encounter stream. Every top-five parse has roughly **48–72%** of its player damage on non-native mobs such as Plagued Ghoul / Plagued Gargoyle / Necropolis Acolyte. Without reproducing that pull/encounter-overlap strategy, absolute Gothik rank comparison is structurally unfair.
* **KT contains a concrete parse-costing assignment:** Haplina has a ~39 s Aimed gap (84.9→123.9) while still shooting Autos, and in that window uses Freezing Trap, Goblin Rocket Helmet/Reckless Charge on a teammate, repeated Hunter’s Mark and Scatter Shot on a teammate. Current top KT logs do not carry the same control burden. This is not merely “press Aimed better”; it is raid-role allocation.

## Pet forensics

### What “pet spec” we can and cannot recover
Classic Era pets use training points rather than a separate talent tree. Raw WCL events expose **active abilities when they are actually cast**. They do not expose passive training choices that never create combat-log events. Therefore the export can reliably answer family (sometimes exact, sometimes inferred), active skill ranks, pet damage, start/stop times and death causes, but not prove “5/5 Frost Resistance + X Stamina + Y Armor” from CombatantInfo because WCL does not emit pet CombatantInfo here.

For Snape, active ranks are explicit from spell IDs: **Bite 8 / Dive 3 / Lightning Breath 6**. That is already a max-rank active kit for a Wind Serpent.

### Haplina pet failures that are visible in the logs

| Boss | Pet result | What happened |
|---|---:|---|
| Patchwerk | 78.0 DPS | Stopped dealing damage 7.1s before fight end |
| Grobbulus | 27.7 DPS | Died at 25.7s — Mutagen Explosion 1609 from Grobbulus; Poison 1116 from Grobbulus Cloud; Poison 868 from Grobbulus Cloud |
| Gluth | 0 DPS | No Hunter pet actor in the selected parse |
| Heigan the Unclean | 0 DPS | No Hunter pet actor in the selected parse |
| Anub'Rekhan | 0 DPS | No Hunter pet actor in the selected parse |
| Grand Widow Faerlina | 58.8 DPS | Stopped dealing damage 5.3s before fight end |
| Gothik the Harvester | 5.4 DPS | Died at 152.7s — Whirlwind 2372 from Spectral Death Knight; Arcane Explosion 426 from Spectral Trainee; Arcane Explosion 285 from Spectral Trainee |
| The Four Horsemen | 28.5 DPS | Stopped dealing damage 48.1s before fight end |
| Sapphiron | 0 DPS | No Hunter pet actor in the selected parse |

Most important examples: Grobbulus pet death at 25.7s is directly attributable to **Mutagen Explosion + Grobbulus Cloud Poison**; Gothik pet dies at 152.7s after Spectral Death Knight Whirlwind / Spectral Trainee Arcane Explosion. On 4HM Snape does not die, but simply stops contributing ~48 s before the end.

## Gear — global leaderboard consensus

* **Head:** Cryptstalker Headpiece — 72/75
* **Neck:** Prestor's Talisman of Connivery — 62/75
* **Shoulder:** Cryptstalker Spaulders — 73/75
* **Chest:** Cryptstalker Tunic — 73/75
* **Waist:** Cryptstalker Girdle — 73/75
* **Legs:** Cryptstalker Legguards — 68/75
* **Feet:** Cryptstalker Boots — 73/75
* **Wrist:** Cryptstalker Wristguards — 73/75
* **Hands:** Marshal's Chain Grips — 49/75
* **Back:** Cloak of the Fallen God — 69/75
* **Ring1:** Ring of the Cryptstalker — 45/75
* **Ring2:** Band of Reanimation — 41/75
* **Ranged:** Nerubian Slavemaker — 70/75

The practical core is therefore seven T3 armor slots + PvP gloves in most parses, with occasional 8-piece/T3 glove variants. Trinkets and melee weapons are the major encounter-specific switches.

## Fight-by-fight dominant swap slots (top five)

| Boss | Gloves | Main-hand / 2H | Ranged | Trinket pattern | Weaving |
|---|---|---|---|---|---|
| Patchwerk | Marshal's Chain Grips (3/5) | The Eye of Nerub (3/5) | Nerubian Slavemaker (5/5) | Mark of the Champion (2/5); Vanquished Tentacle of C'Thun (1/5) | 4/5 Raptor users |
| Grobbulus | Marshal's Chain Grips (2/5) | Kingsfall (2/5) | Nerubian Slavemaker (4/5) | Mark of the Champion (2/5); Slayer's Crest (2/5) | 1/5 Raptor users |
| Gluth | Marshal's Chain Grips (3/5) | Kingsfall (3/5) | Nerubian Slavemaker (4/5) | Jom Gabbar (2/5); Mark of the Champion (4/5) | 0/5 Raptor users |
| Thaddius | Marshal's Chain Grips (3/5) | Kingsfall (3/5) | Nerubian Slavemaker (5/5) | Slayer's Crest (2/5); Mark of the Champion (4/5) | 4/5 Raptor users |
| Noth the Plaguebringer | Marshal's Chain Grips (4/5) | Kingsfall (3/5) | Nerubian Slavemaker (5/5) | Renataki's Charm of Beasts (2/5); Mark of the Champion (4/5) | 1/5 Raptor users |
| Heigan the Unclean | Marshal's Chain Grips (4/5) | Kingsfall (3/5) | Nerubian Slavemaker (5/5) | Slayer's Crest (2/5); Mark of the Champion (4/5) | 4/5 Raptor users |
| Loatheb | Marshal's Chain Grips (5/5) | Kingsfall (2/5) | Nerubian Slavemaker (5/5) | Slayer's Crest (3/5); Mark of the Champion (4/5) | 1/5 Raptor users |
| Anub'Rekhan | Marshal's Chain Grips (3/5) | Kingsfall (5/5) | Nerubian Slavemaker (5/5) | Renataki's Charm of Beasts (2/5); Slayer's Crest (2/5) | 0/5 Raptor users |
| Grand Widow Faerlina | Cryptstalker Handguards (3/5) | The Eye of Nerub (3/5) | Nerubian Slavemaker (5/5) | Slayer's Crest (2/5); Renataki's Charm of Beasts (3/5) | 0/5 Raptor users |
| Maexxna | Marshal's Chain Grips (2/5) | Kingsfall (4/5) | Nerubian Slavemaker (5/5) | Renataki's Charm of Beasts (2/5); Renataki's Charm of Beasts (2/5) | 0/5 Raptor users |
| Instructor Razuvious | Marshal's Chain Grips (4/5) | Kingsfall (3/5) | Nerubian Slavemaker (4/5) | Slayer's Crest (2/5); Mark of the Champion (4/5) | 0/5 Raptor users |
| Gothik the Harvester | Marshal's Chain Grips (4/5) | The Eye of Nerub (4/5) | Nerubian Slavemaker (3/5) | Seal of the Dawn (2/5); Blackhand's Breadth (2/5) | 2/5 Raptor users |
| The Four Horsemen | Marshal's Chain Grips (4/5) | Kingsfall (2/5) | Nerubian Slavemaker (5/5) | Slayer's Crest (2/5); Mark of the Champion (5/5) | 1/5 Raptor users |
| Sapphiron | General's Chain Gloves (2/5) | Kingsfall (3/5) | Nerubian Slavemaker (5/5) | Renataki's Charm of Beasts (3/5); Mark of the Champion (3/5) | 0/5 Raptor users |
| Kel'Thuzad | Marshal's Chain Grips (4/5) | Kingsfall (3/5) | Nerubian Slavemaker (5/5) | Kiss of the Spider (2/5); Mark of the Champion (4/5) | 0/5 Raptor users |

The included `top5_gear_by_boss.csv` contains **every slot for every one of the 75 top parses**, not just the dominant item.

## Priority autopsy 1 — Patchwerk

Haplina: **1000.9 DPS / 84.0s**. Rank 1: **1409.8 DPS / 105.9s**. Your raid kills it faster, so this is predominantly a personal-optimization problem, not a kill-time excuse.

Your shot rate is actually healthy on Autos: 28 Autos = 19.99/min vs top-five median 19.75/min. The clear ranged deficit is Aimed: 7 casts = 5.00/min vs 6.01/min.

* Exact Haplina Aimed completions: **10.91s, 21.88s, 32.75s, 43.28s, 53.25s, 63.15s, 75.47s**.
* Haplina RF: **6.67–25.67s**. Quick Shots: **33.17–50.03s** and **50.59–62.60s**.
* Rank-1 opener: RF 4.20 → Auto 4.51 → Aimed 6.69 → Auto 7.01 → Multi 7.32 → Raptor/Refocus 9.11 → Auto 10.75 → Aimed 13.24 → Multi 13.85. This is the concrete Renataki double-special pattern in a live rank-1 log.
* Pet: Snape **78 DPS** versus top-five median about **174 DPS**. Rank-1 Cat is ~216 DPS.
* Engineering: all five current top Patch parses use Sapper and/or Dense Dynamite; Haplina uses neither in this selected parse.
* Gear answer to the weaving question: **yes, they still use Slavemaker**. All five. Rank 1 uses Dark Edge + Slavemaker; ranks 2/3/5 use Eye of Nerub + Slavemaker and weave; rank 4 uses Kingsfall + Harbinger + Slavemaker and stays ranged-only.

**Patchwerk plan:** 20/31/0; physical/cat pet; DMF Damage; full pet uptime; Slavemaker. Keep the current Eye of Nerub if learning the weave. First master a clean ranged cycle with ~8–9 Aimed casts over an 84s kill, then add a Raptor weave only in genuine dead space. Add an explosive only when it does not displace an Auto. Renataki is proven by rank 1, but current top five also show non-Renataki paths, so it is a ceiling tool rather than the only viable setup.

## Priority autopsy 2 — Grobbulus

Haplina **834.9 DPS / 66.8s** vs rank 1 **1518.3 / 62.5s**.
* **No Rapid Fire at all** in Haplina’s parse. Rank 1 uses it at 2.68s; top-five median first RF is around 9.2s.
* First Aimed is **11.02s**. Rank 1 lands Aimed at 5.17s. You essentially give away the opener’s first Aimed window.
* Auto rate: ~18.9/min vs top-five median ~22.3/min. A large portion is simply the missing haste cooldown/procs and lost uptime.
* Snape dies at **25.68s**. Incoming sequence: Mutagen Explosion 1609, then Grobbulus Cloud Poison 1116 + 868. Pet DPS collapses to **27.7**, vs top-five median ~184.5.
* Only rank 1 meaningfully weaves here; the other four are ranged. Therefore melee weaving is **not** your first Grobbulus fix.

**Grobbulus plan:** RF in the opener; Auto→Aimed immediately rather than Auto→Multi and waiting to 11s; manually recall/reposition the pet out of poison clouds and re-send it; prioritize full ranged/pet uptime. Do not add weaving until the pet survives and the opener is fixed.

## Priority autopsy 3 — Gothik

Haplina **163.2 DPS** vs rank 1 **444.1**. On the surface this looks catastrophic; the raw targets show why.

| Player | Total player damage | Non-native trash damage | Share |
|---|---:|---:|---:|
| Haplina | 48,476 | 0 | 0.0% |
| #1 Andrenn | 130,204 | 62,023 | 47.6% |
| #2 Alldon | 125,260 | 73,177 | 58.4% |
| #3 Eoria | 123,499 | 68,480 | 55.4% |
| #4 Dwarfazz | 117,945 | 59,465 | 50.4% |
| #5 Caffè | 118,843 | 85,777 | 72.2% |

The non-native damage is overwhelmingly Plagued Ghoul / Plagued Gargoyle / Necropolis Acolyte. Those are not Gothik’s normal wave mobs. The current top-five encounter event streams therefore include substantial carried/overlapping trash. This is **parse strategy**, not merely better shot rotation.

* Haplina attacks spectral-side targets and Gothik only; no foreign trash damage.
* Haplina Aimed casts: **16.97s and 299.47s** — a **282.5s gap**. Top-five median is ~11 Aimed casts over the encounter. Even under your assignment there is a very large Aimed-utilization opportunity.
* Your Rapid Fire is at **293.58s**, essentially the boss tail. For an all-damage parse, that misses the high-density wave/trash windows where top logs accumulate most of their score.
* Snape dies at **152.66s**, after Spectral Death Knight Whirlwind and Spectral Trainee Arcane Explosion. Pet DPS is only ~5.4, although pet DPS is not the dominant Gothik differentiator.
* Gear is unusual/encounter-specific: Eye of Nerub 4/5; Slavemaker only 3/5 because two historic leaders use Ashjre’thul. Seal of the Dawn appears 2/5. This is one of the few bosses where the standard Naxx gear census is less rigid.

**Gothik plan:** decide first whether you want a “clean boss strategy parse” or to chase the actual leaderboard meta. For rank chasing, the raid must reproduce the live-side/extra-trash encounter overlap and put you where the target density is. Then Multi, Aimed and explosives on those waves matter far more than waiting for Gothik himself. If you do not reproduce that strategy, compare yourself against native-target damage rather than the displayed top DPS; Haplina’s native-target DPS is ~158, versus roughly 111–230 among these top five — much less disastrous than the raw 163 vs 444 implies.

## Priority autopsy 4 — Kel'Thuzad

Haplina **643.8 DPS / 176.8s** vs rank 1 **1320.6 / 90.4s**. Here both raid speed and personal/assignment cost are enormous.

* Top five are **5/5 Slavemaker**, **0/5 Raptor users**, and Mark of the Champion is in 4/5 second trinket slots. This is a ranged-control fight, not a weaving fight.
* Haplina’s selected KT gear includes **Blackhand’s Breadth + Burrower’s Shell**. The defensive Shell is an obvious parse concession versus the top offensive trinket sets (Kiss/Mark, Renataki/Mark, Mark/Slayer, Slayer/Mark).
* First Aimed: **13.35s** versus rank-1 **3.92s**. This is an avoidable opener loss.
* The biggest event-level finding is the **84.92→123.89s Aimed gap (38.97s)**. Autos continue in the gap, so the bow is not simply offline.
* During that window Haplina drops **Freezing Trap at 97.36s**, uses **Reckless Charge/Goblin Rocket Helmet at 102.51s on teammate Lgbtqt**, repeatedly re-marks KT, and **Scatter Shots teammate Airra at 115.32s**. Those are Mind Control/control responsibilities. Rank-1 Snipex’s comparable log has none of that control sequence; it simply keeps doing damage.
* Top-five median Aimed rate is ~6.55/min. Applied to your long kill, that is ~19.3 Aimed casts versus your 13 — about six cast-equivalents, although some are mechanically/assignment constrained.
* Pet: Snape ~59.6 DPS vs top-five median ~135 DPS.

**KT plan:** if the goal is personal rank, remove MC-control duty from the parsing Hunter. Have another Hunter/player cover trap/Scatter/helmet where possible. Replace Burrower’s Shell with an offensive trinket. Start Aimed immediately in the first cycle. Keep pet active. Do not melee weave. The raid also needs to compress the kill drastically: your 176.8s fight is nearly double rank-1’s 90.4s, so even perfect personal play cannot fully bridge the leaderboard gap.

## All 15 bosses — concrete next-raid plan

| Boss | Highest-value change from these logs | RF / burst timing | Weave? | Pet note |
|---|---|---|---|---|
| Patchwerk | Raise pet output; +1–2 Aimed; add Renataki/explosive ceiling | Pull/first cycle (~4–8s in leaders) | Yes after ranged cycle is perfect | Keep alive to end; physical/cat pet |
| Grobbulus | Fix opener and pet death | Early; you used none | Not required | Recall out of clouds; Snape died at 25.7s |
| Gluth | Bring a pet and actually use RF | Early (~3–12s top) | No in top 5 | No pet actor in your best log |
| Thaddius | Use RF in Thaddius/polarity burn; +2 Aimed-equivalents | Hold; top cluster ~82s | Optional/yes for experts | Pet survives but output ~half top median |
| Noth the Plaguebringer | RF + stronger pet + tighter Aimed cadence | Early/burn before teleport | Mostly no | Pet ~73 vs ~161 median |
| Heigan the Unclean | Bring pet; RF earlier; shorten kill | ~6–18s, earlier than your 18s | Minor only | No pet actor in your best log |
| Loatheb | Align RF to spore damage window; +2 Aimed; pet | ~26–40s leaders, not 72.6s | Usually no | ~76 vs ~191 median |
| Anub'Rekhan | Bring pet; earlier RF; one more Aimed | Early (~4–12s) | No | No pet actor in your best log |
| Grand Widow Faerlina | Aimed immediately; Renataki reset; pet | RF ~10–13s is fine; specials start immediately | No | Pet ends ~5.4s early |
| Maexxna | One extra Aimed via cadence/Refocus; pet/spec | Early ~5–9s | No | Pet survives; output low |
| Instructor Razuvious | Auto uptime + pet damage | Early ~7–12s | No | ~41 vs ~151 median |
| Gothik the Harvester | Raid parse strategy/target assignment; use Aimed on waves | Dense wave/trash window, not 293s | Sometimes | Pet dies at 152.7s |
| The Four Horsemen | RF at pull, much more Aimed during target windows, pet uptime | Pull (~3–10s) | Rare | Pet stops ~48s before end without dying |
| Sapphiron | This is primarily a raid speedkill; burst first ground phase | Pull (rank1 1.6s) | No | Use pet + Frost Resistance training; yours absent |
| Kel'Thuzad | Remove MC-control duty; offensive trinkets; opener; raid speed | Early (~1–11s) | No | ~60 vs ~135 median |

## How to interpret “missed Aimed”
The `boss_timing_forensics.csv` includes an **AimedEquivalentDeficit**: how many Aimed casts Haplina would have produced over his own fight duration if he matched the current top-five median Aimed-per-minute for that boss. It is a benchmark, **not a claim that every difference is a literal player mistake**. Thaddius phase transitions, 4HM movement, Sapphiron air phase, Gothik assignments and KT control duties create legitimate downtime. The raw `all_cast_timelines.csv` and `auto_interval_reconstruction.csv` are included so those intervals can be inspected rather than hand-waved.

## Offline/app feasibility
Yes. In fact, this report was produced **offline from the downloaded export ZIP**. Once WCL data is downloaded, none of the event reconstruction, gear consensus, pet inference, shot timing, target segmentation or comparison requires the WCL website.

A future app should separate two layers: **Acquisition** (online WCL OAuth/API, optional) and **Analysis** (100% offline). The offline layer can import an export ZIP, normalize reports/fights/actors/events/gear into SQLite or DuckDB, compute derived metrics deterministically, cache leaderboard snapshots, and expose a UI. That architecture also lets unsubscribed users analyze public exports and Gold users add archived data without changing the analyzer. I would keep the analyzer as a pure local library so the UI can later be CLI, desktop or web-local without rewriting the logic.

## Files in this pack

* `top5_gear_by_boss.csv` — full 18-slot gear, spec, casts and pet summary for every top-five parse.
* `gear_dominance_all_slots.csv` — boss-by-boss dominant item counts for every gear slot.
* `global_top75_gear_counts.csv` — global item census across all 75 leaderboard parses.
* `melee_weave_gear.csv` — every top parse with Raptor/white-melee activity and its exact melee/ranged weapon set.
* `pet_forensics_with_ranks.csv` — pet name, family inference, observed spell IDs/ranks, DPS, uptime/death and limitations.
* `boss_timing_forensics.csv` — Haplina vs top-five shot-rate, RF, Refocus, pet and percentile benchmarks.
* `all_cast_timelines.csv` — exact timestamp of every Auto/Aimed/Multi/Raptor/RF/Refocus/FD/explosive event for Haplina and top five.
* `auto_interval_reconstruction.csv` — exact Auto-to-Auto gaps for Haplina and rank 1 on every boss, with Aimed/Multi/Raptor/Refocus inside each gap and RF/QS overlap.
* `gothik_target_padding.csv` — target-by-target evidence behind the Gothik leaderboard strategy finding.