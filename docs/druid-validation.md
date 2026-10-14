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
| Balance | Haplina, `WzGF9BjdrHCk8N1X/36` | 40 balance casts; build 37/0/14; event damage 68,395 / 127.776 s = 535.272665 DPS; two exact-build samples leave the median unknown |
| Restoration | Haplina, `D98c7ZTvA1VRKXMW/33` | Effective healing 43,558 / 128.418 s = 339.189210 HPS; missing overheal remains unknown |
| Feral | Stinkface, public Feral category | Saved production acquisition and report; exact source/facts are recorded with frozen fixture provenance |
| Tank category | Suncat, `YhxTZy3BDQN7nkcV/34` | Cat and bear attacks, no incoming damage: category alone does not prove tank duty |
| Tank duty | Harryjam, `vmfnP98zbcVNQpGh/67`, acquired Guardian cohort | 77 Maul + 67 Swipe (Bear), 211,627 incoming damage and 204,209 healing received; missing form aura interval does not become zero tank activity |

The API's hourly budget stopped a later dedicated tank acquisition before fresh
finalization. No snapshot was fabricated from that stopped run. Original
acquisition coverage and budget limits remain intact; a bounded reset-wait run
is recorded separately when it completes.

Local output examples are under `workspace/druid-balance`, `druid-restoration`,
`druid-feral` and `druid-guardian`. These are machine-local review artifacts;
portable raw evidence and checks must live in the test fixtures before acceptance.
This page does not claim full-raid or all-role live acceptance.
