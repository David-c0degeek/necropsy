# Pet evidence behind comparison refusals, 2026-10-27

Question: why do comparisons in the follow-up register refuse? Would
capturing more comparison players help, or is the cause the evidence
contract?

Step 1 is diagnostic only. `diagnose.py` ran on Tower against the
Tower-original measurement archive `caa19938` and its entries. It ran in a
checkout of main `5a851b3`, before D022. `receipt.json` (`8cac77808487`) pins
the archive, the entries, the register then in force (`6476ca5cd231`) and the
producer. Activity is counted only when the archive opens strictly with no
issues and the fight's encounter-All stream reads complete; otherwise the
receipt records the scope as unknown.

Of 75 same-faction comparisons (30 admitted, 20 refused, 25 unverified, none
skipped), the 20 refusals have two causes:

- **11 "pet listings disagree".** The report catalog lists pets of the actor
  that the selected fight does not list. All 39 such catalog-only pets, across
  27 rows, are absent from their fight listing and have no source or target
  event in the certified encounter-All scope.
- **9 missing pet listings.** The fight has active guardians without any owner
  evidence: Battle Chicken ×10, Arcanite Dragonling ×2, Summoned Skeleton ×1.
  There is no summon event and no owner field. They stay unresolved.

The receipt reads the combined report catalog, not every report generation. It
does not enumerate ownership conflicts or residuals. It is not an exhaustive
ownership audit.

## Decision D022 and its effect

The DPS freezer now leaves a report-catalog pet out of one fight's admission
only when two things hold. The pet is absent from the fight's friendlyPets.
And it has no source or target event in that fight's encounter-All pages,
which the freezer certifies itself. Anything else still refuses, and ownerless
active guardians stay unresolved. The pre-mortem entries are PM-43 to PM-46.

The register regenerated on Tower with the D022 freezer is
`followup-comparisons.json` (`3717b49fddfa`). All 11 earlier "disagree" rows
now admit; `d022-new-admissions.json` (`1be1481eb68e`) lists each one with its
published amount, residual and the scoped-out pets. The 9 guardian rows still
refuse. Seven cells still need follow-up:

- Loatheb and Patchwerk, more comparisons: 1 admitted each;
- Anub'Rekhan, Gluth, Faerlina, Heigan and Razuvious, admission missing: the
  untested ranking exclusions keep them unverified.

Every committed DPS oracle replays with exactly the same difference keys under
the D022 freezer as under the previous one (53 of 53, no key added or removed).
Under both, the 51 later oracles differ only in `tool_sha256` and the two
`dps-ranking-pilot` oracles also in `page_validator_sha256`. Those differences
already existed and are not caused by D022.
