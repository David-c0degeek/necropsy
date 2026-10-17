# Recipient-qualified healing in new Era raids

Status: accepted engineering contract; full raid and product acceptance remain separate.

Source ownership of a WCL heal event does not establish friendly healing support.
In the public combined-dragon Guardian captures, Shadow of Ebonroc credits player
actors with healing NPC 14601. Independently enumerated amounts include 125,000,
75,000 and 460,963; a different actor's 1,200 Frenzied Regeneration heals self.
The immutable fixture and arithmetic registers retain all original raw amounts.
The [Ebonroc guide](https://warcraft.wiki.gg/wiki/Ebonroc) corroborates the mechanic;
raw actor/ability/recipient identities establish what these particular logs contain.
No retail hotfix number or nominal per-hit amount drives the calculation.

For MC/BWL/AQ40 Era partitions 1/2, the existing common combat and Druid analysis
plugins qualify heal events by recipient. The fight's friendly player/pet rosters
and the selected actor establish supported recipients. Encounter boss game IDs
identify healing credited to bosses, independently of ranking exclusions.
Other, missing or contradictory recipient identities remain unclassified. Such
events make the exact friendly/boss totals unknown instead of implying zero.
All whole-fight sums retain actor-source coverage requirements. Incoming heals,
pet-owned source actions and absorption events do not become player heal amounts.

`effective_healing`, its whole-fight rate and overhealing use supported
recipients. Additive `raw_source_healing` and its rate preserve the previous raw
source-event arithmetic; `healing_to_bosses` and `unclassified_healing` expose
separate amounts/rates. Missing or negative amounts remain unknown. These are
descriptive measurements, not WCL HPS reconstruction, healer quality or proof
of assigned duty. Actor cast rules still determine inferred duty separately.
Target/spell breakdowns retain raw event context rather than silently discarding
boss effects. Both pages disclose the distinction and applicable boss examples.

The analysis schema remains 1: its existing evidence-tree metric/playbook maps
accept these additive keys, with named `healing-recipients-v1` evidence. Raw
snapshots and normalized storage do not change. Historical Naxx arithmetic and
seasonal behavior retain their previous contract; old saved JSON renders its
saved values. Reanalysis of raw new-raid snapshots produces the qualified values.
Rollback reverts the qualified analysis call sites and optional presentation;
no archive migration or expectation regeneration is needed.

## Credited absorption

The same recipient classifier also qualifies source-owned `absorbed` events.
Additive `raw_source_absorption`, `effective_absorption`, `absorption_to_bosses`
and `unclassified_absorption` retain their distinct totals and rates. Incoming
damage payloads' absorbed fields never enter shield contribution. Malformed
raw source/recipient/amount fields cannot become trustworthy through database
scalar coercion. Qualified source healing uses the same raw scalar guard.

`healing_and_absorption` and its whole-fight rate add known friendly actor heals
and credited absorption, excluding overheal. Existing heal-only measurements
and overheal denominators remain distinct. Pet/guardian contributions are not
automatically assigned to the player. Every aggregate still needs actor-source
coverage, even when global data exist. Both pages show saved support examples.

[WCL pins](https://vanilla.warcraftlogs.com/help/pins) document that the healing
category includes absorbs. Independent66 retained HPS cases reproduce recorded
two-decimal scores using source heals plus absorption over recorded duration.
This bounded observation is not universal ranking validation, a fitted error
tolerance or a quality judgement. Unknown recipients, other classes/encounters,
pet attribution and encounter-specific ranking rules remain explicit limits.
Old Naxx and saved documents retain their previous semantics and content.
