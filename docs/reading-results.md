# Reading your results

[Home](../README.md) · [Documentation](README.md) · [JSON reference](analysis-json.md)

Check the subject and snapshot, then the boss's comparison sample, then its
recommendations. Use the evidence to decide how much weight to give a finding.
This guide describes `analysis.json`; the visual report is planned.

## Choose a fair comparison

Top-level `subject`, `zone`, and `snapshot` identify the character, raid, and
archive. `snapshot.scope` distinguishes a full export from a selected subset.
The historical fixture records the overall top five per boss, not a separately
fetched same-faction top five.

| View | How to use it |
|---|---|
| Same-faction baseline | Median execution and adoption among your faction in the recorded cohort |
| Same-faction ceiling | The best-ranked entry of that faction inside the recorded sample |
| Tauren fill | A separate fallback for unavailable execution medians; advice using it has low confidence |
| Cross-faction | Optional context from `--cross-faction`; it does not replace the baseline |

A median needs **at least three known values**. Check `n_known` before comparing
numbers. Tauren fill requires a proven Tauren race and trusted, complete
`not-observed` Windfury evidence. It never fills kill time or weaving; only Aimed
cadence and pet-DPS recommendations consume it. This fallback is independent of
the optional cross-faction view. No logged Windfury proc does not establish that
the buff could never have been available.

Faction can be inferred. That uncertainty carries through membership, medians,
projected shot ranges, and the ceiling, and lowers recommendation confidence.

## Know what a value means

| JSON level | Plain-language reading |
|---|---|
| `observed` | A log event or API field records it |
| `derived` | Necropsy calculated it from recorded data |
| `inferred` | A named rule suggests it; the rule can be wrong |
| `unknown` | The available data cannot support an answer |

Unknown is **not zero**: `value` is `null`, with a `note` explaining why.
Incomplete pet streams can prevent reliable DPS; a small sample can prevent a
median.

`claim` adds another distinction. A `value` claim describes what is present.
A `complete` claim depends on complete, trusted coverage, including statements
that something did not happen. A subject's 0% target share is coverage-backed
absence of damage, rather than missing data.
[The evidence model](evidence-model.md) defines the exact contract.

## Read the boss context first

**Kill time.** `benchmarks.raid_speed` compares with both the same-faction median
and the fastest same-faction kill. A flag uses the median at 1.5× when at least
three kill times are known; otherwise it uses the fastest kill at 2.0×. Fastest
means shortest duration, separate from the best-ranked DPS ceiling. Both views
remain present when no flag fires. The ratio does not identify a cause.

**Weaving.** Adoption has separate `boss` and `non_boss` roles. Non-boss means
other hostile NPCs, including encounter adds and trash. Counts matter: two out
of five using Raptor Strike does not meet the 50% heuristic threshold. Unresolved
identity or side, or a non-NPC target, makes role counts unknown.

**Damage targets.** `ranking.by_target` retains individual targets and their
`counted`, `excluded`, `own`, or `unclassifiable` ranking categories.
`encounter.ranked_target_shares` compares stable NPC identities, retains alternate
labels as aliases, and groups player and pet damage into clearly named categories.
Check `n_known` and `n_unknown`; incomplete fights do not contribute invented
zeros. Ranking exclusions are empirical rules validated against recorded
rankings, rather than documented WCL guarantees.

**Gothik's trash.** Target integrity separates native units, start trash, and
foreign targets. Spirit of Naxxramas is start trash in the recorded classification
and does not count as foreign padding. Missing identity makes the split unknown.

**Assignments and pets.** Friendly crowd control can provide context for lost shot
windows. Pet death or an early end to damage deserves a review of mechanics and
assignments. An Auto Shot gap is an advisory signal, not a diagnosed clip.

## Turn recommendations into a review list

Each recommendation includes a finding, a suggested action, confidence,
limitations, and `evidence` paths into the same boss section. Follow those paths
before deciding what to change.

`controllability` separates execution, gear/build, pets, raid assignments,
raid speed/environment, faction/racial/external differences, and RNG context.
Confidence (`high`, `medium`, `low`) is a heuristic evidence-quality tier, not a
probability. Severity is a separate tier. Recommendations do not estimate a
guaranteed DPS gain.

[Explore the output fields and schema →](analysis-json.md)
