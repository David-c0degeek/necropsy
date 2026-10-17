# Encounter observations and sourced strategy

Status: accepted incremental engineering contract; complete phase/opportunity,
ranking, boss/class and product acceptance remain separate.

Per-raid rule assets own encounter identities, targets and applicable strategy
or actor-effect definitions. Shared analysis primitives compute event evidence;
the existing analysis document and both renderers consume those results. No
second downloader, parser, metric engine or template-computed recommendation is
introduced. New Era policies apply only to partitions 1/2 and matching raid/
encounter identities. Naxx retains its historical rules and default aura-state
behavior.

General strategy is static knowledge with source, retrieval date, rule ID and
class/metric applicability. It does not establish a personal assignment, phase,
opportunity or mistake. The engine saves the selected items into optional
`playbook.encounter_strategy`. Old JSON does not acquire advice during rendering.
Current sourced strategies cover Lucifron, Magmadar, Gehennas, Garr, Baron Geddon,
combined Ebonroc/Flamegor and Viscidus;
that initial set does not claim complete support for those bosses or other raids.

Optional `playbook.encounter_effects` records actor debuff exposure through
shared aura-state primitives. Initial state remains unknown until a recorded
definitive transition settles it. Simultaneous contradictory transitions cannot
be ordered by event hashes; subsequent state stays unknown until settled.
Contradictory refresh/stack events retain uncertainty. Events outside the fight,
incoming effects on another actor, outgoing casts and wrong aura kinds do not
supply personal debuff evidence.
An observed death or resurrection also resets subsequent aura state to unknown
until another definitive transition; a prior apply event cannot prove continuous
exposure across that boundary. These reset events remain in the window references.

Each exposure retains source/actor/event references, positive transitions,
three-state windows, known affected seconds, unknown-state seconds and a limit
on interpretation. Whole-window measurements require complete actor-target
coverage; partial streams may still prove individual positive transitions.
Known affected time is a partial observation alongside unknown time, not a
claim of zero unobserved exposure. Current policies cover Lucifron's Curse,
Impending Doom and Shadow of Ebonroc in the combined entry.
Magmadar additionally records local Panic state with the same uncertainty rules.
Gehennas records local Curse19716 state. That is the affected actor's exposure,
not a model of all their healing recipients: the curse reduces healing received
by its target. No outgoing-HPS correction, lost-healing estimate or avoidability
grade is inferred from the healer's own window.
Baron Geddon records Ignite Mana19659 exposure, including an observed application
still active at fight end. The end boundary censors the observation; it is not
an implicit removal. Aura duration does not establish actual mana destroyed,
damage taken or a failed removal assignment. Living Bomb/Inferno strategy does
not imply measured bomb applications, splash attribution or movement windows.

Successful mechanic removals are separate source-owned `dispel` effects with
an explicit debuff flag and matching `extraAbilityGameID`. They need not have a
matching cast event. Saved personal and cohort observations retain target,
removing ability, removed mechanic, time and event references; whole-fight counts
require complete source coverage. Positive effects remain visible under partial
coverage, while absent effects remain unknown. Missing/malformed debuff or
removed-mechanic fields also prevent a known absence even when the stream itself
is complete. Raw ability names are display
metadata and do not determine which mechanic was removed. The initial Lucifron
policies separate Curse, Doom and Dominate Mind from unrelated dispels. They do
not establish assignments, available opportunities, reaction time or a utility
score; a recorded zero is not a poor-play finding.

The Magmadar Frenzy policy uses `isBuff=true`, removed effect19451, removing
ability19801 and recipient NPC11982 together. NPC type is part of recipient
identity; a player game-ID collision is not a boss. Unknown required identity
fields keep the exact total unknown. Raw same-name Frenzy abilities do not
substitute for19451, which may appear only as an extra ability in dispel events
and be absent from the report's ability-name catalog. Policy match dimensions
and actor-catalog references are saved alongside the evidence.
The counter applies to Hunters; Priest/Warrior pages retain their own Panic and
pressure context without presenting a zero Hunter-specific job count. General
coordination strategy remains separate from personal capability or assignment.

Actor exposure is distinct from global boss phases, damage targetability,
immunity, assigned duty, dispel opportunity or lost throughput. The currently
sampled WCL report phase fields do not establish those complete windows.
Guide schedules never fill missing observations. Whole-fight comparisons remain
labelled whole-fight values; no exposure-based DPS normalization or quality
penalty is introduced by these policies.

Optional `playbook.control_applications` records source-owned control effects
using the same actor-event and coverage contracts. Garr's Warlock policy matches
applydebuff710/18647 on NPC12099. It retains time, target actor, nullable NPC
instance and ability, separately from cast/begincast and removal. Source
coverage and unambiguous required ability/recipient identity qualify exact
counts; positive effects survive partial streams. Missing instance stays
unknown and does not become a default add. A count cannot establish complete
NPC control uptime, assignment or opportunity. Both pages present the saved
observations; old JSON acquires no current policy during rendering.

The existing schema 1 evidence-tree fields admit the optional additions.
Snapshots and normalized tables do not change. Old documents remain readable;
new observations require reanalysis of raw snapshots. Rollback reverts optional
policy callers and presentation without modifying the immutable raw archive.
