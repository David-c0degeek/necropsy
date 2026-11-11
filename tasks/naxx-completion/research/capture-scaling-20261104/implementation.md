# Acquisition optimization implementation

Authorized: separate metadata validation from ranking acquisition, add database/cost telemetry, and investigate further collection savings while retaining the top-ranked same-faction evidence standard.

## Pre-mortem

Failed future: the optimization seems fast because it silently drops ranking evidence, reuses a different revision, or bypasses old checkpoints and redownloads the corpus.

- **PM-54 — High — lost resume work.** Evidence: Journal hashes exact query text, variables, site, endpoint and scope. Guardrail: inject expanded quota fields only on the wire; saved identities remain stable. Metadata queries may read an explicitly declared full-query superset from the same journal scope. Finalization may reuse an acquisition answer only with independent fresh metadata validation. Verify network-disabled legacy resume and corruption rejection. Resolution pending implementation.
- **PM-55 — High — mixed or invented report evidence.** Evidence: final report bundles feed normalization; rankings can change independently of revision. Guardrail: retain an exact acquired API report object with its rankings. For a singleton report set, independently validate current metadata and retain the original report rather than splicing responses. Multi-fight sets keep their existing combined full-query path. Reject changed revision/identity/fight bounds and preserve actor/pet/faction proofs. Verify archived report evidence and old reader compatibility. Resolution pending implementation.
- **PM-56 — High — quota telemetry creates false readiness.** Evidence: application headroom coexists with exhausted DB allowance; replayed readings are historical. Guardrail: parse optional DB/cost fields defensively, never update live allowance from journal hits, persist each actual HTTP attempt separately from successful response checkpoints, and distinguish known quota errors from retryable HTTP throttling. Verify exhausted DB permits metadata-only work, blocks rankings, and resets retain existing pacing semantics. Resolution pending implementation.

Pressure test: behavior/contract, persistence, quota failure/retry, evidence provenance, mixed-version rollback and detection categories reviewed using the pre-mortem skill reference. Metadata reuse must not make current ranking claims; raw rankings retain their capture provenance.

## Implementation sequence

1. Add wire-only expanded quota fields, optional database readings/per-request costs, and a sanitized append-only network usage ledger. Preserve legacy journal keys and historical replay behavior.
2. Use ranking-free metadata for faction/candidate screening and event acquisition. Fetch ranking-bearing reports only once per combined selected report set at finalization, reusing legacy full answers when present.
3. Finalize singleton report sets with cheap independent metadata validation while retaining the exact acquired ranking-bearing report; preserve existing combined-report behavior for multi-fight sets and all old successful finalization answers.
4. Audit boss/fight reuse, selection dimensions and event redundancy against real archives. Implement additional savings only when the evidence contract and regression proof support them; record remaining opportunities and measured bounds.
5. Run focused failure/resume/provenance tests, ordinary required checks, relevant raw/golden/browser controls, and an independent review if available under the active workflow. No deployment or source-data acceptance follows from a unit-test pass.

Rollback: existing successful request records and archive formats remain readable; new metadata queries and usage telemetry are additive. Do not rewrite or delete old journal/cache entries. Leave Tower's running image unchanged until build and operational verification are concrete.

## Close-out

The implementation and deeper survey are recorded in [implementation-results.md](implementation-results.md).

| Risk | Resolution | Evidence |
|---|---|---|
| PM-54 | Mitigated | Wire-only telemetry keeps journal identities; explicit same-scope supersets reuse legacy answers; independent finalization scope is enforced even outside the CLI. New legacy-replay and scope tests pass. |
| PM-55 | Prevented for this implementation | Exact original API objects are retained or the original full combined query is used; no response splicing or new archive format. Strict archive read, metadata-drift controls, 52 raw golden replays and 96 browser tests pass. |
| PM-56 | Mitigated | Optional DB/cost fields stay unknown when malformed; replays do not update live budget or usage ledger; structured point exhaustion stops while transient throttling retries. Focused regressions and the full fast suite pass. |

The predicted major failure modes were not observed in the completed checks. The deeper survey did uncover four cases that defeat a naive source-stream projection: ownership must include catalog units absent from the fight pet list. No filtered source/critical derivation was promoted into production evidence. Live throughput and new-image behavior remain unmeasured until rollout; unit/raw replay passes do not claim them.
