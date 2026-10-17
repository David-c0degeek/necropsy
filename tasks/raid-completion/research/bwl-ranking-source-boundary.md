# BWL ranking-source boundary — 2026-10-17

New primary-source research; no ranking rule is activated by this note.

[WCL/Archon March2025 launch announcement](https://www.archon.gg/classic-mop/articles/news/bwl-on-fresh-warcraft-logs)
explicitly compared the then-new Fresh rules to Era, described a boss-damage
default and excluded opening stages for Razorgore/Nefarian. This supports
investigating WCL fight bounds and target metrics separately from guide stages;
it does not supply exact event boundaries or certify our per-class arithmetic.

The [June2025 updated Fresh policy](https://www.archon.gg/classic-mop/articles/help/fresh-blackwing-lair-parsing-and-speedrun-rules)
explicitly excludes Era/Hardcore from its scope. Its complete-raid restrictions,
PI treatment, consumable limits and speed penalties cannot be imported into this
Era implementation from similarity or an earlier shared launch statement.

The [generic WCL rankings guide](https://classic.warcraftlogs.com/help/ranks/)
explains metric/partition distinctions and foreign-trash treatment. It does not
provide every Era boss's native-add, healing, pet, Ignite or denominator policy.

Continue exact public Era report/actor score reconciliation with native target,
instance and fight bounds, preserving sampled data/rounded score precision.
Combined50631 remains separate from individual50614/50615. Native aura state is
not physical attackability; guide stage descriptions and nominal timers do not
fill missing WCL phaseTransitions. Until verified, ranked totals remain unknown.

[Live Vanilla API enum receipt](wcl-ranking-metric-enums.json) confirms distinct
`dps` and `bossdps` arguments for both character and report ranking queries.
Current acquisition explicitly requests`dps`/`hps`; the site's default display
must not silently change that metric or supply a target exclusion rule. A future
metric change would require scope/cache/archive/document compatibility review,
not a string replacement or a rewrite of frozen scores.
