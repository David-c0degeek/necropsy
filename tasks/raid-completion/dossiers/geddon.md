# Baron Geddon — partial evidence dossier

Reviewed 2026-10-17. Initial observed Ignite Mana and general strategy only;
no complete boss, class/role/faction or domain acceptance.

## Identity, sources and ruleset

Era zone2000/encounter50668, boss NPC12056, Elemental. Policies apply only to
Era partitions1/2; real captures use1. Sources:
[Classic guide](https://www.wowhead.com/classic/guide/baron-geddon-molten-core-strategy-wow-classic),
[NPC](https://www.wowhead.com/classic/npc=12056/baron-geddon),
[Ignite Mana19659](https://www.wowhead.com/classic/spell=19659/ignite-mana).
The shared wiki page includes RPG prose and SoM multiple-bomb behavior; neither
is imported into Era policy. The Classic spell page describes a magic effect
that burns mana and causes damage when mana is burned. No nominal duration,
damage, resistance threshold or cast schedule manufactures a measured window.

Living Bomb20475 and Inferno19695 are also identified in the maintained
[DBM Vanilla module](https://github.com/DeadlyBossMods/DBM-Vanilla/blob/master/DBM-Raids-Vanilla/MC/Geddon.lua).
That consumer supports event identity, not proof the event occurred in one of
our fights. It contains seasonal IDs too; those are not substituted. The
automated Classic Living Bomb page was blocked. No bomb exposure matcher or
success/failure diagnosis is enabled without a usable selected positive source.

Source recheck 2026-10-19: the Wowhead Classic guide URL above returned only
site boilerplate (no strategy text) on two fetches, so it cannot support any
sentence. The Holy Paladin strategy items, the Paladin loadout applicability
item and the encounter facts now cite
[warcraft.wiki.gg/wiki/Baron_Geddon](https://warcraft.wiki.gg/wiki/Baron_Geddon),
whose Classic sections support each sentence (Living Bomb separation, melee
leaving during Inferno, no Ignite Mana dispel on Warriors or Rogues, healers
outside Ignite Mana range but in healing range, Elemental type). That page has
no healer gear guidance; its only resistance mention ("over 315 FR") concerns
the bomb or main-tank context, so no Geddon-specific Paladin loadout change is
claimed. The Hunter pet-recovery item still inherits the unverified guide and
needs its own source before any Hunter cell closes.

## Immutable observations

Normal finalized public captures `mc-geddon-holy` and `mc-geddon-hunter`, six
sources each. Raw files/member manifests and provenance/fact/coverage registers
are in `tests/golden/raids/`. Twelve independently enumerated actor cases bring
totals to25 archives/150 cases; original138 expected cases remain untouched.
All25,818,371 new extracted raw bytes passed unlimited gitleaks8.30.1.

| Actor | Exact source | Observed exposure | Interpretation |
|---|---|---|---|
| Almsivi, Holy | fdRrFwaKmvy3xJZD / fight10 / actor7 | Ignite Mana applies16.037 s; fight ends16.240 s;0.203 s known affected,16.037 s initial unknown | No removal event; end of fight censors a still-active observation. |
| Trazel, Hunter | kw1KFhxA4mfY8aRD / fight42 / actor116 | Applies21.033 s; fight ends26.071 s;5.038 s known affected,21.033 s initial unknown | No inferred removal, mana-loss amount or failed job. |
| Inkia, Holy comparison | 1QatCkbxLyrZzNAg / fight15 / actor21 | Apply7.667 s / remove9.275 s over16.285 s | Positive transition pair;1.608 s known affected. |
| Ivokros, Hunter comparison | Lwa74rJDPthfdCRY / fight16 / actor44 | Apply13.004 s / remove16.037 s over30.274 s | Positive transition pair;3.033 s known affected. |
| Vadik, Hunter comparison | ApbxvjzTX8mqVnY1 / fight25 / actor11 | Apply14.980 s; raw feign15.460 s; fight ends43.113 s | Nine effect-damage ticks continue after the feign.28.133 s affected /14.980 s initial unknown; end censored. |

Follow-up reviewed2026-10-18: the shared observer previously reset on Vadik's
raw `death` event despite its literal `feign:true`. Old installed replay gives
0.480s affected; corrected source and installed replay give28.133s, with the
original event retained. Independent literal expectations and mutation checks
are in `effect-facts.json#geddon-feign-actor-effects-1`; see
[lifecycle guardrails](../research/feign-lifecycle-contract.md). This establishes
continued observed exposure, not a removal assignment or a mana-loss estimate.

No selected actor in these12 sources records Living Bomb20475 application.
Other raid actors may receive it. Absence in this actor subset is not absence
of the boss mechanic. Personal Ignite Mana windows likewise cannot establish
actual resource loss, explosion recipients, damage avoidance or every dispel
opportunity. Warrior/Rogue strategy does not equate an aura with mana loss.

## Runtime seams and open work

2026-10-18 extension: six independently frozen Priest contexts in the existing
full-MC capture retain one owned Dispel Magic988 effect removing Ignite Mana19659
and five zero counts. Inkia (`1QatCkbxLyrZzNAg`, fight15, actor21) records
application775695ms and removal777303ms alongside the self-dispel. Relative
boundaries are7.667/9.275s;1608ms describes recorded exposure. Immateriall's988
effect removes19635 instead and remains excluded. Exact source member/index
locators precede modeling in
[the raw register](../research/geddon-priest-removal-raw-facts.json).
The shared pairing requires SOURCE/TARGET plus exact encounter-event coverage;
ambiguous transitions or raw identity withhold it independently of removal
counts. Self-clear priorities and backup dispel coverage remain raid coordination,
not a reaction grade, causal proof or saved-mana estimate. Other five actors are
not accused of missing a dispel assignment. All class/faction/domain gates stay open.

Paladin extension: six independently frozen contexts retain four Cleanse4987
effects across two actors and four zeros. Anrylla (`CN3cTnkWYr6mVQD7`, fight81,
actor3) has explicit7.262/10.144-second endpoints alongside an owned self-clear:
2882ms recorded exposure. A later application stays censored. Resurgance
(`kvJ2WVF1chC9R4wd`, fight43, actor35) removes19659 from16/30/20; none of these
effects ends his own exposure. The real other-recipient case protects against
nearest-time attribution. Classic Cleanse includes Magic while Purify1152 only
removes poison/disease; Holy school alone cannot decide capability. Exact raw
locators are in [the Paladin register](../research/paladin-geddon-removal-raw-facts.json).
The same shared guards and coordination limits apply; no reaction grade,
assignment, prevented damage or saved mana is inferred.

Existing shared effects state machine, actor coverage, optional JSON and both
page adapters are reused. Per-raid YAML supplies general preparation, bomb
isolation, Inferno recovery, Priest/Paladin magic removal, healer support and
Hunter pet-positioning review. No assigned job, pet failure, bomb splash cause,
movement duration or ranking reconstruction is inferred. Old JSON and Naxx
historical behavior remain unchanged.

Open: positive usable bomb sources; full actual Inferno/Armageddon/targetability
and pet/summon windows; native/foreign/ranking reconciliation; precise resource,
damage, removal and assignment evidence; all legal class/faction/tank/loadout/
item cases; full rendered/domain/product acceptance. The two representative
role captures and sourced static strategy do not close those obligations.
