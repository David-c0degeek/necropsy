# Capture scaling investigation — 4 November 2026

More independent allowance could materially accelerate collection. More containers or IPs alone cannot create that allowance. Creating accounts to multiply the allowance is explicitly prohibited by the published API terms; an exception would need RPGLogs' consent. No accounts, clients, proxies or additional workers were created during this investigation.

There is also a measured opportunity beyond the optimizations already attempted: a metadata-only version of the report request succeeded while database quota was exhausted. This is a query and evidence-contract investigation, not another assertion that generic caching will solve the problem.

## Measured production state

Evidence: [runtime.json](runtime.json), collected read-only from Tower at its recorded UTC timestamp; [probes.json](probes.json), two bounded live diagnostics at 13:52 and 13:53 UTC. Collector image remains d72b207a2f9c (0.7.1). Both Necropsy containers were running. No deployment or operational state changes were made. The metadata diagnostic used the existing saved user token without refreshing it, and its response was not inserted into the capture cache or journal.

The collector had 11 partial configurations, 23 deferred, zero complete, and no active child. The next scheduled retry was 14:09:56 UTC. These are capture outcomes, not accepted content cells. Partial captures can contain substantial usable evidence while retaining source limitations.

The quota diagnostic returned:

| Allowance | Spent | Hourly limit |
|---|---:|---:|
| Application | 1,736 | 3,000 |
| Database | 1,144 | 1,050 |

There were 947 seconds to reset, and user points remained available. This confirms database exhaustion despite application headroom. The returned database counter exceeds its limit; these observations do not establish the precise billing or overshoot mechanism. The limits match the beta Gold row, but account subscription and beta opt-in settings were not inspected.

The active Horde Marksmanship run had 1,556 successful journal records, captured between November 3 at 16:34 UTC and November 4 at 13:10 UTC. All 1,556 stored data digests were checked against canonical JSON. There were 1,528 acquisition records and 28 finalization records. Of all successful records, 1,191 were report queries, 310 event queries, 32 leaderboard queries, 15 subject queries and eight combatant-context/prelude queries. Successful records exclude failed requests and network retries; these counts are not point invoices. They show that event pagination alone is not an adequate explanation of this run's workload.

Recent attempts failed during combined-report finalization. The last three retained successful finalizations were at 11:06, 12:08 and 13:10 UTC. Attempts 045 and 046 then stopped on different report codes. There is incremental progress across resets, rather than evidence of repeatedly restarting the entire acquisition from nothing.

## The account-farm proposal

The API terms explicitly prohibit multiple accounts or credentials in section 2(d), and circumvention of limits in 2(e). Going beyond the limits requires express consent. This directly addresses the proposed account farm; it is not an inference from a generic video-hosting policy. [RPGLogs API terms](https://www.archon.gg/classic-sod/articles/help/rpg-logs-api-terms-of-service).

The schema describes application/database allowances for the API key. It separately states that a user's bonus allowance is shared across applications. These documents do not prove whether sibling clients owned by one account have separate effective budgets, nor whether a large fleet of new accounts would retain independent allowances in practice. No such fleet was tested. Different LAN container addresses also do not imply different public egress addresses. [RateLimitData](https://www.warcraftlogs.com/v2-api-docs/warcraft/ratelimitdata.doc.html).

If independent free allowances were explicitly authorized, the capacity arithmetic would be:

| Independent free allowances | App points/hour | DB points/hour | DB capacity vs observed 1,050/hour |
|---:|---:|---:|---:|
| 1 | 1,000 | 250 | 0.24× |
| 4 | 4,000 | 1,000 | 0.95× |
| 5 | 5,000 | 1,250 | 1.19× |
| 10 | 10,000 | 2,500 | 2.38× |
| 100 | 100,000 | 25,000 | 23.81× |
| 980 | 980,000 | 245,000 | 233.33× |

These are hypothetical sums, not attainable or permitted service guarantees. The beta lists free limits of 1,000 application/250 database points, Gold 3,000/1,050, and Platinum 9,000/3,200. New keys enter the beta; older keys may have different rules. WCL invites affected community research/theory projects to contact it. [Beta announcement](https://www.archon.gg/classic-mop/articles/help/archon-api-updates-beta).

Thus 980 free accounts would not represent 980 times the current database capacity. It would represent about 233 times its published allowance, assuming all independent budgets were usable. One cell can require subject selection, several comparison fights, identity/faction/spec checks, event pages and finalization. One cell is not one API call, and a small per-account budget may require several reset cycles for its assigned slice. Fixed one-account-per-cell allocation also strands capacity when easy cells finish before difficult ones.

A provider-approved implementation would use a work queue and a bounded worker pool, with a separate limiter for each authorized allowance. Task identities would include site, partition, report, revision, fights and evidence scope. Jobs would need leases, idempotent results, private credentials and explicit provenance. Existing checkpoints do not bind requests to credential identity: journal identities contain site, endpoint, query, variables and scope. Sharing them across accounts requires addressing permissions and provenance. The serial runner has an OS lock and a single account gate, so cloning it against the same state is not a multi-worker design. This is an architectural assessment, not implemented infrastructure.

The 980-cell example is treated as the user's hypothetical wider matrix. The current Naxx queue has 34 configurations covering 15 bosses: 510 cells. A queue entry currently spans a configuration, not an individual cell.

## A bounded diagnostic that produced new evidence

The latest failure named report Mgp1LQB46fcDh3mW, fight 26. One diagnostic used the installed report query, removed only its rankings field, and requested the expanded quota fields. It succeeded with report revision 23, fight 26, masterData and playerDetails. The database counter remained 1,144. The request's cost breakdown was 4.01 user points, zero application points before minimum-cost accounting, and no reported database component. The full quota-only diagnostic and metadata probe are retained in probes.json.

This demonstrates that this report's metadata can be obtained while its rankings-bearing finalization path is blocked. It does not measure the exact cost of the rankings field or prove the speedup of a changed capture pipeline. No extra rankings query was sent into an exhausted database allowance.

The reason this matters is visible in the source:

- `src/necropsy/wcl/client.py`: RATE_FIELDS and RateLimit retain only the older application fields. Database-aware scheduling and exact currentRequest telemetry are missing.
- `src/necropsy/wcl/fetch.py`: REPORT_QUERY combines metadata, playerDetails and rankings. Candidate inspection and finalization use this shape.
- `src/necropsy/wcl/acquire.py`: finalize_reports requests that full query again in an independent journal scope, checks revision/fights/actors/pets, then saves the combined report. Successful finalizations survive resume.
- `src/necropsy/snapshot/v1_writer.py`: archives use the finalization report sets as their report bundles.
- `src/necropsy/normalize/ingest.py`: report rankings are loaded into REPORT_RANKINGS. Removing rankings blindly would change captured/normalized evidence even if finalization validation passed.
- `src/necropsy/wcl/checkpoint.py`: successful answers are bound to exact queries and scopes. Adding telemetry to every query changes journal identities unless compatibility is designed deliberately; doing it naively could defeat reuse and repeat expensive work.

A safe change would first distinguish identity/revision validation from ranking evidence, define the provenance of each, and preserve existing readers and analyses. The measured metadata-only query provides a concrete test case. It does not authorize merging historical rankings into a newly finalized bundle without an explicit evidence contract. Likewise, a cheaper candidate screen must retain the owner's top-ranked, same-faction selection rules.

## What the earlier optimization evidence actually supports

The October 26 [capture-cost measurement](../capture-cost-20261026/receipt.json) found redundant target streams in an earlier corpus. Production already runs the later derived-target implementation: the next step is not to propose that same saving again. The [leaderboard overlap measurement](../leaderboard-overlap-20261026/receipt.json) found 22 of 874 depth-three slots sharing fights across leaderboards, with 13 coalescable acquisitions. That is about 1.5% fewer acquisitions in that sample, not a general large reduction in requests or database points. The owner declined widening the ranking window. Generic raid-wide harvesting should not be sold as a demonstrated large saving under those constraints.

More throughput also cannot manufacture missing subject fights, resolve all unknown pet ownership, or turn a source-limited capture into accepted cell evidence. These explain why zero complete configurations does not imply zero collection progress.

## Recommended course

1. Request a temporary project-specific database allowance or another explicitly approved bulk-access arrangement. The provider's community-research invitation makes this a concrete option. An unsent request is provided alongside this assessment.
2. If considering a subscription change, verify the account's actual entitlement first. The published Platinum database allowance is about 3.05 times the currently observed 1,050/hour; it cannot promise a matching wall-clock speedup or completion of source-limited cells. The older subscription page's headline limits should not override this live reading and beta documentation.
3. Prepare a focused pre-mortem and implementation for database telemetry and separated metadata/ranking queries, preserving resume identities, ranking evidence, revisions, faction/spec checks and top-three selection. Measure representative short/complex fights after a reset before estimating throughput.
4. Add concurrency only after an approved budget and scheduling design exist. Multiple workers sharing today's allowance cannot multiply it, though a future scheduler could continue genuinely DB-free work during database waits.

No current-request invoices exist for the historical failed ranking queries, so there is no defensible end-to-end speedup or completion ETA from these observations alone. The research produced two new measured facts: the live database allowance is exhausted, and the corresponding metadata-only query can still succeed.
