# Evidence model

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
targets). A damaged target can only be judged when it is a listed actor with a
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
  The true total Windfury damage is always UNKNOWN; with no uniquely matched
  proc the estimate is UNKNOWN rather than 0.

## Aura uptime

Each aura is tracked on its own: apply turns it on, remove turns it off,
refresh and stack changes require it to be on. The starting state comes from
the starting-aura snapshot taken at the pull; without one, an aura's first
event settles it. Intervals are clipped to the fight and merged, so overlapping
auras count once. A state that cannot be settled makes the result UNKNOWN.

## Rules files

Game facts live in `src/necropsy/rules/classic_era/*.yaml` (package data, so
they ship in the wheel). Each entry records whether its ID was seen in the
Haplina fixture or comes from Classic Era spell data.
