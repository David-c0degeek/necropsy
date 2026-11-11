# Ordered raid capture

Status: implemented in the development tree; private collector rollout recorded
in the Tower maintenance repository. Public release remains separate.

The owner requested Naxxramas → AQ40 → BWL → MC. A plain ordered list does not
enforce this: the legacy scheduler skips deferred entries and considers partial
and refused captures terminal. Later work could consume the shared allowance
while an earlier raid remains incomplete.

Queue version 2 therefore declares contiguous raid stages. Selection is confined
to the first raid with any entry short of capture-complete, including across
quota waits, transient retries and restarts. When that raid has only terminal
entries but includes partial/refused results, the controller pauses for review.
Clearing attention alone cannot bypass the barrier. Capture-complete still does
not establish content acceptance. Legacy v1 queues retain their original
behavior; old runners refuse v2 queues.

An explicit locked `extend-queue` command handles the production transition.
Existing entries must be the exact prefix of the new queue, including candidate
definitions and evidence. It requires idle matching state, preserves a synced
byte-identical backup, atomically updates the queue identity and appends pending
entries. All prior entry records, quota gates, archives, alert records and
attempt paths survive. The migration is idempotent after successful commit and
does not fabricate delivered notifications or send a duplicate start alert.

The pinned campaign combines 34 unchanged Naxx entries with 93 scheduled
AQ40/BWL/MC entries. Nine prior reuse dispositions remain outside the schedule.
Rollback requires preserving subsequent progress and matching the saved state
to its queue; an older runner cannot consume the new ordered queue or v4
archives without compatible consumers.
