# Credited absorption by ability and recipient

Status: accepted · 2026-10-18

Priest reports in Era MC, BWL and AQ40 retain optional saved
`playbook.healing_context.absorption_examples`, deduplicated by selected actor,
report and fight. Group recorded friendly source-attributed absorption by numeric
ability and recipient. Reuse the shared recipient classifier after validating
owner, catalog, selected roster and raw/normalized event identities. Read event
occurrences directly; ability names are optional display metadata and cannot
multiply amounts. Existing actor totals, comparison eligibility and scores stay
unchanged.

Complete totals require exactly one selected SOURCE stream bound as a player
with no owner, trusted coverage and unrestricted encounter event-set proof.
Validate possible absorption rows before excluding inconsistent or unresolved
identities, chronology or types. Incomplete coverage or ambiguous rows withholds
totals while retaining separately qualified observations. Known zero is possible
only with complete evidence; missing data cannot establish shield non-use.

Both pages render the saved breakdown through their shared presentation. A
recorded positive Power Word: Shield10901 effect supplies a review prompt to
separate its recipients from other credited absorption and coordinate shield
priorities with tanks and healers. Initial prompt coverage is this observed rank;
other ranks receive numeric breakdowns without that prompt. This is not a
cast-frequency prescription, assignment, healing-quality or mana-efficiency
assessment. Effects are not casts, and credited absorption does not establish
prevented damage, equipment causality or WCL ranking policy. Rendering old saved
documents does not create observations or new advice.

The official [WCL AbsorbedEvent documentation](https://de.warcraftlogs.com/scripting-api-docs/warcraft/interfaces/RpgLogs.AbsorbedEvent.html)
separates absorbed events from casts and retains nullable source/ability
identity. Its scripting wrapper is distinct from the raw GraphQL field names;
the retained raw occurrences establish the actual amounts and bindings here.

Initial real acceptance covers60 full-MC Priest contexts independently frozen
before implementation. Almsivi's Sulfuron context records2406 absorption from
four10901 effects and4845 from17 Persistent Shield26470 effects, alongside only
one10901 cast. These are distinct measurements. BWL/AQ40 use the same evidence
contract; full class, rank and encounter coaching remains incomplete.
