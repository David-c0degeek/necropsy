# Targeted follow-up: supplement design, 2026-10-27 (D023, deferred by D024)

Status: deferred by the owner on 2026-10-27 (D024). The first slice (schema, writer, reader, freezer path and tests) is parked unmerged as a patch. Codex's checkpoint CHALLENGE (mailbox 131) found that the reader only checked that some event member exists. It did not prove each actor's pages, digests and request identity. The
candidate, ledger and participant mapping was not one to one, and the cell was not bound to the raw scope. A resumed
build must first share the strict reader's raw proofs (a neutral helper refactor across v1–v3), then fix those points,
before the orchestrator.

This is part of owner decision A (D019): cells whose admitted comparisons fall
below the minimum get more comparison players. It continues unchanged
leaderboard order, never a lower window (B denied). This design answers Codex's
CHALLENGE in mailbox 129. Codex agreed it in mailbox 130, with the guardrails
below. It covers the schema and the offline orchestration
only. Runner and queue integration is a separate, later checkpoint. D019 stays
not fully operational until both exist. Admission-missing (exclusion) cells
stay blocked on separate policy work and are never followed up here.

## S1. A separate supplement kind, not a re-labelled depth

- Marker `kind: necropsy.live-supplement`, `formatVersion: 1`, read by its own
  strict reader `open_supplement`. `open_snapshot` refuses this kind, so the
  analyzer and pages can never present a supplement as a reference cohort.
  Normal v1/v2/v3 archives and their bytes are unchanged.
- One supplement covers exactly one source cell: a configuration, zone,
  partition and encounter. The marker pins its source:
  - the source archive and entries SHA-256, plus any earlier supplements of the
    same cell (a chain);
  - the register SHA-256;
  - the admission contract digest: the DPS freezer and page validator digests,
    the detector digest and the packaged `min_same_faction`.
- Separate typed counts: `limit` (the maximum number of new deep captures),
  `examined` (ranking rows read), `captured` (new comparisons with complete
  streams), `admitted` (by the admission run during capture), and `stop`. The
  stop is one of `minimum-met`, `limit`, `exhausted`, `quota` or `refused`.
  None of these is called top_n.
- No subject fights. Admission of a comparison needs only that comparison's
  report, fight, streams and leaderboard row. The supplement is complete for
  its own comparisons and states that it holds no subject or reference cohort.

## S2. Candidate ledger and ordering

- The leaderboard is fetched fresh for the cell: configuration, partition,
  metric and the boss. Every page used is stored with its hash.
- The ledger lists every row examined in current rank order:
  - the rank position in this response and the identity (name, realm, class);
  - its status: `retained-in-source`, `attempted-in-source`,
    `attempted-in-supplement-N`, `captured-here`, `skipped`, with a typed
    reason (other faction observed, faction unknown, not a deep candidate);
  - the actor id, once known after fetch. Name+realm is never treated as an
    actor identity before then.
- Exclusion works by identity across the source and every earlier supplement,
  never by an old raw position. A player who moved up in a refreshed ranking is
  still found by identity.
- Metadata-only rows from earlier captures count as "attempted" only if a deep
  acquisition was actually tried. Otherwise they stay eligible.

## S3. Admission-driven stopping, one candidate at a time

For each next eligible candidate, in rank order:

1. Acquire its comparison streams through the normal acquisition path, with
   the same strict actor and ownership bindings, and finalize its report.
2. Write the candidate's members into the supplement checkpoint.
3. Run the DPS admission (`freeze_dps_ranking.compute`) on that candidate's
   exact published row. Record admitted, or refused with its reason.
4. Recount distinct admitted comparisons for the cell: the source register's
   admitted plus this chain's, deduplicated by name+realm.

Stop at once when the count reaches the minimum (`minimum-met`), at `limit`
new captures, when the ranking runs out (`exhausted`), or at a quota stop
(`quota`, resumable from the checkpoint). With per-candidate granularity there
is no overshoot past the minimum. Unknown and unverified states stay fail
closed: an HPS cell or a cell with production exclusions is never started.

## S4. Reports and evidence reuse

- A candidate's report bundle and streams come from the verified cache or a
  fresh fetch. A report already present in the source is reused only if its
  revision and finalization match. Otherwise the supplement holds its own
  generation with strict revision binding. Generations are never merged.
- Nothing in the source archive is mutated. A supplement never references
  external bytes by hash alone; it is self-contained for what it claims.

## S5. Detector

`comparison_followup.py` reads a source archive plus its supplement chain per
cell. It verifies the source pins and the contract digest, and counts distinct
admitted comparisons with per-row provenance (archive, supplement, ledger
position). A stale or mismatched register or chain is refused before any
network call.

## Offline first, then runner integration

1. Schema, writer, strict reader and orchestrator, behind an explicit CLI
   (`necropsy supplement REGISTER --encounter ID --limit N`), tested with fake
   WCL fixtures. Tests cover a moved rank, a guardian refusal, minimum-met
   after the first admitted candidate, exhaustion, a quota resume, a
   generation mismatch and a stale register. No live use and no queue
   migration.
2. Later checkpoint: runner and queue integration. This includes an explicit
   state and queue migration with copy-state tests, preserving all existing
   entries, the quota gate, incidents and retry progress. It is serialized
   with the main queue under one account owner, with register, chain and
   option pins in the resume keys.
3. Owner question once the mechanism is known: the spending ceiling, stated
   separately as rows examined, new deep captures and target admitted.

## Guardrails from the design review (mailbox 130)

- **Real supplement admission.** `freeze_dps_ranking.compute` requires a
  `necropsy.live-snapshot` marker today. Its raw-proof path is factored to
  verify the typed supplement contract directly. No fake normal snapshot,
  invented subject or top_n is built, and no existing live check is relaxed.
  The strict supplement reader validates every provenance, count and stop
  relationship, not only the field types.
- **Recount, never trust.** The register describes its input; it is not proof
  of admission. The detector reproduces the source's admitted identities from
  the pinned original bytes under the current pinned contract, and re-admits
  every chain candidate itself. It refuses forks, cycles, missing parents,
  duplicate identities or evidence, and any mismatch in configuration, zone,
  partition, metric or faction. A cached counter never confers acceptance.
- **Bounded attempts.** The spending limit counts every candidate whose deep
  acquisition was started, including failed or partial attempts. A slot is
  reserved before a candidate starts and survives a quota resume. Resuming the
  same partial attempt neither resets the budget nor charges a second slot.
  Ranking rows and pages examined have their own bound.
- **Sealed generations.** Each candidate's report generation is sealed with it.
  A later finalization that changes a shared report's revision never replaces a
  bundle beneath an already admitted candidate. Cache reuse needs a pinned
  request identity, complete pages and finalization, not a matching revision
  number alone. A quota stop keeps completed evidence and never presents a
  partly sealed candidate as admitted.

Offline tests add: normal archive compatibility; ordinary CLI and page refusal
for supplements; partial and corrupt supplement proofs; chain tampering and
dedupe; and attempted-budget resume.
