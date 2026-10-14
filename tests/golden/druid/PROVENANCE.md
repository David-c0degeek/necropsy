# Druid raw evidence

David supplied his character 110733843 (Haplina, Dragonfang EU) for balance and
restoration analysis and explicitly authorized public feral/tank leaderboard logs
as fixtures on 2026-10-14. Public Feral subject: Stinkface, Whitemane US. Public
Guardian subject: Suncat, Ashkandi US. Guardian cohort includes actual tank duty
evidence for Harryjam, Windseeker US.

These are byte-identical copies of the original production snapshot-writer
outputs. See `provenance.json`, raw ZIP checksums and member manifests. Git LFS
holds the ZIPs; ordinary CI does not need them. Fetch with `git lfs pull` before
`uv run pytest tests/golden/test_druid_replay.py`.

Scope: Classic Era, Naxxramas, partition 1, Patchwerk, user endpoint; each archive
contains the subject, five same-faction deep entries and 25 metadata rows.
Unknown pet ownership keeps acquisition partial. Metadata never fills event
medians. Raw API responses and generated selection/proofs are distinguished by
the snapshot marker and member manifests. Player names remain identifiable.

The expected arithmetic and role cases in `facts.json` are independently checked
against raw events. Role and practical-advice domain review is **pending**.
These fixtures do not certify all-raid or final product acceptance.

Two additional captures on 2026-10-15 cover Four Horsemen Guardian (Suncat
subject plus five deep entries, including mixed cat/tank Mìlfurion) and David's
Sapphiron Restoration performance. Both have complete acquisition coverage with
25 metadata rows and five deep entries. David states he mostly heals on Sapphiron;
the selected performance contains healing actions and no actor damage. His
assignment statement is user provenance, separate from inferred duty.

The extra ZIPs are byte-identical to writer outputs, renamed for distinct fixture
identities; their checksum sidecars name the new basenames. Original basenames
are recorded in `provenance.json`. Gitleaks scanned all 62,401,552 extracted bytes
of these two captures on 2026-10-15, exit 0, no leaks found.

Do not rewrite these archives when analysis changes. Regenerate derived outputs;
add a new captured archive with its own provenance for later evidence.

Secret scan: installed gitleaks scanned all extracted members (169,740,861 bytes)
with `gitleaks dir workspace/druid-scan --redact --max-target-megabytes 0` on
2026-10-14; exit 0, no leaks found. This heuristic scan is not proof of absence.
