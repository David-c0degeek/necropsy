# Capture-cost measurement, 2026-10-26

This is an offline measurement of where one real v2 Naxx capture spent its
requests, and which event pages repeat data the capture already holds. It is
not a capture change. Any change to acquisition, the snapshot reader or the
engine needs its own plan and pre-mortem.

```powershell
uv run python tasks/naxx-completion/research/capture-cost-20261026/measure.py
```

Check mode writes nothing. It fails if a fresh measurement differs from
`receipt.json`.

## Inputs

The inputs are pinned by SHA-256 in the receipt:

- **Measurement archive.** The registered measurement archive, from Git LFS:
  89 fights in 73 report sets, with 194 actor streams, all Balance DPS
  Alliance.
- **Production copy.** All 724 of its event members are byte-identical to the
  measurement archive. It is a second serialization of the same events, not
  an independent sample.
- **Capture queue.** The pinned 34-entry capture queue, checked against its
  `.sha256` pin.
- **Request journal.** The measurement run's 916-request journal, retrieved
  read-only from Tower into the ignored workspace. It remains on Tower under
  `/mnt/user/appdata/necropsy-naxx-measurement-20261022/data/out/naxxramas-druid-balance-dps-alliance/candidate-0/.necropsy-run/requests/`.
  A clean checkout needs that tarball restored at the receipt's workspace path
  before replay.

## Findings

Every rule below is an exact match for the observed rows of this corpus. None
is a certified statement of how the API selects events in general.

- **Actor target streams duplicate the fight.** The journal shows all 189
  actor target requests were sent with the actor's `targetID`. Every response
  carries the same event data as the encounter-All response for the same
  window. In the archive, all 97 target streams equal their fight's All stream
  as event multisets. These requests are 189 of 554 event pages (34%).
- **Actor source streams are derivable from All.** All 97 equal the rows of All
  whose sourceID or targetID is the actor or one of the fight's listed owned
  units. A first narrower rule (target only the actor) left six streams with
  extra rows. Codex showed that each of those rows targets a listed owned
  unit, from Sapphiron, Blizzard, Loatheb or the environment. The rule here is
  the one that matches all 97, with no counterexample in this corpus.
- **Critical streams are contained in All.** All 89 equal "damage with hitType
  2, 5 or 17" over All. No critical row carries `isCritical`, so the server's
  filter `isCritical = true` cannot be reproduced from that field. The
  critical request's identity is bound by ADR 0016. A derived replacement
  would therefore need its own proof of filter membership.
- **Report queries dominate the hourly points we can see.** Of the 9523
  account points measured between consecutive journal records:
  - `NecropsyReport` accounts for 71%: 322 requests over 190 distinct reports.
    No full request identity repeats. 60 parameter sets appear in both
    acquisition and finalization. Those are independent answers by design,
    because finalization re-reads the report, so they are not reusable
    duplicates. 308 requests ask for a single fight.
  - Actor source requests account for 28%, almost all in a few large jumps.
    Only 38 of 97 show any change, with a maximum of 1766.
  - Event requests for All, target and critical register at most 1 point
    each.

  These are account-wide readings, not per-request invoices. The separate
  database allowance that stalled earlier runs is not visible in them.
- **Queue overlap is small, and fight overlap is unmeasurable from the
  queue.** The pinned queue has 34 entries, 94 candidates and 92 distinct
  characters; 2 characters appear in more than one entry. The queue pins
  characters, not fights: fights are chosen from leaderboards at capture
  time, so the originally planned report/fight overlap across entries is not
  measured here.
- **Each captured fight could serve other configurations.** Each fight's report
  bundle already holds published ranking rows and faction-bearing player
  details for 9–14 (median 11) of the 34 legal configurations. That is
  potential reuse only: cohort selection, ownership and stream completeness
  for those actors are not established.

## Recommendations, each a separate plan

1. **Stop requesting actor target streams when the fight's All stream is
   captured.** This has the highest confidence, because the server returned
   identical data for all 189 requests. Reader, `actor_problems`, the fact
   freezer and the HPS/DPS tools must take target observations from All, and
   all existing archives must keep replaying byte-for-byte.
2. **Cut report-query cost.** Batch one report's fights into one request where
   the selection allows it. This is the largest visible hourly-point lever.
   Finalization keeps its independent first answer. Any reuse across
   acquisition and finalization needs its own replacement proof.
3. **Reuse captured fights across configurations.** This needs eligibility,
   ownership and cohort rules for actors taken from another configuration's
   capture.
4. **Derive source streams only after a plan proves the rule.** Source streams
   match a simple rule here, but one corpus does not certify it. Keep critical
   requests, because their filter identity is contract-bound.
