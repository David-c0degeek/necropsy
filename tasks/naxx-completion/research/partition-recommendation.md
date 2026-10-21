# Naxx partition evidence and recommendation (draft)

Recommendation: scope initial Naxx completion to partition 1 (S0), 510 cells. Keep partition 2 (S0 without world buffs) a separate prospective scope; if adopted, its cell keys and denominator must be extended explicitly. This is a scope recommendation, not a claim that partition 2 is unavailable or illegal.

## Direct observations

- Live official user-endpoint zone 2006 metadata returns partition 1 S0 as default and partition 2 S0 (Without World Buffs) as nondefault. Raw request/variables/UTC timestamps/HEAD/data/rate readings are retained under partition-probe/.
- Page 1 of Patchwerk (51118) was requested for both partitions across all 20 distinct class/category/metric pools underlying 34 faction configurations. This is one encounter and one page, not whole-raid or exhaustive faction availability.
- Partition 1 returned rows in all 20 pools; partition 2 returned rows in 18. Protection Paladin DPS and Enhancement Shaman DPS returned zero rows in partition 2. Those are sampled gaps, not unavailability findings.
- Rows are not necessarily positive performance. Partition 2 Balance HPS returned 22 rows but only one positive amount; Protection Paladin partition 1 returned 88 rows but only 32 positive amounts. Retain amounts and do not count zero as useful healing evidence.
- Character identity lookups observe current faction/class/hidden state. They do not prove historical fight faction, an owned-unit listing, complete streams, whole-raid coverage, or actor identity within the report. Metadata lookups check report visibility and positive fight IDs/encounter kill, not acquisition completeness. Unknown character factions remain unknown.
- Bounded candidate verification attempted indices 0,1,2,4,9,19,49,99, stopping once both legal current factions had witnesses or at the cap. Detailed availability-summary.json covers 37 fully attempted pools; the final three partition-2 Shaman pools were not fully attempted before the cap. validated-pools.json recomputes all available cached witnesses for all 40 ranking requests; neither summary certifies all 68 partition/configuration combinations usable.

## Partition-2 integration gap

- All nonempty sampled partition-2 pools use negative report.fightID values. Example: Warlock ranking report 7H8D2fFtbyndBJVc fight -29; public report metadata contains Patchwerk kill +29. The signed representation is retained unchanged.
- cohort.py candidate parsing accepts only fight > 0; acquire.py subject ranking validation likewise requires a positive fight. Thus currently returned partition-2 rows do not enter normal acquisition. This is an actual software compatibility gap, not absence of public rankings.
- Do not fix this by blindly taking abs(). Verify the official representation, report/fight/encounter identity, character identity and partition semantics; then add focused request/response fixtures before partition-2 acquisition is accepted.

## Per-configuration evidence

See partition-configurations.csv (34 rows), with separate row/positive-amount counts and observed current-faction/public-kill witnesses. Partition-2 magnitude matches are corroboration only; they are not direct accepted fight bindings. Zero witness count can mean sampled lookup failure, unknown current faction, no sampled positive amount, missing report metadata, or budget-limited coverage. It is never an N/A decision.

| Class | Category | Metric | P1 rows / positive | P2 rows / positive | P2 negative IDs |
|---|---|---|---:|---:|---:|
| Warlock | Destruction | dps | 100 / 100 | 100 / 100 | 100 |
| Warrior | Fury | dps | 100 / 100 | 100 / 100 | 100 |
| Warrior | Protection | dps | 100 / 100 | 100 / 100 | 100 |
| Druid | Balance | dps | 100 / 100 | 22 / 5 | 22 |
| Druid | Balance | hps | 100 / 100 | 22 / 1 | 22 |
| Druid | Feral | dps | 100 / 100 | 12 / 12 | 12 |
| Druid | Guardian | dps | 100 / 100 | 13 / 13 | 13 |
| Druid | Restoration | hps | 100 / 100 | 100 / 100 | 100 |
| Hunter | Marksmanship | dps | 100 / 100 | 100 / 100 | 100 |
| Mage | Fire | dps | 100 / 100 | 100 / 100 | 100 |
| Mage | Frost | dps | 100 / 100 | 64 / 35 | 64 |
| Paladin | Holy | hps | 100 / 100 | 100 / 100 | 100 |
| Paladin | Protection | dps | 88 / 32 | 0 / 0 | 0 |
| Paladin | Retribution | dps | 100 / 100 | 20 / 4 | 20 |
| Priest | Holy | hps | 100 / 100 | 100 / 100 | 100 |
| Priest | Shadow | dps | 100 / 100 | 24 / 6 | 24 |
| Rogue | Assassination | dps | 100 / 100 | 100 / 100 | 100 |
| Shaman | Elemental | dps | 100 / 100 | 10 / 1 | 10 |
| Shaman | Enhancement | dps | 100 / 100 | 0 / 0 | 0 |
| Shaman | Restoration | hps | 100 / 100 | 100 / 100 | 100 |

## Budget and provenance

- Zone metadata first reading: 3000/hour, spent 1. Last retained candidate response: spent 285.4. No concurrent WCL workload was reported by Claude; Tower remained stopped. These account readings are not an exact marginal per-query tariff. The probe stopped with headroom and made no event-stream/capture requests.
- Every retained JSON file is SHA256-pinned in partition-evidence-manifest.json. Original draft scripts are naxx_partition_probe.py and naxx_candidate_probe.py. A read-only summary recomputed positive amounts and direct versus magnitude fight matches after the exploratory probe; the raw responses remain unchanged.
- Public primary sources establish independently selectable cohorts, not exact actor availability: [official Naxx statistics](https://vanilla.warcraftlogs.com/zone/statistics/2006), [official partition schema](https://ru.warcraftlogs.com/v2-api-docs/warcraft/partition.doc.html), [official ranking guide](https://vanilla.warcraftlogs.com/help/ranks). Vanilla schema direct browsing returned 403; authenticated introspection is retained in encounter-schema.json.

## Capability decision

- Adopt existing repository WclClient + Auth + OS credential store, no setup/install or new permission. Read-only queries remain on the existing allowed Vanilla user endpoint. This preserves current error, budget and credential handling.
- No WCL-specific connector was exposed in the live tool inventory or available skill catalog. Existing capture_queue and cohort query builders are prior art; no duplicate product capture layer is proposed.
- Defer [vinylflamingo/wcl-mcp](https://github.com/vinylflamingo/wcl-mcp): discovered by concrete-name web research; it adds a Node service plus client-secret environment configuration and installation/trust review, while existing approved tooling already performs the required queries. No install/configuration change made.

## Proposed executable decision

Record partition 1 only for this plan; keep 510 as the current denominator. All applicable partition-1 cells must still complete, with sampled faction/stream gaps OPEN until normal candidate resolution and capture validate them. Partition 2 remains a distinct unimplemented extension requiring signed fight-ID semantics and partition-bearing cell identity. Do not add partition-2 cells, waive partition-1 cells, or promise quota throughput from this sample.
