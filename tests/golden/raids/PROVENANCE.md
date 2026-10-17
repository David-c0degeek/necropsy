# Public raid seed evidence

Captured through the existing production `WclClient`, acquisition, immutable
cache, request journal, combined-report finalization and snapshot-v1 writer on
2026-10-16. The current fixture scope is deliberately small:

| Fixture | Zone / encounter | Category / metric / faction | Usable actor sources |
|---|---|---|---|
| mc-holy | 2000 / Lucifron 50663 | Priest Holy / HPS / Alliance | 6 |
| bwl-combined-holy | 2002 / Ebonroc / Flamegor 50631 | Priest Holy / HPS / Alliance | 6 |
| aq40-viscidus-hunter | 2005 / Viscidus 50713 | Hunter Marksmanship / DPS / Horde | 6 |
| mc-hunter | 2000 / Lucifron 50663 | Hunter Marksmanship / DPS / Alliance | 6 |
| mc-protection | 2000 / Lucifron 50663 | Warrior Protection / DPS / Alliance | 6 |
| bwl-combined-hunter | 2002 / Ebonroc / Flamegor 50631 | Hunter Marksmanship / DPS / Alliance | 6 |
| bwl-combined-protection | 2002 / Ebonroc / Flamegor 50631 | Warrior Protection / DPS / Horde | 6 |
| aq40-viscidus-holy | 2005 / Viscidus 50713 | Priest Holy / HPS / Alliance | 6 |
| aq40-viscidus-protection | 2005 / Viscidus 50713 | Warrior Protection / DPS / Alliance | 6 |

The first three captures date to 2026-10-16; the additional six were captured
2026-10-17. There are 54 actor cases across nine immutable archives. Protection
is a ranking category; actual tank duty must be established separately from
the raw actions and incoming boss hits, including counterexamples.

Partition 1, Vanilla user endpoint, public reports only. Every finalized report
was checked for public visibility before copying into fixture storage. Public
player identities are retained; these are not anonymized examples. Existing
project fixture policy authorizes public sources; account access does not grant
permission to publish private reports. No private reports or credentials are
included. Capture dates differ from the original fights' dates, which remain in
the raw reports and rankings.

ZIP files are byte-identical snapshot-writer outputs. `provenance.json` retains
source character URLs, category/metric, partition, usable source counts and whole
archive hashes. Each ZIP has its original `.entries` member manifest and
`.sha256` companion. Snapshot markers bind exact report revisions, actor/fight
identities, stream directions, page hashes, endpoint and ownership. Git LFS holds
the raw ZIPs; ordinary CI does not fetch them.

`facts.json` freezes 54 independently enumerated actor cases, including raw
amounts, exact durations, targets and NPC IDs, actor-owned casts and timings,
and the fight/master-data pet owner records. Expected arithmetic was enumerated
directly from source pages for outgoing actions and target pages for incoming
actions, then compared with a separate source/target maximum-multiplicity union.
Neither method calls production analyzers or the normalizer. The committed
checker cannot refresh expectations. Synthetic mutation checks prove that
rehashing altered duration/target/owner/timing/amount inputs does not make them
agree with the frozen expected facts.

```sh
uv run python scripts/check_raid_facts.py tests/golden/raids/facts.json
uv run pytest tests/unit/test_raid_facts.py tests/unit/test_raid_coverage.py -q
uv run pytest tests/golden/test_raid_evidence.py -q
```

`absorbed_amount` is a raw event sum attributed to the source actor. It is not
universally healing: Hunters may have protection-potion absorption events.
For the Lucifron Holy subject, 48,161 heal amount + 6,159 absorbed amount over
38.851 seconds gives 1398.1622, versus recorded WCL HPS 1398.16. That one
reconciliation neither approves a universal HPS policy nor changes the existing
heal-only measurement. Pet/guardian participation and unresolved ownership remain
separate from recorded ranking scores.

Gitleaks 8.30.1 scanned all **113,744,740 extracted raw bytes**, with
`gitleaks dir workspace/raid-research/raw-scan --redact --max-target-megabytes 0`,
2026-10-17: exit 0, no leaks found. The scan is heuristic, not proof of absence.
Generated-output scans follow actual replay; raw scan alone does not cover them.

Follow-up scan of all nine archives: **301,461,037 extracted raw bytes**, same
unlimited command/tool, 2026-10-17: exit 0, no leaks found. Three installed-wheel
replays from outside the checkout produced the correct 2000/2002/2005 identities,
both pages and packages; their 16,267,142 generated file bytes were separately
scanned with no findings. Subsequent source strategy changes receive their own
content/replay checks and preserve the raw bytes. The structural register's
`cell_id` is a comparison identity, not an API credential; renaming the original
generic `key` field removed three verified false-positive generic-key findings
without a scanner suppression or real credential change.

These captures establish usable seed evidence and arithmetic. They do not
close any boss/class cell: mechanics, opportunity/ranking policies, assignment
semantics, source-sensitive guidance, rendered review and domain acceptance
remain open. The missing Naxx Holy Priest fixture is unchanged. New Holy raid
evidence does not silently certify old Naxx cases or inherit its waivers.

The MC Guardian retry completed after the normal quota reset on 2026-10-17:
six usable sources, immutable archive/member receipts and six additional
independent actor cases (60 total). The original 54 expectations are unchanged.
The new archive receives its own raw/output scans and replay checks. Earlier
budget stops remain acquisition history and do not certify GUI/CLI resume.

BWL combined and AQ Viscidus Guardian captures subsequently completed through
the same acquisition/finalization pipeline. All three new Guardian archives
contain six sources apiece; the register now holds 12 archives and 72 actor
cases. Unlimited gitleaks 8.30.1 scanned all 81,152,275 extracted Guardian raw
bytes on 2026-10-17: exit 0, no findings. No quota policy was weakened.

MC Protection regression counts were separately enumerated from target pages,
NPC 12118 and raw Melee ability IDs 1/-4: Maasumi 9, Doljin 15, Pale 7,
Frozion 15, Panzèrzug 8, Cailo 19. Protector/trash and outgoing events are
excluded. These counts establish pressure, not assignments or tanking quality.

Lucifron Holy actor-target pages independently show Impending Doom (19702)
apply at 12,141 ms, remove/damage at 22,145 ms, then apply at 34,796 ms;
Lucifron's Curse (19703) applies at 13,760 ms and removes at 21,432 ms.
The pull ends at 38,851 ms. Damage is not an aura transition. Conservative
unknown initial state gives 7.672 s known cursed/13.760 s initial unknown and
14.059 s known Doom/12.141 s initial unknown. Real replay assertions freeze these
manual target-only calculations independently of the production state machine;
no nominal guide schedule or analyzer-generated expectation supplies them.

Four additional public six-source Lucifron captures cover Balance/DPS,
Balance/HPS, Fire Mage and Enhancement Shaman. The 24 new independently
enumerated cases bring the register to 96 actor cases and 16 archives. All
57,112,206 extracted utility raw bytes passed unlimited gitleaks 8.30.1 on
2026-10-17, no findings. The original 72 expectations remain unchanged.

Independent actor-source dispel enumeration requires `isBuff=false` and the
exact removed mechanic ID, separately from cast counts. Balance/HPS Truudee
records five Curse removals, Ragny 12 and 海兰 one; Mage Benoii and Darkwizzardo
one each. Holy Bluebeard records one Dominate Mind removal and Maoainai one Doom
removal plus unrelated ID11672, which must be excluded. These are successful
effects, not an assignment or available-opportunity denominator. The Druid
raw spell name may say Remove Corruption for ability 2782; IDs and effect fields
identify the recorded action without importing a modern spell-name policy.

Magmadar Hunter adds one finalized six-source public archive and six independent
raw actor cases (17 archives,102 cases). All 24,601,508 extracted raw bytes
passed unlimited gitleaks8.30.1 on2026-10-17, no findings. No prior raw expected
values were regenerated. Independent source enumeration fixes successful
Tranquilizing Shot19801 dispels of buff19451 on NPC11982: Xelown, Charies and
Clicker each one; Fleskhunter, Cartman and subject Trazel zero. Cast/effect
relative times are Xelown12.377/13.329 s, Charies9.363/10.722 s and
Clicker9.414/10.122 s. Those intervals do not establish reaction time: the
actor's cast is not the boss's Frenzy start. Panic19408 appears as damage events
for Xelown/Clicker, which are not aura transitions. Trazel has no recorded aura
transition and34.485 s unknown state; this is not proof of immunity or a missed
fear-handling job. Some master ability catalogs omit19451 even while dispel
events reference it, and unrelated Frenzy23537/25801/8269 must not substitute.

Holy and Protection Magmadar add12 independent actor cases (19 archives/114
cases). Their33,805,841 extracted raw bytes pass unlimited gitleaks8.30.1,
2026-10-17, no findings. Almsivi's Holy observation binds report
`aFQ7MPVdWTAvpK1Y`, fight4, actor41, raw pull309977–354067 ms:
Panic apply319284 ms and remove327280 ms give relative9.307/17.303 s, exposure
7.996 s and initial unknown9.307 s over44.090 s. A new manual test initially
used a different Almsivi pull endpoint; replay rejected it. The raw expected
duration and transition readings were already correct and were preserved.
