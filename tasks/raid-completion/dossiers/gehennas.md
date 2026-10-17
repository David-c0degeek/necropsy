# Gehennas — partial evidence dossier

Reviewed 2026-10-17. Initial Holy evidence and shared exposure/strategy wiring;
no complete boss, class/category/faction or domain acceptance.

## Identity and dated sources

Era zone 2000 / encounter 50665, boss NPC 12259. Current policy is partition 1/2
only; the real fixture uses 1. Humanoid creature type is independently visible
in the [Classic NPC record](https://www.wowhead.com/classic/pt/npc=12259/geena).
Do not import that page's seasonal health/loot rows. Static context is sourced
from [Gehennas](https://warcraft.wiki.gg/wiki/Gehennas) and the
[Classic guide](https://www.wowhead.com/classic/guide/gehennas-molten-core-strategy-wow-classic).

The [Curse 19716 record](https://www.wowhead.com/classic/spell=19716/gehennas-curse)
explicitly describes an aura modifying healing taken, with default reduction 75%,
Curse dispel type and Shadow school. The same page also lists seasonal values
of 99%/74%; spell ID alone therefore does not certify ruleset semantics. No
numeric healing correction, nominal curse timer or range model is implemented.
The [Rain of Fire 19717 record](https://www.wowhead.com/classic/spell=19717/rain-of-fire)
is a separate ability; the raw catalog names 19715 Counterspell. Do not guess
ability identity by adjacent spell numbers or import SoM add counts/cadence.

## Immutable raw observations

`mc-gehennas-holy` is normal public acquisition/finalization/snapshot output:
six sources, six independent actor cases, Alliance Holy/HPS. Exact identities,
revision, raw direction/member/cursor proofs and measurement expectations are
under `tests/golden/raids/`. The additional 11,096,461 extracted raw bytes pass
unlimited gitleaks 8.30.1 with zero findings. Current 132-case register totals and
the full matrix remain partial.

Subject Almsivi is `wjWt8JCzRKqV1gkG` fight 6 actor 28. Pull 6075151–6099542 ms
is 24.391 s. Curse 19716 applies 6081514 ms, removes 6085571 ms: relative 6.363–10.420 s,
4.057 s known affected and6.363 s initially unknown. Known unaffected time
after removal ends at the exact 24.391-second pull boundary. Comparison Almsíví
is a different actor/report and has a different duration; never borrow its
endpoint from the shared name appearance.

At 6085571 ms a successful dispel 2782, source 38 (Druid Paracetalol), target 28,
extra 19716/isBuff=false is recorded alongside the removal transition. It proves
an individual positive effect, not that Druid's full source coverage, assigned
target list or every available opportunity. Some actor-filtered pages contain
other raid actors' dispel events; explicit local source/target matching remains
required. Do not treat returned-page membership as actor ownership.

Subject raw healing 22177, absorbed 3719 and damage 168 remain separate facts.
The personal curse reduces healing received by that actor, not all their
outgoing healing. No multiplier or throughput blame follows from the window.
The enemy roster also lists Flamewaker 11661 and Firelord 11668; roster presence
alone does not make the latter a native or ranked target.

## Integration and remaining obligations

The existing shared actor-effect state machine, optional saved JSON and both
page adapters implement the observation. MC-owned YAML supplies sourced facts,
class-specific Mage/Druid removal strategy, healer-recipient context and raid
coordination; no alternate engine or raw pipeline is introduced. Old JSON
does not acquire current strategy during rendering.

Open: complete target/native/foreign and ranking reconciliation; global phase,
recipient-state/healing-opportunity and duty models; all school/resistance/
item/pet/loadout/class/tank obligations; Horde and remaining legal categories;
full real/behavior/render and domain/product acceptance. The Mage capture is
retained in ignored cache/journal but stopped finalization at the normal quota
reserve (161 left versus 162 estimated). It is not a usable fixture yet. Retry
after reset without weakening policy. No scarcity-based N/A or closure follows.

## Mage follow-up

The normal quota retry finalized `mc-gehennas-mage`: six Horde Fire/DPS
sources, six independent actor cases. Subject Suffel, `x4zfwgJZTAV3PYQK`
fight13 actor13, pull975032–1001082 ms (26.050 s), Curse apply9.718 s /
remove15.769 s:6.051 s known exposure,9.718 s initial unknown. All six selected
Mages record no source-owned Curse dispel; this does not establish failed jobs.
The subject's target stream records Frost Mage Fallout's2782 removal at15.770 s,
one millisecond after the boss-sourced removal transition. Those two event times
are not a reaction-time measurement or evidence that selected Mages neglected
decurse. Four representative page/viewport checks and exact raw replay pass;
full cell/class/ranking acceptance remains open.
