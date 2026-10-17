# Garr — partial evidence dossier

Reviewed 2026-10-17. Initial engineering evidence; no complete boss or cell.

## Identity and scope

WCL zone2000, encounter50666; Garr NPC12057 and Firesworn NPC12099 are
present in immutable public raw reports. Policies apply to Era partitions1/2
only, with current real evidence in partition1. Static Elemental type and
strategy context: [Garr](https://warcraft.wiki.gg/wiki/Garr) and
[Firesworn](https://warcraft.wiki.gg/wiki/Firesworn). The wiki describes multiple
add strategies; Warlock selection does not establish a Banish assignment.
Do not import retail/world-boss quantities or SoM Magmakin mechanics.

Classic database links identify [Banish18647](https://www.wowhead.com/classic/spell=18647/banish)
and [Firesworn12099](https://www.wowhead.com/classic/npc=12099/firesworn), but
automated page retrieval returned an anti-bot page. No numeric behavior is
claimed from those unavailable contents. Actual raw WCL IDs below establish
the implemented match. NPC Banish8994 is not a player spell substitute.
An additional bounded existing-client source query for Greasecup actor11 in
`8Lt3zrD92h7Ty6xv`/fight22 independently confirms Banish710 cast/application
on NPC actor122, instance2, at1866432 and1887431 ms. This resolves the rank1
mapping without asserting canonical faction or promoting that query into a
complete fixture. The implemented mechanic reference links to the public
Rumplock report; the blocked database page is not its evidence source.

## Verified observations

Two normal acquisition/finalization/snapshot captures: `mc-garr-warlock`
(Finia) and `mc-garr-control-warlock` (Rumplock), six sources each, both Horde
Destruction/DPS. Twelve independently enumerated raw actor cases supplement
the original114; immutable manifest/identity/duration/amount/cast/owner facts
are under `tests/golden/raids/`. One additional matrix configuration, not two.

Rumplock's `DWACqnQrmMxdgYpt`/fight17/actor38 has pull1141770–1193237 ms.
Banish18647 begins2.742 s, casts4.258 s, applies4.258 s and removes34.271 s.
The target is NPC actor100, gameID12099, instance8. Source-owned application
count is1. Finia's `yKBC4j3tzL8mDrNR`/fight22/actor9 has29.453 s duration and
zero recorded Banish applications. Neither result establishes an assignment,
available-opportunity denominator, control quality, break cause or raid-wide
uptime. No nominal duration is used to manufacture a control window.

Initial global-cast probes found other actors controlling adds while selected
ranking actors did not. One probe included only a begin-cast; never equate
the probe's event count with successful casts or effects. Server filtering
did not guarantee exact ability IDs; all implemented measurements match local
raw fields. Greasecup's canonical profile has observed Warlock class but
unknown faction, so it was rejected by normal same-faction capture readiness.
Rumplock has observed Horde faction and uses the unchanged production path.

## Implemented and open

Shared control observations use existing deduplicated actor events, source
coverage and report-local NPC identity. They retain actor/instance/spell/time
and distinguish source-owned applydebuff from cast/begincast/removal. Known
wrong NPC/player/spell/source events are excluded; missing/conflicting required
identity yields unknown totals. Positive evidence remains under truncation.
Missing instance identity stays missing rather than guessing instance1.

Sourced preparation, add death positioning, assigned Warlock control, healer
context and recovery coordination are saved separately from observations and
appear in both pages. No new parser/schema/downloader/renderer is introduced.

Remaining: native/start-trash/foreign and ranked-target reconciliation, full
phase/opportunity/control windows, exact school/resistance/item effects,
pet/tank/healer/hybrid/class/loadout analysis, Alliance and other category
evidence, complete behavioral/render acceptance and domain review. Current
target/ranking policies remain unvalidated. All full MC boxes stay open.

## Encounter-wide observed control

The normal finalized format2 Finia capture supplies six independently frozen
control contexts in control-facts.json. Finia is Horde and selected Destruction;
own yKBC4j3tzL8mDrNR/22 has zero Banish applications both personally and globally.
Do not put positive observations from other examples into Finia's fight.

Forand's cohort fight8Lt3zrD92h7Ty6xv/22 contains the actual caster Greasecup11,
who applies710 to Firesworn122/instance2 at24.404 and45.403 s, with observed
removal44.403 s and fight end52.694 s. Manual subtraction gives27.290 s known
active,24.404 s initial unknown and1.000 s known inactive; the last effect is
censored. These are target observations in Forand's fight, not Forand's uptime.

RaYB3pbDkPGd6gxK/30 reuses Firesworn102 for distinct instances4/8 and separate
Warlock casters. Known active durations20.009/30.000 s remain separate. The
Rank2 effect18647 in Tr3GVvF4t8MPbqYp/13 lasts13.700 observed seconds through
fight-end censoring; no nominal30-second duration extends the fight. All six
payloads contain no native Firesworn death/resurrect rows. Three examples have
no Banish transitions; their initial aura state is not assumed inactive.

The [Classic710 record](https://www.wowhead.com/classic/spell=710/banish) and
[Classic18647 record](https://www.wowhead.com/classic/spell=18647/banish) verify
Warlock capability; later indexed retrieval resolved the initially blocked
18647 page. Its nominal duration is not a measured control interval. Seasonal
instant Banish and later-expansion recast cancellation are excluded.

Shared NPC aura logic now accepts class-qualified player casters and debuff
transitions, preserving exact source class, native recipient, instance, scope,
raw integer identities, lifecycle and initial uncertainty. Other named caster
classes, NPCs/pets, invalid/ambiguous class or coerced raw IDs cannot certify a
Warlock effect. Existing personal SOURCE-owned counters remain separate.
Actor-only legacy archives retain positive observations but unknown global
counts/windows. Both pages label cohort states as observations in that fight.
No assigned job, physical attackability, optimal control or lost DPS is inferred.
Full class/faction/duty, phase, ranking and human review obligations stay open.
