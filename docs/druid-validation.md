# Druid validation

[Druid analysis](druid-analysis.md) · [Hunter validation](live-validation.md)

Implementation and acceptance are separate. David supplied character 110733843
for balance/restoration validation and explicitly authorized public feral/tank
leaderboard logs as fixtures on 2026-10-14. Domain adjudication and final product
acceptance remain outstanding.

The bounded production acquisition library was exercised against Classic Era,
Naxxramas, partition 1, Patchwerk, user endpoint. It acquired five same-faction
deep samples and 25 metadata rows per category. Metadata is not event evidence.
Unresolved pet ownership remains partial acquisition and never becomes known
absence. Source archives and derived outputs remain separate.

| Case | Raw evidence | Observed behavior |
|---|---|---|
| Balance | Haplina, `WzGF9BjdrHCk8N1X/36` | 40 balance casts; build 37/0/14; event damage 68,395 / 127.776 s = 535.272665 DPS; the original exact-build view had two samples; current spec/faction comparisons retain all five sources with their builds |
| Restoration | Haplina, `D98c7ZTvA1VRKXMW/33` | Effective healing 43,558 / 128.418 s = 339.189210 HPS; missing overheal remains unknown |
| Feral | Stinkface, `maHpk8K4hvLQzFRf/35` | 166,047 actor damage over 108.1 s; feral duty inferred from recorded attacks, separately from the ranking category |
| Tank category | Suncat, `YhxTZy3BDQN7nkcV/34` | Cat and bear attacks, no incoming damage: category alone does not prove tank duty |
| Tank duty | Harryjam, `vmfnP98zbcVNQpGh/67`, acquired Guardian cohort | 77 Maul + 67 Swipe (Bear), 211,627 incoming damage and 204,209 healing received; missing form aura interval does not become zero tank activity |
| Tank subject | Suncat, `ZKbwBpmxnHvFC2DT/19`, Four Horsemen | 169 bear actions, 107,140 incoming damage; tank duty inferred separately from category |
| Mixed duty | Mìlfurion, `HYjBacLFMqrzCmy8/25`, Four Horsemen Guardian cohort | 24 feral and 92 tank casts plus direct hits; hybrid role, 79,548 incoming damage; excluded from aggregate single-role cohorts |
| Own healing assignment | Haplina, `arYtVP9kgnjBJp7K/48`, Sapphiron | User reports mostly healing; 66 healing casts, 84,631 effective healing / 174.912 s, zero actor damage, build 24/0/27; inferred healer agrees with the stated assignment |

The API's hourly budget stopped a later dedicated tank acquisition before fresh
finalization. No snapshot was fabricated from that stopped run. Original
acquisition coverage and budget limits remain intact; a bounded reset-wait run
completed after the observed reset on 2026-10-15 and produced the Four Horsemen
capture above. The waiting process had imported older analyzer code; its raw
snapshot was preserved and successfully replayed with current code.

Local output examples are under `workspace/druid-balance`, `druid-restoration`,
`druid-feral`, `druid-guardian`, `druid-mixed` and `druid-sapphiron-restoration`.
These are machine-local review artifacts;
portable raw evidence and checks must live in the test fixtures before acceptance.
This page does not claim full-raid or all-role live acceptance.

Portable fixtures and independent arithmetic checks live in `tests/golden/druid/`;
six raw snapshots cover all requested roles across three bosses. Initial four
one-boss outputs passed the existing acceptance artifact checker and output
scans. Gitleaks also passed over all extracted members of both added captures.
Browser checks passed at 1400px and 390px for both pages (16 initial real cases),
including navigation/search/theme and zero automatic remote requests; synthetic
browser cases additionally verify HTML escaping. Latest verification and review
receipts are recorded separately; human domain acceptance remains pending.

The explicit Balance/HPS Sapphiron query also returned five public deep entries,
but no matching personal Balance row: the subject remains absent with the
exclusion recorded. The separate Restoration/HPS query acquired David's actual
healing performance. Neither metric choice nor a leaderboard category proves duty.

The versioned role heuristic also requires a non-tank secondary signal to account for at least 20% of categorized duty casts. Minor signals are retained in activity spans and observed-role evidence, even when they do not change the primary inferred duty. This threshold remains provisional pending domain adjudication. Direct evidenced tank duty is never suppressed solely by this share threshold.

Selected-spec validation now includes a separate Guardian acquisition for David's
own character on Patchwerk. No matching personal Guardian ranking was found;
the view shows insufficient personal Tank data. Harryjam's evidenced tank fight
is shown as a learning example at its actual leaderboard position **4**. Suncat's
overall #1 Guardian score remains separately labelled category metadata, without
promoting its non-tank fight to a tank example. The seventh frozen capture is
`tests/golden/druid/raw/druid-tank-view.zip`; independent raw-event arithmetic and
its 32,499,807 extracted bytes passed checks and gitleaks. The earlier Guardian
fixture likewise keeps Suncat's incompatible subject in audit data instead of
grading it as personal tank performance.

The full selected Balance view completed through the normal CLI on 2026-10-15.
All 15 bosses remain visible; 14 have matching personal Balance performances.
Sapphiron has no personal Balance grade and shows Alyrian's acquired #1 Balance
fight as a learning example. The first attempt spent the hourly allowance on
early comparisons and was cancelled with its cache retained. The replacement
waited once for 1,712.99 seconds, then collected personal encounters first.
Comparison acquisition remains partial after the finalization-reserve guard;
complete personal coverage does not mean complete comparison coverage.

The eighth frozen archive is `tests/golden/druid/raw/druid-balance-view.zip`.
All 15 actor-damage facts (14 personal plus the Sapphiron example) match independent
raw-event arithmetic. Its replay, package checks and four desktop/mobile browser
cases passed, bringing real-artifact browser verification to 32 cases across
eight outputs. Unlimited-size gitleaks scans covered 266,125,045 extracted raw
bytes and 35,283,900 generated-output bytes without findings. The serial full
golden/acceptance run passed 236 tests with four existing expected failures;
the subsequently added full-view golden test also passed. A native loader failure
occurred during overlapping large replays; its cause remains unconfirmed and it
did not recur in serial verification. Domain acceptance remains pending.

The subsequent comparison capture, `druid-balance-comparisons.zip`, contains
ranking references for every boss before deep event sampling. Current replay
has all 15 references, 14 personal Balance encounters, and five same-spec/faction
event sources for each of seven personal bosses. Known differing builds remain
context; one/two sources still provide labelled individual comparisons.
Overall top is a closed optional disclosure. Missing personal Guardian data
shows an Alliance tank practice example with Harryjam's recorded ability use.
Both final outputs passed artifact/package checks and eight real desktop/mobile
page cases. Full serial golden/acceptance: 238 passed, four retained expected
failures. The nine raw fixtures remain immutable. Linux/Windows source CI and
scoped independent review passed; domain/product acceptance remains outstanding.


Shared presentation verification now covers Balance, Restoration, missing-personal Tank and Hunter: four actual raw replays and sixteen refreshed desktop/mobile page cases. Golden/acceptance remains 238 passed/four expected failures. Linux/Windows CI passed on ad833d8 after the source-link and package-test corrections. Old saved Hunter document artifacts remain byte-identical; new replays add the shared ability table and CSV. Scoped final independent review and human domain/product acceptance remain pending.


## Accepted validation boundary

On 2026-10-15 David approved the delivered implementation and instructed final closure after the remaining domain-review requirements were disclosed. Additional standalone Druid SME adjudication was retired by product-owner decision; no new per-finding review is claimed. The accepted scope retains conservative duty heuristics, assignment/coverage unknowns and the missing real Holy Priest healing fixture. Arithmetic and automated role-regression checks are engineering evidence, not universal rotation, quality or assignment certification. Earlier pending handoff records are historical. Further refinement is separately scoped.
