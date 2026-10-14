# Druid analysis

[Documentation](README.md) · [Connection guide](warcraft-logs.md) · [Reading results](reading-results.md)

Classic Era Naxxramas Druids use the same acquisition, snapshot, evidence,
report and package pipeline as Hunters. Select a WCL ranking category explicitly:

```sh
uv run necropsy analyze "https://vanilla.warcraftlogs.com/character/id/110733843" --category Balance --endpoint user --cache workspace/druid-cache --out workspace/balance
uv run necropsy analyze "https://vanilla.warcraftlogs.com/character/id/110733843" --category Restoration --endpoint user --cache workspace/druid-cache --out workspace/restoration
```

These commands use saved personal WCL credentials and acquire all supported
Naxxramas bosses. Use separate output directories for categories. Archived logs
may need the user endpoint and an eligible WCL account. Existing budget, revision,
identity, faction, pet ownership and partial-output rules still apply. Exit 4
means written partial coverage; complete pagination does not imply domain approval.
An opt-in `--wait-for-reset` permits one bounded hourly reset wait.

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

Multiple qualifying signals produce hybrid duties. Incomplete actor streams or
insufficient signals leave the aggregate role unknown. The activity spans show
the first and last qualifying casts; they are not continuous assignment windows.
No whole-fight benchmark is offered for mixed, uncertain or overridden duties.

A primary comparison needs exact known class, encounter, faction, build, WCL
category, role, metric and partition, within Classic Era Naxxramas. Different
builds remain visible in the full cohort but never fill a sparse exact-build
median. Three known metric values are required. Role-based membership is inferred;
that uncertainty carries into its medians. Metadata-only rankings never enlarge
event baselines. Cross-faction acquisition remains separate context; Druid
recommendations use the matching primary cohort only.

## Measurements and practice notes

Feral and balance detail includes cast counts and the full timestamped event
timeline with source/target names, faction and external-buff context, form intervals,
resource observations and cooldown/utility
casts. A recorded first-ten-seconds sequence is a practice example; a short or
specialized parse does not establish an optimal rotation. Event damage is the
actor's raw damage across targets, separately labelled from WCL's category score.
Hunter-specific ranking exclusions and pet/shot advice never apply to Druids.

Restoration shows effective healing, healing rate, overheal where present,
targets and spell use. WCL event `amount` is effective healing; `overheal` is
separate. Missing overheal is unknown, never zero. Raw HPS and overheal cannot
rank healing quality without assignments, incoming raid damage and other healers.

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
