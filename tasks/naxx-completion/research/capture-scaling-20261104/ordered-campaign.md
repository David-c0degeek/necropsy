# Ordered optimized capture campaign

Owner authorization: extend the optimization, then collect Naxxramas → AQ40 → BWL → MC. Preserve live Naxx progress and quota safeguards; do not infer accepted cells from capture completion.

## Pre-mortem — proceed with guardrails

- **PM-60 — Later raids run while Naxx is deferred or partial.** The existing serial scheduler selects the first runnable entry, skipping deferred/terminal partial entries. Use an explicitly ordered v2 queue, constrain selection to the first unfinished raid, preserve the account-wide quota gate, and stop for review if that raid ends with partial/refused entries. Clearing attention must not bypass the stage barrier. Old v1 queues retain their behavior; old runners refuse v2 queues.
- **PM-61 — Queue replacement loses existing progress.** Runner state binds to an exact queue digest. Provide an explicit locked append-only migration: old definitions must be the exact prefix of the new queue, no inflight attempt, old state identity verified, byte-preserving state backup before atomic replacement, existing entry records/quota/outbox untouched, new entries pending. Reject edits/removals/reorderings. Make retry after successful migration idempotent; do not fabricate delivered alerts.
- **PM-62 — Generalizing v4 reinterprets v3 or unsupported contexts.** Keep v3 Naxx-only. Enable other raids through the v4 contract on supported partitions only, including target-only reuse when old requested sources/critical streams are cached. Keep unknown ownership/hit-type fallback. Verify native plus independent proofs and unchanged ordered events against the six hash-pinned MC/BWL/AQ40 inputs; exercise both supported partitions and a legacy cache resume.

Implementation includes a pinned combined queue built from the unchanged 34-entry Naxx queue followed by the 93 scheduled AQ40/BWL/MC entries. Historical reuse dispositions remain explicit; no captured/partial configuration or content cell is silently marked accepted. Deployment must preserve the current worker definition/state privately and test the actual candidate image without networking before an idle swap.

## Outcomes

- **PM-60 prevented:** v2 stage selection survives deferred/retry waits and restart; a partial stage pauses for review and clearing attention does not advance it. Legacy v1 behavior remains covered. Real-image proof exercised all four successive stages without live API calls.
- **PM-61 prevented:** locked migration rejects inflight work, wrong identity, changed/removed/reordered entries and competing state owners; retry is idempotent. Actual rollout preserved all34 existing records and quota gate, appended93 pending records, retained a byte-identical backup and emitted no duplicate start alert. Eleven private recovery files matched independently onPC.
- **PM-62 prevented:** v3 allowlist is unchanged; v4 supports all four raids, including target-only legacy cache reuse. Six new raid/partition proofs and three legacy-resume cases passed. Nineteen hash-pinned corpus tests include full native/independent archive round trips; unsupported ownership/hit types retain requested scopes.

Deployed at22:06:59UTC, independently checked22:07:45UTC. Image805ee67c1c01, worker cd67af216265, queue4f1a300a7b3f. Naxx remains waiting until22:26:13UTC; all later stages are pending behind it. See [campaign-deployment.json](campaign-deployment.json) and `campaign-verification.json`. No new capture or live billed-point saving is established by this rollout.
