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
