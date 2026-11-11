# Acquisition optimization results

The implementation removes report-ranking calls from candidate screening and event acquisition. New captures fetch ranking-bearing reports once per combined selected report set, at finalization. Existing singleton ranking-bearing acquisition answers can finish with an independent metadata-only validation. Database quota and per-request cost telemetry are persisted separately from replayable acquisition answers.

This is implemented and tested in the working tree. Tower's running 0.7.1 image has not been replaced, and no live throughput improvement or completion ETA is claimed.

## What changed

- Candidate faction/identity checks use a smaller query: report revision, the selected fight's identity/bounds, actor identity and playerDetails. They do not fetch rankings or the ability catalog.
- Selected entries acquire full metadata and events without report rankings. Finalization fetches the combined ranking-bearing report exactly once for the selected fights of each upload. Its successful answer remains resumable in the independent finalization scope.
- Legacy successful queries keep their exact logical request identities. Expanded quota fields are injected only into the HTTP payload. Screening/metadata queries can read declared full-query supersets from the same scope; they cannot use an acquisition answer as independent finalization validation.
- A legacy single-fight ranking-bearing answer is retained as an exact API object only when an independent metadata response matches every non-ranking field. Changed metadata and multi-fight sets use the full report path. There is no splicing of old ranking rows into a new report response or new archive format.
- `RateLimit` retains optional database limits/usage and WCL's request-cost breakdown. `auth status --check` prints the DB allowance. Malformed optional fields remain unknown.
- `.necropsy-run/usage.jsonl` records each actual HTTP attempt with operation, request identity digest, endpoint/scope, status, current quota and supplied costs. Replays add no entries. Missing costs remain unknown; this is a diagnostic ledger, not an invoice or checkpoint.
- Known structured point-exhaustion errors on HTTP 429 stop immediately. Ordinary throttling still honors Retry-After and bounded retries. A known exhausted DB allowance prevents fresh ranking calls while permitting metadata calls and saved-answer replay.

## Measured request reduction

[request-comparison.json](request-comparison.json) compares the pre-change acquisition module from its recorded Git commit with the new module, using identical fake-server data and cache/transport dependencies. Both cases preserve the same 25 metadata rows, three comparison players and complete subject.

| Synthetic workload | Ranking-bearing report requests before | After | Total HTTP requests before → after |
|---|---:|---:|---:|
| Selected fights in separate uploads | 30 | 4 | 40 → 43 |
| Selected fights in one upload | 27 | 1 | 37 → 40 |

This is an 86.7% and 96.3% reduction in ranking-bearing report requests in these cases, **not** a measured reduction in total points or wall-clock time. Total HTTP requests increase by three: the optimization trades small metadata requests for removal of expensive ranking fields. The earlier live diagnostic in [probes.json](probes.json) established that the metadata-only query succeeds for user points while DB quota is exhausted.

Report grouping also means several selected fights in the same uploaded log need only one combined report-ranking request. The top-ranked same-faction selection and 25-row metadata context were not reduced to make the result look cheaper.

## Boss/fight collection versus class views

The user's proposed physical unit is correct: a unique boss fight can supply encounter data for every player in it. Its whole-fight request has no class/spec filter. The existing shared cache already keys that scope by site, endpoint, report, revision, fight and request options rather than by class. Actor-specific views do not require fetching encounter-All again when that exact cached scope exists.

Selection still needs separate class/category/metric/faction eligibility. A good Warrior parse does not establish that the Priest in the same kill is a top-three Priest comparison. Once the required top players' fights have been selected, the union of their exact fight identities is the physical collection set. Shared uploads can also combine report-ranking work even when the selected fights differ.

There are 20 class/category/metric combinations and 34 legal faction-specific configurations in the present matrix, not nine classes times three interchangeable specs. Naxx currently requests three independent comparison players **plus a subject** for each boss/configuration. Thus its nominal maximum is 102 comparison slots plus 34 subject slots per boss before overlap, candidate refusals and source limitations. Three actors in one fight need one whole-fight scope, not three. A slot is neither a unique fight nor an API request.

Changing the primary/comparison evidence model to use only three total players would be a different behavior change: the existing view excludes its subject from the minimum-three comparison cohort. That standard remains intact here.

## Deeper raw-data audit

[corpus-survey.json](corpus-survey.json) is produced by [inspect_corpus.py](inspect_corpus.py) from six registered Druid configuration archives plus a read-only copy of the completed Hunter Alliance archive. Every input is bound to its whole-file SHA256 and member manifest. The Hunter copy is retained outside Git at `workspace/capture-scaling-20261104/hunter.zip`; its expected SHA256 is `98a2d5a39d3b85dfee8db0b777b1c74cbef11656138baa5b7b892302311050a1`. It was copied from the matching completed production snapshot, not generated or admitted as new cell evidence.

Results:

- 435 captured fight occurrences, 434 distinct exact fight identities, one cross-configuration duplicate.
- 7,511,279 encounter-All events in 999 pages.
- All 435 critical streams equal an exact ordered projection of encounter-All using damage events with hitType 2, 5 or 17.
- All 529 actor-source streams equal an exact ordered projection using sourceID/targetID membership in the actor plus its transitively owned report-catalog/fight units.
- The simpler fight-pet-list-only projection fails four times. [source-residuals.json](source-residuals.json) records those diagnoses: the missed events belong to catalog-owned units absent from friendlyPets. They are present in encounter-All; including the report ownership graph resolves all four cases.
- The corpus has 281 singleton report sets and 65 multi-fight report sets. The new fresh-capture path prices ranking acquisition per report set; the legacy fast path can avoid re-buying singleton rankings.

The single duplicate supports a small deduplication opportunity in this historical sample, not a global guarantee. The previous top-three leaderboard study likewise found limited exact-fight overlap. This does **not** invalidate boss-based acquisition: it shows that most of the selected fights are genuinely different under the existing ranking rules.

## Further event reduction: initial candidate (subsequently implemented)

After the already-shipped target-stream reuse, this corpus still fetched 529 source pages and 435 critical pages alongside its 999 encounter-All pages. Replacing those extra event requests with the verified ordered projections would remove 964 of 1,963 event-page fetches, about **49.1% in this sample**. This is event-page arithmetic, not DB-point savings or a prediction for another corpus.

At the end of the metadata-only implementation pass, the raw equality checks made this the next candidate. Snapshot v3 accepts derived actor targets only and certifies their parent bytes. Filtered actor sources and critical streams required a new derivation contract/version, strict projection validation in the reader, compatible freezer/oracle tooling and fallback rules for unsupported ownership/hit-type data. Calling a projected stream an API response would destroy provenance; using friendlyPets alone demonstrably loses data. The subsequent owner-authorized implementation is recorded in [v4-results.md](v4-results.md); this section preserves the initial measurement rather than claiming it was already enabled during that earlier pass.

## Verification

- Ruff lint and formatting pass; mypy passes all 289 checked source files.
- Maintained documentation link check: 299 links checked.
- Fast suite: 2,814 passed, 29 skipped.
- Golden raw replay suite: 52 passed (`test_raid_evidence.py -k seed_capture`).
- Browser suite: 96 passed.
- Focused new regressions cover legacy replay without credentials/HTTP, historical-budget isolation, exhausted DB versus metadata, structured quota stops versus transient throttling, unchanged comparison selection, finalization scope restoration and retention of raw ranking evidence through a strict archive read.

Commands/logs and changed-file hashes are retained in verification.json and the ignored workspace. No archive intake, ranking policy, content cell or product acceptance was changed. A release/image build and installed live capture verification remain rollout work; the production collector is unchanged.
