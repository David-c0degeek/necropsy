# Evidence model

[Home](../README.md) · [Documentation](README.md) · [Reading results](reading-results.md)

Every value Necropsy reports says how it is known. Analyzers build values only
through the factories in `necropsy.analysis.evidence`, which enforce the rules
below.

| Level | Meaning | Example |
|---|---|---|
| OBSERVED | Read directly from a WCL field or event | Faction from `combatantinfo`; a Raptor Strike cast |
| DERIVED | Deterministic calculation over observed data | Aimed Shots per minute; pet died 25.678 s into the fight |
| INFERRED | Produced by a named rule that can be wrong | Pet family from abilities; damage among uniquely matched Windfury swings |
| UNKNOWN | The data cannot support a value | Exact pet passive training |

Every value is also one of two claims:

- **VALUE**: read or computed from what is present ("this cast happened", "this
  field says 0").
- **COMPLETE**: true only if no event is missing — whole-fight totals, counts,
  cadences, and every statement of non-occurrence ("no Windfury proc", "zero
  deaths"). A COMPLETE claim carries a coverage reference (report, fight,
  actor, stream direction, trusted) for every stream it read, all trusted;
  otherwise it is UNKNOWN and still records which stream was not trusted.
  NOT_OBSERVED can only exist as a COMPLETE claim.

Rules:

- UNKNOWN carries no value; every other level cites at least one reference
  (events by `(report, fight, event_uid, copy_index)`, or a table field).
- INFERRED names its rule and parameters.
- COMPLETE claims are built with `complete_or_unknown`, which takes the
  coverage decisions (`has_complete_coverage`, see `docs/database.md`). Events
  seen in an incomplete stream are still reported as a partial VALUE claim.

## How the interface names these concepts

| Player-facing label | Technical meaning |
|---|---|
| Calculated | `derived`; a deterministic calculation, not an observation |
| Inferred faction | The subject's faction evidence is inferred; a colored badge does not upgrade it |
| Limited sample | A small comparison group; the overview flags fewer than four entries, while each metric has its own `n_known` |
| No reliable comparison | No eligible baseline entries; this does not erase observed personal data |
| Some comparisons unavailable | At least one saved median is unknown despite available entries |
| Data limitations | Incomplete streams, snapshot issues, anomalies or acquisition shortfalls are recorded; inspect the actual causes. This describes evidence quality, not sync progress |
| Not assessed | No matching personal encounter in the selected view |
| No finding flagged | No saved recommendation, not proof of complete assessment or perfect execution |
| Reviewed locally | A browser annotation keyed to the analysis, not analytical evidence |

A median still requires **three known measurements**. A three-value median can
be displayed while remaining a limited sample. Comparison entry counts are not
interchangeable with metric-specific known counts. The overview groups existing
recommendations by rule and orders by their existing severity, preserving
confidence, control and limitations. It does not assign a player score.

## Faction

OBSERVED from the `combatantinfo` event or the report's `combatantInfo.factionID`
(`0` = Horde, `1` = Alliance). When neither exists, rule `raid-class-faction-v1`
INFERS it from the raid: Classic Era raids are single-faction, Paladins are
Alliance-only and Shamans Horde-only, so a report whose players include exactly
one of the two classes reveals the faction. Reports listing both are never used.
Every direct reading is collected; if any two disagree, or a code is not
recognised, the faction is UNKNOWN and the inference does not run. In the
Haplina cohort two of the 75 top-five rows rely on the inference (Ixtlan on
Instructor Razuvious, 古美门研介 on Grobbulus), so the reproduced 63 / 12 split
confirms the inference output, not two observed factions.

### Same-faction membership

Benchmarks compare the subject with entries of the same faction. Rule
`same-faction-membership-v1` grades that selection by its weakest proof: if the
subject's faction or any included entry's faction is INFERRED, the membership is
INFERRED, and so is everything aggregated over it — medians
(`median-over-inferred-membership`), the shot-target ranges projected from them,
and the same-faction ceiling. Recommendations built on an inferred membership
are at most `medium` confidence (raid speed drops to `low`). Aggregation never
turns an inferred membership into a confirmed one. Every median lists one
reference per member, so the entries behind it can be audited.

## Target integrity

Encounter rules say which units belong to an encounter (Gothik's native
targets) and which trash every raid kills at the start (`start_trash`, e.g.
Spirit of Naxxramas on Gothik). Start trash is neither native nor foreign: it is
reported separately and never counts as padding. Both lists are empirical
classifications from recorded kills. A damaged target can only be judged when it is a listed actor with a
game ID. If any damaged target has no target ID, no actor record or no game ID,
the native and foreign totals and the foreign share are UNKNOWN, the
unclassifiable targets are listed separately, and no padding finding is raised.

## Race

Only RACIAL_EVENT_CONFIRMED (the character cast its own racial ability) or
UNKNOWN. Race is never inferred from faction or class.

## Windfury

- **Status**: CONFIRMED when the Hunter has a Windfury Totem `extraattacks`
  event; NOT_OBSERVED only when the Hunter's own event stream is complete and
  trusted (a short fight can simply produce no proc); otherwise UNKNOWN.
- **Procs / extra attacks**: DERIVED counts, UNKNOWN on an incomplete stream.
- **Attributed damage**: INFERRED under rule `wf-unique-swing-v1`. A melee swing
  within 400 ms after a proc counts for it only when it lies in no other proc's
  window and the window holds exactly as many swings as the proc's extra
  attacks. No swing is used twice. The value is *damage among uniquely matched
  candidate swings*, reported with matched / ambiguous / unmatched proc counts.
  With observed procs but no uniquely matched proc, the estimate is UNKNOWN
  rather than 0. With a complete trusted stream and zero procs, matched proc
  damage is a complete derived zero (`windfury-no-procs-v1`); this says nothing
  about whether a totem was available or what would have happened with one.

## Aura uptime

New local encounter-effect observations use the shared aura-state primitive in
observed-only mode. Missing initial state stays unknown until a definitive
transition. Simultaneous contradictory events leave subsequent state unresolved;
out-of-fight and wrong-kind events do not supply personal exposure. Reports show
known affected time beside unknown time. Complete windows require trusted target
coverage; partial streams may still prove positive transitions. This is separate
from global phases, immunity, assignment, dispel opportunity and lost throughput.
Saved cohort effect examples identify their actor, report and fight separately
from personal measurements. Available raw recipient/spell identities must agree
with normalized IDs; relevant unresolved aura/lifecycle identity withholds
windows and retains unattributed evidence. A class-qualified effect is not a
universal assigned duty. Resource-aura exposure is not resource quantity, and
Bronze affliction duration is not a measurement of its individual stuns.
The historical aura calculations below retain their original policy.

Each aura is tracked on its own: apply turns it on, remove turns it off,
refresh and stack changes require it to be on. The starting state comes from
the starting-aura snapshot taken at the pull; without one, an aura's first
event settles it. Intervals are clipped to the fight and merged, so overlapping
auras count once. A state that cannot be settled makes the result UNKNOWN.

## Rules files

In Molten Core, Blackwing Lair and AQ40 Era partitions 1/2, repeated direct boss
melee pressure prevents a simple action-based DPS/healer duty inference when
repeated tank actions are missing. The duty stays unknown; damage actions and
incoming pressure remain evidence. This guards against classifying Fury-style
tanking as ordinary DPS without asserting an assignment from category or hits.
The optional saved `playbook.duty_context` retains coverage-qualified boss melee
counts and positive observed timestamps, including for excluded personal entries.
Three events trigger ambiguity, not tank qualification. Swings include avoided
and fully absorbed outcomes; they do not define continuous tanking opportunity.
Historical Naxx inference remains unchanged.

New Era raid combat/Druid healing measurements additionally qualify recipients
using the fight's friendly player/pet roster, self identity and encounter boss
game IDs. Boss-mechanic healing credited to a player is distinct from friendly
support. Other/missing/conflicting recipients keep the exact qualified totals
unknown. Raw source sums remain separate, and all totals require complete actor
source coverage. Neither the qualified values nor raw sums reconstruct WCL HPS
or measure healing quality. See the
[recipient contract](decisions/0014-recipient-qualified-healing.md), including
the real Shadow of Ebonroc counterexample. Old Naxx and saved JSON are unchanged.

Static encounter strategy is labelled general strategy, with versioned rules,
sources and retrieval dates. Applicability by class, metric and ruleset does not
establish a player's actual duty, phase, opportunity or fault. It does not change
measurement evidence, cohort eligibility, medians or recommendation severity.
The selected strategy is saved during analysis; rendering older saved JSON does
not introduce current advice or new observations.

Game facts live in `src/necropsy/rules/classic_era/*.yaml` (package data, so
they ship in the wheel). Each entry records whether its ID was seen in the
Haplina fixture or comes from Classic Era spell data.

NPC buff observations retain exact report actor and instance. Complete target
state requires trusted unrestricted encounter coverage, with the actorless role
explicit in its reference. The merged event union must contain no extra
identities or occurrences beyond that All read: equal occurrence counts prove
this under maximum-multiplicity ingestion. Missing or inconsistent count
metadata withholds complete counts and windows while preserving positive
observations. Critical or personal coverage cannot certify global
absence. Different instances never share transitions; missing instance identity
withholds windows. State starts unknown and lifecycle/contradiction uncertainty
is preserved. Observed buff state does not define a physical phase or a
player's safe attack opportunity. See the
[instance contract](decisions/0017-target-instance-aura-windows.md).

Credited absorption is a source-owned absorb event, distinct from an incoming
damage event's absorbed field. Friendly, boss and unresolved recipients stay
separate. Combined friendly healing and absorption retains whole-fight actor
source coverage, with no implicit pet attribution or quality judgement. Raw
scalar coercion cannot turn boolean or fractional support fields into valid
integer ownership/amount evidence. Heal-only and overheal values stay distinct.

Era raid class reports additionally retain each known owned summon's friendly
healing, credited absorption and whole-fight support rate. Master actor,
selected-fight pet and exported source ownership must agree. Trusted pet SOURCE
coverage plus the exact unrestricted encounter event set qualify these totals;
TARGET coverage does not prove outgoing healing. Possible support rows are
validated before identity/time/type exclusions, and projected event occurrence
multiplicity must match the original event set. Conflicting ownership, malformed
events or unknown recipients withhold certainty. A known individual contribution
can coexist with an incomplete overall pet listing; it never certifies an
all-summon total. These optional saved fields do not modify actor support,
recorded WCL scores or older saved analyses. Each entry groups all logged
instances of the same pet actor; it does not identify a physical summon lifetime
or uptime window.

Optional raid-roster interruption context names the actual source actor, stopped
spell and recorded target instance. It is separate from selected-player utility.
Trusted unrestricted All and exact merged-event proof qualify complete counts;
unselected raid actors need no individual SOURCE stream. Possible interruption
rows are validated before exclusion. Partial coverage or malformed rows withhold
the total while independently qualified positive effects remain observed. A zero
describes matching retained raid-roster effects, not personal non-use. These
measurements imply no opportunities, assignment, reaction or quality grade.
