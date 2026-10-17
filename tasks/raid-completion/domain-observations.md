# Domain observations awaiting encounter implementation

Research date: 2026-10-17. These findings constrain implementation; they do not
close boss dossiers, role adjudication or any completion cell.

## Observed public report metadata

Public MC ZzYr1NR6LpHkyjTc contains all ten bosses; public AQ40
tcJdbDx3rMGTzpLX contains all nine. Public BWL cg1mfw64BzAhNd97 contains seven
canonical fight entries using the combined dragon variant, not separate Ebonroc
and Flamegor fights. These inventories are retained in
research/raid-report-inventory.json. Candidate pools/metadata cannot certify
actor coverage. Original report dates/revisions differ from retrieval dates.

- MC Lucifron has Lucifron 12118, two Protectors 12119 and ten Core Hounds 11671
  listed in the sampled fight. A fight NPC list includes pulled trash; never
  automatically label every listed NPC native or eligible for ranked damage.
- Garr lists eight Firesworn 12099 plus two Ancient Core Hounds 11673; Golemagg
  lists Core Ragers 11672 and a Firelord 11668. Classify the foreign/context
  targets independently before judging target selection or duty.
- BWL combined fight 19 is encounter 50631, originalEncounterID 615 and display
  name Flamegor, with both NPCs 14601 and 11981. Match numeric encounter identity,
  not display name or the individual original encounter. Never manufacture
  combined rankings by adding the two individual scores/durations.
- AQ Skeram lists original 15263 and six instances of 176525 under the same
  displayed name. Separate clone identity must be researched; names do not
  identify the original boss. The raw observation is primary evidence for this
  report; a third-party emulator issue mentioning 176525 is corroboration only,
  not authority for modern Era phase/scoring behavior.
- Viscidus lists 15299, Glob 15667 and Toxic Slime 15925. DPS alone cannot assess
  frost/frozen/shatter participation. Do not infer transitions from static hit
  thresholds or globally assign hit-based opportunity from a damage-only view.
- Twin Emperors lists 15275/15276, Scarabs 15316, Scorpions 15317 and trigger
  15695. C'Thun lists Eye 15589/body 15727 plus distinct tentacle types. Class
  target eligibility cannot be reduced to a single same-name actor.

## Real action and measurement counterexamples

The nine raw archives and 54 independent actor cases live under
tests/golden/raids. Public visibility, immutable revisions, member/stream hashes,
ownership and independent cast/amount/timing checks are retained there.

- Lucifron Holy subject: heal amount 48,161, absorption-event amount 6,159,
  duration 38.851 seconds; their sum yields 1398.1622 versus WCL 1398.16 HPS.
  Preserve heal-only metrics separately; absorption events from Hunters can be
  protection-potion effects and are not automatically healing quality.
- Every sampled MC Protection Warrior is currently inferred DPS. Maasumi takes
  nine Lucifron melee hits plus one Protector melee, while casting Bloodthirst,
  Cleave and Whirlwind with no three-action set from the current narrow tank
  ability list. Other samples also take repeated boss melee while using Fury
  actions. This is direct incoming-pressure evidence alongside damage actions,
  not enough to assert assignment or accept the DPS label as domain truth.
  Subject 02.4 must resolve Fury-tank/temporary-aggro ambiguity without using
  category alone or changing accepted Naxx behavior silently.
- BWL combined and AQ Viscidus Protection samples currently infer tank for six
  actors each. This is engineering role regression, not SME adjudication.
- A further MC Guardian capture acquired data but stopped during finalization
  at the deliberately conservative 80% budget boundary (1302/1800 account points
  after a fresh reading). No ZIP was published and no tank fixture is claimed.
  Keep its cache/request journal and resume after reset using the same inputs.
  A retry using the existing normal 90% policy also stopped in finalization:
  159 of 1620 allowed points remained, below the 162-point unknown-query reserve.
  Do not weaken that standard reserve; no additional usable fixture was published.

## Guide-source boundaries

A bounded Magmadar Hunter capture subsequently finalized six public actors
under the normal quota policy (account spend1331.2/1800; reset646 s at receipt).
It remains ignored research until raw/member/independent checks and provenance
promotion complete. Three cohort actor-source streams directly show successful
Tranquilizing Shot dispels (`isBuff=true`, extraAbilityGameID19451) on the boss;
the removing ability is19801. The removed effect19451 is absent from some raw
master ability catalogs, so a name-only join would lose the mechanic.
Other same-name Frenzy entries23537/25801/8269 are not equivalent IDs. Subject
and two other samples have no own successful effect; this cannot prove an
unfulfilled assignment or unused opportunity. No Magmadar runtime policy or
matrix completion is certified by this research observation.

Further raw direction-only ranking audit (not an approved policy): combined
Hunter damage to NPCs14601/11981 plus consistently owned pets agrees with all
six recorded scores at their displayed rounding. MC Balance/DPS mostly agrees
with raw player sums, but Teris has 577 damage to a player-gameID recipient
alongside a 22.446 DPS discrepancy. MC Hunter Charies' 854 damage to two
player-gameID recipients accounts for a 57.571 DPS difference, while another
Hunter's player-recipient damage is included in an otherwise matching raw sum.
Recipient actor type/name alone cannot implement the exact WCL exclusion rule.
MC Fire Mage Benoii: 43,382 raw damage /24.016 s =1806.379 versus recorded
1352.31; 21,815 raw Ignite damage is among the components. No positive overkill
field explains the difference. An Ignite attribution hypothesis remains
unverified; do not implement it from community descriptions or this one sample.
AQ Hunter Temison: raw owned actor/pet amount50,509 over101.893 s =495.706 versus
490.711 recorded; 509 damage to the player-gameID recipient is the difference.
These discrepancies preserve the unvalidated ranking gate. Exact owner,
hostility, attribution and window contracts still require independent proof.

BWL Guardian captures expose hostile healing credited to tank actors: raw
source-only heal events from Trashhealz to NPC 14601 (Ebonroc) total 125,000;
Obviously 75,000; Belkala 460,963. All are named Shadow of Ebonroc in raw ability
metadata. Suncat's 1,200 is Frenzied Regeneration on self; these are different
semantics despite all being raw source-heal amounts. The independent register
correctly freezes raw sums, but those sums cannot automatically become friendly
healing/HPS or healer-quality claims. Existing cast-qualified duty inference
does not use passive heal events. Reconcile recipient/ability semantics before
approving a healing metric policy; preserve historical arithmetic explicitly.

2026-10-17 follow-up: the normal-policy Guardian retry succeeded after the quota
reset, preserving retained request/cache data. MC now has a public six-actor
Guardian archive and six additional independent actor cases; earlier budget
stops above remain history, not current availability. The direct melee ambiguity
guard now leaves the six MC Protection duties unknown, retaining damage-action
signals and observed pressure rather than asserting assigned tank jobs. Naxx's
historical duty contract remains unchanged. Independently enumerated Lucifron
melee counts are Maasumi 9, Doljin 15, Pale 7, Frozion 15, Panzèrzug 8, Cailo 19;
only target pages, NPC gameID 12118 and raw melee IDs 1/-4 were counted.

Live phase schema and report observations are retained in
research/phase-observations.json. `ReportFight.phaseTransitions` gives semantic
phase IDs and report-relative start times; the next transition/fight end closes
the phase according to the live schema. The full MC/AQ sample reports return
null transitions for every boss. BWL returns only one start marker each for
Razorgore and Nefarian, with empty phase-name catalogs; combined dragons have
null transitions. This does not establish the physical absence of phases.
Do not substitute those fields for actor opportunity or invent missing phases
from a guide. These are research receipts; current acquisition does not yet
request/store these optional fields. Official field descriptions are also
available in [ReportFight](https://br.warcraftlogs.com/v2-api-docs/warcraft/reportfight.doc.html)
and [PhaseTransition](https://tw.warcraftlogs.com/v2-api-docs/warcraft/phasetransition.doc.html).

[Lucifron](https://warcraft.wiki.gg/wiki/Lucifron) separates Era's two guards
from Season of Mastery's four. Its curse/resource and control/dispelling advice
is static strategy, not evidence of a particular actor's assignment. The raw
Era report corroborates two Protector instances; neither source validates WCL
ranking exclusions.

[Magmadar](https://warcraft.wiki.gg/wiki/Magmadar) separates fear/frenzy utility
from additional Season of Mastery hounds. Do not import the seasonal adds or a
guide's nominal timing into observed personal downtime.

Mixed-version pages require section-level review. General dispel tables and
Nefarian tactics pages include retail-only classes/abilities; restrict Era
applicability to the nine verified classes and independently verified spells.
Never cite an undated generic table as proof of an Era utility option.
