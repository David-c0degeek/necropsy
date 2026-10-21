# D007 independent Naxx raw-oracle design

Draft only; 2026-10-21. Independent Codex review seat. No runtime implementation,
archive execution, database, live API or fresh external mechanics research performed.
Read repository evidence as text; this document does not certify existing guide
claims. Only this ignored draft is written. Actor/ability constants below are
repository candidates, not newly verified game facts.

## Independence and deliverables

Implement the eventual oracle with Python standard library only: zipfile, json,
hashlib, collections, math, decimal/fractions, pathlib. Do not import necropsy,
pytest helpers importing analysis code, DuckDB, the production snapshot reader,
production canonicalization or normalized tables. Production output is a comparison
target after raw expectations have been frozen, never an oracle input. Read YAML
as evidence during design; a future implementation uses a reviewed explicit JSON
query specification, not a YAML dependency or analyzer policy discovery.

Each frozen case identifies archive SHA256, entries sidecar SHA256, marker SHA256,
report code/revision, fight ID, encounter ID, subject actor ID, query-spec digest,
oracle source Git blob/hash and independently enumerated raw results. Include:

- archive members and SHA256 values used; report/master actor/roster locators;
- stream proof status, exact request identity, page counts and pagination proof;
- per-stream raw multiplicities and merged multiplicities, not just final totals;
- each contributing event's canonical hash, occurrence index, and all raw locators
  `(member, data[index])`; raw positions are provenance, not extra observations;
- requested fields, exact values, units/time origin, unsupported inputs and reasons;
- excluded or unresolved candidate events and reasons, to expose false-zero filters.

Use status `observed`, `complete-scope-empty`, `unknown`, or `invalid-input` per
measurement. Unknown has null value, never zero. Positive observations can survive
incomplete coverage if identity/time are sound, clearly labelled partial; absence,
rates over a claimed whole fight and exact full-fight counts cannot. Invalid
archive identity/digests fail the case, rather than becoming an empty observation.

## Shared trust, event and time contract

1. Hash the exact ZIP and sidecar bytes before parsing. Reject duplicate ZIP names,
   unsafe member paths, encryption, unsupported compression and declared/actual
   size/hash mismatches. Read members in memory; do not extract paths. Record
   size caps. Sidecar membership and hashes must agree, not merely ZIP CRC.
2. Parse JSON with duplicate-key and nonfinite-number rejection. Distinguish
   bool from integer. Validate the actual marker kind/version, zone 2006,
   partition and selected `(report,fight,participant)` identities. A v1 marker
   can yield actor-scoped observations; never manufacture encounter proofs for it.
3. Bind report bundle and scoped fight to the certified report revision, public
   report and marker report-set hashes. Check report code, fight ID, encounter,
   start/end, actor catalog and selected participant name/realm/class identity.
   The raw acquisition certificate proves declared capture provenance, not
   independent authenticity of the upstream server. Preserve that limit.
4. For each stream, require exact proof key `(report,revision,fight,role,actor,
   direction,endpoint)`, fight bounds, All data type, request version/limit,
   include_resources/translate and, for critical, its exact reviewed filter.
   Require ordered numbered page names, every certified page hash, no missing,
   duplicate or unexplained extra page member. Metadata saying complete alone
   is insufficient.
5. Pages must contain data lists of event objects and explicit nextPageTimestamp.
   Require at least one page, progressive finite in-bounds cursors and exactly
   one terminal null cursor at the final page. Reject pages after terminal,
   missing terminal, cursor repeats/backtracking and wrong critical event kinds.
   Resource/account readings and stopped status do not replace pagination proof.
6. Preserve every event within each page and across consecutive pages. Identical
   boundary rows are ambiguous: keep their multiplicity and record ambiguity;
   do not silently delete a presumed repeated API boundary event. A zero claim
   does not rely on ambiguous stream coverage.
7. Canonical event identity is SHA256 of UTF-8 JSON with sorted keys, no separator
   whitespace and ensure_ascii=False, independently implemented. Scope identity
   additionally includes report revision and fight. Never hash just timestamp,
   type, spell and participants; unknown raw fields can distinguish real events.
   For each stream s build Counter_s(canonical event). Merged multiplicity is
   max_s Counter_s, not a set and not a sum. Assign occurrence indices 0..n-1.
   Keep mismatches between overlapping streams as explicit coverage anomalies;
   never match occurrence indices to undocumented real-world event order.
8. A certified v2 encounter-All stream must contain every actor/critical event
   with at least equal multiplicity. Its actor-direction projections must also
   be present in each certified SOURCE/TARGET actor stream. Compare Counters in
   both required directions. Extra critical/actor rows are contradictions, not
   an invitation to extend encounter-All. Critical damage cannot certify all
   damage, aura, removal, summon or no-event claims.
9. Validate required event fields before semantic filters. Count and expose
   malformed actor/spell/time candidates rather than filtering them to zero.
   Numeric spell ID is primary; missing ability-name metadata is not absence.
   Conflicting names/IDs are unresolved. Never use localized names alone.
10. Time is raw report-relative milliseconds. Local time is `(timestamp -
    fight.startTime)/1000`, using exact integer/rational arithmetic where possible.
    Keep events at exact bounds; sort ties deterministically without inferring
    causality. Out-of-window/nonfinite/boolean times are excluded with reasons.
    Fight-relative zero is not proof of full encounter pull. Report start epoch,
    prelude combatant snapshots, absolute timestamps and encounter timelines are
    different origins and must not be combined implicitly.
11. Entity identity is `(report,revision,fight,actor_id,instance)` plus catalog
    gameID. sourceInstance/targetInstance are separate fields. Do not collapse
    by gameID or name. Missing instance is unknown for multi-instance actors;
    permit a single-instance interpretation only with an explicit proven roster
    cardinality and documented policy. Reconcile fight enemyNPCs/friendlyPets
    with masterData; present roster entries are not spawn times or proof of
    continuous availability. Missing roster is unknown, not empty.
12. Aura events establish transitions, not uninterrupted known state from pull.
    Preserve initial unknown state, explicit stack changes, refreshes, missing
    removals and right-censoring. Tied conflicting transitions produce ambiguous
    state, not an arbitrary lexical ordering. Spell rank families require an
    explicit sourced registry with unsupported ranks recorded.

## Encounter contracts

### Four Horsemen — encounter 51121

Candidate boss gameIDs from current rules: 16062,16063,16064,16065. Enumerate each
catalog actor/instance separately, and emit the observed subset of all four;
never choose one boss actor as representative. Per actor: incoming direct boss
melee events partitioned by horseman, raw aura/mark transitions and stack values,
damage/healing totals and observed timestamps for reviewed spell IDs. Raw totals
remain separately inspectable for each boss before any summed view.

If marks are later named, require sourced spell IDs and raw-caster identity;
the current design does not guess them from guide text. Keep observed marks
from unresolved casters separate. Do not infer rotation schedule, tank duty,
safe stacks, corner assignment, mark range, movement, death order or Shield
Wall opportunities from counts/time gaps. Explicit boss death evidence may
support an observed death timestamp; last damage/overkill alone stays an event
bound. Full boss lifetime and attackable windows remain unknown.

Adverse cases: four bosses hit one actor; one absent from actor streams but
present encounter-wide; same actor number in another report; NPC name alias;
duplicate gameID instances; null sourceInstance; mark remove without apply;
simultaneous stack transitions; late-selected fight; NPC roster missing one boss.

### Gothik — encounter 51109

Candidate boss gameID 16060. Snapshot current reviewed target lists as query-spec
inputs. Current YAML actually lists nine native targets including Gothik, plus
Spirit of Naxxramas 16449 separately as empirical start_trash; do not propagate
an older prose count of eleven. Native membership is a repository hypothesis,
not upstream-ranked-target certification for every new capture.

Emit per-target actor/instance observed summon/spawn markers (if any), first/last
relevant event, explicit death markers, participant damage/healing/control events,
and uncatalogued targets. Enumerate living-named and spectral-named gameIDs as
target types only. No inference of physical side, assigned group, gates,
reachability, wave number or dead-to-living conversion from species names or
scheduled guide times. Do not invent wave births from first player damage.
Link conversions only if raw records directly and unambiguously identify them;
otherwise retain separate independent instances and unknown relationship.

Adverse cases: all observed targets on one species family; opposite-family event
at same timestamp; recurring NPC instances; target missing from roster; Spirit
event late in fight (retain type; do not call it scheduled opening trash); no
explicit spawn/death; Gothik-only actor streams without full wave coverage.

### Thaddius — encounter 51120

Candidate boss gameID 15928. Stalagg/Feugen IDs and polarity ability IDs require
independent sourcing/raw discovery; do not invent constants or copy UI labels
as identity. Query-spec may include reviewed add IDs once established.

Emit per-actor raw charge aura transitions, stack fields, raw Polarity Shift
casts, charge-associated damage with source/recipient identity, and separate
events for identified adds and boss. Record incompatible/overlapping charge
states as ambiguity. Repeated applications and refreshing must not be counted
as independent player mistakes or inferred transitions between sides.
An explicit cast permits a cast timestamp, not proof everyone changed charge.
Do not infer spacing, proximity bonus, movement correctness, correct crossing,
add-death synchronization or activation phase from charge/damage counts. Guide
timers must never establish fight-relative phase origins.

Adverse cases: charge absent at pull then first observed remove; both charges
same millisecond; unchanged charge reapply; unknown spell rank; charge damage
with null caster; add death missing; encounter starts during boss combat.

### Loatheb — encounter 51115

Candidate boss gameID 16011. Current rule lowers role evidence threshold to one
healing action: oracle emits raw action/effect observations, not a role verdict.
Source exact Corrupted Mind, spore and Doom ability IDs before naming them.
Separate raw healing casts, direct/periodic heal effects, absorbed amounts,
overheal and distinct recipients; one cast can produce multiple effects and
one effect does not prove a cast count. Separate pets/procs/consumables and
unresolved ownership. Freeze low-action and zero-action cases explicitly.

Restriction aura transitions can bound observed state; they do not assign a
healing rotation or prove missed opportunities. Spore aura positives do not
prove proximity, intended recipient, group benefit or optimal buff uptime.
Whole-fight HPS is arithmetic, not a healing-quality score. No opportunity
denominator from elapsed fight time divided by a guide cooldown.

Adverse cases: one cast with multiple heal effects; zero personal casts but pet
healing; one or two healing actions with many buff/damage casts; initial unknown
restriction state; truncated aura duration; absent ownership listing; observed
heal during nominal guide restriction (report contradiction, do not discard).

### Kel'Thuzad — encounter 51114

Candidate boss gameID 15990. Source exact guardian/add/control/interrupt/Frost
Blast identities before classifying them. Emit boss and add instances separately;
for reviewed spells emit raw casts, interrupt/removal/control effects, target
auras and damage recipient/timestamp sets. Interrupted casts and successful
interrupt effects are different raw observations; correlate only with supported
identity/time evidence, preserving competing matches.

Full-pull time origin is unresolved unless independently present. A selected
fight may start after opening waves: no phase-two at fight+310s or phase-three
at inferred 40% without explicit raw phase/health evidence and verified units.
Current acquisition may not request phaseTransitions; omitted is unmeasured,
different from an explicitly requested null result. A guardian first seen is
not a phase transition. Multi-target Frost Blast observations do not establish
geometry, chained player blame, avoidability or assigned distance.

Adverse cases: late-start fight; explicit null versus absent phase field;
guardians present in roster with no events; repeated guardian instances; control
changes caster allegiance; friendly actor becomes hostile without losing identity;
interrupt cast without effect; same-timestamp multiple interrupt candidates;
Blast damage on two actors without positions; mind-controlled owned summon.

## Acceptance sequence and review boundary

1. Review query-spec identity/scope and needed source constants first. No sourced
   gameplay number becomes an observed expected value without a raw locator.
2. Independently scan exact archives using this contract; freeze raw cases before
   implementing Naxx analysis behavior. Record empty/missing/unknown distinctly.
3. Add a small synthetic ZIP family for every adverse class above, with explicitly
   constructed event lists and hand-computed Counters/times. Validate the raw
   oracle itself, not just that analyzer and oracle agree. Separate corrupt-input
   failures from valid-but-insufficient evidence.
4. Reviewer independently re-enumerates at least one multi-boss case, repeated-
   instance case, censored aura case, low-healing case and late-start case; include
   all newly claimed positive policies and consequential zero claims. Parallel
   review is allowed; no shared output paths or shared-tree writers.
5. Compare analyzer fields to frozen results with exact IDs/counts/units and
   explicit rounding rules only at display boundaries. Missing prerequisites must
   stay unknown, and v1 compatibility controls remain separate from v2 evidence.
6. All current Naxx archives being v1 does not invalidate their actor arithmetic.
   Reuse eligible v1 actor/ranking cases; require new certified scopes only for
   observations needing them. A capture can support several cells and a cell can
   have multiple evidence dimensions. Do not equate 510 cells with 510 API runs.

Design references inspected: snapshot/v1.py stream/report/actor proofs;
snapshot/v2.py encounter proof multiplicity checks; wcl/cache.py check_identity,
_PageCheck; snapshot/canonical.py identity semantics; normalize/schema.py raw
instance/stack fields; zones/naxxramas.yaml and naxxramas_facts.yaml. Their current
code is reference behavior to examine independently, not an oracle dependency.
