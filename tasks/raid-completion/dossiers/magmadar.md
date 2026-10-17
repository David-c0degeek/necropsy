# Magmadar â€” partial evidence dossier

Reviewed 2026-10-17. Engineering research and initial implementation only;
no full boss, class, faction or domain acceptance.

## Identity and sources

- WCL zone 2000, encounter 50664, NPC 11982. New policies apply only to Era
  partitions 1/2; current real fixtures use partition 1.
- Static creature type Beast and mechanics context:
  [Warcraft Wiki](https://warcraft.wiki.gg/wiki/Magmadar),
  [Classic NPC guide](https://www.wowhead.com/classic/npc=11982/magmadar).
  [Classic skill-book source](https://www.wowhead.com/classic/item=16665/tome-of-tranquilizing-shot)
  supports confirming the learned Hunter spell. Retail changes and SoM spawn
  timings are not Era policy evidence.
- Immutable public six-actor fixtures: `mc-magmadar-hunter`,
  `mc-magmadar-holy`, `mc-magmadar-protection`; raw archives/member manifests,
  report/fight/actor/revision, faction/category/metric and independent arithmetic
  are in `tests/golden/raids/{provenance,facts,coverage}.json`.

## Verified observations and boundaries

| Concern | Evidence and implemented boundary | Open obligation |
|---|---|---|
| Boss identity | Every sampled fight lists NPC 11982; the removal matcher requires NPC type and exact game ID, rejecting player-ID collisions and conflicting identities. | Full phase/instance and ranking eligibility reconciliation. |
| Other targets | Several Era Hunter/Holy fights list ordinary Core Hound 11671, up to 15 instances. Enemy-roster presence does not prove a seasonal spawn or native encounter target. | Native/start-trash/foreign classifications and independent ranked amounts; current target policy remains unvalidated. |
| Frenzy utility | Source-owned dispel effects with `isBuff=true`, extra 19451, removing ability 19801 and recipient NPC 11982. Xelown/Charies/Clicker one each; Fleskhunter/Cartman/Trazel zero. | Full raid buff windows, assignments, available opportunities, unsuccessful attempts and other factions/categories. |
| Cast versus effect | Raw cast/effect pairs: Xelown 12.377/13.329 s, Charies 9.363/10.722 s, Clicker 9.414/10.122 s. | No reaction-time score: none of those cast times is the boss Frenzy start. |
| Ability names | Extra 19451 can be absent from the master ability-name catalog; same-name 23537/25801/8269 are not substituted. | Any new spell/ruleset mappings need their own evidence. |
| Personal Panic | Holy Almsivi, `aFQ7MPVdWTAvpK1Y` fight4, actor 41: apply 9.307 s, remove 17.303 s, pull 44.090 s; known exposure 7.996 s, initial unknown 9.307 s. | Global fear range, immunity/avoidability, cast interruption causes and fear-handling assignments. |
| No transition | Hunter Trazel: no Panic aura transition; all 34.485 s remain unknown-state. Some other actors have zero-damage19408 events, which are not aura transitions. | Damage hit codes alone do not establish a continuous fear window or why an actor was unaffected. |
| Partial/conflicting data | Positive observations survive partial streams; complete counts/windows require appropriate source/target coverage. Missing fields, simultaneous contradictory transitions, death/resurrection and conflicting actor identities retain uncertainty. | Actual full coverage across every legal class/category/faction cell. |
| Schools/resistances | Sources describe fire hazards; no resistance value, immunity model or gear threshold is implemented from that description. | Independently verified spell schools, item effects and ruleset-specific resist mechanics. |
| Roles/loadout/pets | Static Hunter Frenzy preparation, healing/fear recovery and raid coordination are saved and presented separately from observations. Category is not assignment; tank DPS is not threat/survival. | Full class/loadout/cooldown/resource/pet and tank/healer duty analysis; all applicable negative and real cases. |

The original manual healer-window test used a duration from a different Almsivi
pull. Real replay rejected that endpoint. The expectation now binds the exact
report/fight/actor and raw 44.090-second duration above; apply/remove times and
the independent raw-fact register were not regenerated from the analyzer.

## Runtime integration and remaining gate

`mc_guidance.yaml` owns sourced strategy, local Panic and exact Frenzy-removal
policies. `mc_facts.yaml` holds sourced basic facts. Shared encounter-effects,
actor-event/aura-state, analysis JSON and existing Report/Playbook adapters own
calculation/presentation. No new downloader, parser, normalized schema or
renderer is introduced. Saved old JSON and Naxx defaults remain unchanged.

The coverage matrix records only IN_PROGRESS cells. Complete school/target/
ranking/phase/opportunity, class/role/loadout/pet, independent facts and actual
render acceptance are required before closure. Full boss-domain review is
still the explicit human-owned 03.10 action; no sign-off is inferred here.
