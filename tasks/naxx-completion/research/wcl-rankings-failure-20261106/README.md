# Report rankings internal error recovery

Live report y7wV3DT6ZNABYGtF fight29 repeatedly fails finalization on the
rankings field alone (HTTP200 GraphQL errors). A separate metadata query
succeeds at revision2. Partial responses are not valid snapshot evidence.

Pre-mortem guardrails:
- PM-1: accepting a partial report would silently weaken raw evidence. Discard
  the partial response and independently fetch metadata; leave unrelated errors fatal.
- PM-2: metadata fallback could accept a revised fight or another actor. Preserve
  all existing revision, fight/encounter, actor and pet validation; test revision refusal.
- PM-3: a recovered run could appear complete despite missing rankings. Mark
  every affected boss coverage incomplete with a report-specific reason.

Implementation changes only fetch.py and acquire.py relative to the installed
campaign image. No state or queue format changes. Regression tests cover both
metric query shapes, fallback snapshot writing, other-field/mixed errors and
revision mismatch. Deployment uses a child of the exact current image with
only those two source files replaced; old worker remains stopped for rollback.

Verification:96 focused acquisition/finalization tests plus265 client/CLI/
snapshot/runner tests passed;3 skipped. Ruff and mypy passed. Production image
4658ddfefd6f deployed15:48UTC; attempt038 passed the exact blocked request via
successful separate metadata validation and continued other report finalization.
Raw partial response not stored. Prior worker and four-file private rollback
bundle retained and independently verified onPC. deployed-fix.patch is the
exact two-file delta from the prior production image; other pre-existing local
campaign edits are outside this deployment delta.

Guardrail calibration: PM-1 rejection of poisoned partial content and mixed
errors passes; PM-2 revision mismatch refusal passes; PM-3 limited coverage is
asserted and snapshot writing passes. Live archive completion remains pending.
