# Raid evidence register

The packaged `raid_scope.yaml` and existing encounter/category catalogs define
952 legal configurations: 28 encounters × 34 category/metric/faction choices.
Declared talent trees remain independent context. The combined BWL dragon
encounter is a distinct obligation. Era partitions 1/2 remain separate cohorts;
Season of Mastery and Hardcore catalog entries do not approve Era policies.

`coverage.json` records evidence against stable keys
`raid/encounter/class/category/metric/faction`. Missing records mean TODO.
The partial register deliberately certifies no complete domain cells.

```sh
uv run python scripts/check_raid_coverage.py --inventory
uv run python scripts/check_raid_coverage.py --inventory --staged
uv run python scripts/check_raid_coverage.py --require-complete
```

Inventory reports every outstanding obligation. The strict command exits 1
until all cells are COMPLETE and their receipts validate. An inventory exit 0
is never acceptance. Evidence shortage cannot become NOT_APPLICABLE: all
enumerated cells are legal; a genuine API/ruleset scope correction requires
reviewing the supported scope itself.

Receipts distinguish implementation, mechanics/guidance, synthetic behavior,
real actor source, independent facts, ranking reconciliation and render review.
References bind a repository-relative path, SHA-256 and a locator. The checker
refuses changed/missing bytes, disposable paths, duplicate/illegal cells,
unsupported dimensions, empty encounter facts/guidance and COMPLETE records
without a usable public actor archive and member manifest. The strict snapshot
reader verifies raw generation/page proofs; both actor stream directions must
exist and contain usable events for the correct zone/category/metric/faction.

This structural audit does not independently execute every cited behavioral
test or adjudicate a guide's factual correctness. Run the independent raw-fact
checks, actual tests and rendered review before adding their receipt. Domain
and product acceptance remain explicit review actions. A raw amount agreeing
with a ranking once is not a universally validated ranking policy.

Public captures must retain report/fight/actor identity, revision, partition,
endpoint, ownership and stream provenance. Keep raw bytes immutable, put full
archives in Git LFS, and scan all extracted members and generated outputs with
`gitleaks dir DIRECTORY --redact --max-target-megabytes 0`. Do not commit
credential material, private reports, developer cache paths or generated pages.

Git preserves register JSON and native `.entries`/`.sha256` sidecars as exact
bytes. Automatic newline conversion would invalidate reference hashes after
staging, even when every working-tree check passed. Verify staged metadata blobs
and LFS object identities against the receipt hashes before pushing captures.
The `--staged` option checks the Git index as well as the working files and
rejects missing staged evidence, changed bytes and invalid LFS object IDs/sizes.
It does not replace raw-archive or domain acceptance checks.

The Lucifron context Mage fixture and cross-raid MC/BWL/AQ40 captures exercise
live format2 through the normal pipeline. Independent raw facts also bind unfiltered/critical counts,
Mage fire-critical target sets, Ignite owner/target sums and control/death
transitions. These are observations, not validated ranking or phase policies.
Captured actor directions must agree with their owned unrestricted events.
Unselected actors retain unknown personal stream completeness. Historical
actor-only fixtures and their original arithmetic expectations remain intact.

`healing-facts.json` separately freezes recipient-qualified healing/absorption
for 239 retained HPS actor cases, without changing original actor expectations:

```sh
uv run python scripts/check_raid_facts.py tests/golden/raids/healing-facts.json
```

Its `healing-recipients` kind binds explicit boss identities, friendly roster,
source ownership, actual amounts and combined support. It does not certify a
universal ranked HPS policy. Six source participants can share fewer fights;
actorless scopes are certified once per distinct fight, not per participant.

The full `mc-holy-raid` capture retains its original ZIP, member manifest and
hash filenames in a nested directory. Its 60 actor cases span all ten bosses
and 57 fights. All 120 player directions are complete; two pet discovery
listings retain unresolved ownership and missing coverage. The capture remains
partial. It supplements stronger encounter-context fixtures rather than
replacing them or certifying complete pet coverage.

`control-facts.json` separately freezes six whole-encounter control contexts,
including caster/recipient identities, instance transitions and lifecycle rows.
Manual interval expectations were reviewed in integer milliseconds before the
control-window implementation. They are neither analyzer-generated actor facts
nor physical attackability, personal uptime or assignment certificates.

```sh
uv run python scripts/check_raid_facts.py tests/golden/raids/control-facts.json
```

The separate `mc-holy-raid-context` fixture preserves the normal installed CLI's
native ZIP and sidecar filenames. It has the same 60 selected actor/fight pairs
as the earlier full capture, with all 114 whole-encounter scopes complete. All
60 original actor measurements agree independently; the new cases additionally
freeze raw All/critical context. The earlier archive and expectations remain
unchanged. Both captures retain the two unresolved pet ownership listings.
The register now contains 41 archives, 401 actor cases, 239 recipient cases and
six separate NPC-control contexts. No domain cell is certified complete.

The full `bwl-holy-raid-context` capture spans all nine BWL encounter entries,
with 53 public selected actors in 53 fights and 106 complete player directions
plus 106 complete global scopes. One pet ownership listing is missing. Nefarian
has five complete cohort actors and no acquired personal fight: fight-level
faction evidence was unavailable. Its golden explicitly rejects a fabricated
subject, excluded subject or personal duty context. Combined and individual
dragon entries retain separate identities and independent raw facts.

`effect-facts.json` separately freezes seven actor-recipient contexts and fifteen
reviewed aura timelines. Its `actor-effects` checker projects raw transitions and
lifecycle rows from the maximum-multiplicity actor directions; it does not call
production state helpers or generate expected windows. Golden replay compares
the manually reviewed integer-ms boundaries with actual saved observations.
Initial state, contradictory transitions, lifecycles and fight-end censoring stay
explicit. Bronze exposure is not stun uptime; resource-aura exposure is not
resource quantity; Priest-call exposure is not a healing-quality grade.

```sh
uv run python scripts/check_raid_facts.py tests/golden/raids/effect-facts.json
```
