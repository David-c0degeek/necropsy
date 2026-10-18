# Raid-roster interruption context

Status: accepted · 2026-10-18

Successful interruptions by other raid members can explain encounter execution
without establishing the selected player's utility. Save these observations in
optional `playbook.raid_interrupt_contexts`, deduplicated by report and fight.
Initial activation is Shaman reports, Era partitions1/2, Sulfuron50669, friendly
raid-roster Shaman sources interrupting Dark Mending19775 on Flamewaker Priest11662.
Source class does not establish a talent build or assignment.

Catalog identity, selected friendly roster, selected NPC identity and instance
cardinality must agree. Validate possible interruption rows over the full fight
before exclusions, including raw/normalized type, identities, time, spells and
recorded target instance. Query event occurrences directly so ability metadata
cannot multiply counts. Preserve legitimate copies. Complete counts require
unrestricted encounter coverage and exact merged event-set proof; no unselected
actor SOURCE stream is required. Partial coverage or unresolved rows withholds
the total while preserving independently qualified positive observations.

Both pages render the saved report/fight, actual source names, target instances
and uncertainty through the shared encounter presentation. The coordination
prompt asks for an interrupt order and backup coverage. Counts never enter
personal metrics, scores, recommendation comparisons or talent claims. Complete
zero means no matching retained raid-roster effects, not player non-use. No cast
opportunity, failed interrupt, reaction time, saved healing or quality follows.
Old saved documents acquire no observations during rendering. Other classes and
Naxx retain their previous output.

The [WCL scripting interface](https://es.classic.warcraftlogs.com/scripting-api-docs/warcraft/interfaces/RpgLogs.InterruptEvent.html)
documents `stoppedAbility`; the retained raw events instead use
`extraAbilityGameID`. The representations are not interchangeable aliases.
The [DBM Sulfuron module at r832](https://github.com/DeadlyBossMods/DBM-Vanilla/blob/r832/DBM-Raids-Vanilla/MC/Sulfuron.lua)
registers cast19775 and interruption events, stopping the target timer on
`extraSpellId==19775`. It supports mechanic identity, not a measured opportunity
window or universal cast duration.
