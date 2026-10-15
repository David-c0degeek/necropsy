# Resumable acquisition and current installs

The v0.1.0 install predates the coaching redesign. Build a distinct 0.1.1
artifact, verify its embedded assets outside the checkout, and document upgrades.
Do not move the old release tag or silently replace its published artifacts.

Pre-mortem guardrails:

- PM-1 (high): starting over after every quota reset spends the next allowance
  replaying work and may never finish. Persist successful acquisition requests,
  including individual event pages, and finalization responses in separate
  namespaces. Never persist failures or authentication material. Replay must not
  replace the current rate reading with the saved reading. Verify a stop/reset/
  resume run makes forward progress without requesting successful pages again.
- PM-2 (high): a resumed run mixes characters, specs or revisions, or overwrites
  unrelated outputs. Bind the checkpoint to options and resolved context; retain
  revision checks and invalidate a report's saved requests on revision changes.
  Keep the output lock, require explicit --resume, and verify output digests
  before replacing partial pages. Keep previous snapshots. A checkpoint captures
  a historical acquisition across attempts; a successfully finalized report need
  not be re-fetched on every attempt. No global point-in-time claim is made.
- PM-3 (medium): a wheel builds successfully but ships the old presentation.
  Check installed report/playbook identity markers and embedded asset equality
  against the checkout, as well as package integrity.

Implementation order: progress UI; request journal and resume ownership; quota
and interruption regression checks; versioned wheel, clean install and docs.

The Druid/spec comparison reserve previously scaled with the full raid's
estimated finalization cost. On a small allowance that reserve can exceed a
whole hour's quota, blocking new work even after every reset. Journal-backed
runs cap the reserve at half the permitted budget; finalization itself can now
continue across attempts. Non-journal acquisition keeps its previous reserve.
A focused small-quota regression checks this progress guarantee.

Disposition: proceed with the guardrails above.

- PM-1 — Mitigated. [evidence: `wcl/checkpoint.py:Journal`,
  `test_resume_after_quota_stop_partway_through_event_pagination`,
  `test_resume_reuses_reports_finalized_before_a_quota_stop`,
  `test_small_quota_keeps_room_for_comparisons_when_finalization_can_resume`]
  Successful requests survive stops; finalization spans attempts; the capped
  reserve leaves comparison headroom. API permissions and reset timing remain
  external constraints.
- PM-2 — Mitigated. [evidence: `Checkpoint.bind`, `Checkpoint.__init__`,
  `Run.bundle`, `finalize_reports`,
  `test_resume_refuses_changed_options_or_modified_outputs_before_credentials`]
  Context/options and owned-file digests are checked, report revisions still
  invalidate incompatible data, and leaderboard capture times survive replay.
  The existing publisher's crash-during-multi-file-publication limitation remains;
  ambiguous/modified files cause a refusal rather than automatic overwriting.
- PM-3 — Prevented for the built wheel. [evidence:
  `scripts/check_distribution.py:main`, `workspace/distribution-0.1.1.json`]
  Clean installed replay checks design markers and exact embedded asset bytes.
  The old published tag is documented as old; its artifacts are not replaced.

Verification: 218 focused tests passed; Ruff checks/formatting and strict mypy
passed (156 source files). A clean wheel install exercised synthetic public auth,
offline replay, package integrity, current design and artifact secret scans.
Live account/quota testing was not performed; quota/reset cases use fake WCL.
