# Game builds and WCL comparison categories

Status: implemented.

Classic Era has three talent trees per class. WCL Vanilla exposes 19 ranking
categories across nine classes, with display names that can differ from API slugs.
Rogue DPS, for example, uses `Assassination`; Warrior Tank uses `Protection` even
for Fury-heavy builds. The [verified research](../class-taxonomy-research.md)
records the primary evidence and its limits.

Keep the game tree catalog, WCL category ID/name/slug catalog, recorded talent
totals, inferred encounter duty, declared assignment, race evidence and faction
evidence independent. WCL IDs are namespaced to WCL Vanilla. Valid race/class/
faction combinations constrain known identity; they never create an observed race.

The guided apps offer an optional declared talent tree independently of the WCL
comparison category. CLI `--talent-tree` records this declaration; existing
`--spec`/`--category` retain their category semantics. No automatic tree-to-category
mapping is introduced: hybrid Warriors and Mages make that mapping ambiguous.
Selections remain valid even when observed talents or duty differ from intent.

Snapshots add optional `subject.talent_tree`; saved run checkpoints permit an
optional `talent_tree` option. Existing snapshots/checkpoints without it keep
working. Archived participant `spec` still means WCL category. No normalized
database schema change is needed; acquisition JSON carries the declaration into
offline reports. New snapshots with the optional field require an updated reader;
the change promises old-to-new readability, not forward compatibility with old
strict readers.

Analysis schema 1 adds optional `taxonomy` evidence. Current live outputs and
non-Hunter class outputs expose declared intent, the comparison pool, and each
recorded actor's build/category/duty/race context. Historical Hunter output omits
the section to preserve its existing replay contract. Old analysis documents
remain readable and are never filled with invented declarations.

Combatant event `talents[*].id` and fight-scoped playerDetails
`combatantInfo.talents[*].guid` are validated as three ordered point totals. Spell
names decorated onto those numbers are not individual talent identities.
Leaderboard talent placeholders are not usable point distributions. A unique
largest total permits a derived primary-tree label; ties stay unknown/mixed.
The legacy `build_matches` field compares valid tree totals and remains null if
either is unknown. Equal totals do not prove identical individual talents.

Comparisons remain category-wide. Declared tree preference does not narrow the
leaderboard or change role eligibility. Event-qualified comparisons still apply
Necropsy's inferred-duty checks; WCL category policy is not an observed assignment.
The legacy acquisition dimension `role.status=enforced` is retained for archive
compatibility and denotes category policy. The taxonomy section states that scope
explicitly. Ranking metadata scores remain distinct from reconstructed throughput.

No exact current WCL classifier parity or global leader for an unranked talent
tree is claimed. Such features require separately verified rules and bounded
search coverage.
