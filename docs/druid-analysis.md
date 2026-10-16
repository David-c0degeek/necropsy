# Druid analysis

[Documentation](README.md) · [Connection guide](warcraft-logs.md) · [Reading results](reading-results.md)

Druid shares the same character overview, class accent, boss triage and review
workflow as other classes. **Playbook** leads to practical preparation;
**Report** emphasizes role-appropriate comparisons. Expand **Role, category and
coverage context** or **Your measurements** to inspect the inference and its
limits. Orange class identity never implies a specific spec or duty.

Classic Era Naxxramas Druids use the same acquisition, snapshot, evidence,
report and package pipeline as Hunters. In the TUI, paste your character link,
choose Balance, Feral, Tank or Restoration and start the analysis. The following
commands are the equivalent advanced CLI examples:

```sh
uv run necropsy analyze "https://vanilla.warcraftlogs.com/character/id/110733843" --faction Alliance --spec Balance --cross-faction --endpoint user --cache workspace/druid-cache --out workspace/balance
uv run necropsy analyze "https://vanilla.warcraftlogs.com/character/id/110733843" --faction Alliance --spec Restoration --endpoint user --cache workspace/druid-cache --out workspace/restoration
uv run necropsy analyze "https://vanilla.warcraftlogs.com/character/id/110733843" --faction Alliance --spec Tank --endpoint user --cache workspace/druid-cache --out workspace/tank
```

These commands use saved personal WCL credentials and acquire all supported
Naxxramas bosses. Use separate output directories for categories. Archived logs
may need the user endpoint and an eligible WCL account. Existing budget, revision,
identity, faction, pet ownership and partial-output rules still apply. Exit 4
means written partial coverage; complete pagination does not imply domain approval.
An opt-in `--wait-for-reset` permits one bounded hourly reset wait.

An interactive terminal asks for faction and spec when absent. Scripts can pass
the flags explicitly; old noninteractive commands remain readable and usable.
The spec prompt offers `all` for the legacy Hunter all-spec DPS view; explicit
`--spec all` also selects that policy. Druids require a supported explicit spec.
The chosen faction is checked against the character before report acquisition.
The main list uses that faction and selected spec. The same selection flow also
supports Hunter's Classic Era WCL category, `--spec Marksmanship` (`MM`). Race and
talent-point builds are context, not extra selection requirements.

The selected spec filters the whole view. Every requested boss remains visible.
Your personal analysis uses only a matching ranking category and evidenced
encounter duty. If you heal Sapphiron, the Balance view leaves your Sapphiron
performance unassessed and shows an eligible Balance player's recorded example.
Restoration shows your healing performances. Tank shows no personal tank data
where none was established, alongside eligible tank examples for learning.
The report says **not enough personal data in this spec**; it never grades your
healing as Balance DPS or turns a Guardian ranking into proof that you tanked.

`--category` remains supported. `Tank` maps to WCL `Guardian`; `boomkin` maps to
`Balance`. Names are case-insensitive. Conflicting `--spec`/`--category` selections
are refused. Use a separate output directory for each view.

Learning examples require matching category, metric, partition and inferred duty,
known faction/difficulty, complete actor source/target streams, and no
assignment override. They are labelled with their actual leaderboard position.
The highest acquired example may be #4; it is never relabelled #1. Saved overall
#1 category metadata is separate from acquired event evidence. `--cross-faction`
can acquire a global #1 from another faction when accessible. No example creates
a personal median, gap or recommendation when your selected-spec data is missing.
With no personal fights, the main practice playbook still shows the faction
leader's recorded opener, ability counts/rates and role-specific measurements.
The unfiltered overall-top comparison is **collapsed by default**, with faction,
race, buffs and assignment caveats. It does not replace the faction leader.

For multi-boss Druid views, acquisition fetches personal encounters first, then
first-page ranking references for every boss before deep comparison samples,
prioritizing bosses without personal data for deep examples. It keeps budget
for fresh report finalization and records comparison order and partial targets.
The original reset policy applies while collecting personal data; comparison
collection stops when its reserved allowance is exhausted. A boss not queried
because acquisition stopped says **not assessed**, rather than asserting that you
never played the role. Missing event samples do not hide a saved ranking-score
comparison. Missing ranking metadata remains unknown rather than fabricated.

| WCL category | Ranking metric | Possible encounter duty |
|---|---|---|
| `Balance` | DPS | Balance damage |
| `Balance --metric hps` | HPS | Healing in a Balance category/build |
| `Feral` | DPS | Feral damage |
| `Guardian` | DPS | Feral tank or other evidenced duties |
| `Restoration` | HPS | Healing |

Guardian's DPS score is a category ranking, never a tank survival or threat score.
The taxonomy was checked against the live WCL game-data and ranking endpoints.
WCL uses class ID 2 for Druid, independently of Blizzard class IDs.

For Balance-category healing assignments, select `--category Balance --metric hps`
in a separate output directory. Category, metric and inferred encounter duty stay
separate: healing on Sapphiron does not require relabelling the build Restoration.
The other categories retain the metrics above; unsupported combinations fail
before acquisition. Metric selection chooses the saved ranking performance, not
an assignment override.

## Duties and comparisons

The report keeps the actor's class, observed talent points, WCL category, inferred
fight role, assigned duty and any user override separate. Repeated class casts
provide affirmative signals: three feral, balance or healing casts qualify as
an action signal. A non-tank signal also needs at least 20% of the categorized
duty casts to qualify as an inferred duty; three incidental off-heals or damage
casts therefore do not automatically make the fight hybrid. These provisional
thresholds use cast share, not active-time share, and need domain review. All
minor signals and activity spans remain in the evidence. Tank inference additionally needs
three recorded direct encounter-enemy melee/Hateful Strike hits alongside
repeated bear-only actions. Raid AoE, bear form or talents alone do not establish
tanking. This is an inference to review, not a statement of the raid's assignment.

Loatheb's encounter rule lowers the healing-action minimum to one: Corrupted Mind
restricts healing opportunities, so one or two heals can establish a healing
signal. Coverage and competing-duty checks still apply. Whole-fight healing
cadence and throughput findings are suppressed on this encounter; review the
assigned healing rotation instead.

Multiple qualifying signals produce hybrid duties. Incomplete actor streams or
insufficient signals leave the aggregate role unknown. The activity spans show
the first and last qualifying casts; they are not continuous assignment windows.
No whole-fight benchmark is offered for mixed, uncertain or overridden duties.

A primary comparison uses the same known class, encounter, faction, WCL category,
duty, metric, difficulty and partition, within Classic Era Naxxramas. Different
known talent-point builds and unknown builds remain in this selected-spec group,
with known differences and unknown builds disclosed separately. Missing talents
do not prevent event analysis or recommendations. **One or two event sources
still provide direct comparisons**, labelled as a limited sample with individual
measurements, signed differences and source links. Medians summarize three or more
known metric values. Unknown measurements stay unknown; a percentage difference
from zero is undefined. Role-based membership remains inferred.

The playbook compares your spell counts and casts per minute with the best-ranked
acquired same-faction source. Its saved WCL score is compared separately with the
best recorded same-faction WCL score. Global #1 is separate, optional context.
Unresolved earlier players
prevent claiming faction rank #1. Metadata never fills event metrics or increases
the event sample size. Global #1 remains separately labelled. No personal data
means no personal gap, even when a reference score is available. Sparse individual
differences are descriptive and do not trigger the median-based damage rule.

## Measurements and practice notes

Druid uses the same visual hierarchy and components as the Hunter playbook:
raid sheet, boss metric cards, benchmark context, KISS opener, loadout/execution,
Do not/Raid ask, full named pull gear with enchants, and faction cohort details.
World buffs and cooldown timing are recorded per encounter. Role-specific numbers
replace Hunter-specific measurements; missing evidence remains visible as unknown.
Review marks and keyboard navigation work through the shared page controls.

**Ability use vs [player]** is shared across classes. It shows recorded spells,
shots, melee skills and cooldown/item casts as counts and uses per minute. These
are actor cast events, excluding passive damage ticks and pet actions. Whole-fight
counts need trusted source coverage; an unobserved action is zero only with that
coverage. Different fight lengths and assignments can explain differences. New
packages export `tables/ability-use.csv`. Older saved documents still render;
replay their raw snapshots to populate the new common entry data.

Feral and balance detail includes cast counts and the full timestamped event
timeline with source/target names, faction and external-buff context, form intervals,
resource observations and cooldown/utility
casts. A recorded first-ten-seconds sequence is a practice example; a short or
specialized parse does not establish an optimal rotation. Event damage is the
actor's raw damage across targets, separately labelled from WCL's category score.
Hunter-specific ranking exclusions and pet/shot advice never apply to Druids.

Restoration shows effective healing, healing rate, overheal where present,
targets and spell use. WCL event `amount` is effective healing; `overheal` is
separate. WCL's sparse heal payload omits `overheal` when zero (as handled by
[WoWAnalyzer's healing parser](https://github.com/WoWAnalyzer/WoWAnalyzer/blob/midnight/src/parser/shared/modules/throughput/HealingDone.tsx)).
Explicit null, malformed or negative overheal stays unknown; complete source
coverage is still required for totals. Raw HPS and overheal cannot
rank healing quality without assignments, incoming raid damage and other healers.

Healing review prompts cover overhealing above 50%, cast rate or effective HPS
below 80% of a same-faction median with at least three known values, and unused
Innervate/Nature's Swiftness when at least three and a majority of comparable
sources used it. Cooldown comparisons exclude fights substantially longer than
yours (your duration must be at least 80% of the source duration). These are
low-confidence assignment reviews, not instructions to chase HPS or cast more.
Findings retain observed values, known source counts, evidence and limitations.
Unavailable primary measurements are named with their reasons; missing tank
mitigation fields do not mark healer comparisons unavailable. Assessment limits
also explain skipped overheal reviews and restricted-healing mechanics.

Tanking shows incoming damage, healing received, death recaps, available
mitigation fields, form evidence and cooldown timings. Missing mitigation,
threat or form evidence stays unknown. Bear attacks can establish a form-related
action without establishing a complete form interval. Logged deaths and low DPS
do not establish player fault. Resource readings are point observations; missing
or zero capacity cannot prove usable mana/energy/rage availability.

## Explicit assignment overrides

Replay a saved snapshot with an optional file:

```json
{
  "REPORT_CODE/34": {
    "role": "feral-tank",
    "reason": "Assigned off-tank for this encounter"
  }
}
```

```sh
uv run necropsy offline snapshot.zip --role-overrides assignments.json --out workspace/assigned
```

Allowed values: `feral-dps`, `balance-dps`, `restoration`, `feral-tank`, `hybrid`,
`uncertain`. Every override needs a reason and an acquired subject report/fight.
It changes the selected assignment label, preserves conflicting observations,
and removes that fight from aggregate role comparisons. It never changes raw
snapshots, talents, WCL category or observed evidence.

## Outputs and validation limits

Both offline pages retain unknowns, practical notes and full supporting detail.
The ZIP exports roles, metrics, exact-key comparisons and full event timelines as CSV, plus analysis JSON
and recommendation evidence. Logs and derived outputs contain player identities;
share only where the source data may be shared.

Authenticated one-boss saved runs cover the supplied character's balance and
restoration logs, plus public feral and Guardian-category examples. Unknown pet
ownership keeps acquisition partial. Real tank/mixed examples, independent fact
checks and domain acceptance are tracked separately; implementing a role is not
the same as validating it across every Naxxramas encounter. See
[Druid validation](druid-validation.md) for the current evidence.

Druid execution plans now use the same labelled plan rows as Hunter: opener, individual core abilities and recorded cooldowns, first-use timing, counts/cadence, target context and resource review. Weapons/trinkets/relic/world buffs share the same loadout hierarchy. Each comparison retains source fights; incomplete or missing personal streams stay unknown.
