# AQ40 Hunter ranking investigation

2026-10-18. These are candidate arithmetic explanations, not enabled ranking
policies or proof of a universal Era rule. Inputs are the immutable
`aq40-hunter-raid-context` archive, its independent actor/pet registers and the
exact selected native API scores/durations. Preserve residuals and acquire
independent samples before policy activation. A name or Fresh guide cannot
establish ranked eligibility.

| Selected source | Candidate numerator observation |
|---|---|
| Ouro, Temison, `27PcXw8mQZr3NMGg/44` | 110238 owner +54 owned unit damage over115.137s matches957.92. The owned unit's trained-pet category remains unknown. |
| Skeram, Kasvo, `JYGzpAj2d7bvkwy6/4` | Owner+known pet68201 over69.008s matches988.306. Controlled-player hits fall inside observed785 windows. |
| Sartura, Temison, `Jw7RDb43XKALngca/18` | Explicitly empty pet roster;51842 over50.597s matches1024.61. Royal Guard15984 damage15405 is included. |
| Huhuran, Temison, `Jw7RDb43XKALngca/28` | Owner+known pet55912 over47.665s matches1173.02. |
| Fankriss, Temison, `QhKBGtanZckAyDbL/20` | 49445 raw minus955 on Hatchling15962 leaves48490 over38.872s, matching1247.43. One parse cannot certify the exclusion. |
| Royalty, Temison, `WQDaF9kpYbBPLCKM/16` | 79727 raw minus3120 on Yauj Brood15621 leaves76607 over76.131s, matching1006.25. Does not establish pre-heal boss-reset eligibility. |
| Twins, Temison, `WQDaF9kpYbBPLCKM/38` | 138601 owner+known pet over193.579s matches715.992, including3331 on Scorpion15317. Battle Chicken159 has no owner; agreement does not prove complete guardian credit. |
| C'Thun, Temison, `k6zpdLvaqJ4xXPCQ/56` | 121944 raw minus11068 on Giant Claw15728 leaves110876 over223.955s, matching495.082. Eye15589, body15727 and other named tentacle types contribute. One parse cannot establish target rules. |
| Viscidus, Temison, `tcJdbDx3rMGTzpLX/26` | 50509 raw minus509 self-inflicted Sapper13241 damage leaves50000 over101.893s, matching490.711. Glob15667 damage12618 is included. |
| Skeram, Anavarlol, `cb7dmjfDntT189FG/3` | 57549 owner+known pet over52.743s matches1091.12. |
| Skeram, Scttrkuntz, `gnJcDvZABFtTX2N/4` | 52152 raw minus401 to Bujak18 leaves51751 over54.966s, matching941.509. Hit48643ms occurs219ms after785 removal48424ms; the observed application is39564ms. |
| Skeram, Temison, `WQDaF9kpYbBPLCKM/4` | 62704 damage amounts +108 damage-event absorption over66.616s matches942.897. Multi-Shot25294 hits Premixxzug37 at40160ms with43 absorbed and Srapurple25 at51784ms with65 absorbed; both recipients are inside observed785 windows. |

For Temison's Skeram fight,785 apply/remove pairs are Binsto32
13423–25873ms, Premixxzug37 37695–43660ms and Srapurple25
45761–65761ms. Kasvo's captured controlled-player hits also fall inside their
recipients' observed785 windows. These Era examples contradict blindly importing
Fresh's blanket controlled-player exclusion. The later Scttrkuntz hit provides
a useful boundary counterexample; it does not make initial unknown state known.

Damage-event `absorbed` is distinct from credited shield-healing events of
type`absorbed`. The captured Fankriss955 damage has separately recorded1500
overkill; subtracting overkill again from the amount would be wrong. The
[WCL expression definitions](https://classic.warcraftlogs.com/help/pins)
distinguish raw and effective damage, but do not by themselves establish the
API amount field or ranked numerator. Verify each with native observations.

Next: additional independent selected actor/pet captures, exact API score
bindings, control-window boundary facts and mutations, target-specific negative
cases, and unknown guardian/reset/opportunity handling. No ranking dimension
is closed by this research.
