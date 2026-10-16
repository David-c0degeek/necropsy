# Full raid completion contract

## Scope and units

MC, BWL and AQ40 contain 27 canonical bosses and 28 WCL encounter entries,
including combined Ebonroc / Flamegor. Preserve Naxx's 15 encounters as the
regression reference. The seed CSV contains 952 TODO rows: 28 encounters × 34
legal category/metric/faction configurations from the current catalog. These
cover 19 WCL category pools and explicit Balance/HPS. Reverify this denominator
in 00/01; add newly verified applicable configurations through a decision.

All nine classes and all 27 declared talent trees must work. A declared tree is
build intent, not a separate WCL category. Preserve actual talent totals, hybrid
builds and unknowns. Never invent Survival, Combat or Affliction API filters.
Paladin/Horde and Shaman/Alliance are excluded by Classic Era faction legality;
record that rationale and revisit it if the ruleset changes.

The CSV is disposable tracking. Durable manifests, fixture facts and automated
coverage assertions live in normal project locations without plan references.
The product must not read tasks/ at runtime.

## Every boss must deliver

1. Verified encounter/NPC identities, canonical/variant rules, ordering,
   ruleset/partition applicability, and classification of bosses, native adds,
   foreign trash, self/friendly targets and unclassifiable actors.
2. Sourced mechanics and opportunity constraints: vulnerability/immunity,
   resistance, target switches, transitions, forced downtime, healing/tank
   restrictions, dispels/interrupts/control and distinct assignments where
   applicable. Do not force a mechanic onto a boss to fill a column.
3. Observed phase/opportunity detection with event references and confidence.
   Static guide timings remain general advice, never an observed phase or an
   automatic personal failure. State what the available log cannot establish.
4. Independently reconciled ranking amounts, durations, targets, exclusions and
   pet/guardian contributions for each applicable encounter/metric policy.
   Distinguish documented from empirical rules, retain residuals, justify
   tolerances by precision and metric, and investigate contradictions. Do not
   copy Naxx tolerances or fit exclusions to one parse. Recorded WCL scores stay
   independently useful while reconstructed quantities remain unknown.
5. Useful class/role-aware preparation/loadout, opener/cooldowns, execution,
   resource/utility/pet handling, avoidances and raid coordination. Each
   applicable advice category needs a boss-specific outcome or an explicit,
   evidence-grounded reason it does not apply. Descriptive comparisons,
   general strategy and personal findings remain distinct.
6. Fair assignment/opportunity comparisons. Label whole-fight and active-window
   denominators. Immunity, control duty, threat duty, class calls, dispelling or
   add assignments cannot automatically become poor execution. Mixed duty
   remains mixed and encounter-restricted sparse activity is not a universal
   cadence failure.
7. Usable real actor/event captures, immutable hashes, coverage and ownership
   provenance, independent expected facts and reviewed disagreements. Include
   positive, negative, partial/missing, wrong-duty and relevant variant cases.
8. Actual Playbook and Report content, source/evidence links, gear and class
   detail, exports/packages, desktop/mobile/print checks and deterministic
   offline replay.

## Every matrix cell must close explicitly

| CSV field | Required closure evidence |
|---|---|
| implementation | Correct raid/category/metric/faction/encounter acquisition or replay; appropriate plugin and duty eligibility |
| mechanics_and_guidance | Applicable boss/class/role preparation, execution and coordination advice, sourced and wired; no generic-only replacement |
| synthetic_behavior | Positive, negative, sparse, wrong-duty and incomplete-coverage behavior through real callers |
| real_actor_source | At least one usable real actor/fight with this actual category, metric and faction; source/archive/member/report/fight/actor IDs and coverage |
| independent_facts | Applicable raw totals, durations, targets, counts, timings, duty evidence and advice conclusions checked independently of the analyzer |
| ranking_reconciliation | Actual ranking reconciliation or an explicitly linked, mathematically applicable metric-policy proof; no unresolved contradictory source |
| render_review | Real boss/class Playbook and Report content, links and package checked; shared layout reviews may cover multiple cells, content checks may not disappear |
| status | COMPLETE only when applicable fields have durable source/test/review refs; otherwise TODO, IN_PROGRESS, BLOCKED_EVIDENCE, BLOCKED_REVIEW or justified NOT_APPLICABLE |

Initial TODO values assert no unperformed work. Replace them with evidence
references, not unsupported PASS labels. Every applicable cell must be COMPLETE
for full sign-off. Scarce public logs, quota exhaustion, unavailable reviewers,
missing Holy Priest events, empty streams or unknown assignment are open work,
not N/A. Genuine ruleset illegality or nonexistent ranking modes may be N/A only
with a cited reason and explicit review. Do not fabricate samples or promote
cross-faction examples. Sparse cohorts can still support individual comparisons;
fewer than three known measurements cannot support a median.

A roster fixture may close several cells only when it actually contains those
actors' categories, metrics, factions and usable streams. A shared policy proof
needs an explicit applicability argument and no contradictory source. Reuse
evidence without creating hundreds of duplicate archives or identical tests.

## Independent evidence and provenance

Preserve raw bytes and source/subset digests, report revisions, site/ruleset,
zone/partition, filters/metric, endpoints, actor identities and stream coverage.
Real captures, synthetic tests, historical oracles and independent arithmetic
are distinct evidence tiers. Private data stays in authorized fixture storage;
ordinary CI receives permitted deterministic subsets without account secrets,
developer cache paths or an unplanned full-LFS download.

Expected facts must not call production metric/recommendation functions.
Independently inspect raw events and WCL values, preserve discrepancies, and
prove that known wrong target/duration/phase/ownership mutations fail. Do not
update a golden result merely to match the implementation. Naxx's historical
Hunter prose is a content inventory, not a source of new players' conclusions.

## Class and role depth

| Class | Boss-aware behavior to implement and verify |
|---|---|
| Hunter | Auto/Aimed/Multi opportunities, opener/cooldown/reset ordering, target-aware weaving, ammunition/loadout, owned pets versus guardians, survival/activity and raid utility |
| Druid | Balance/Feral/Guardian/Restoration and Balance/HPS, resources/forms, feral attacks, actual tank/healer duty, mitigation/healing context, hybrids and utility |
| Mage | Fire/Frost pool versus actual build, school eligibility, cooldown/mana windows, multi-target duty and decursing/control/utility |
| Paladin | Holy/Protection/Retribution, healing versus damage effects, actual tank evidence, cooldown/defensive context, blessings/dispels/utility and assignment-sensitive throughput |
| Priest | Holy/Shadow, healing windows/assignment, dispels, defensives/offensive cooldowns, resources; usable real Holy events required |
| Rogue | WCL DPS pool with actual tree context, resources/cooldowns/eligible uptime, threat, interrupts/control and boss-specific targets |
| Shaman | Elemental/Enhancement/Restoration, healing/damage duties, shock/interrupt/purge, totem/weapon utility and owned summons; missing signal is not proven absence |
| Warlock | WCL DPS pool with actual build, schools/DoTs/cooldowns/resources/life-tap context, curses, banish/control, summons and special tank duty when evidenced |
| Warrior | Fury/Protection, rage/execute/cooldown opportunities, actual tank duty, defensive/debuff/interrupt utility and threat-sensitive assignments; tank DPS is not tank quality |

Actor-owned casts differ from damage/healing ticks, incoming casts and pet
actions. A cast gap alone cannot prove movement, mana failure or fault. Missing
threat, dispel-opportunity or assignment data stays unknown. Supply safe general
guidance while stating why a personal judgement cannot be supported.

## Naxx and product gates

Preserve all 15 Naxx sections, historical Hunter facts, existing class/category
fixtures and accepted limitations, strict live-v1/legacy reading, saved-run
identity/resume, both HTML pages and sanitized package contracts. Explain and
review intended semantic changes before changing baselines. Naxx's historical
missing Holy Priest fixture is not a waiver for new raids.

For every new raid, exercise select → resolve → acquire → stop/save → reload/
continue → snapshot → offline replay → Report/Playbook → export/import. Store
distinct raids for one character and filter/open them correctly. Exercise
missing-personal, wrong-duty, sparse, no-pet, unresolved-owner and partial-source
cases. Links must land on the same encounter/source. Useful content survives
desktop/mobile/print; offline pages make no automatic network requests.

A release candidate and evidence packet precede product acceptance. An approved
partial release remains named partial and cannot satisfy FULLY implemented.
Publishing is a separate deliberate action after final sign-off. This plan's
creation performs neither implementation nor release.
