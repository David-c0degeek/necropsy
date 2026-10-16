# Hunter analysis (Classic Era)

[Home](../README.md) · [Documentation](README.md) · [Reading results](reading-results.md)

In the application, start with the raid priorities and boss actions. **Your next
pull** collects the existing opener and cooldown guidance; **Compared with your
faction** shows shot rates with numeric values and known-sample labels. Full pet,
gear, weaving, target and timeline evidence remains available in disclosures.
These are Hunter-specific measurements within the shared class-neutral shell.

The Hunter plugin (`necropsy.analysis.classes.classic_era.hunter`) analyzes one
Hunter in one fight on top of the generic environment profile. Every value
follows the evidence model in [`evidence-model.md`](evidence-model.md); rule
data lives in `src/necropsy/rules/classic_era/hunter.yaml` and `items.yaml`.

## What it reports

| Area | Values |
|---|---|
| Shots | Auto, Aimed, Multi, Arcane and Raptor casts with times and per-minute rates; Rapid Fire, Refocus and Hunter's Mark casts; explosives |
| Opener | The first 10 shots and cooldowns of the fight |
| Auras | Quick Shots procs and uptime, Rapid Fire uptime |
| Auto Shot cycle | Every Auto → Auto interval with its gap, whether a ranged haste aura overlapped, and the special shots cast inside it |
| Long-gap signal | Advisory (INFERRED, `auto-gap-v1`): clean intervals longer than 1.25 × the fight's median clean interval |
| Melee | Raptor Strike damage, white melee swings and damage; Windfury comes from the environment profile |
| Friendly crowd control | Freezing Trap, Scatter Shot and Reckless Charge cast on a target on the Hunter's side (e.g. a mind-controlled raid member) |
| Pets | Every pet-linked actor classified; per Hunter pet: abilities seen, family, damage, DPS, activity window, deaths |
| Gear | Ranged weapon and scope, trinkets, main and off hand, and whether Renataki's Charm was equipped at the pull |

## Rules worth knowing

- **Auto intervals.** A special shot belongs to the interval whose end Auto it
  precedes or shares a timestamp with. Simultaneous casts are all kept.
- **Long-gap signal.** Only "clean" intervals form the baseline: no special shot
  inside and no ranged haste aura (Rapid Fire, Quick Shots, Berserking)
  overlapping. With fewer than 5 clean intervals the signal is UNKNOWN. A
  flagged interval means "possible clipping, movement or downtime"; it is not a
  diagnosed clip and carries no damage estimate. Encounter context comes later.
- **Pet classification.** Known non-Hunter actors by game ID first
  (engineering guardians, traps, mind-controlled or summoned units). Otherwise
  an actor that uses a Hunter-pet ability is the Hunter's pet. Anything else
  stays UNKNOWN.
- **Pet family.** INFERRED (`pet-family-abilities-v1`) only when the
  family-restricted abilities the pet used fit exactly one family (from
  Petopia's Classic ability table); Claw + Dash identifies a Cat. Otherwise the
  family is UNKNOWN and the candidates are listed. Ability ranks are not
  reported; the spell IDs are.
- **Target side** (`target-side-v1`). The event's own friendly flag wins;
  otherwise the fight's friendly lists (players, pets) and enemy list decide,
  for a pet also through its owner. Actor type alone never decides. A ground-placed
  ability (Freezing Trap) aimed at WCL's "Environment" placeholder (actor -1) has
  no unit target and is not counted as undecided; a missing target ID, or the
  placeholder on a unit-targeted ability, stays undecided. Each cast
  records how its side was known. An undecided side makes the friendly
  crowd-control list a partial observation instead of a complete one. Spells sharing a name (two
  Reckless Charge IDs) are all counted.
- **Gear.** The snapshot taken at the pull. A "no Renataki" claim needs both
  trinket slots recorded (a recorded empty slot counts); with a slot missing it
  is UNKNOWN. "Renataki at the pull" and "Refocus
  cast" are separate facts; trinket swaps are not inferred.

## Ranking damage

When event reconstruction cannot establish ranked DPS, a strictly matching live
WCL Hunter DPS ranking row supplies the score independently. Its evidence records
the limitation. Raw/external/ranked damage totals stay unknown when attribution
is incomplete; a known score never repairs missing pet ownership or events.

Unknown engineering ownership does not erase a positively owned Hunter pet's
individual analysis. `hunter.pet_roster_complete` separately establishes whether
every possible Hunter pet is accounted for; `hunter.total_pet_dps` can therefore
remain known even when the all-pet roster is incomplete. Multiple actual Hunter
pets retain per-actor results rather than a silently combined baseline.

Family inference can cite positive ability evidence from the same report pet
actor and proven owner in another acquired fight (`pet-family-report-abilities-v1`).
Current-fight casts, damage, uptime and deaths are never imported. Conflicting
abilities remain unknown; ambiguous families show their candidates.

Missing starting snapshots can be recovered from an earlier raw combatant event
and complete intervening recipient buff changes (`combatant-prelude-auras-v1`).
Context pages never extend the ranked damage or cadence window. Missing or
invalid context retains uncertainty while ordinary fight streams remain usable.

`aura-state-windows-v1` retains active, inactive and uncertain haste windows.
Known active haste establishes overlap even if another aura is uncertain. An
observed Alliance faction excludes Troll-only self-Berserking; an inferred
faction does not. This does not identify a character's race.

`necropsy.analysis.generic.targets.ranking_damage` reproduces what WCL ranks:
damage by the Hunter and every pet-linked actor to anything except the Hunter
itself and its own pets (`external-damage-v1`). Self-damage from Sapper Charges
and Dynamite is left out; damage to mind-controlled raid members counts. On the
Haplina fixture this reproduces 64 of the 75 top-five rankings exactly. The
other 11 are on bosses whose adds WCL leaves out (Faerlina, Razuvious,
Anub'Rekhan, Gluth, Heigan); encounter rules supply those exclusions.

Both rules are empirical: WCL does not document them. With the Naxxramas
exclusions (`naxx-ranking-exclusions-v1`) all 90 recorded fights reproduce
their ranked amount within 15 damage, and the golden test
`tests/golden/test_ranking_rules_full.py` keeps that validation standing.
`analysis.json` labels the exclusion rule `basis: empirical` in every boss's
`rules` block, lists every damaged target with its ranking category, and shows
per boss which targets make up the same-faction entries' ranked damage.

## Melee weaving by target role

Raptor Strike casts are split by what they hit (rule `cast-target-role-v1`): the
boss itself, or another hostile NPC (encounter adds, start trash, pulled-in
trash). On Gothik, for example, the recorded top five never weave on Gothik but
two of them use Raptor Strike on adds that reach melee. A cast whose target side
or identity is unknown, or whose target is not an NPC (a hostile player or pet), makes the split unknown.

Any damage event with no target ID makes the external and ranked totals UNKNOWN,
because it could be self-damage. Encounter exclusions cannot be applied to a
target without a game ID (missing from the report's actor list, or listed without one), so the ranked total is then UNKNOWN; a display name alone never decides an exclusion.
