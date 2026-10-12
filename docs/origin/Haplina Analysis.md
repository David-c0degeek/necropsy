Yes — **this export finally contains what we wanted**. It successfully used `/api/v2/user`, pulled all 85 reports / 89 selected fights, including archived event streams, and finished with **zero extraction errors**. I can now compare Haplina against the actual top-5-per-boss event data rather than guessing from leaderboard cards.

And there are already some very large findings.

## The biggest problems are not your basic gear

Your armor/ranged setup is already very close to the real parsing meta. Across the 75 top-five boss parses, Nerubian Slavemaker appears in **70/75**, Marshal/General PvP gloves dominate the hand slot, Ring of the Cryptstalker + Band of Reanimation dominates the rings, and Kingsfall / Harbinger / Eye of Nerub make up most melee setups. That broadly matches current P6 BiS guidance. [Wowhead](https://www.wowhead.com/classic/guide/wow-classic-hunter-dps-naxxramas-best-in-slot-gear)

Your major differences are elsewhere:

| Area | Haplina | Actual top-log pattern | Importance |
|---|---|---|---|
| **Spec** | **12/33/6** on essentially all analyzable best logs | **20/31/0 in 45/68** top parses with CombatantInfo | 🔴 Very high |
| **DMF** | **Agility** on every Haplina DMF log I found | **Damage in 65/68** top logs | 🔴 Very high |
| **Trinket #1** | **Blackhand's Breadth 15/15** | Slayer / Renataki / Mark dominate | 🔴 Very high |
| **Renataki** | Never used | **24 top parses equip it; all 24 actually trigger Refocus** | 🔴 Very high |
| **Pet** | Wind-serpent-style Bite + Lightning Breath | Top logs overwhelmingly use Claw/Bite physical pets | 🔴 High |
| **Pet output** | ~78 DPS on your Patchwerk | ~160 DPS median among accessible top Patch pets | 🔴 High |
| **Aimed frequency** | Usually noticeably below top | Elite logs squeeze substantially more Aimed casts | 🟠 High |
| **Melee weaving** | Almost none | Encounter-dependent; enormous on some Patchwerk ranks | 🟠 Situational |
| **Engineering summons** | Already doing them | Also common at the top | 🟢 Good |
| **Core armor/ranged** | Very strong | Very similar | 🟢 Good |

That changes the diagnosis quite a bit.

---

# 1. Your spec is genuinely leaving damage behind

Your combatant info consistently reports:

**12 / 33 / 6**

The top-five dataset with readable talent trees gives:

```text
20/31/0   45 parses
5/31/15   10
7/31/13    4
5/34/12    3
14/31/6    2
19/32/0    1
2/31/18    1
19/31/1    1
17/31/3    1
```

So **20/31/0 is not theorycraft folklore — it is by far the dominant build in the actual top-five Era logs.**

It is also the build used in **8 of the 14 rank-1 fights where the combatant data is available**.

There are legitimate Survival/MM variants at the top, so I'm correcting something from my earlier answer: **20/31/0 isn't mandatory for every encounter or every record.** But your particular 12/33/6 configuration doesn't appear even once among the 68 readable top-five talent setups.

The current August 2026 Era parsing guide independently arrives at the same conclusion: once hit is solved, move to 20/31/0 and use the BM points to increase pet contribution. [Wowhead](https://www.wowhead.com/classic/guide/the-indefinite-wow-classic-era-hunter-guide-by-nelenya-34233)

For you, I'd change this before the next serious parse raid.

---

# 2. You're taking the wrong Darkmoon Faire buff

This one is exceptionally clear in the logs.

Whenever your best parses contain a Sayge buff, you're using:

**Sayge's Dark Fortune of Agility**

The elite logs almost universally have:

**Sayge's Dark Fortune of Damage**

In the top dataset:

**65 of 68 readable top combatants had Sayge Damage.**

The three remaining simply didn't have Damage recorded; they're not evidence for Agility being competitive.

And mechanically:

- Agility fortune = **+10% Agility**
- Damage fortune = **+10% all damage** [Wowhead](https://www.wowhead.com/classic/spell%3D23736/sayges-dark-fortune-of-agility)

The current Era parsing guide explicitly specifies **Sayge's Dark Fortune of Damage** as the Hunter DMF world buff. [Wowhead](https://www.wowhead.com/classic/guide/the-indefinite-wow-classic-era-hunter-guide-by-nelenya-34233)

So during DMF week:

**Stop taking Agility. Take Damage.**

This may be the single easiest large increase available to you.

---

# 3. Your biggest gear weakness is the trinket slot

Your best parses show:

**Blackhand's Breadth: 15/15**

That is a perfectly respectable Hunter trinket.

It is emphatically **not** what the top-end meta mostly uses anymore.

Across the 150 trinket slots represented by the 75 top-five parses:

| Trinket | Appearances |
|---|---:|
| **Mark of the Champion** | **55** |
| **Slayer's Crest** | **33** |
| **Renataki's Charm of Beasts** | **24** |
| Blackhand's Breadth | **11** |
| Jom Gabbar | 10 |
| others | remainder |

That's a giant difference.

### Renataki is not just sitting in people's gear

I checked the raw casts.

Exactly **24 top parses equip Renataki**.

Exactly **24/24 of those logs cast `Refocus`**, the reset produced by Renataki.

So this isn't speculative BiS-list advice. Top hunters are actively exploiting the reset.

On Rank-1 Patchwerk Smcadogx's opener, the raw event sequence is essentially:

```text
Rapid Fire
Auto
Aimed
Auto
Multi
Raptor
REFocus  ← Renataki
Auto
Aimed
Multi
Auto
...
```

That is precisely the trick described in the current Era guide: consume the first Aimed/Multi pair, trigger Renataki, then immediately get another Aimed/Multi cycle. [Wowhead](https://www.wowhead.com/classic/guide/the-indefinite-wow-classic-era-hunter-guide-by-nelenya-34233)

**Getting Renataki should be a priority for you.**

Slayer's Crest would obviously be excellent too, but Renataki is the more Hunter-specific opportunity.

---

# 4. Your Patchwerk log is extremely instructive

Your Patchwerk:

**1000.9 DPS — 96.03 current percentile — 84.04 seconds**

Rank 1 Smcadogx:

**1409.8 DPS — 105.93 seconds**

This is important because **his raid actually kills Patchwerk more slowly than yours**.

So on Patchwerk we cannot blame your raid's kill speed.

Your damage breakdown:

| Source | Haplina | Rank 1 Smcadogx |
|---|---:|---:|
| Auto Shot | **520 DPS** | 438 DPS |
| Aimed Shot | **215** | 239 |
| Multi-Shot | **188** | 192 |
| Raptor Strike | **0** | **145** |
| Melee swings | **0** | **140** |
| Pet | **~78** | elite Patch pets ~160 median |
| Engineering | negligible | additional Sapper/etc. |

The shocking bit is:

**Your ranged foundation isn't terrible at all.**

You actually produced **more Auto-Shot DPS than rank 1** in that particular comparison.

Smcadogx gains a ridiculous amount from melee weaving:

**~285 DPS from Raptor Strike + ordinary melee swings.**

He landed:

- 11 Raptor Strikes
- 13 melee swings
- 11 Aimed Shots
- 10 Multi-Shots
- 30 Autos
- Renataki/Refocus

You had:

- 0 Raptor
- 0 melee
- 7 Aimed
- 8 Multi
- 28 Autos
- no Renataki

So for **Patchwerk specifically**, melee weaving is absolutely not a tiny theoretical optimization. One current rank-1 log is building a huge portion of its advantage from it.

But here's the other important comparison:

### Xert's top-5 Patchwerk is effectively ranged-only

Xert did **1347 DPS** with:

- 42 Autos
- 12 Aimed
- 11 Multi
- **0 Raptor**
- Dense Dynamite
- 20/31/0
- Slayer + Mark
- DMF Damage
- stronger pet output

His ranged breakdown was approximately:

```text
Auto       650 DPS
Aimed      295
Multi      229
Dynamite     9
Arcane       4
```

So you **do not have to become a melee-weaving god before improving substantially**.

There's clearly a route from ~1000 toward ~1300+ using cleaner ranged execution + correct spec + buffs + pet + trinkets.

Then weaving becomes the next ceiling.

---

# 5. Your pet needs serious attention

This is much bigger than I expected.

Your Patchwerk pet, Snape:

- starts doing damage ~6.3 seconds after pull
- stops doing damage **7.1 seconds before Patchwerk dies**
- contributes **~78 DPS**
- uses Bite + Lightning Breath

Comparable elite Patch pets:

- begin around the same ~5-second mark
- keep attacking until **<1 second before boss death**
- contribute roughly **160 DPS median**
- typically use Claw/Bite

For example:

```text
Haplina / Snape:
78 DPS
lost final ~7.1 sec

Xert / Slicky:
~160 DPS
last attack 0.86 sec before boss death

Charies / GaryPrime:
~149 DPS
last attack 0.47 sec before boss death
```

Across the accessible top logs, the actual Hunter-pet attack abilities heavily favor:

**Claw + Bite**

while your pet consistently shows:

**Lightning Breath + Bite**

The current 2026 parsing guide recommends Broken Tooth for maximum personal pet DPS, with wolf or owl/bat as utility alternatives; it doesn't recommend Wind Serpent as the max-DPS choice. It also stresses that the 20/31/0 build makes pet uptime and survival increasingly important. [Wowhead](https://www.wowhead.com/classic/guide/the-indefinite-wow-classic-era-hunter-guide-by-nelenya-34233)

So this isn't merely:

> “maybe get a different pet.”

It's:

**20/31/0 + higher-DPS pet + full pet consumes/buffs + tighter pet control + zero early recall.**

On Patchwerk alone, that package appears capable of being worth well north of **50–80 DPS** relative to what you're currently getting.

---

# 6. Your shot rotation has a consistent pattern

Across nearly every boss, your **Aimed Shot frequency is lower than the elite median**.

Some representative casts/minute:

| Boss | Your Aimed/min | Top-5 median | Your Auto/min | Top-5 median |
|---|---:|---:|---:|---:|
| Patchwerk | 5.00 | **6.01** | 19.99 | 19.75 |
| Grobbulus | 5.39 | **6.10** | 18.87 | **22.30** |
| Gluth | 4.32 | **5.70** | 17.27 | **23.71** |
| Thaddius | 4.41 | **5.43** | 15.67 | **17.15** |
| Noth | 5.02 | **6.79** | 20.09 | **24.15** |
| Heigan | 4.36 | **5.81** | 19.64 | **23.80** |
| Loatheb | 4.97 | **5.99** | 18.96 | **20.82** |
| Anub | 5.10 | **7.28** | 23.78 | **25.88** |
| Faerlina | 4.50 | **6.66** | 23.98 | **26.87** |
| Maexxna | 4.95 | **7.37** | 23.11 | **26.59** |
| KT | 4.41 | **6.55** | 18.32 | **21.84** |

Multi-Shot is often much closer.

That tells me your first mechanical priority should be:

**stop leaving Aimed Shot cycles unused.**

This isn't simply “cast Aimed on cooldown,” because clipping Autos is bad. The correct principle remains Auto → fit Aimed/Multi inside the weapon cycle. The recent Era guide likewise lists Auto > Aimed > Multi and emphasizes not clipping the ranged swing. [Wowhead](https://www.wowhead.com/classic/guide/the-indefinite-wow-classic-era-hunter-guide-by-nelenya-34233)

But your logs suggest you're erring too far in the conservative direction.

On Patchwerk:

```text
Haplina:  7 Aimed in 84 sec
Xert:    12 Aimed in 120 sec
Smcadogx:11 Aimed in 106 sec
```

That is material.

---

# 7. Melee weaving: boss-specific, not universal

This was one thing I wanted the logs to settle rather than relying on forum dogma.

They do.

For Patchwerk, top-five Raptor Strike use is approximately:

```text
Smcadogx  11
Charies    9
Andrenn    8
Xal        6
Xert       0
```

So **4/5 top Patchwerk hunters melee weave**, and rank 1 does it aggressively.

But on many other bosses the top-five median is literally **zero Raptor Strikes**.

So I would not adopt:

> “melee weave every boss.”

I would adopt:

> **Learn perfect ranged cycling first, then add weaving aggressively on encounters where the geometry actually rewards it.**

That's consistent with the 2026 guide, which treats Raptor Strike as a way to exploit genuinely empty space between ranged cycles rather than something that should ever cost an Auto. [Wowhead](https://www.wowhead.com/classic/guide/the-indefinite-wow-classic-era-hunter-guide-by-nelenya-34233)

---

# 8. Your Engineering preparation is actually pretty good

This is one area where you're already behaving like the serious parsers.

Across your 15 selected parses:

- Battle Chicken appears in **9**
- Arcanite Dragonling in **10**
- other engineering/summoned helpers are also present

Top logs also use Battle Chicken heavily.

So I'm not going to waste your time telling you “pick up Engineering and pre-pop chicken” as though you've missed something fundamental.

You're already doing it.

---

# 9. Some bosses are personal-performance problems; others are raid-speed problems

This distinction is extremely important.

Your current WCL percentages:

| Boss | Current % | Your DPS | Current #1 DPS | Your kill | #1 kill |
|---|---:|---:|---:|---:|---:|
| Patchwerk | 96.03 | 1001 | 1410 | 84s | 106s |
| Grobbulus | 88.89 | 835 | 1518 | 67s | 63s |
| Gluth | 95.22 | 807 | 1434 | 56s | 48s |
| Thaddius | 95.70 | 1362 | 2044 | 123s | 135s |
| Noth | 95.70 | 1053 | 1523 | 48s | 41s |
| Heigan | 95.29 | 883 | 1371 | 55s | 42s |
| Loatheb | 93.24 | 1046 | 1565 | 133s | 143s |
| Anub | 97.03 | 1232 | 1950 | 35s | 42s |
| Faerlina | 98.28 | 1087 | 1547 | 40s | 40s |
| Maexxna | **99.08** | 1122 | 1650 | 36s | 33s |
| Razuvious | 98.01 | 834 | 1347 | 45s | 50s |
| Gothik | 83.88 | 163 | 444 | 307s | 297s |
| Four Horsemen | **99.05** | 496 | 826 | 142s | 102s |
| Sapphiron | **98.99** | 815 | 3559 | **116s** | **21s** |
| KT | 83.93 | 644 | 1321 | **177s** | **90s** |

There are some fascinating conclusions here.

### Patchwerk, Loatheb, Anub, Razuvious

Your raid kill is **as fast or faster than rank 1**.

Those are primarily **personal optimization fights for you**.

You can't hide behind kill time there. That's actually great news because they are fixable.

### Sapphiron

Your current parse is already basically **99**, but the top five Sapphiron kills are:

**18–22 seconds.**

Yours is **116 seconds**.

No individual Hunter optimization is going to bridge 815 → 3500 DPS under those two completely different raid environments.

That rank-1 chase is fundamentally a **raid-composition / speedkill project**.

### Kel'Thuzad

Same problem, though less extreme.

Your kill:

**176.8 sec**

Top five:

**74–135 sec**, with #1 at ~90 sec.

There's plenty you can personally improve on KT, but absolute rank contention requires the raid to remove a gigantic amount of encounter time.

### Gothik

Interestingly, kill times are basically identical (~297–307 sec), yet you're 163 DPS versus ~413–444.

So **Gothik is absolutely worth a separate event-by-event investigation.**

Something other than raw encounter duration is killing your parse there.

---

# 10. Your current gear isn't as far off as the DPS gap suggests

The top-five equipment census is remarkably consistent:

**70/75 use Nerubian Slavemaker.**

For hands:

- 49 Marshal's
- 7 General's
- 16 Cryptstalker

For cloak:

**69/75 Cloak of the Fallen God.**

For melee/stat weapons:

- Kingsfall 39 times as main hand
- Eye of Nerub 19
- Hatchet 8
- Harbinger dominates offhand choices

You already have most of that architecture.

Current Era BiS guidance also favors Nerubian Slavemaker, the PvP Multi-Shot gloves, Cryptstalker pieces, and either dual-wield stat sticks or Eye of Nerub depending on whether you are weaving. [Wowhead](https://www.wowhead.com/classic/guide/wow-classic-hunter-dps-naxxramas-best-in-slot-gear)

So I'm substantially less interested in telling you:

> “get more Naxx gear.”

and much more interested in:

> **spec + DMF + trinkets + pet + rotation.**

---

# 11. One older issue in some of your best logs is already fixed in newer ones

Your Patchwerk best uses:

**Biznicks +3% hit scope**

while the dominant top setup is **Sniper Scope +7 weapon damage**.

Top five data:

```text
Sniper Scope (+7)   70/75
Biznicks (+3 hit)    3/75
unknown              2/75
```

Your own selected logs are:

```text
Sniper Scope 13/15
Biznicks      2/15
```

So it looks like you've already transitioned away from Biznicks on newer gear.

That's good.

Biznicks is enchant ID 2523 (+3% ranged hit), while Sniper Scope is 664 (+7 ranged weapon damage). [Wowhead](https://www.wowhead.com/classic/spell%3D22779/biznicks-247x128-accurascope)

Once you're hit-capped without Biznicks, Sniper is clearly what the elite logs are doing.

---

# What I would change before your **next raid**

In this order:

1. **Respec to 20/31/0.**
2. **DMF Damage, never DMF Agility for parse night.**
3. **Get Renataki.**
4. Ideally acquire **Slayer's Crest**; otherwise use encounter-appropriate alternatives rather than treating Blackhand's as permanent.
5. Keep **Mark of the Champion** where applicable.
6. Move away from your current Wind Serpent for personal parse attempts; prepare a max-DPS physical pet and fully buff/consume it.
7. Fix pet recall/uptime — especially the last several seconds of fights.
8. Increase Aimed-Shot utilization without sacrificing Autos.
9. Add Dense Dynamite to genuinely empty ranged cycles.
10. Learn melee weaving on **Patchwerk first**, because the actual top logs prove the payoff there is enormous.
11. For DMF push nights, farm **Doomshot**; the current parse guide specifically does so for leaderboard attempts. [Wowhead](https://www.wowhead.com/classic/guide/the-indefinite-wow-classic-era-hunter-guide-by-nelenya-34233)

The current Era guide's consumable baseline also includes Mongoose, Grilled Squid, Juju Might, relevant Blasted Lands/Darnassus buff, Dark Desire when needed for hit, Engineering explosives, and separate pet consumables. [Wowhead](https://www.wowhead.com/classic/guide/the-indefinite-wow-classic-era-hunter-guide-by-nelenya-34233)

---

## One WCL/Gold oddity I noticed

Archive access **did work** — that's why we now have the old top logs.

But WCL reported your API token's live limit as:

**1,800 points/hour**

despite the current Gold subscription page advertising **9,000 points/hour**. WCL's `rateLimitData` field is specifically documented as the total hourly points available to that key. [Warcraft Logs](https://www.warcraftlogs.com/subscribe)

So the subscription is definitely benefiting us via archive access, but the API-rate entitlement either hadn't propagated yet or WCL is applying the limit differently to this OAuth/application combination.

It didn't prevent this export from completing, so I'd leave the throttling in place for now.

---

This is only the **first-pass forensic analysis**. I now have all 89 fights locally, so the next useful layer is much nastier: **boss-by-boss event reconstruction** — exact Auto intervals, each missed Aimed opportunity, Quick Shots/Rapid Fire timing, Renataki opener timings from the top hunters, pet start/stop timestamps, engineering windows, and then a concrete optimal opener/rotation for **Haplina on each Naxx boss**.

And based on what I've seen already, **Patchwerk, Gothik, Grobbulus and KT deserve individual autopsies first**, while your Maexxna/4HM/Sapphiron parses are already in a very different category.

Yes. The second pass changed the picture quite a bit, especially around pets, Gothik, and what the melee-weave logs are actually doing.

I also turned the analysis into a reusable forensic pack rather than leaving it only in chat:

Haplina_Naxx_Forensic_Pack.zip[Download the complete Haplina Naxx forensic pack](sandbox:/mnt/data/Haplina_Naxx_Forensic_Pack.zip)

:chatgpt-content-reference{index="7"}[Read the full forensic report](sandbox:/mnt/data/Haplina_Naxx_Forensic_Pack/Haplina_Naxx_Forensic_Report.md)

The pack includes every top-five gear set, pet data with ability ranks, every cast timestamp, every Auto→Auto interval for Haplina and rank 1, boss timing comparisons, melee-weave gear, and the Gothik target breakdown.

## 1. Yes — we can get substantially better pet data

There is one distinction: in Classic Era, pets don't have a Retail-style talent “spec.” They have a **family plus trained active/passive abilities bought with training points**.

WCL lets us recover the actual pet actor, pet name, damage, start/end uptime, death, active abilities used and their spell IDs. It does **not** expose passive training choices such as exactly how many TP were spent on Great Stamina, Natural Armor, Frost Resistance, etc., because those passives don't appear in the pet's event stream.

For Snape specifically, I can now prove from the event IDs that you're using:

**Bite 8 — spell 17261**  
**Dive 3 — spell 23148**  
**Lightning Breath 6 — spell 25012**

So Snape's offensive abilities are not under-ranked. Lightning Breath 6 is the maximum level-60 Lightning Breath, and Lightning Breath uniquely identifies a Wind Serpent. [Wow Petopia](https://www.wow-petopia.com/classic/abilities.php)

The top-parser data is striking. Across the **75 top-five boss parses**, 74 have a real Hunter pet present. Among those 74:

**65 use Claw. Zero use Lightning Breath.**

At least 42 have the observed combination **Claw + Dash**, which effectively identifies a Cat because Cat is the intersection of Classic families that can learn both. There are additional explicitly identifiable cats such as BrokenTooth, Rakshiri, pets literally named Cat, etc. Petopia confirms the Classic family/ability restrictions. [Wow Petopia](https://www.wow-petopia.com/classic/abilities.php)

Even more interesting is the association with 20/31/0. Among top parses using **20/31/0**, median pet DPS is about **158** across the whole dataset. If I exclude the weird/pet-hostile Gothik, 4HM and Sapphiron situations, that rises to about **164 DPS**.

Snape on Patchwerk:

**78 DPS.**

The top-five Patchwerk pets:

**216, 149, 222, 160, 174 DPS.**

That's not a small difference.

And your pet-management losses are now identifiable rather than inferred. On Grobbulus, Snape actually **dies at 25.678 seconds**:

> Mutagen Explosion: 1609  
> Grobbulus Cloud Poison: 1116  
> Grobbulus Cloud Poison: 868  
> death

On Gothik, Snape dies at 152.664s after Spectral Death Knight Whirlwind plus Spectral Trainee Arcane Explosions.

On Four Horsemen, Snape does **not** die — he simply stops doing damage about **48 seconds before the encounter ends**.

And on your selected best logs for **Gluth, Heigan, Anub'Rekhan and Sapphiron**, there is **no Hunter pet actor at all**.

That's an enormous amount of parse potential.

For Sapphiron specifically, the top pets also show frequent partial resists on the 600-damage Frost Aura ticks. We cannot reverse-engineer the exact passive TP allocation with certainty, but it is consistent with serious Frost Resistance investment; Classic pets can train Frost Resistance up to rank 5 / +140. [Wow Petopia](https://www.wow-petopia.com/classic/abilities.php)

The complete fight-by-fight pet data is here:

:chatgpt-content-reference{index="8"}[Pet forensics with families, skills, ranks and deaths](sandbox:/mnt/data/Haplina_Naxx_Forensic_Pack/pet_forensics_with_ranks.csv)

---

# 2. Gear: yes, I now have the exact top-five sets per boss

And your Slavemaker/melee-weaving question has a very clear answer:

**Melee weaving does NOT mean replacing Nerubian Slavemaker.**

On Patchwerk, **all five current top parses use Nerubian Slavemaker.**

Rank 1 Smcadogx:

**Dark Edge of Insanity + Nerubian Slavemaker**  
11 Raptor Strikes  
13 ordinary melee swings

Rank 2 Charies:

**Eye of Nerub + Nerubian Slavemaker**  
9 Raptor Strikes

Rank 3 Andrenn:

**Eye of Nerub + Nerubian Slavemaker**  
8 Raptor Strikes

Rank 4 Xert:

**Kingsfall + Harbinger + Nerubian Slavemaker**  
0 Raptor Strikes — pure ranged

Rank 5 Xal:

**Eye of Nerub + Nerubian Slavemaker**  
6 Raptor Strikes

So for Patchwerk, **Eye of Nerub is the dominant weaving weapon**, while Slavemaker remains the ranged weapon regardless.

And globally, the gear meta is incredibly stable. Across the 75 top-five parses I found **72/75 Cryptstalker heads, 73/75 shoulders, 73/75 chests, 73/75 belts, 73/75 boots, 73/75 wrists, 62/75 Prestor's necks, 69/75 Fallen God cloaks, and 70/75 Nerubian Slavemakers**. The median parse has **seven Cryptstalker armor pieces**, usually breaking 8p specifically for the PvP Multi-Shot gloves.

Here is the encounter-specific picture:

| Boss | Dominant melee setup | Slavemaker | Weaving | Dominant trinket signal | Main takeaway |
|---|---|---:|---:|---|---|
| Patchwerk | Eye of Nerub 3/5 | **5/5** | **4/5** | Very mixed; rank 1 Renataki | This is the real weaving fight |
| Grobbulus | Kingsfall 2/5 | 4/5 + 1 unknown | 1/5 | Mark / Slayer | Mostly ranged |
| Gluth | Kingsfall 3/5 | 4/5 | 0/5 | Mark 4/5 | Pure ranged |
| Thaddius | Kingsfall 3/5 | **5/5** | **4/5** | Mark 4/5 | Weaving viable |
| Noth | Kingsfall 3/5 | **5/5** | 1/5 | Mark 4/5; Renataki 2/5 | Mostly ranged |
| Heigan | Kingsfall 3/5 | **5/5** | 4/5, usually only 1 Raptor | Mark 4/5 | Opportunistic weave only |
| Loatheb | Kingsfall/Eye | **5/5** | 1/5 | Slayer 3/5 + Mark 4/5 | Ranged/spore timing |
| Anub | **Kingsfall 5/5** | **5/5** | 0/5 | Renataki/Slayer/Mark | Stat-stick ranged setup |
| Faerlina | Eye 3/5 | **5/5** | 0/5 | **Renataki 3/5 in T2 slot** | Burst/reset encounter |
| Maexxna | Kingsfall 4/5 | **5/5** | 0/5 | Renataki common | Burst/reset encounter |
| Razuvious | Kingsfall 3/5 | 4/5 + unknown | 0/5 | Mark 4/5 | Pure ranged |
| Gothik | **Eye 4/5** | 3/5; Ashjre'thul 2/5 | 2/5 | Seal/Mark/Blackhand varied | Weird historic/padding meta |
| 4HM | Kingsfall/Eye | **5/5** | 1/5 | **Mark 5/5** | Movement/ranged |
| Sapphiron | Kingsfall 3/5 | **5/5** | 0/5 | **Renataki 3/5** | Extreme burst |
| KT | Kingsfall 3/5 | **5/5** | **0/5** | Mark 4/5; Kiss 2/5 | Never prioritize weaving |

And I exported **all 18 gear slots for all 75 parses**, so you don't have to rely on that summary:

:chatgpt-content-reference{index="9"}[Complete top-five gear by boss](sandbox:/mnt/data/Haplina_Naxx_Forensic_Pack/top5_gear_by_boss.csv)

:chatgpt-content-reference{index="10"}[Melee-weave parses and their exact weapons](sandbox:/mnt/data/Haplina_Naxx_Forensic_Pack/melee_weave_gear.csv)

:chatgpt-content-reference{index="11"}[All-slot gear dominance per boss](sandbox:/mnt/data/Haplina_Naxx_Forensic_Pack/gear_dominance_all_slots.csv)

---

# 3. Yes — the analysis can be completely offline

This is actually an important discovery for the app idea:

**The analysis I just did was offline.**

I did not need to query WCL again. Your ~80 MB export contains enough information to reconstruct the fights locally.

So the eventual application can have a very clean architecture:

**Online component:** optionally download WCL rankings/reports/events and refresh the snapshot.

**Offline component:** import one or more exported ZIPs and do everything else locally — gear comparisons, talents, pets, shot cycles, buff intervals, target segmentation, Auto clipping, Renataki detection, raid kill-time comparisons, etc.

I'd probably normalize the raw JSON into **DuckDB** or SQLite and make the actual analyzer a standalone library. Then a desktop/web-local UI can sit on top of it.

That means a user could:

> Export logs once → disconnect from the Internet → open the app → select Hunter → select boss → compare against cached Top 5 → inspect every shot cycle.

And it also cleanly solves the Gold/non-Gold distinction: subscription status only affects **what data you're able to acquire**. It does not affect the analyzer.

I've kept this as the next project phase rather than derailing the current analysis. 

---

# 4. The deeper autopsy has already found some very concrete things

## Patchwerk — your ranged foundation is better than the DPS number suggests

You did:

**1000.9 DPS / 84.0 seconds**

Rank 1:

**1409.8 DPS / 105.9 seconds**

Your guild actually killed Patchwerk **22 seconds faster**, so kill time isn't your excuse here.

Your Auto rate is:

**19.99 Autos/min**

Top-five median:

**19.75 Autos/min**

That is actually excellent.

Your Multi rate is also basically fine.

The clearer ranged difference is Aimed:

**you: 5.00/min**  
**top-five median: 6.01/min**

Your exact Aimed completions:

`10.91 → 21.88 → 32.75 → 43.28 → 53.25 → 63.15 → 75.47`

At the elite cadence, your fight length suggests roughly **8–9 Aimed Shots instead of 7**.

But the giant Patchwerk difference isn't just those 1–2 Aimeds.

Your pet:

**78 DPS**

Top-five median:

**~174 DPS**

And four of the top five then add melee weaving on top.

Rank 1's opener is extremely instructive:

`RF 4.20 → Auto 4.51 → Aimed 6.69 → Auto 7.01 → Multi 7.32 → Raptor + Refocus 9.11 → Auto 10.75 → Aimed 13.24 → Multi 13.85`

That's not theorycrafting anymore. That's the **actual rank-1 Renataki sequence**.

Your RF timing itself is already reasonable: **6.67–25.67s**.

So my Patchwerk priorities are now:

**pet/spec → extra Aimed utilization → Renataki/explosive tech → then weave.**

Not “fix your Auto Shot rotation,” because the evidence doesn't support blaming Autos as the primary Patchwerk problem.

Also: every top-five Patchwerk Hunter used an explosive. You used **zero Dense Dynamite and zero Sapper** in that parse.

---

# Grobbulus — this one is much easier to fix

Your first Auto is at **1.84s**, which is fine.

Then Multi at **2.96s**.

But your **first Aimed isn't until 11.02s**.

Rank 1:

Auto 2.99  
Aimed **5.17**  
Multi 5.85

You've effectively skipped the opener's first real Aimed window.

More importantly, you never use **Rapid Fire at all**.

Rank 1 RF: **2.68s**.  
Top-five median first RF: about **9.2s**.

And then Snape dies halfway through your burn from the poison cloud sequence described above.

Your pet:

**27.7 DPS**

Top-five median:

**~184.5 DPS**

Only **one** of the top five meaningfully melee-weaves Grobbulus, so don't waste practice time on that yet.

For your next Grobb parse the prescription is very straightforward:

**early Aimed + use Rapid Fire + don't let the pet stand in a poison cloud.**

That alone is a very different parse.

---

# Gothik — I found the real reason the leaderboard looks insane

This one is probably the most interesting result in the whole research project.

Your player damage:

**48,476**

Damage to unrelated trash:

**0**

Rank 1 Andrenn:

**130,204 total**  
**62,023 from unrelated trash — 47.6%**

Rank 2:

**58.4% unrelated trash**

Rank 3:

**55.4%**

Rank 4:

**50.4%**

Rank 5:

**72.2%**

The extra targets are things like:

**Plagued Ghoul**  
**Plagued Gargoyle**  
**Necropolis Acolyte**

Those are **not normal Gothik wave mobs**.

So the leaderboard parses are carrying/overlapping additional Naxx trash into the WCL Gothik encounter window.

This is why blindly comparing your 163 DPS against their 444 DPS was misleading.

If I remove that foreign trash:

**Haplina native Gothik-target DPS: ~158**

The top five native-target values are approximately:

**230 / 172 / 183 / 197 / 111 DPS**

You're suddenly not remotely as far behind as the parse number says.

You are, however, leaving real rotational damage behind:

Your Aimed Shot timestamps are:

**16.97s**  
**299.47s**

That's it.

A **282.5-second gap** between Aimed Shots.

Top hunters are around **11 Aimed casts** over the encounter.

You're also using RF at **293.58 seconds**, basically saving it for Gothik himself, whereas the leaderboard parse is predominantly about **wave/trash damage**.

So there are actually two different Gothik goals:

**Clean raid strategy:** improve your Aimed/Multi utilization and pet survival on your assigned side.

**Actual rank-chasing:** your guild has to reproduce the extra-trash pull/encounter overlap strategy, put you in the correct target-dense assignment, and then optimize Aimed/Multi/Dynamite around it.

Without that raid strategy, **rank 1 Gothik is not an apples-to-apples target.**

I exported the evidence separately:

:chatgpt-content-reference{index="12"}[Gothik target/padding breakdown](sandbox:/mnt/data/Haplina_Naxx_Forensic_Pack/gothik_target_padding.csv)

---

# Kel'Thuzad — your raid assignment is directly costing your parse

This one is almost as revealing.

Your kill:

**176.8 seconds**

Rank 1:

**90.4 seconds**

So there's already a huge raid-speed problem.

But your own event stream exposes something else.

Aimed:

`... 65.65 → 75.05 → 84.92 → [nothing] → 123.89 ...`

That's a **38.97-second Aimed gap**.

Yet you are still Auto Shooting during it:

`85.37 → 88.17 → 90.95 → 93.76 ...`

So this isn't simply “boss unavailable.”

Then the event stream shows what you're actually doing:

**97.36 — Freezing Trap**  
**102.51 — Reckless Charge on teammate Lgbtqt**  
**108.12 — Hunter's Mark KT again**  
**115.32 — Scatter Shot on teammate Airra**  
**119.36 — Hunter's Mark again**

Reckless Charge is the stun produced by the Goblin Rocket Helmet/Horned Viking Helmet effect. [Wowhead](https://www.wowhead.com/classic/spell%3D22641/reckless-charge?utm_source=chatgpt.com)

You're helping control **Mind Controlled raid members**.

Rank-1 Snipex's corresponding log?

Basically just keeps shooting KT. No equivalent Trap → Rocket Helmet teammate → Scatter teammate control sequence.

That is a giant realization:

**your KT parse is partially being sacrificed for raid utility.**

If the explicit goal is a Hunter 100, your parsing Hunter should ideally **not be the primary MC-control player**.

And then there's your KT gear:

**Blackhand's Breadth + Burrower's Shell**

Top five:

Kiss + Mark  
Renataki + Mark  
Mark + Slayer  
Slayer + Mark  
Kiss + Mark

Burrower's Shell is costing offensive throughput on exactly the boss where you already have major uptime losses.

KT is also **5/5 Slavemaker and 0/5 weaving** in the current top five. Don't melee weave this.

Your shot-rate benchmark over your very long kill works out to roughly:

**13 actual Aimeds vs ~19 at the top-five median rate.**

Not all six are personally “missed” — mechanics and your control assignment matter — but the 39-second section alone contains several legitimate special-shot opportunities that disappear because you're doing utility work.

---

# The rest of Naxx now has a much clearer plan

The other major things I found are that **Gluth, Heigan, Anub and Sapphiron need a pet before we discuss micro-optimizations at all**; your selected best logs literally have no Hunter pet present. Thaddius needs Rapid Fire held for the actual Thaddius/polarity burn — the elite RF timing clusters around ~82s, while you never cast RF at all. Loatheb has you using RF at 72.6s while the leaders are commonly using it around the first useful spore/burst window, roughly 26–40s. Faerlina is an opener problem: your first Aimed is 16.2s versus rank 1 at 2.08s, and four of the five leaders use Refocus/Renataki. Maexxna is similar: you're already parsing 99, but the absolute top adds another Aimed/Refocus burst and substantially more pet damage.

Four Horsemen is especially interesting because your Auto volume is actually decent, but you have two enormous Aimed gaps of ~35 seconds, RF doesn't happen until **120.4s**, and your pet stops attacking ~48 seconds before the encounter ends. Rank 1 uses RF at **2.63s**. That 99.05 is good relative to the population, but there is still a surprisingly large difference between “99” and the absolute top.

Sapphiron is still fundamentally a raid-speed problem. Your kill is **116s**. The current top-five kills are roughly **18–22 seconds**. Their entire fight ends before you even press Rapid Fire at 24.6s. For absolute Sapph ranking, we're talking about a completely different raid project, not simply playing Hunter better.

---

## And I did the “exact interval” part rather than approximating it

There are too many individual events to dump sensibly into a chat message, so the pack contains two useful forensic datasets:

:chatgpt-content-reference{index="13"}[Every relevant cast timestamp for Haplina + all top five](sandbox:/mnt/data/Haplina_Naxx_Forensic_Pack/all_cast_timelines.csv)

:chatgpt-content-reference{index="14"}[Every Auto→Auto interval for Haplina and rank 1](sandbox:/mnt/data/Haplina_Naxx_Forensic_Pack/auto_interval_reconstruction.csv)

The second file includes, for each interval:

`Auto #` → start time → end time → exact gap → whether RF overlapped → whether Quick Shots overlapped → Aimed inside that gap → Multi inside → Raptor inside → Refocus inside.

So we can now move beyond:

> “maybe you're clipping Autos.”

and identify **which exact shot cycle was abnormal and what you pressed inside it**.

The next step I want to do from this dataset is even more targeted: turn all of this into a **personal Haplina Naxx parse playbook** — one page per boss with the gear/trinket set to equip, pet to use, whether to weave, exact pull opener, planned RF/Refocus timing, expected shot counts for *your guild's likely kill time*, and encounter-specific “do not do this” items. That would turn the research into something you can actually keep open on a second monitor during raid.


Done. I turned the forensic work into an actual **raid-use playbook**, not just another report.

### Main deliverables

:chatgpt-content-reference{index="4"}[**Open the offline Haplina Naxx Parse Playbook**](sandbox:/mnt/data/Haplina_Naxx_Parse_Playbook/Haplina_Naxx_Parse_Playbook.html)

Haplina_Naxx_Parse_Playbook.zip[**Download the complete playbook package**](sandbox:/mnt/data/Haplina_Naxx_Parse_Playbook.zip)

:chatgpt-content-reference{index="6"}[Markdown version](sandbox:/mnt/data/Haplina_Naxx_Parse_Playbook/Haplina_Naxx_Parse_Playbook.md)

:chatgpt-content-reference{index="7"}[Boss-by-boss plan as CSV](sandbox:/mnt/data/Haplina_Naxx_Parse_Playbook/boss_playbook.csv)

The HTML is the one I'd actually keep on your second monitor. It's completely self-contained/offline, has boss navigation, search, collapsible top-five gear tables, and persistent **reviewed** checkboxes.

## What's now in each boss page

For all 15 bosses it gives you:

- your current DPS, percentile and kill time
- current #1 DPS and kill time
- your **Auto / Aimed / Multi** count
- projected shot-count benchmark for **your guild's current kill length**
- your exact gear from that best parse
- recommended melee weapon setup
- recommended trinket setup
- pet plan
- whether you should melee weave
- exact opener
- Rapid Fire timing
- Refocus/Renataki strategy
- specific **“DO NOT”**
- what you need to ask/change at the **raid level**
- expandable table showing the actual current top five:
  - spec
  - trinkets
  - melee weapon(s)
  - ranged weapon
  - Raptor count
  - pet DPS

So for example Patchwerk is no longer generic advice. It tells you your logged setup was:

**Blackhand + Mark / Eye of Nerub / Slavemaker**

and then gives you the two progression paths:

**Safe high parse:**  
Slayer + Mark / Kingsfall+Harbinger / pure ranged

**Ceiling attempt:**  
Renataki + Slayer → first Aimed+Multi → Refocus → second Aimed+Multi → FD swap Renataki→Mark → Eye of Nerub weave

with the actual rank-1 sequence as the model.

The Renataki/FD swap is also consistent with the current 2026 Era parsing guide's explicit recommended use: Renataki + Slayer, consume the first pair, reset, consume the second pair, then FD-swap Renataki to Mark. [Wowhead](https://www.wowhead.com/classic/guide/the-indefinite-wow-classic-era-hunter-guide-by-nelenya-34233)

## Shot targets are now quantitative

For your current-ish kill lengths, the playbook calculates targets like:

| Boss | Current Auto/Aimed/Multi | Benchmark |
|---|---:|---:|
| Patchwerk | 28 / 7 / 8 | **27–28 / 8–9 / 7–8** |
| Grobbulus | 21 / 6 / 6 | **24–25 / 6–7 / 5–6** |
| Gluth | 16 / 4 / 5 | **21–22 / 5–6 / 5–6** |
| Thaddius | 32 / 9 / 10 | **35–36 / 11–12 / 9–10** |
| Loatheb | 42 / 11 / 10 | **46–47 / 13–14 / 11–12** |
| 4HM | 44 / 8 / 11 | **42–43 / 13–14 / 12–13** |
| KT | 54 / 13 / 8 | **64–65 / 19–20 / 13–14** |

These are deliberately called **benchmarks**, not “you definitely made X mistakes.” Phase transitions, movement, MC control, Sapph air phase etc. matter.

But a number like **4HM: 8 Aimeds versus ~13–14 at elite cadence** tells us exactly where to start looking.

## There are also some immediate no-loot changes hiding in this

A few stand out.

**KT:** your logged set is Blackhand + **Burrower's Shell**. You already own Mark. So before obtaining any new item, a parse attempt can stop using the defensive Shell and use an offensive pair. And much more importantly, you need to stop being the Hunter handling Trap + Scatter + Rocket Helmet on MC'd teammates if the goal for that pull is your parse.

**Thaddius:** your best log had **Blessed Qiraji Pugio + Harbinger**, despite your other logs proving you own Kingsfall. Your playbook now calls for Kingsfall + Harbinger unless you're deliberately setting up an Eye weave. The bigger fix is RF: **hold it for Thaddius/polarity**, around the ~82s region represented by the current elite logs.

**Faerlina:** you logged Blackhand + Royal Seal. Since you demonstrably own Jom Gabbar and Mark doesn't apply here, **Jom + Blackhand is already a better parse-oriented fallback** while you work toward Renataki/Slayer.

**Gluth, Heigan, Anub and Sapphiron:** your selected best logs had **no Hunter pet actor at all**. That is now flagged in giant letters on those pages.

**Grobbulus:** your missing pet DPS isn't mysterious anymore. Snape gets killed at ~25.7s. Fixing pet handling is worth vastly more than debating one Agility enchant.

---

## Pet setup is now part of the playbook

For serious personal parsing I'm moving you toward a **Cat**, ideally Broken Tooth.

The current Era guide likewise calls Broken Tooth the highest individual-DPS pet, recommends Great Stamina 10, zero Natural Armor and putting remaining points into the raid-appropriate resistance. [Wowhead](https://www.wowhead.com/classic/guide/the-indefinite-wow-classic-era-hunter-guide-by-nelenya-34233?utm_source=chatgpt.com)

Petopia confirms the Classic rank/TP system: Claw 8 is 25 TP, Dash 3 is 25 TP, Great Stamina 10 is 185 TP, while Frost Resistance 3 costs 45 TP and FR5 costs 105. [Wow Petopia](https://www.wow-petopia.com/classic/abilities.php?utm_source=chatgpt.com)

So I've deliberately given you two practical profiles rather than pretending you can max everything:

**Damage profile:** Great Stamina 10 + Claw 8 + Bite 8 + Dash 3, then whatever FR fits.

**Sapph/survival profile:** Great Stamina 10 + Claw 8 + Dash 3 + Frost Resistance 3.

And **0 Natural Armor** for the raid parse pet.

That's much more defensible than saying “just max Frost Resist” and accidentally blowing the 300-TP budget.

---

## The future app idea is already beginning to validate itself

The new HTML is actually a tiny proof-of-concept.

It needs **zero WCL access to run**.

The pipeline we're naturally ending up with is:

```text
WCL/API
   │
   │  occasional refresh
   ▼
Raw snapshot ZIP
   │
   ▼
Local normalizer
   │
   ├── fights
   ├── players
   ├── gear
   ├── pets
   ├── casts
   ├── buffs
   └── events
   │
   ▼
Offline analyzer
   │
   ├── shot-cycle reconstruction
   ├── clipping detection
   ├── pet uptime/deaths
   ├── gear consensus
   ├── cooldown comparison
   ├── target/padding analysis
   └── parse recommendations
   │
   ▼
Local UI
```

So yes: eventually this can become something where you point it at a WCL export and get:

**“Why is my Patchwerk 96 instead of 100?”**

without sending the data anywhere.

But I'm keeping that as phase two like you requested.

For now, I'd use the new playbook for the next raid and make the first big practical changes:

1. **20/31/0**
2. **DMF Damage**
3. **Cat + serious pet management**
4. **Renataki acquisition**
5. **Slayer acquisition**
6. follow the boss-specific RF/openers in the playbook
7. fix the KT assignment
8. start learning Patchwerk weaving only after the new ranged/pet baseline is stable

The next research layer I want to add is a **post-raid grader**: feed it your next Naxx export and have it automatically say something like *“Patchwerk: opener A, pet C, shot cadence B+, 2 probable clipped cycles, missed 1 Aimed, RF excellent, +92 estimated controllable DPS left.”* That is also exactly the analysis engine we'd eventually put behind the offline app.

Yes — and this changes how I would interpret the melee-weave results for **you**.

I re-ran the raw event data specifically for faction, racial usage and Windfury. The headline is:

**The top Hunter dataset is overwhelmingly Alliance, and melee weaving is absolutely viable without Windfury. But the current #1 Patchwerk parse is indeed an Orc + Windfury outlier, and I was giving that parse too much weight when I quoted its ~286 melee DPS.**

### Overall top-5 dataset

Across all 15 bosses, 75 current top-five parses:

| Faction | Parses | Share |
|---|---:|---:|
| **Alliance** | **63** | **84%** |
| Horde | 12 | 16% |

By boss:

| Boss | Alliance | Horde |
|---|---:|---:|
| Patchwerk | **4** | 1 |
| Grobbulus | 3 | 2 |
| Gluth | **5** | 0 |
| Thaddius | **4** | 1 |
| Noth | **5** | 0 |
| Heigan | **5** | 0 |
| Loatheb | **5** | 0 |
| Anub | 3 | 2 |
| Faerlina | 4 | 1 |
| Maexxna | 3 | 2 |
| Razuvious | **5** | 0 |
| Gothik | **5** | 0 |
| 4HM | **5** | 0 |
| Sapphiron | 2 | **3** |
| KT | **5** | 0 |

And **Haplina is Alliance** in the CombatantInfo data, so Alliance is the benchmark that actually matters to you.

## Now the important part: melee weaving

There are **18 top-five parse instances with at least one Raptor Strike**.

Of those:

**15 are Alliance.  
3 are Horde.**

Even better: those three Horde instances are all the **same Hunter: Smcadogx**.

Across distinct players, there are **13 different top-five Hunters who weave**:

**12 Alliance, 1 Horde.**

So no — the melee-weave evidence is emphatically **not** “Horde gets Windfury, therefore weaving looks good.”

If I tighten the definition to more meaningful weaving — **5+ Raptor Strikes** — I get:

| | Parse instances |
|---|---:|
| Alliance, no Windfury | **5** |
| Horde + Windfury | 3 |

Still more Alliance examples.

---

# Patchwerk is especially revealing

The current top five are:

| Rank | Hunter | Faction | Race evidence | WF | Raptor | White melee | DPS |
|---:|---|---|---|---|---:|---:|---:|
| 1 | **Smcadogx** | Horde | **Orc — Blood Fury logged** | **YES** | 11 | 13 | 1409.8 |
| 2 | **Charies** | Alliance | — | No | 9 | **0** | 1367.9 |
| 3 | **Andrenn** | Alliance | — | No | 8 | **0** | 1349.4 |
| 4 | **Xert** | Alliance | — | No | 0 | 0 | 1347.3 |
| 5 | **Xal** | Alliance | — | No | 6 | **0** | 1333.0 |

This is much more useful than the previous comparison.

### Smcadogx really is Orc

His raw event stream contains:

**Blood Fury — spell 20572**

so there is zero ambiguity about him being Orc.

And he gets actual:

**Windfury Totem — spell 10610**

`extraattacks` events.

Not merely “there was a Shaman somewhere in the raid.”

I count **9 actual Windfury procs on Patchwerk**.

Windfury Totem gives the affected main-hand weapon a 20% proc chance for an extra attack, with additional melee AP on that attack. [Wowhead](https://www.wowhead.com/classic/spell%3D10610/windfury-totem?utm_source=chatgpt.com)

---

# And I can quantify how much WF inflated that rank-1 melee number

Remember when I said Smcadogx got approximately:

**145 DPS Raptor + 140 DPS white melee = 286 DPS melee**

?

That needs an important footnote.

I matched each `Windfury Totem extraattacks` event to the subsequent melee damage event.

His 13 white melee hits dealt:

**14,860 damage**

Of that, approximately:

**12,066 damage came from the 9 Windfury-generated extra attacks.**

Over 105.93 sec:

### ~113.9 DPS of his 140.3 white-melee DPS is directly Windfury-generated.

Meaning:

| Smcadogx melee component | DPS |
|---|---:|
| Raptor Strike | 145.4 |
| Normal + WF white melee | 140.3 |
| of which directly WF-generated | **~113.9** |
| Total melee package | **285.7** |

So Windfury itself accounts for roughly:

**40% of his entire melee-weaving damage package**

and approximately:

**8.1% of his total 1409.8 DPS parse.**

That's enormous.

And that's **before** accounting for his Orc racial.

Blood Fury increases **base melee AP by 25% for 15 seconds** in Classic — it doesn't increase his ranged AP, but that's perfectly relevant when he's doing this much melee damage. [Wowhead](https://www.wowhead.com/classic/spell%3D20572/blood-fury?utm_source=chatgpt.com)

Plus Orc Hunters have **Command**, giving their pet +5% damage. [Wowhead](https://www.wowhead.com/classic/spell%3D20575/command?utm_source=chatgpt.com)

So Smcadogx has a genuine Horde/Orc advantage for this particular playstyle.

---

# But this makes the Alliance logs MORE interesting

Look closely at Charies, Andrenn and Xal.

They have:

**zero separate white melee hits.**

Their melee contribution is purely their queued **Raptor Strikes**:

| Hunter | Faction | Raptor count | Raptor DPS | WF |
|---|---|---:|---:|---|
| Charies | Alliance | 9 | **123.5** | No |
| Andrenn | Alliance | 8 | **114.3** | No |
| Xal | Alliance | 6 | **97.8** | No |

That is almost a textbook Alliance weave.

They aren't hanging around in melee trying to white-swing.

They're essentially:

> ranged cycle → queue Raptor → get into melee → consume Raptor → get back out → resume ranged cycle.

And they're gaining roughly **100–125 DPS purely from Raptor Strike**, without Windfury.

That's the benchmark I would now use for **you**, not Smcadogx's 286 DPS Horde melee package.

---

# This changes my recommendation for Haplina

Your target should **not** be:

> “Copy Smcadogx's Patchwerk melee behavior.”

He's Orc, has Windfury, Blood Fury, Orc pet bonus and Dark Edge.

That's a different environment.

Your Alliance progression should instead be:

**Stage 1 — Xert model**

Pure ranged, perfect pet, 20/31/0, proper buffs/trinkets, perfect Auto/Aimed/Multi.

Xert is Alliance, does **zero melee weaving**, and is still:

**1347 DPS / rank 4.**

That alone is nearly **+350 DPS over your current Patchwerk**.

Then:

**Stage 2 — Charies / Andrenn / Xal model**

Add **Raptor-only weaving**, preferably with Eye of Nerub.

Don't try to manufacture white swings.

Aim eventually for something like **6–9 properly inserted Raptors during a ~100-second Patchwerk**, provided they cost you **zero ranged cycles**.

That's what the Alliance leaderboard evidence actually supports.

---

# What about Horde races in the rest of the top dataset?

Race itself isn't exposed cleanly as a field by our current export, so I only call race when the event stream **proves it through a racial ability**.

Among the 12 Horde top-five parse instances:

**6 explicitly use Berserking → Troll.**

Berserking increases attack/cast speed by 10–30% for 10 seconds, so Troll is naturally very attractive to a ranged Hunter. [Wowhead](https://www.wowhead.com/classic/spell%3D20554/berserking?utm_source=chatgpt.com)

**3 explicitly use Blood Fury → Orc.**

Those are all:

**Smcadogx — Patchwerk, Grobbulus, Thaddius.**

And all three are melee-weave parses with actual Windfury procs:

| Boss | Smcadogx Raptor | White melee | WF procs |
|---|---:|---:|---:|
| Patchwerk | 11 | 13 | **9** |
| Grobbulus | 6 | 7 | **4** |
| Thaddius | 12 | 6 | **2** |

The remaining **3 Horde parses don't use a race-defining active ability**, so I can't responsibly tell you whether they are Orc/Troll/Tauren from this dataset alone.

---

## The conclusion is actually very favorable for you

I was initially worried your question might uncover:

> “Oops, all the crazy weavers are Orc Hunters sitting in Windfury groups.”

It uncovered the opposite.

**12 of the 13 distinct top-five Hunters who weave are Alliance.**

And on Patchwerk specifically:

**3 of the 4 weaving top-five parses are Alliance/no-WF.**

So melee weaving is absolutely a real Alliance Hunter optimization.

What **was** misleading was using **Smcadogx's 285 DPS melee contribution** as the example of how much *you* might gain. His parse is juiced enormously by Windfury and additionally benefits from Orc melee/pet racials.

For Haplina, I would revise the realistic Patchwerk melee-weave upside from:

> potentially ~285 DPS

to more like the observed Alliance benchmark:

> **~100–125 DPS of Raptor damage at top execution**, before considering whether getting those Raptors costs you any ranged damage.

And critically, **Xert's 1347 Alliance pure-ranged parse says you have a very large amount of improvement available before weaving is even required.**

This is significant enough that I'm going to treat **faction/race/Windfury context as a mandatory field in the eventual analyzer**. A top log shouldn't be shown as a direct execution benchmark without telling us whether the Hunter had Horde-only melee advantages.


It changes **one major part** of the assessment, but reassuringly it does **not** blow up the whole playbook.

The biggest correction is this: I was giving **Smcadogx’s Patchwerk rank-1 log too much weight** as the model for melee weaving. He is Orc + actual Windfury, so his total melee package is not a fair Alliance benchmark for Haplina.

I rebuilt the playbook around **Alliance-normalized comparisons**:

Haplina_Naxx_Parse_Playbook_Alliance_Normalized_v2.zip[Download the revised Alliance-normalized playbook v2](sandbox:/mnt/data/Haplina_Naxx_Parse_Playbook_Alliance_Normalized_v2.zip)

:chatgpt-content-reference{index="1"}[Open the revised offline HTML playbook](sandbox:/mnt/data/Haplina_Naxx_Parse_Playbook_Alliance_Normalized_v2/Haplina_Naxx_Parse_Playbook_Alliance_Normalized_v2.html)

### What materially changes

| Area | Old assessment | Revised assessment |
|---|---|---|
| Patchwerk weaving | Potentially enormous ~285 DPS melee package | **Real, but Alliance benchmark is ~98–124 DPS of Raptor damage**, not the Orc+WF package |
| Patchwerk model | Smcadogx rank 1 | **Xert first for pure ranged; Charies/Andrenn/Xal for Alliance weaving** |
| Grobbulus weaving | Maybe worth considering | **No for Haplina** — meaningful top-5 weave is the Orc+WF example |
| Thaddius weaving | Optional/high-ceiling | **Opportunistic only** for Alliance |
| Patchwerk Renataki | Treated as part of ideal ceiling setup | **Downgraded substantially for Patchwerk** |
| Pet benchmarks | Overall top-five | **Alliance-only** |
| Shot-rate benchmarks | Overall top-five | **Alliance-normalized** |
| Rank-1 comparisons | Always current #1 | Use **best Alliance comparator** when #1 is Horde |

The Renataki correction is actually important. Among the **four Alliance Hunters inside the current Patchwerk top five, none uses Renataki**:

- Charies: Jom Gabbar + Badge of the Swarmguard
- Andrenn: Mark + Blackhand
- Xert: **Slayer + Mark**
- Xal: **Mark + Slayer**

So for **Patchwerk**, your ideal Alliance-first trinket recommendation becomes:

**Slayer's Crest + Mark of the Champion**

And until you have Slayer:

**Blackhand + Mark is demonstrably good enough for current rank-3 Alliance performance.**

Renataki is still a very valuable Hunter item overall — especially Faerlina, Maexxna, Anub, Sapphiron, etc. — but I would no longer tell you:

> “Get Renataki primarily because Patchwerk requires the reset opener.”

It doesn't.

## Patchwerk now has a much cleaner progression path

Your first target should be **Xert**, not Smcadogx.

Xert is Alliance, has no Windfury, does **zero Raptor Strikes**, and still produces:

**1347 DPS**

with:

**20/31/0**  
**Kingsfall + Harbinger**  
**Nerubian Slavemaker**  
**Slayer + Mark**  
strong pet  
clean ranged execution

That means there is roughly **+346 DPS between your 1001 and Xert's 1347 before melee weaving becomes necessary at all**.

That is enormously useful.

Then once you're near that ranged baseline, add the Alliance weave model:

**Charies: 9 Raptors**  
**Andrenn: 8 Raptors**  
**Xal: 6 Raptors**

Those three are Alliance/no-WF.

And crucially, they have essentially **no ordinary white-melee package**. They're not standing there meleeing like Smcadogx.

They're doing what you should do:

> Ranged cycle → identify free window → enter → consume queued Raptor → leave → resume ranged cycle.

That is now the Patchwerk model in the playbook.

---

## How much did Windfury distort the original Patchwerk comparison?

A lot.

Smcadogx's melee contribution was about:

**145 DPS Raptor**  
**140 DPS white melee**

But roughly **114 DPS of that white-melee portion came directly from Windfury extra attacks**.

So when I originally pointed at his roughly **286 DPS melee package** as evidence of the possible weave upside, that was misleading for an Alliance Hunter.

For Haplina the observed high-end Alliance evidence is closer to:

**~98–124 DPS from Raptor Strike**

provided those Raptors replace **nothing** from the ranged cycle.

That's still enormous. It's just not +285 DPS.

---

# The really reassuring result: almost everything else survives

The full dataset is:

**63 Alliance parses / 12 Horde parses**

out of the 75 current top-five entries.

So this was **not** secretly a Horde-biased study.

The following conclusions remain strong:

**20/31/0** remains the dominant parsing build.

**DMF Damage over DMF Agility** remains completely unchanged.

**Nerubian Slavemaker** dominance remains unchanged.

**PvP Multi-Shot gloves** remain unchanged.

Your **pet situation is still a huge weakness**.

Your **Aimed utilization is still too low** on many bosses.

The **KT MC-control assignment** is still directly damaging your parse.

The **Gothik leaderboard padding/trash-overlap finding** is unchanged.

The **Sapphiron raid-speed problem** is unchanged.

The **engineering/Chicken/Dragonling findings** are unchanged.

The **kill-time analysis** remains valid.

---

# Pets barely change after faction normalization

Patchwerk is a nice example.

I previously quoted top-five median pet DPS around:

**174 DPS**

Alliance-only median becomes approximately:

**167 DPS**

Your Snape:

**~78 DPS**

So instead of being at 45% of the all-faction benchmark, you're at about **47% of the Alliance benchmark**.

That doesn't change the conclusion in any meaningful way.

Andrenn is Alliance and his pet does:

**222 DPS**

so high pet output is clearly not an Orc-Command-only phenomenon.

The Orc +5% pet racial helps Smcadogx, yes.

It does not explain why your pet is doing half the output.

---

# Shot cadence also survives surprisingly well

Patchwerk overall top-five Aimed rate was roughly:

**6.01/min**

Alliance-only:

**5.97/min**

Essentially identical.

Auto:

overall ~19.75/min  
Alliance-only ~19.95/min

Again: no meaningful Horde inflation.

Interestingly, on some bosses the Alliance-only special-shot benchmark actually becomes **higher**.

For example your Grobbulus benchmark moves from approximately:

**24–25 / 6–7 / 5–6**

to:

**24–25 / 7–8 / 6–7**

Auto / Aimed / Multi.

So the Horde players weren't artificially making our shot-rate target too aggressive. In that case the opposite was true.

---

# Bosses where I now stop using rank 1 as *your* primary comparator

The overall #1 is Horde on five encounters in this snapshot:

| Boss | Better same-faction reference |
|---|---|
| Patchwerk | **Charies, rank 2 — 1368 DPS** |
| Grobbulus | **Clicker, rank 2 — 1416 DPS** |
| Anub'Rekhan | **Clicker, rank 2 — 1721 DPS** |
| Maexxna | **Clicker, rank 2 — 1568 DPS** |
| Sapphiron | **Folk, rank 3 — 3537 DPS** |

I'll still look at the Horde #1 because it tells us what the encounter ceiling looks like.

But for questions like:

> “What should *Haplina* actually do?”

the primary comparison becomes the best Alliance example.

Sapphiron especially needs this treatment because **3/5 of the current top five are Horde**, and the fights are only ~20 seconds long. A Troll Berserking burst is proportionally much more meaningful in a fight that short.

---

# Revised melee-weaving matrix

This is where faction context has the greatest effect.

**Patchwerk:** **YES**, eventually. Strong repeated Alliance evidence: 3/4 Alliance entries weave heavily.

**Grobbulus:** **NO.** The meaningful top-five weave is Smcadogx Orc+WF. The Alliance top players stay ranged.

**Gluth:** **NO.**

**Thaddius:** **opportunistic only.** Three Alliance parses contain some Raptor activity, but none has 5+ Raptors. Heavy weaving is the Horde case.

**Noth:** mostly no; tiny opportunistic usage.

**Heigan:** opportunistic only. Four Alliance logs show Raptor, but none does 5+; these are little free inserts rather than a weaving strategy.

**Loatheb:** potentially useful — there is an Alliance heavy-weave example — but not dominant.

**Anub:** no.

**Faerlina:** no.

**Maexxna:** no.

**Razuvious:** no.

**Gothik:** technically yes in some Alliance logs, but the encounter's weird trash-overlap strategy makes that a low-priority lesson.

**4HM:** almost entirely no.

**Sapphiron:** no.

**KT:** absolutely no.

So the new mental model becomes:

> **Patchwerk is the actual “learn to melee weave” boss.**

Everywhere else, treat Raptor as an opportunistic free insert unless the logs for that encounter clearly prove otherwise.

That is a much cleaner training plan.

---

## My revised priority order for you

The ordering changes slightly:

1. **20/31/0**
2. **DMF Damage**
3. **fix pet/spec/uptime and move toward the cat setup**
4. **improve Aimed utilization**
5. **Slayer's Crest becomes a particularly important acquisition**
6. **Renataki remains important, but as a boss-specific tool rather than “the Patchwerk trinket”**
7. fix encounter-specific RF timing
8. remove parse-killing utility assignments like KT MC control where possible
9. get your **pure ranged Patchwerk** much closer to Xert
10. **then** learn Alliance-style Raptor-only Patchwerk weaving

That actually makes the progression easier.

You don't need to learn a complicated melee-weaving opener immediately to find hundreds of DPS.

You have an **Alliance, no-WF, zero-weave 1347 DPS Patchwerk log** sitting there telling us exactly that.

The updated v2 pack also contains `top5_gear_with_faction_context.csv`, which now records **Faction, proven race where possible, and actual Windfury extra-attack count** for each of the 75 parses. That's going to be a permanent field in the eventual offline analyzer.

Yes. You were right: the normalized version corrected the analysis, but it also threw away a lot of what made the original useful — especially the fixed sidebar/navigation and richer per-boss presentation. The original clearly had the better raid-use structure. Haplina_Naxx_Parse_Playbook The normalized version had the important factual corrections around Alliance/Horde/Windfury, but it was much more stripped down. Haplina_Naxx_Parse_Playbook_All…

I merged them into **one definitive replacement**:

:chatgpt-content-reference{index="2"}[**Open Haplina Naxx Definitive Playbook**](sandbox:/mnt/data/Haplina_Naxx_Definitive_Playbook/Haplina_Naxx_Definitive_Playbook.html)

Haplina_Naxx_Definitive_Playbook.zip[**Download the complete definitive package**](sandbox:/mnt/data/Haplina_Naxx_Definitive_Playbook.zip)

This one has:

- the **original sidebar/navigation and detailed visual layout**
- all 15 detailed boss pages
- your current DPS / percentile / kill time
- overall #1 **and** Alliance comparator
- Alliance-normalized Auto/Aimed/Multi targets
- corrected melee-weave recommendations
- exact faction per top parse
- race **only when proven by racial casts**
- actual detected **Windfury extra-attack count**
- Raptor + white-melee counts separately
- trinkets / weapons / specs
- pet name, inferred/known family, abilities and DPS
- your complete logged gear for each selected parse
- complete top-five full gear sets in expandable sections
- opener / RF / Refocus / pet / “do not” / raid-assignment advice
- the Gothik/KT/etc forensic conclusions
- persistent “reviewed” checkboxes
- everything still works **completely offline**

I also made the methodology explicit inside the playbook so we stop accidentally turning an inference into a fact. For example:

> **Alliance comparator** means the best Alliance Hunter among the **downloaded overall top five**, not “top-five Alliance” — because we didn't separately query ranks 1–5 filtered to Alliance.

And:

> **WF procs = 0** means we saw zero actual Windfury `extraattacks` events. It does **not** claim that a Shaman never dropped Windfury.

That's the level of precision I want the eventual app to use too.

### Patchwerk is now represented correctly

The page shows all of this together instead of making you mentally reconcile two reports:

**Smcadogx**
- Horde
- Orc proven by Blood Fury
- 9 actual WF extra-attack procs
- 11 Raptors
- 13 white melee
- 1410 DPS

versus the reproducible Alliance examples:

**Charies**
- Alliance
- 9 Raptors
- 0 white melee
- 0 detected WF
- 1368 DPS

**Andrenn**
- Alliance
- 8 Raptors
- 0 white melee
- 0 detected WF
- 1349 DPS

**Xert**
- Alliance
- 0 Raptors
- 0 white melee
- 1347 DPS

**Xal**
- Alliance
- 6 Raptors
- 0 white melee
- 1333 DPS

So the page now tells you:

**Step 1:** pursue the Xert-style pure-ranged baseline.  
**Step 2:** add Charies/Andrenn/Xal-style Raptor-only weaving.  
**Do not:** model your expected gain on Smcadogx's Orc+WF melee package.

It also fixes the Patchwerk Renataki overstatement: **Slayer + Mark is now the Alliance-first recommendation**, with Blackhand + Mark explicitly recognized as proven top-three-capable in Andrenn's log. Renataki remains a strong boss-specific tool rather than being presented as mandatory Patchwerk tech.

This is the one I would keep going forward; the other two can effectively be considered superseded.


Yes. This is very achievable, and we have already accidentally built most of the **hardest proof-of-concept pieces**:

- WCL acquisition
- archived-log access
- event normalization
- deep fight forensics
- pet analysis
- faction/race/Windfury correction
- gear/build comparison
- boss-specific interpretation
- static offline report/playbook generation

The next move is **not** “make the current Hunter script prettier.” It is to turn what we have into a clean engine with class/spec/role plugins, then put an app UI on top.

I wrote the full architecture/spec here:

:chatgpt-content-reference{index="10"}[Download the WCL Forensics app architecture](sandbox:/mnt/data/WCL_Forensics_App_Architecture_v0.1.md)

## The core rule

The app should default to:

> **same game/version + same zone + same partition + same class + same WCL spec/category + same role + same faction**

That means an Alliance character gets **Alliance benchmarks only**.

A Horde character gets **Horde benchmarks only**.

Cross-faction is a deliberate opt-in called something like:

**“Show cross-faction absolute ceiling — may be heavily biased/unreproducible.”**

And even if enabled, it would show:

**Realistic benchmark:** same faction  
**Absolute ceiling:** cross-faction

side by side. It never replaces the realistic recommendation.

That directly prevents the mistake we discovered with Smcadogx.

---

# 1. The user experience

The end product should be almost stupidly simple from the user's perspective.

User pastes:

```text
https://vanilla.warcraftlogs.com/character/id/86583560
```

The app resolves:

```text
Haplina
Ashbringer
Alliance
Hunter
Classic Era
Naxxramas
S0
WCL category: Marksmanship
Actual observed build: 12/33/6
```

Then it might show:

> **Analyze Naxxramas**

with a few optional advanced settings:

```text
Benchmark size:
● Top 5 same-faction deep analysis
● Top 25 same-faction statistical context

Cross-faction comparisons:
○ Off (recommended)
○ Show separately with bias warnings

Include archived logs:
✓ Available through your WCL account

Analysis depth:
● Full forensic
○ Faster summary
```

Then:

```text
Analyzing…
✓ Character
✓ Rankings
✓ Same-faction benchmark set
✓ Reports
✓ Gear
✓ Talents
✓ Events
✓ Pets
✓ Rotation
✓ Boss mechanics
✓ Playbook
```

And the output is essentially our definitive Haplina package.

---

# 2. Faction becomes a first-class data field

WCL exposes the character's faction directly. [Warcraft Logs](https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/character.doc.html?utm_source=chatgpt.com)

So the app knows the subject faction **before it selects benchmark logs**.

For Haplina:

```text
Faction = Alliance
```

The benchmark collector therefore pages through rankings until it has, say:

```text
Top 5 usable Alliance parses
```

not:

```text
whatever happens to be in overall ranks 1–5
```

That's important because the API's `characterRankings` call has class/spec filtering and a general ranking filter, but faction isn't exposed as a simple dedicated GraphQL argument. [Warcraft Logs](https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/encounter.doc.html?utm_source=chatgpt.com)

So initially I would do the robust thing:

```text
fetch rankings
→ inspect faction
→ discard opposite faction
→ continue paging
→ stop when we have 5 same-faction deep-analysis fights
```

No reliance on undocumented faction-filter syntax.

---

# 3. I would actually use more than five logs

This is a lesson from our current analysis.

One top parse can be weird.

Smcadogx:
- Orc
- Windfury
- unusual melee package

Gothik:
- enormous foreign-trash contribution

Sapphiron:
- insane 20-second speedkill environment

So the app should use **two benchmark groups**.

### Ceiling group

**Top 5 same-faction**

These get the complete event-level autopsy.

That's where we answer:

- what exactly did rank 1 do?
- opener
- cooldown timestamps
- weaving
- pets
- item swaps
- etc.

### Robust group

Something like:

**Top 20–30 same-faction**

We don't necessarily need to download every event from all of those.

We use them to establish:

- dominant spec
- talent distribution
- gear dominance
- median pet DPS
- typical kill duration
- typical Aimed/min
- trinket popularity
- RF timing distribution

That means one bizarre rank-1 strategy cannot redefine the whole recommendation.

---

# 4. Class/spec/role classification must be dynamic

You're completely right about Boomkin vs Resto and tanks.

WCL already gives us useful primitives: character rankings support both `specName` and `role`, and Classic WCL's own UI distinguishes categories such as Druid Balance, Feral, Tank and Healer, and Warrior DPS versus Tank. [Warcraft Logs](https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/character.doc.html?utm_source=chatgpt.com)

So we'd build a `CharacterContextResolver`.

It produces something like:

```text
Class: Druid
WCL spec/category: Feral
Role: Tank
Talent build: 11/33/7
Classification confidence: 99%
```

rather than merely:

```text
Druid
```

## Druid example

A Druid could become one of:

```text
Balance DPS
Feral DPS
Tank
Healer
```

If WCL reports:

```text
spec = Feral
role = Tank
```

then we compare against tanks.

Not cat DPS.

If classification is less clear, we verify against event behavior:

- Bear/Dire Bear uptime
- Maul
- Swipe
- incoming boss damage
- threat
- boss target uptime
- tank cooldowns

and assign a confidence.

## Warrior

Same concept.

```text
Warrior DPS
Warrior Tank
```

A tank shouldn't be told:

> your DPS is low compared with rank-1 Fury Warriors.

Its report would instead look at things such as:

- threat
- rage
- Defensive Stance
- boss target time
- mitigation
- incoming damage
- cooldown usage
- tank gear choices

---

# 5. Exact talent build is another layer

This distinction is also important.

For our Hunter analysis WCL essentially gives us the Hunter ranking category, but the actual top players had:

```text
20/31/0
5/31/15
7/31/13
...
```

So the system shouldn't require:

> compare only exact 20/31/0 characters

because that can make the cohort too small.

Instead:

```text
Benchmark identity:
Hunter
Marksmanship/WCL category
DPS
Alliance
```

and then inside that group:

```text
Talent fingerprint:
20/31/0 = 66%
5/31/15 = 15%
...
```

Then the analyzer says:

> 20/31/0 dominates your comparison cohort.

That's much more useful.

---

# 6. Race must be treated carefully

This was another thing we learned.

The documented Character object gives us faction, class, etc., but not a convenient authoritative race field. [Warcraft Logs](https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/character.doc.html?utm_source=chatgpt.com)

So race becomes an **evidence field**.

For example:

```text
Smcadogx
Faction: Horde              [OBSERVED]
Race: Orc                   [CONFIRMED BY BLOOD FURY]
```

A Troll:

```text
Race: Troll                 [CONFIRMED BY BERSERKING]
```

If nothing proves the race:

```text
Race: Unknown
```

Not:

> probably Night Elf.

No guessing.

If `Character.gameData` eventually gives us a reliable race property for that game/version, we can promote that to authoritative. Until then, the racial event is the evidence.

---

# 7. Windfury needs three states, not yes/no

Our current discovery makes this mandatory.

I would store:

```text
CONFIRMED
NOT_OBSERVED
UNKNOWN
```

### CONFIRMED

We saw an actual:

```text
Windfury Totem extraattacks
```

event or another reliable buff event.

### NOT_OBSERVED

We downloaded the relevant data and saw no WF evidence.

This is deliberately **not identical** to saying:

> there was definitely no Windfury totem.

A short fight could theoretically produce no proc.

### UNKNOWN

We don't have enough relevant event data.

The report then renders:

> **Windfury: CONFIRMED — 9 extra attacks**

rather than casually writing “WF: Yes/No.”

That truth model should exist throughout the application.

---

# 8. The application needs an evidence system

This is probably one of the most important architectural decisions.

Every finding should have a provenance level:

```text
OBSERVED
DERIVED
INFERRED
UNKNOWN
```

For example:

### Observed

```text
Faction: Alliance
Raptor Strike casts: 8
Blood Fury cast: yes
Gear: Eye of Nerub
```

### Derived

```text
Aimed Shots/min: 5.02
Pet stopped attacking 7.1 sec before death
Windfury contributed ~114 DPS
```

### Inferred

```text
Pet is probably a Cat based on Claw + Dash ability compatibility
```

### Unknown

```text
Exact pet passive training
```

This would make the app much more trustworthy than a typical log-analysis site.

---

# 9. Acquisition and analysis must be two completely separate systems

This is what allows the app to work offline.

Think:

```text
          ONLINE
             │
             ▼
      Warcraft Logs API
             │
             ▼
        Raw Snapshot
             │
═════════════╪════════════
             │
          OFFLINE
             ▼
        Normalizer
             │
             ▼
         DuckDB
             │
             ▼
       Analysis engine
             │
       ┌─────┴─────┐
       ▼           ▼
 Desktop UI    Static report
                   │
                   ▼
              Playbook ZIP
```

Once the raw logs have been acquired:

**everything else happens offline.**

Exactly like the analysis we've already been doing.

---

# 10. Storage: raw snapshot + DuckDB

I would not analyze giant JSON trees directly forever.

The acquisition layer saves the original WCL payloads unchanged.

Then we normalize them into DuckDB:

```text
characters
zones
encounters
reports
fights
actors
abilities
events
gear
talents
pets
buffs
debuffs
benchmark_sets
derived_features
recommendations
```

Why DuckDB?

Because what we're doing is fundamentally analytics:

```sql
SELECT AVG(pet_dps)
FROM fights
WHERE encounter_id = ...
  AND faction = 'Alliance'
  AND spec = ...
```

or:

```sql
SELECT timestamp, ability
FROM events
WHERE actor_id = ?
ORDER BY timestamp
```

It's perfect for this sort of local workload.

The WCL docs also note that game/static data changes relatively infrequently and can be cached rather than fetched constantly. [Warcraft Logs](https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/gamedata.doc.html?utm_source=chatgpt.com)

---

# 11. API downloads need to become much smarter

Our original exporter was intentionally brute-force because we needed the data.

The proper app should do a two-pass download.

### Pass 1 — cheap metadata

For perhaps the top 25 same-faction candidates:

- ranking
- report/fight IDs
- gear
- talents
- duration
- actors
- pet metadata

Then determine which fights are worth deep analysis.

### Pass 2 — deep events

Full event analysis only for:

```text
subject fight
+ top five same-faction fights
+ optional cross-faction #1
```

That keeps API usage sane.

WCL supports paginated event queries with filters by fight, ability, source, target and event type, so we can request only what a particular analysis needs. [Warcraft Logs](https://sod.warcraftlogs.com/v2-api-docs/warcraft/report.doc.html?utm_source=chatgpt.com)

And the app should continuously inspect:

```text
limitPerHour
pointsSpentThisHour
pointsResetIn
currentRequest
```

from WCL's rate-limit API. [Warcraft Logs](https://www.warcraftlogs.com/v2-api-docs/warcraft/ratelimitdata.doc.html?utm_source=chatgpt.com)

So it could literally show:

```text
Warcraft Logs API

3,215 / 9,000 points used
Reset: 37 min
Estimated analysis cost: ~740
```

instead of discovering the limit by crashing into HTTP 429.

---

# 12. OAuth needs one major redesign

For our personal script it was okay to use a client secret stored locally.

For a publicly distributed desktop application:

**we should not embed a WCL Client Secret in the executable.**

WCL officially supports **PKCE** specifically for applications that cannot securely hold a secret. [Warcraft Logs](https://www.warcraftlogs.com/api/docs?utm_source=chatgpt.com)

So the desktop flow becomes:

```text
Connect Warcraft Logs
        │
        ▼
system browser
        │
        ▼
WCL login/authorize
        │
        ▼
localhost callback
        │
        ▼
PKCE verification
        │
        ▼
token stored in Windows Credential Manager / Keychain
```

No secret in the binary.

And an unsubscribed user can still use the app — they just won't get archive access their account isn't entitled to.

Gold/archive capability is detected rather than hardcoded. Gold currently includes Logs Archive and an increased API limit, but the app shouldn't depend on a specific plan name because those offerings can change. [Warcraft Logs](https://www.warcraftlogs.com/subscribe?utm_source=chatgpt.com)

---

# 13. The analyzer itself should use plugins

Something like:

```python
class AnalyzerPlugin:
    classify_build()
    extract_features()
    analyze_rotation()
    analyze_resources()
    analyze_cooldowns()
    analyze_gear()
    analyze_external_buffs()
    analyze_pets()
    make_recommendations()
```

Then:

```text
classic_era/
  hunter/
  warrior/
  druid/
  rogue/
  mage/
  warlock/
  priest/
  paladin/
  shaman/
```

Plus encounter rules:

```text
classic_era/
  naxxramas/
    patchwerk.py
    grobbulus.py
    ...
    kelthuzad.py
```

That split is essential.

Because:

> “Hunter rotation analysis”

and:

> “Gothik has foreign trash being counted”

are two completely different types of knowledge.

---

# 14. Hunter is our first plugin

We already know what it contains:

```text
Auto Shot cycle
Aimed Shot opportunities
Multi-Shot
Auto clipping
Quick Shots
Rapid Fire
Renataki / Refocus
FD swaps
Raptor weaving
pet skills
pet uptime
pet deaths
Hunter's Mark
engineering
gear
trinkets
race
Windfury
target integrity
```

Most of this code already exists in some form from our current analysis.

We just need to turn it from:

> scripts I used to investigate Haplina

into:

> functions that accept any Hunter fight.

---

# 15. Encounter plugins solve cases like Gothik

This is another critical point.

Without encounter knowledge, the app would say:

> Gothik rank 1 = 444 DPS  
> You = 163 DPS  
> Get good.

Our analyzer knows better.

A Naxx/Gothik plugin can define:

```text
native targets:
- Gothik
- Unrelenting Trainee
- Unrelenting Deathknight
- Unrelenting Rider
- spectral variants
...

foreign targets:
anything else
```

Then:

```text
Raw leaderboard DPS: 444

Native encounter DPS: 230

Foreign/padding DPS: 214
48.2%
```

Now the playbook can say:

> The ranking ceiling requires reproducing a specific trash-overlap strategy.

That distinction is exactly what makes this application special.

---

# 16. KT is another perfect example

Generic analyzer:

```text
Large 39-second Aimed gap
```

Hunter analyzer:

```text
Several potential special-shot windows unused
```

KT encounter analyzer:

```text
Freezing Trap
Scatter Shot on teammate
Reckless Charge on teammate
```

Conclusion:

> **Raid assignment caused the rotational loss.**

Recommendation:

> If this is a dedicated parse pull, move MC control away from the parsing Hunter.

That's a far better diagnosis than:

> press Aimed more.

---

# 17. Every recommendation should be structured data

Not generated freeform prose first.

Something like:

```json
{
  "boss": "Patchwerk",
  "category": "rotation",
  "severity": "high",
  "confidence": 0.96,
  "controllability": "player",
  "finding": "Aimed usage below same-faction elite cadence",
  "benchmark": {
    "faction": "Alliance",
    "sample": 20
  },
  "evidence": [
    ...
  ],
  "recommendation": "..."
}
```

Then the UI can sort:

```text
Highest impact
Highest confidence
Player controllable
Raid changes
Gear upgrades
```

And every recommendation can have a button:

> **Show evidence**

That's where it becomes really powerful.

---

# 18. We should not pretend to know exact DPS gains

This is something I'd deliberately improve over our current manual analysis.

We can safely say:

> Elite Alliance pets median 167 DPS; yours was 78.

We cannot automatically say:

> Changing your pet will give exactly +89 DPS.

Those are correlated values from different fights.

So recommendations should use:

```text
Observed gap: ~89 DPS
Likely impact: High
Confidence: High
```

until we have a proper counterfactual simulator.

That keeps it truthful.

---

# 19. UI technology

For the fastest path to something excellent:

### Backend / analysis

**Python**

because all our successful work is already Python.

I'd use:

```text
FastAPI
Pydantic
httpx
Polars
DuckDB
Jinja2
pytest
keyring
```

### Frontend

```text
React
TypeScript
Vite
```

### Desktop wrapper

**Tauri**

So users get an actual:

```text
WCLForensics.exe
```

rather than needing Python installed.

The Tauri UI talks locally to the bundled Python analyzer.

Later, if something genuinely becomes performance-critical, we can rewrite that piece in Rust.

Do **not** rewrite the whole working analysis engine in Rust/TypeScript on day one.

---

# 20. The static playbook remains a first-class product

The app UI isn't the only result.

Every analysis should still be exportable as:

```text
Haplina_Naxx_Analysis.zip

report.html
playbook.html
analysis.json
manifest.json

tables/
  boss_summary.csv
  gear.csv
  pet.csv
  casts.csv
  cooldowns.csv
  benchmark_context.csv
```

The HTML files remain completely offline and self-contained.

So someone can send their analysis to a guildmate without them even installing the application.

---

# 21. Our Haplina dataset becomes the automated test suite

This is incredibly valuable.

We now have known expected outputs.

For example, our tests can assert:

```text
top-five rows = 75
Alliance = 63
Horde = 12
```

Patchwerk:

```text
Smcadogx:
  Horde
  Blood Fury => Orc
  WF procs detected

Charies:
  Alliance
  9 Raptors

Andrenn:
  Alliance
  8 Raptors

Xert:
  Alliance
  0 Raptors
```

Grobbulus:

```text
Snape death ~= 25.7 sec
```

Gothik:

```text
foreign-trash anomaly detected
```

KT:

```text
MC-control actions detected
```

Every time we change the analyzer:

```text
pytest
```

If those answers suddenly change unexpectedly, the build fails.

This prevents us from silently reintroducing exactly the sort of faction-bias bug we just caught.

---

# 22. I would build it in this order

Not GUI first.

The first proper milestone should be a command like:

```powershell
wcl-forensics analyze "https://vanilla.warcraftlogs.com/character/id/86583560"
```

and at the end:

```text
Analysis complete.

Character: Haplina
Faction: Alliance
Class: Hunter
Role: DPS
Zone: Naxxramas
Partition: S0

Benchmarks:
  5 same-faction deep parses / boss
  25 same-faction metadata parses / boss

Generated:
  Haplina_Naxx_Definitive_Playbook.html
  Haplina_Naxx_Analysis.zip
```

**If we can reproduce our current definitive Haplina report from nothing except that URL, automatically, the core application works.**

Then build the nice desktop interface around it.

---

# The development milestones

1. **Freeze Haplina as our golden fixture.**
2. Turn the v6 exporter into a proper reusable WCL client.
3. Replace desktop client-secret auth with **PKCE**.
4. Build `CharacterContextResolver`.
5. Build **same-faction BenchmarkSelector**.
6. Make it paginate until it actually has five same-faction candidates.
7. Add raw cache + DuckDB normalization.
8. Refactor our Hunter analysis into `HunterClassicEraAnalyzer`.
9. Refactor Naxx logic into encounter plugins.
10. Produce one versioned `analysis.json`.
11. Generate the definitive HTML/playbook solely from that JSON.
12. Make `WCL URL → final ZIP` work from the CLI.
13. Wrap that in React/Tauri.
14. Then tackle **Druid**, specifically because it forces us to solve the Feral-DPS-vs-Tank classification problem correctly.
15. Then Warrior DPS/Tank.
16. Then expand classes/raids.

And I would **not** start by trying to support every class, every raid and every WoW version. That would bury us.

The correct first vertical slice is:

> **Classic Era → Naxxramas → Hunter → any faction → automatic definitive package**

because we already have the expected answer.

Once that produces Haplina's current report automatically, we know the architecture is sound.

Then Druid/Warrior prove that the abstraction actually works.

The architecture document I generated goes further into the proposed repo structure, database schema, analyzer-plugin interface and exact milestone definition:

:chatgpt-content-reference{index="11"}[**WCL Forensics — Product & Architecture Specification v0.1**](sandbox:/mnt/data/WCL_Forensics_App_Architecture_v0.1.md)

The next concrete step I would take is **Milestone A: create the headless application/repository and get `WCL URL → Haplina definitive package` running end-to-end**. After that, the desktop UI is relatively straightforward compared with the analysis engine.