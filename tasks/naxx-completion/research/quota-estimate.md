# D007 Naxx v2 capture quota estimate (draft)

No cold-capture quota floor is provable from these records. The MC measurements support a planning scenario and a first-capture measurement plan; they do not establish Naxx throughput.

| Historical MC run | Actor contexts / distinct fights | Player / pet pages | All / critical pages | Retained successful requests | Positive adjacent account-point deltas |
|---|---:|---:|---:|---:|---:|
| Holy Paladin | 60 / 59 | 127 / 0 | 66 / 59 | 476 | 1547.30 |
| Holy Priest | 60 / 57 | 122 / 0 | 59 / 57 | 357 | 1471.84 |
| Restoration Shaman | 60 / 58 | 132 / 37 | 70 / 58 | 538 | 1687.45 |

All three cover ten bosses and stopped=null. Exact archive paths, SHA256s, journal directories, checkpoint hashes, capture windows and journal catalog hashes are recorded in quota-estimate.json.

These October 17/18 readings had a 1800-point/hour key limit. Root separately reports 3000 from its October 21 live zone probe. Those observations are separate: this reviewer made no live API request, and did not independently inspect that probe's timestamp/key identity or infer currently available points.

Chronological retained-query deltas have median 1 point for events and 6.01 for report queries in every run. Paladin All 66 pages showed 66 account points; Shaman All 70 pages showed 70. Priest All 59 pages showed 79.04, illustrating why metadata is not an exact per-stream invoice. Snapshot stream metadata explicitly says account-wide between readings. Do not sum it with journal expenditure.

For a deliberately MC-shaped illustration only: 15/10 times the retained sums gives 2207.76–2531.175 points per 15-boss configuration. At 34 configurations (510/15), that is 75063.84–86059.95 points, or 25.02–28.69 gross 3000-point hourly-cap equivalents before budget share/reserves. This is neither a lower/upper bound nor a wall-clock/reset forecast. Initial spend, shared account activity, cache hits, missing/forgotten requests and reset gaps prevent attributing these sums to a complete cold capture.

Horsemen duration/multiple NPCs, Gothik waves and KelThuzad phases can add substantial whole-fight All/critical pagination. Healing/damage source-target streams and owned units also differ by configuration. Existing v1 Naxx actor captures cannot establish the missing whole-fight v2 page costs.

Official WCL [RateLimitData schema](https://www.warcraftlogs.com/v2-api-docs/warcraft/ratelimitdata.doc.html) defines key limit, spent points and reset seconds. It also lists currentRequest JSON in the common schema, which our historical queries did not select; Vanilla-specific docs returned 403, so do not assume support without normal schema verification. No authoritative numerical per-page tariff was established.

Next measurement: retain normal quota safeguards and one API owner; on the first normal successful v2 Naxx acquisition, preserve complete timestamped request readings (including resets/retries/cache reuse), page/event counts and report/fight/actor identities. Compare a short fight and at least one Horsemen/Gothik/KT fight before estimating bulk windows. No probe bypass, forced faction, reserve reduction or custom cache change is justified by this scenario.
