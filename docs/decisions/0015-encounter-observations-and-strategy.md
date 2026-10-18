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
Current sourced strategies cover all ten MC bosses, all nine BWL encounter
entries and Viscidus;
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

Removal qualification examines the full report/fight before normalized actor,
type or time filters can hide a raw-owned candidate. Available raw source,
recipient, ability, timestamp, type and fight identities must agree without
coercion. Missing normalized ownership or chronology cannot establish absence.
Malformed required mechanic metadata remains unresolved; known unrelated effects
stay excluded. Valid positives survive alongside an unknown total.

Chromaggus Priest Blue-affliction removals require effect23153, harmful-effect
flagfalse and removing spell527/988. Magic dispel eligibility is separate from
Frost damage school. Its counts require both actor-source trust and complete
unrestricted encounter event-set consistency. Existing policies retain their
original coverage contract. Six raw Priest contexts preserve three owned effects
and explicit other-owner/cast-only negatives; only988 has observed positives.
No assignment, nominal removals per cast, reaction-time or utility score follows.

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

Raw WCL death events distinguish Feign Death with a literal `feign: true`.
Shared lifecycle classification excludes these events from genuine death
observations and aura resets while preserving them in immutable raw/normalized
data. An absent flag or literal false retains ordinary death semantics;
malformed flags remain unresolved, never coerced. Genuine positive deaths may
remain observed under ambiguous or partial evidence without certifying a total.
Resurrections still reset state. The scripting API's `isFeign` property is a
separate interface, not an assumed alias in raw JSON. A real Geddon Hunter
capture retains Ignite Mana ticks after a feign and verifies the distinction.

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

Shazzrah uses the same observed-only state contract for Curse19713. An active
curse remains end-censored. Static strategy distinguishes friendly curse removal
from hostile Deaden Magic19714 removal; neither capability implies assignment.
No successful hostile removal counter or Counterspell lockout window is inferred
from the current selected actor streams.

BWL observations also retain Burning Adrenaline18173, the logged Essence of the
Red23513 aura, Flame Buffet23341, the five Chromaggus afflictions and Nefarian
fear/curse/Priest-call effects. Logged debuff type does not mean an effect is
harmful: resource-aura exposure is not resource quantity. Bronze exposure does
not measure individual stun intervals. Corrupted Healing23401 is class-qualified
for Priest and observed only from actual transitions, never a nominal call timer.

Optional `playbook.cohort_encounter_effects` saves separately identified player,
report and fight examples with the same exposure contract. Both pages label the
example actor. These do not create personal context when the subject is missing;
old saved JSON without examples does not acquire them during rendering.

Available raw recipient/spell scalar IDs must be positive integers matching their
normalized projections before another recipient is excluded. Relevant ambiguous
aura or lifecycle identity withholds exposure windows and transitions; its event
reference has no actor attribution. Coerced booleans, fractions or nulls cannot
certify an absence. Older rows omitting raw scalar keys retain compatibility
with established normalized identity. This guard is confined to new Era actor
effects; historical Naxx aura inference remains unchanged.

AQ40 boss aura events can omit `targetInstance`. An explicit singleton policy
may certify unnumbered state only when the exact fight's `enemyNPCs` roster has
one unambiguous actor/game-ID binding with integer `instanceCount == 1`.
Missing, duplicate, conflicting, boolean or repeated cardinality withholds
durations while retaining positive transitions. Numbered repeated-add policies
keep their existing instance requirement. Unnumbered state references include
the fight metadata as well as transitions and lifecycle evidence.

Observed Sartura Whirlwind/Enrage, Huhuran Frenzy/Berserk, each Twin Emperor's
teleport aura and Ouro Berserk remain distinct effects. Teleport aura duration
does not define the pickup cycle, and missing C'Thun vulnerability transitions
cannot supply a guide-timed weakening phase. Personal Sand Blast remains actor
exposure, without inferred tank duty, avoidability or a lost-casting interval.

Optional summon observations use the same NPC catalog/cardinality qualification
as aura observations, extracted into a shared primitive. They retain separate
numbered instances and observed summon-to-positive-overkill event bounds.
The maximum-multiplicity normalized union must have the same occurrence count
as the trusted unrestricted All read before it supplies certified bounds;
otherwise actor/critical-only additions could masquerade as scoped events.
Missing count metadata withholds that proof. This uses existing coverage and
event tables; no schema migration or alternate parser is introduced.
An overkill marker is not a certified death or proof of continuous attackability.
Repeated starts, lifecycle reuse, conflicting later damage, ambiguous raw IDs
or incomplete unrestricted All coverage withhold elapsed bounds. Missing ends
are never filled by the next group or fight end. Skeram's overlapping image
groups remain separate; no phase denominator, target eligibility or personal
quality score is derived from these observations. Raw archives and prior
expectations are immutable; old saved documents acquire no observations during
rendering. Both personal and labelled comparison views use the saved data.

Explicit aura endpoints can be retained alongside source-owned self-dispels
through optional shared Playbook records. Pair only exact mechanic/recipient
identity and integer timestamps with complete actor SOURCE/TARGET and encounter
event-set proof. A recorded application must precede one removal endpoint;
matching successful effects at that endpoint must be unique. Reapplications,
refreshes, stacks, lifecycle interruptions and raw/projection conflicts withhold
pairing. Genuine death and Feign Death remain distinct. Standalone removal counts
do not depend on obtaining a pair. Endpoint coincidence is not causal ordering,
reaction quality, saved mana/damage or an assigned dispel opportunity. Coordination
text is sourced policy, saved with the record; rendering old documents cannot
invent it. Separate Priest Dispel Magic and Paladin Cleanse policies apply to
Ignite Mana on Geddon. A successful effect on another recipient does not define
the subject's own exposure endpoint; Purify's Holy school does not grant Magic
removal capability.
