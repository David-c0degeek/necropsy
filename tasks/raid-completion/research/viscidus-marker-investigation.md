# Viscidus marker investigation

Reviewed2026-10-17. The new public whole-fight fixture retains frost spells,
Toxin25989, Volley25991 and Rejoin25896. A named spell catalog entry is not an
observed freeze boundary. Numeric school masks classify recorded damage events,
not whether the server counted them toward a mechanic.

Primary [DBM consumer](https://raw.githubusercontent.com/DeadlyBossMods/DBM-Vanilla/master/DBM-Raids-Vanilla/AQ40/Viscidus.lua)
uses monster emotes for freeze/shatter state, and treats Frost Weakness spellcast
availability/timing as uncertain. Rejoin25896 can be cast by multiple surviving
globs; its deduplication heuristic is not a universal observed boundary. Its
spellcast-only and seasonal1215736 branch must not become Era combat-log facts.
A blocked Classic25937 page and TBC/retail spell results are not Era evidence.

Next: independently enumerate exact actor/target/school/proc and rejoin events,
verify event versus hit distinctions and ambiguous school catalog bindings,
freeze expected raw facts and record possible markers separately. Do not count
frost damage events as proven freeze credit or derive stage denominators from
thresholds, timers, activity gaps or missing markers. Full physical stage,
class/item/pet contribution and ranking validation remain open.
