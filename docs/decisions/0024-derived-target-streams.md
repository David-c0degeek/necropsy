# Derived actor target streams

Status: accepted · 2026-10-26

ADR 0016 added a whole-fight encounter-All stream to every selected fight while
keeping each actor's source and target requests. An offline measurement of the
first real Naxx v2 capture showed that every actor target request was sent with
the actor's `targetID` and still returned exactly the whole-fight data. All 97
target streams had the same page digests as their fight's encounter-All stream,
and they were 189 of the capture's 554 event pages. The measurement and its
reproducible receipt were committed in 96f728c.

For Naxxramas captures with encounter context (`DERIVED_TARGET_ZONES`), acquisition
fetches the fight's encounter-All stream first and does not request actor or pet
target streams. Each target stream is recorded as derived:

- Its page members are byte copies of the encounter-All pages, read from the
  verified All cache entry. Their entries are `generated`, not `acquired`.
- Its marker entry has `identity: null` and a `derivation` record: the rule
  `target-equals-encounter-all-v1`, the parent's exact canonical request and the
  parent's page digests. No cache entry, journal record, account reading or
  completion marker is created for it, and the cache identity contract is
  unchanged.
- An archive that contains a derived stream is snapshot format 3. Format 1 and 2
  archives are written and read exactly as before. Released readers accept only
  formats 1 and 2, so they refuse a format 3 archive at marker validation.

The format 3 reader accepts a derived stream only when it is a target stream
whose parent is the same fight's certified encounter-All proof, with the same
identity and page digests. The parent's request contract is checked again over
the derived pages, and those pages must be the parent's bytes. Mixed or missing
provenance, unknown rules, derived source streams, other raids and format 3
archives without a derived stream are refused. The ADR 0016 subset and
owned-event proofs still run.

Consumers that gate on the v2 capability accept the set `ENCOUNTER_FORMATS`
(formats 2 and 3), never format 1 or unknown formats. The DPS freezer checks a
derivation independently of the snapshot reader.

This rests on observed server behaviour, not a documented API guarantee. If
Warcraft Logs starts honouring `targetID` for these requests, a requested
target stream would become a subset of All, while a derived one stays equal to
All. Current archives already contain that whole-fight data, and every proof
still holds, so this is accepted explicitly. Re-verify with a requested sample
when the API changes or before extending the rule to another raid.

MC, BWL and AQ40 keep requesting target streams. Rollback removes Naxx from
`DERIVED_TARGET_ZONES`; format 3 archives then need a reader from this or a
later release.
