# Haplina Naxx Parse Playbook — Alliance-Normalized v2

## What changed

The original forensic conclusions were built from the current overall top five. Haplina is Alliance, so v2 adds faction normalization and stops treating Horde-only racial/Windfury advantages as directly reproducible execution.

Across the 75 overall top-five parses, **63 are Alliance and 12 Horde**. Among 18 parse instances with any Raptor Strike, **15 are Alliance and only 3 Horde**; the three Horde weaving instances are all **Smcadogx**, the Orc whose logs show actual Windfury extra-attack events. Therefore melee weaving remains real for Alliance, but its expected magnitude changes.

### Corrected Patchwerk interpretation

- Smcadogx (#1) is Orc + Windfury and is **not** the correct Haplina melee benchmark.
- Charies (#2), Andrenn (#3) and Xal (#5) are Alliance/no-WF and use **9 / 8 / 6 Raptors** respectively.
- Those Alliance logs have effectively **no ordinary white-melee contribution**; they are Raptor-in/Raptor-out weaves.
- The practical observed Alliance Raptor contribution is roughly **~98–124 DPS**, not Smcadogx's ~286-DPS total melee package.
- Xert (#4) is Alliance, pure ranged, and still does **1347 DPS**, so weaving remains a late optimization rather than the first fix.

### What does NOT change

20/31/0, DMF Damage, Nerubian Slavemaker, PvP gloves, pet management, higher Aimed utilization, engineering, kill-time analysis, KT utility-duty diagnosis, Gothik padding diagnosis, and the need for better pet uptime all remain supported. Renataki also remains a high-value **boss-specific** item, but it should no longer be presented as the default Patchwerk Alliance trinket. Most of the source dataset is Alliance, so those conclusions were not Horde artifacts.

### What does change

- **Patchwerk:** keep weaving as an advanced goal, but benchmark Alliance Raptor-only weaving.
- **Grobbulus:** downgrade weaving to **NO** for Haplina; the meaningful weaving example in the top five is Orc+WF.
- **Thaddius:** downgrade from 'high-ceiling weave' to **opportunistic only**; Alliance leaders show small Raptor use, not the heavy Horde pattern.
- **Pet benchmark:** use Alliance-only medians. Patchwerk becomes about **167 DPS** instead of ~174; Haplina's ~78 DPS is still less than half the same-faction benchmark.
- **Shot-count benchmark:** use Alliance-only median rates. These are usually almost identical to the overall top-five rates; on some mixed-faction bosses Alliance actually has the higher Aimed rate.
- **Leaderboard comparisons:** on Patchwerk, Grobbulus, Anub'Rekhan, Maexxna and Sapphiron, the overall #1 is Horde. v2 shows the best Alliance hunter inside the current overall top five separately.

## Boss-by-boss Alliance normalization

|Boss|A/H in overall top 5|Best Alliance in current top 5|Alliance target Auto/Aimed/Multi|Alliance Raptor users|5+ Raptor users|
|---|---:|---|---|---:|---:|
|Patchwerk|4/1|#2 Charies (1368 DPS)|27–28 / 8–9 / 7–8|3|3|
|Grobbulus|3/2|#2 Clicker (1416 DPS)|24–25 / 7–8 / 6–7|0|0|
|Gluth|5/0|#1 Clicker (1434 DPS)|21–22 / 5–6 / 5–6|0|0|
|Thaddius|4/1|#1 Xert (2044 DPS)|35–36 / 10–11 / 9–10|3|0|
|Noth the Plaguebringer|5/0|#1 Clicker (1523 DPS)|19–20 / 5–6 / 4–5|1|0|
|Heigan the Unclean|5/0|#1 Clicker (1371 DPS)|21–22 / 5–6 / 5–6|4|0|
|Loatheb|5/0|#1 Tagx (1565 DPS)|46–47 / 13–14 / 11–12|1|1|
|Anub'Rekhan|3/2|#2 Clicker (1721 DPS)|15–16 / 4–5 / 4–5|0|0|
|Grand Widow Faerlina|4/1|#1 Andrenn (1547 DPS)|17–18 / 4–5 / 4–5|0|0|
|Maexxna|3/2|#2 Clicker (1568 DPS)|15–16 / 5–6 / 4–5|0|0|
|Instructor Razuvious|5/0|#1 Clicker (1347 DPS)|16–17 / 4–5 / 3–4|0|0|
|Gothik the Harvester|5/0|#1 Andrenn (444 DPS)|56–57 / 11–12 / 19–20|2|1|
|The Four Horsemen|5/0|#1 Folkx (826 DPS)|42–43 / 13–14 / 12–13|1|0|
|Sapphiron|2/3|#3 Folk (3536 DPS)|53–54 / 13–14 / 16–17|0|0|
|Kel'Thuzad|5/0|#1 Snipex (1321 DPS)|64–65 / 19–20 / 13–14|0|0|

## Revised action plan

### Patchwerk

- **Same-faction benchmark:** #2 Charies, 1368 DPS; Alliance sample inside overall top five: 4/5.
- **Shot benchmark at your current kill:** 27–28 / 8–9 / 7–8 Auto/Aimed/Multi.
- **Weave:** YES — advanced Alliance optimization, but use the Alliance model. 3/4 Alliance hunters inside the current overall top five weave heavily (Charies 9, Andrenn 8, Xal 6 Raptors), all without Windfury. Benchmark Raptor-only weaving, not Smcadogx's Orc+WF white-melee package.
- **Weapons:** Alliance advanced weave: Eye of Nerub + Nerubian Slavemaker. Pure-ranged baseline: Kingsfall + Harbinger + Slavemaker. Do not use Smcadogx's Dark Edge/Orc/Windfury package as the Haplina benchmark.
- **Trinkets:** Alliance-first benchmark: Slayer's Crest + Mark of the Champion. Andrenn proves Blackhand + Mark can also reach the current top 3; Charies uses Jom Gabbar + Badge of the Swarmguard. None of the four Alliance hunters inside the current overall top five uses Renataki on Patchwerk, so Refocus is optional tech here rather than the primary Patchwerk recommendation.
- **Pet:** Cat. Keep it in until boss death; Snape stopped ~7.1s early. Target ~150–200+ pet DPS rather than ~78.
- **Opener:** Alliance baseline: establish the clean ranged cycle first (Auto/Aimed/Multi + early RF), then insert Raptor only in a genuinely free weapon window. Do not make the opener depend on Refocus; none of the four Alliance Patchwerk hunters inside the current overall top five uses Renataki.
- **Rapid Fire:** Pull / first cycle. Rank 1 used RF at 4.20s; your 6.67s timing is already reasonable.
- **Do not:** Do not target Smcadogx's ~286 DPS melee package. About 114 DPS of his white-melee component was directly Windfury-generated. For Haplina, judge weaving by net Raptor gain with zero lost ranged cycles.

### Grobbulus

- **Same-faction benchmark:** #2 Clicker, 1416 DPS; Alliance sample inside overall top five: 3/5.
- **Shot benchmark at your current kill:** 24–25 / 7–8 / 6–7 Auto/Aimed/Multi.
- **Weave:** NO for Haplina. The only meaningful current top-five weaver is Smcadogx, an Orc receiving Windfury. None of the three Alliance hunters inside the top five weave.
- **Weapons:** Kingsfall + Harbinger + Nerubian Slavemaker. Stay ranged as Alliance.
- **Trinkets:** Slayer + Mark; or Renataki + Mark. Current fallback: Blackhand + Mark.
- **Pet:** Cat. Manual recall before poison/cloud danger, then resend. Snape died at 25.7s in your best parse.
- **Opener:** RF → Auto → Aimed → Auto → Multi. Your old opener delayed Aimed to 11.0s; aim for ~4–6s.
- **Rapid Fire:** Early. Rank 1 2.68s; top-five median ~9.2s. Your selected parse used none.
- **Do not:** Do not let the pet stand in Grobbulus Cloud. Do not lead Auto→Multi and then sit on Aimed for ~8s. Do not import the Orc+Windfury weave into the Alliance plan.

### Gluth

- **Same-faction benchmark:** #1 Clicker, 1434 DPS; Alliance sample inside overall top five: 5/5.
- **Shot benchmark at your current kill:** 21–22 / 5–6 / 5–6 Auto/Aimed/Multi.
- **Weave:** NO — 0/5 top parses weave.
- **Weapons:** Kingsfall + Harbinger + Slavemaker.
- **Trinkets:** Mark + Slayer/Jom; Renataki + Mark is also proven. Current fallback: Blackhand + Mark.
- **Pet:** Cat, present from pull. Your selected best has no Hunter pet actor at all.
- **Opener:** Auto + RF → Aimed → Auto → Multi. If Renataki: reset after the first pair and spend the second pair immediately.
- **Rapid Fire:** Early (~3–12s in top logs). Your selected parse used none.
- **Do not:** Do not raid this boss petless on a parse attempt. Do not hold RF.

### Thaddius

- **Same-faction benchmark:** #1 Xert, 2044 DPS; Alliance sample inside overall top five: 4/5.
- **Shot benchmark at your current kill:** 35–36 / 10–11 / 9–10 Auto/Aimed/Multi.
- **Weave:** OPPORTUNISTIC ONLY for Alliance. 3/4 Alliance hunters inside the top five show some Raptor use, but none reach 5+ Raptors; the heavy weaving example is Smcadogx with Orc+Windfury. Do not build the fight around weaving.
- **Weapons:** Default Alliance set: Kingsfall + Harbinger + Slavemaker. Eye of Nerub only if you are already executing opportunistic Raptor inserts without ranged loss.
- **Trinkets:** Slayer + Mark; Renataki + Mark also works. Current fallback: Blackhand + Mark.
- **Pet:** Cat. Your pet survives but is ~half the top median output.
- **Opener:** On the add phase: Auto → Aimed → Auto → Multi. Preserve clean cycles through the transition. On Thaddius activation, re-establish Auto/Aimed/Multi immediately.
- **Rapid Fire:** HOLD. Top-five RF timing clusters around ~82s. Use it on the real Thaddius/polarity damage window, not Feugen/Stalagg.
- **Do not:** Do not burn RF on the opening add phase. Do not weave during polarity movement if it jeopardizes ranged uptime. Do not treat Smcadogx's heavy Orc+WF weaving as the Alliance target.

### Noth the Plaguebringer

- **Same-faction benchmark:** #1 Clicker, 1523 DPS; Alliance sample inside overall top five: 5/5.
- **Shot benchmark at your current kill:** 19–20 / 5–6 / 4–5 Auto/Aimed/Multi.
- **Weave:** Mostly NO — 1/5 top parses weave.
- **Weapons:** Kingsfall + Harbinger + Slavemaker.
- **Trinkets:** Renataki + Mark or Slayer + Mark. Current fallback: Blackhand + Mark.
- **Pet:** Cat; your pet ~73 DPS vs ~161 top median.
- **Opener:** Pre-cast Aimed so it lands just after pull → Auto → Multi → continue Auto/Aimed/Multi. Renataki can reset the first spent pair.
- **Rapid Fire:** Early enough that the entire haste window lands before a teleport. Median ~6.3s.
- **Do not:** Do not hold RF until a phase change. Do not let pet uptime trail the boss.

### Heigan the Unclean

- **Same-faction benchmark:** #1 Clicker, 1371 DPS; Alliance sample inside overall top five: 5/5.
- **Shot benchmark at your current kill:** 21–22 / 5–6 / 5–6 Auto/Aimed/Multi.
- **Weave:** Only opportunistic. 4/5 show Raptor, but mostly a single weave — not a reason to rebuild the fight around melee.
- **Weapons:** Kingsfall + Harbinger + Slavemaker.
- **Trinkets:** Slayer + Mark. Current fallback: Blackhand + Mark.
- **Pet:** Cat. Your selected parse has no Hunter pet actor.
- **Opener:** RF near first Auto → Aimed → Auto → Multi. Your old first Aimed was ~14.5s.
- **Rapid Fire:** ~6–10s is a good target; top median ~9.9s. You used it at 18.1s.
- **Do not:** Do not arrive at Heigan petless. Do not postpone the first Aimed/RF while standing in a stable ranged position.

### Loatheb

- **Same-faction benchmark:** #1 Tagx, 1565 DPS; Alliance sample inside overall top five: 5/5.
- **Shot benchmark at your current kill:** 46–47 / 13–14 / 11–12 Auto/Aimed/Multi.
- **Weave:** NO by default. Only 1/5 top parses weaves.
- **Weapons:** Kingsfall + Harbinger + Slavemaker.
- **Trinkets:** Slayer + Mark is the dominant pattern. Current fallback: Blackhand + Mark.
- **Pet:** Cat; your ~76 DPS vs ~191 top median is a large gap.
- **Opener:** Auto → Aimed → Auto → Multi; maintain cycle while waiting for the planned spore burst.
- **Rapid Fire:** HOLD for the first useful spore/crit burst. Top leaders commonly trigger ~26–40s; you used 72.6s.
- **Do not:** Do not use RF late unless your raid's spore assignment explicitly demands it. Do not let spore movement cost Autos.

### Anub'Rekhan

- **Same-faction benchmark:** #2 Clicker, 1721 DPS; Alliance sample inside overall top five: 3/5.
- **Shot benchmark at your current kill:** 15–16 / 4–5 / 4–5 Auto/Aimed/Multi.
- **Weave:** NO — 0/5 top parses weave.
- **Weapons:** Kingsfall + Harbinger + Slavemaker (5/5 top main-hand Kingsfall).
- **Trinkets:** Renataki + Slayer/Mark or Slayer + Mark. Current fallback: Blackhand + Mark.
- **Pet:** Cat. Your selected best has no Hunter pet actor.
- **Opener:** RF early → Auto → Aimed → Auto → Multi → optional Refocus after both specials.
- **Rapid Fire:** Very early. Top median ~4.0s; your 9.34s is usable but later.
- **Do not:** Do not parse this boss petless. Do not delay Aimed to ~8s if you can fit it in the opening cycle.

### Grand Widow Faerlina

- **Same-faction benchmark:** #1 Andrenn, 1547 DPS; Alliance sample inside overall top five: 4/5.
- **Shot benchmark at your current kill:** 17–18 / 4–5 / 4–5 Auto/Aimed/Multi.
- **Weave:** NO — 0/5 top parses weave.
- **Weapons:** Kingsfall + Harbinger is the safe stat-stick set; Eye of Nerub appears 3/5 but isn't being used for Raptor weaving.
- **Trinkets:** NO Mark. Ideal: Renataki + Slayer/Jom. Current no-loot fallback: Jom Gabbar + Blackhand rather than Royal Seal + Blackhand.
- **Pet:** Cat; your pet ends ~5.4s early and outputs ~59 DPS vs much stronger top cats.
- **Opener:** Pre-cast Aimed to land ~2–3s → Auto → Multi → RF / continue cycle. With Renataki, reset after both specials are spent.
- **Rapid Fire:** Your ~10.8s is acceptable; top median ~13.2s. The real loss was first Aimed at 16.2s.
- **Do not:** Do not equip Mark of the Champion here. Do not allow the first real Aimed to occur halfway through a 40s kill.

### Maexxna

- **Same-faction benchmark:** #2 Clicker, 1568 DPS; Alliance sample inside overall top five: 3/5.
- **Shot benchmark at your current kill:** 15–16 / 5–6 / 4–5 Auto/Aimed/Multi.
- **Weave:** NO — 0/5 top parses weave.
- **Weapons:** Kingsfall + Harbinger + Slavemaker.
- **Trinkets:** NO Mark. Ideal: Renataki + Slayer/Jom. Your existing Jom + Blackhand is a valid fallback.
- **Pet:** Cat; yours survives but ~61 DPS is well below top output.
- **Opener:** Auto → Aimed → Multi quickly; RF ~5–9s; use Renataki only after both Aimed and Multi are spent, then immediately spend the reset.
- **Rapid Fire:** Your 9.04s is fine; top median ~5.9s.
- **Do not:** Do not melee weave. Do not save Refocus so late that the second pair cannot finish before death/web disruption.

### Instructor Razuvious

- **Same-faction benchmark:** #1 Clicker, 1347 DPS; Alliance sample inside overall top five: 5/5.
- **Shot benchmark at your current kill:** 16–17 / 4–5 / 3–4 Auto/Aimed/Multi.
- **Weave:** NO — 0/5 top parses weave.
- **Weapons:** Kingsfall + Harbinger + Slavemaker.
- **Trinkets:** Slayer + Mark; Renataki + Mark also appears. Current fallback: Blackhand + Mark.
- **Pet:** Cat; yours ~41 DPS vs ~151 top median.
- **Opener:** Auto → Aimed → Auto → Multi; RF in first ~7–12s.
- **Rapid Fire:** Your 10.34s is in the correct window.
- **Do not:** Do not give away Autos to unnecessary movement. Do not let pet control be an afterthought.

### Gothik the Harvester

- **Same-faction benchmark:** #1 Andrenn, 444 DPS; Alliance sample inside overall top five: 5/5.
- **Shot benchmark at your current kill:** 56–57 / 11–12 / 19–20 Auto/Aimed/Multi.
- **Weave:** Conditional. 2/5 top parses weave; Eye of Nerub appears 4/5.
- **Weapons:** Leaderboard-meta: Eye of Nerub is common. Clean ranged alternative: Kingsfall + Harbinger. Ranged weapon remains Slavemaker where available.
- **Trinkets:** Mark is valid on the undead encounter targets. Current clean fallback: Mark + Blackhand/Seal. Renataki appears but isn't the primary differentiator.
- **Pet:** Cat with careful recall. Snape died at ~152.7s to wave AoE.
- **Opener:** For a leaderboard-style pull: Auto/Multi immediately into dense targets, Aimed in every real window, Dynamite in empty windows. Do not save everything for Gothik himself.
- **Rapid Fire:** Use during a dense wave/trash damage window (~20–25s in top logs), NOT ~293s.
- **Do not:** Do not compare your displayed DPS to leaderboard DPS without reproducing the extra-trash overlap. Do not go 282s between Aimeds.

### The Four Horsemen

- **Same-faction benchmark:** #1 Folkx, 826 DPS; Alliance sample inside overall top five: 5/5.
- **Shot benchmark at your current kill:** 42–43 / 13–14 / 12–13 Auto/Aimed/Multi.
- **Weave:** NO by default — 1/5 top parses has a Raptor.
- **Weapons:** Kingsfall + Harbinger + Slavemaker.
- **Trinkets:** Mark is 5/5. Ideal Slayer + Mark; Renataki + Mark also proven. Current fallback: Blackhand + Mark.
- **Pet:** Cat; yours stopped attacking ~48s before the fight ended without dying.
- **Opener:** RF → Auto → Aimed → Multi, then move immediately after Autos and preserve Aimed windows during horseman swaps.
- **Rapid Fire:** Pull. Rank 1 2.63s; top median ~7.1s. Your 120.4s RF is far too late.
- **Do not:** Do not save RF for the tail. Do not leave the pet parked/inactive for the final third.

### Sapphiron

- **Same-faction benchmark:** #3 Folk, 3536 DPS; Alliance sample inside overall top five: 2/5.
- **Shot benchmark at your current kill:** 53–54 / 13–14 / 16–17 Auto/Aimed/Multi.
- **Weave:** NO — 0/5 top parses weave.
- **Weapons:** Kingsfall + Harbinger + Slavemaker.
- **Trinkets:** Renataki + Mark is common in the extreme speedkill logs; Slayer + Mark is the longer-fight alternative. Current fallback: Blackhand + Mark.
- **Pet:** Cat with Naxx/Sapph survival training. Your best selected parse has no pet. For a survival profile: Great Stamina 10 + Claw 8 + Dash 3 + Frost Resistance 3 is a practical 300-TP-safe shape.
- **Opener:** RF at pull → Auto → Aimed → Multi → Refocus → second Multi/Aimed pair. The absolute top fight is over before your old RF timing.
- **Rapid Fire:** Pull (~1.6–5s). Your old 24.6s is already later than the entire rank-1 kill.
- **Do not:** Do not chase current rank-1 DPS with a 116s kill and expect personal execution to bridge it. Do not run petless.

### Kel'Thuzad

- **Same-faction benchmark:** #1 Snipex, 1321 DPS; Alliance sample inside overall top five: 5/5.
- **Shot benchmark at your current kill:** 64–65 / 19–20 / 13–14 Auto/Aimed/Multi.
- **Weave:** NO — 0/5 top parses weave.
- **Weapons:** Kingsfall + Harbinger + Slavemaker. Eye is acceptable as a stat stick but do not weave.
- **Trinkets:** Mark is 4/5. Ideal: Slayer + Mark, Kiss + Mark, or Renataki + Mark. Immediate no-loot fix: replace Burrower's Shell with Mark and pair it with Blackhand/Jom.
- **Pet:** Cat; your ~60 DPS vs ~135 top median leaves substantial damage.
- **Opener:** Auto → Aimed → Auto → Multi; RF ~6–9s. Keep shooting through the boss phase instead of spending the central window on MC-control duties.
- **Rapid Fire:** Early. Top median ~8.7s; your 13.85s is slightly late but not the main problem.
- **Do not:** Do not be the parse Hunter AND the primary trap/Scatter/rocket-helmet MC controller. Do not wear Burrower's Shell on a rank attempt.

