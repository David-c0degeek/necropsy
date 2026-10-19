# Classic Era class analysis

[Home](../README.md) · [Connection](warcraft-logs.md) · [Read results](reading-results.md)

Necropsy supports all nine Classic Era classes across the [supported raid modules](raids.md) through the same
character → faction/spec → faction-leader comparison workflow. Every requested
boss remains visible. Without matching personal duty/coverage, the leader remains
a practice reference and your performance is not assessed. One or two comparison
sources still show their individual values and sample count. Overall leaders are
in a separate disclosure, collapsed by default, with faction differences noted.

## Select a ranking category

The guided apps separate your optional **talent tree** declaration from the
**WCL comparison category**. All 27 game talent trees are available as declarations;
the categories below are the comparison pools. WCL display labels such as Rogue
**DPS** use API slugs such as `Assassination`. The
[taxonomy research](class-taxonomy-research.md) explains the evidence and
[the class/build contract](decisions/0012-game-build-and-wcl-category.md) defines
the implemented boundaries.

A Combat-heavy Rogue still compares within WCL Rogue DPS. A Fury-heavy Warrior
can choose Tank comparisons. Recorded talent totals, derived primary tree, WCL
category, inferred duty, race and faction appear separately in the report's
**Observed builds, categories, duties and race evidence** table. Unknown builds
remain unknown; catalog consistency never guesses a race. Choosing a tree does
not filter the leaderboard or claim the best player for that talent build.

CLI example (legacy `--spec` remains an alias for `--category`):

```sh
uv run necropsy analyze CHARACTER_URL --talent-tree Combat --category Assassination --endpoint user --cache workspace/cache --out workspace/rogue
```

The declaration survives saved-run resumes and snapshot offline replay. Leave it
unspecified for hybrids, or select a tree as a preference without asserting your
exact allocation. Three recorded point totals do not identify individual talents.

| Class | Supported WCL categories (API slugs) | Default ranking metric |
|---|---|---|
| Druid | Balance, Feral, Guardian (Tank), Restoration | DPS; Restoration HPS; explicit Balance HPS supported |
| Hunter | Marksmanship; legacy all remains supported | DPS |
| Mage | Fire, Frost | DPS |
| Paladin | Holy, Protection, Retribution | Holy HPS; others DPS |
| Priest | Holy, Shadow | Holy HPS; Shadow DPS |
| Rogue | Assassination | DPS |
| Shaman | Elemental, Enhancement, Restoration | Restoration HPS; others DPS |
| Warlock | Destruction | DPS |
| Warrior | Fury, Protection | DPS |

These are WCL ranking labels, **not talent-tree diagnoses**. Classic Era groups
Rogue damage under Assassination and Warlock damage under Destruction, including
other talent builds. Hunter game data exposes one ranking category. Combat,
Affliction and Survival filters are rejected as invalid
class/spec combinations by the Vanilla API. Necropsy does not invent those as
supported ranking filters. Your actual talent-point build remains visible for
each encounter and source when evidence is available. Category names and slugs
were reverified on 2026-10-16; see the linked research for the bounded ranking
probes and additional rejected filters. New categories require evidence.

`Tank`, `Healer` and `DPS` aliases resolve by class where unambiguous. For example:

```sh
uv run necropsy analyze CHARACTER_URL --faction Alliance --spec Fire --endpoint user --cache workspace/cache --out workspace/mage
uv run necropsy analyze CHARACTER_URL --faction Alliance --spec Healer --endpoint user --cache workspace/cache --out workspace/paladin-healer
uv run necropsy analyze CHARACTER_URL --faction Horde --spec Tank --endpoint user --cache workspace/cache --out workspace/warrior-tank
```

Use the actual character faction. Explicit incompatible categories/metrics are
refused; no hidden cross-faction fallback is used. Faction selection precedes deep
comparison fetching; unknown factions are verified, not guessed from class/race.

## Read the playbook

The shared overview identifies your class/category, faction evidence, coverage,
priorities and encounters needing review. **Playbook** gives supported actions
and stacked **Before the pull**, **During the fight** and **Coordinate with the
raid** sections. Relevant uncertainty stays beside the advice. Boss links open
the same encounter in **Report** for classifications, comparisons, gear and evidence.
Class color is
identity only; it does not communicate a rating or analytical confidence.
Report execution rows use the class's recorded core abilities and cooldowns, comparing
counts, uses per minute and actor-owned first-use timing with source links.
**Ability use vs player** includes all recorded actor cast abilities, items and
utility. It excludes passive damage/healing ticks and pet actions; rates use each
player's own full fight duration. Incomplete streams stay unknown, never zero.
Pets and summons retain separate damage, DPS, casts, deaths and listing limits.

Repeated action sets and direct encounter hits infer duties. A ranking category,
talent build, form or incidental off-heal alone cannot establish assignment.
Mixed/uncertain or incomplete duties are excluded from single-role personal
comparisons. Known talent-point differences remain context, not a reason to hide
same-category players. HPS is not healing quality, tank DPS is not survival/threat,
and a cast gap cannot establish movement, mana starvation or fault. Threat and
unavailable defensive/assignment measurements remain explicitly unknown.

## Contracts and validation

The existing class registry, source coverage, event normalization, cache,
credentials, snapshot verification and publisher are shared. Hunter's `hunter`
and Druid's `druid` data stay compatible; other classes use optional `combat`
entry evidence in schema1. Old saved Hunter documents still render without the
new optional field. Common metrics/roles/timeline/comparison and ability CSVs use
the same sanitized package path. The full analysis JSON retains detailed evidence.

All fourteen added category contracts and missing-personal/partial cases have
synthetic offline and desktop/mobile checks. Public real-log validation boundaries
are recorded below; synthetic checks do not approve domain advice or product limits. Existing [Druid validation](druid-validation.md) and
[Hunter validation](live-validation.md) keep their original scope.


Real public Patchwerk captures now cover all seven added classes: Mage Fire,
Paladin Holy, Priest Shadow, Rogue Assassination, Shaman Restoration, Warlock
Destruction and Warrior Protection. Each has six actor entries and independent
raw amount checks. Warrior captures retain DPS-duty Protection entries separately
from tank comparisons. [Provenance](../tests/golden/classes/PROVENANCE.md) records
hashes, coverage and the additional budget-only Priest Holy snapshot. Real Holy
Priest event validation for that original Naxxramas/Patchwerk acceptance remains
unavailable; synthetic checks and verified HPS ranking metadata do not complete
that fixture. Later [MC/BWL/AQ40 evidence](raids.md) retains usable real Holy Priest
healing separately. Full-MC Holy Paladin evidence also retains60 actors and58
qualified recipient contexts, with two empty enemy rosters and one unknown
guardian owner. These module-specific captures do not establish universal healer
quality or complete class/duty/faction coverage.

Holy Paladin healing views add sourced class notes for the personal fight. They
record Divine Favor casts with its two-minute cooldown, any emergency cooldowns
used (with no expected-use target) and in-fight blessing casts. Cooldown
availability and pre-pull blessings are not measured. When every mana reading
lacks a capacity, the notes say that mana timing and mana lost to encounter
effects cannot be assessed, rather than treating the value as zero. Wrong-duty
and incompletely recorded fights receive no notes.

Where an encounter declares mechanic-presence rules (currently Baron Geddon),
combat-class views also label the selected reference fight. The label gives both
fight durations and names boss mechanics the reference records none of, or
cannot measure without a complete encounter event set. It also keeps each
comparison fight's recorded duration, mechanic counts and other listed enemies.
The label does not explain why a reference differs and does not exclude it.

Full-MC Horde Restoration Shaman evidence retains60 actor and60 recipient
contexts, with17 owned Healing Stream Totem units in59 independently checked
owner contexts. One Magmadar pet owner remains unresolved. Both raid pages show
each verified owned unit's friendly healing, credited absorption and whole-fight
rate separately from actor support. Conflicting ownership or incomplete event
evidence remains unknown. This does not establish a WCL HPS policy or complete
summon coaching.

Shaman Sulfuron reports also retain separate raid-roster interruptions of Dark
Mending. Six independently checked fights contain four qualified effects by
Sabshaw, Minni and Healybeams; these are other raid members, not the selected
Restoration players. Both pages retain actual source names and target instances.
The count cannot establish talent builds, assignments or missed opportunities.

An initial Elemental Shaman capture retains25 DPS comparison actors across five
MC bosses and five personal ranking-selected contexts with unknown duty. The
latter remain excluded from personal DPS assessment; a ranking label alone does
not establish duty. Sixteen owned damage totems are retained, including confirmed
individuals beside incomplete overall ownership. Remaining boss comparisons and
full category/faction advice stay open.

The resumed Elemental capture now retains five acquired comparison actors per MC
boss:50 peers, with49 eligible for DPS comparisons. Pythón's Golemagg fight has
positive damage and repeated boss melee; its duty remains unknown, leaving four
eligible Golemagg examples. The five personal contexts remain duty-unknown and
the other five personal encounters are absent, so no personal DPS assessment is
available. Forty known owned damage totems remain separate from actor totals,
beside the existing unresolved Healing Stream owner. Real comparison collection
does not complete class coaching, assignments or ranked-damage reconciliation.

A completed Shadow Priest capture retains five acquired Alliance comparison
actors per MC boss, 50 overall, with 40 eligible for DPS comparisons. The
subject recorded Holy, not Shadow, in every fight, so no personal Shadow
assessment exists. Eight peers who mostly cast Holy Nova on adds (all five on
Garr, three on Majordomo) keep unknown duty because Holy Nova is not in the
Priest duty-action lists; they are not judged as poor DPS or as healers. Holy
Nova alone is not sufficient for duty under the current classifier: each cast is
untargeted and produces both enemy damage and ally healing under one ability
name, so its damage cannot certify an assigned DPS role. One
actor labelled Shadow Priest by the report and ranking shows Warrior stance,
gear and abilities in two fights; it is excluded only because no Priest duty
action is recorded, since the runtime has no general class-conflict check.
Garr therefore has no eligible Shadow comparison.

A Restoration Druid capture retains 59 Alliance fights: nine personal fights and
five acquired comparison Druids per MC boss. Every one records repeated Druid
healing casts and no feral, balance, bear or form actions. Personal assessment
exists on nine bosses. Sulfuron's personal fight was not acquired because its
player details carry no factionID, so its five peers keep a Restoration role but
form no comparison. One Majordomo peer stays duty-unknown because repeated boss
melee conflicts with an action-based duty; this is not a tank conclusion.
Repeated healing casts do not certify assigned duty, overheal efficiency or
healing quality, and heal-over-time ticks count as heal events, not casts.


Priest raid pages also separate credited absorption by numeric ability and
recorded friendly recipient. Power Word: Shield effects stay distinct from
Persistent Shield and other absorption, and from casts. The review prompt asks
players to agree shield priorities with tanks and healers; it does not prescribe
cast frequency or grade healing quality. Initial prompt coverage is observed
rank10901. All60 independently checked full-MC contexts preserve their previous
actor totals and comparison scores. Incomplete source/context evidence withholds
totals while retaining qualified observations; full class and rank coverage stays
open. See the [absorption context decision](decisions/0020-absorption-ability-context.md).

## Accepted validation boundary

On 2026-10-15 David approved the delivered implementation and instructed final closure after the remaining domain-review requirements were disclosed. Additional standalone Druid SME adjudication was retired by product-owner decision; no new per-finding review is claimed. The accepted scope retains conservative duty heuristics, assignment/coverage unknowns and the missing real Holy Priest healing fixture. Arithmetic and automated role-regression checks are engineering evidence, not universal rotation, quality or assignment certification. Earlier pending handoff records are historical. Further refinement is separately scoped.
