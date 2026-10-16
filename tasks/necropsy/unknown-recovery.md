# Recover usable evidence without weakening uncertainty

Authorized 2026-10-16: implement the Ayneri unknowns investigation fully; commit
and push to main. Private replay artifacts remain in ignored workspace/.

## Guardrails from the pre-mortem

- PM-U1: partial pet discovery must never become complete. Keep confirmed actor
  IDs and unresolved discovery independent through acquire, export, read, ingest,
  analysis and resume. Test conflicting ownership and unknown actual pets.
- PM-U2: report aggregates must never masquerade as fight snapshots. Preserve
  original single-fight metadata with generation digest; reject changed identity,
  revision and scope. Do not use the metadata artifact list as starting auras.
- PM-U3: clearer labels must not increase analytical confidence. Preserve sample
  thresholds; distinguish known absence, not collected, ambiguity and unproven
  identity. Localize aura uncertainty rather than initializing missing buffs off.

## Work and verification

1. Extend partial pet discovery and original fight metadata export; retain old
   snapshots. Rebuild normalized databases with a schema-version bump.
2. Add scoped talent fallback, report/actor/owner family evidence, and locally
   evidenced haste state. Retain event conflicts and explicit provenance.
3. Repair metadata-only selected-category leader context and uncertainty wording:
   known-zero pet DPS, no Windfury procs, family candidates, small cadence sample,
   optional timing not acquired and race unproven.
4. Run targeted contract/failure tests, lint/type/format and full ordinary suite;
   replay historical/golden behavior appropriate to affected rules; browser-check
   actual outputs. Recover the existing acquisition using immutable cache plus
   required live requests, preserving original artifacts; verify before/after.
5. Record actual recovery counts and PM-U1/U2/U3 dispositions; commit and push.

No race, pet passive training or starting-buff state will be fabricated to make
the report appear complete. Read-only live probes may determine whether missing
combatant snapshots can be recovered. Unavailable source data remains explicit.

## Result (2026-10-16)

Recovered the Ayneri acquisition into a separate saved run, leaving the original
untouched. The final snapshot contains 90 participant entries across 89 fights.
Reused 363 recorded WCL requests; additional read-only context queries were
verified against actual recipient buff events before enabling the fallback.

- All 11 previously blocked Hunter-pet rosters now have complete Hunter-pet
  analysis, including Charies (149.456820 pet DPS) and Ayneri on Loatheb
  (81.350771). All-pet damage remains incomplete for these entries because the
  engineering guardian's owner is unresolved.
- All six Kel'Thuzad talent splits and starting aura contexts are recovered.
  Context events stay outside the ordinary events table and ranked window.
- All 15 bosses retain optional overall-leader records; five were previously
  rejected because their category was selected Marksmanship.
- All 90 shot-count records and all 79 previously known reconstructed ranked
  damage totals are unchanged. Recorded WCL DPS covers the other 11 entries.
- Two earlier ambiguous family findings resolve using the same report pet and
  owner; newly recovered pets add two ambiguous findings. The remaining 28 show
  candidate families. Cadence samples remain insufficient in 57 entries (61
  before recovery); their actual clean sample counts are visible.
- Race remains unproven in 90 entries. Empty race columns are omitted and the
  evidence limitation is explained once. No race or passive pet training is
  guessed. No-proc Windfury damage and positively known pet absence show zero.

Verification: ordinary suite 1,112 passed; final recovery/render/browser contracts
74 passed; final source-attribution and context contracts 22 passed. The full
historical suite passed 244 checks with four expected unresolved golden facts;
its one failing Mage compatibility case was fixed, then all eight captured-class
replays passed. The acceptance gate passes. Ruff lint/format and strict mypy pass.
Actual recovered desktop/mobile pages load without script errors or network
requests; Charies has recorded WCL DPS and calculated pet DPS on both layouts.
Private comparison evidence is in ignored workspace/ayneri-recovery-verification.json.

The full historical replay caught a context-reader regression on the captured
Fire Mage report: another actor had the same character name on another server.
Context resolution now uses the selected participant's recorded server, matching
the existing actor/stream validation. The class capture is rerun after the fix.
An additional source-attribution guard refuses buff-removal reconstruction when
the snapshot's caster cannot be identified; all six real contexts still pass.

PM-U1: guarded. Confirmed actors survive acquisition/export/normalization, while
the all-pet completeness claim stays false. Ownership conflicts and unknown
possible Hunter pets are covered by failure tests.

PM-U2: guarded. Exact fight metadata is bound to its original generation digest,
actor, scope and revision. Earlier combatant snapshots and complete intervening
buff pages have independent provenance. WCL's Buffs recipient filtering proved
unsuitable in the live probe; the final query uses All with explicit game-actor
recipient and buff-event filtering. Optional context failures preserve ordinary
verified streams. Tampering and incomplete context are rejected.

PM-U3: guarded. Haste uncertainty stays local to the affected windows; sample
thresholds are unchanged. Known zero, candidate families, unavailable optional
comparisons and missing identity evidence remain distinct in the presentation.

Status: complete; verified and committed for publication to main.
