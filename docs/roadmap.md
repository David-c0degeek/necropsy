# Roadmap

[Home](../README.md) · [Documentation](README.md) · [Changelog](../CHANGELOG.md)

The intended experience is simple: paste a Warcraft Logs character URL, select
the raid, and get a report and a practical boss-by-boss playbook. The analyzer
comes first, so every screen can explain the evidence behind its advice.

## Available now

All nine Classic Era classes in Naxxramas from live snapshots, plus saved
Hunter v6 deep-export ZIP analysis:
`necropsy ingest` builds a database; `necropsy offline` writes `analysis.json`, an
offline HTML report and playbook, and a package; `necropsy render` rebuilds the
pages from an existing `analysis.json`. `necropsy auth` supports public PKCE and
personal confidential clients; `necropsy resolve` looks up a character URL. Acquisition
orchestration is available as a library alongside benchmark selection, report/event
fetching and the immutable cache. The library can finalize acquired report bundles
and write a snapshot v1 for the existing offline analysis and rendering commands.
`necropsy analyze URL --endpoint user --cache DIR --out DIR` connects these pieces into one
workflow, with explicit cache and output paths, requested-boss coverage, partial
report exit statuses and offline recovery from a saved snapshot.
Same-faction comparisons, encounter context, and evidence-linked recommendations
are implemented. [Try the sample](getting-started.md).

## Planned milestones

| Milestone | Intended result | Dependency |
|---|---|---|
| A — Hunter/Naxxramas analysis | A browsable offline report and playbook, then live acquisition from a character URL | Personal-use milestone signed off; accepted source/coverage limitations remain |
| B — Desktop app | Paste a URL, authenticate, choose raid/partition, follow acquisition progress, inspect bosses, export, and open cached analyses | Stable analysis JSON; public-client authentication before distribution |
| C — Broader classification | Class/spec/role taxonomy and build clusters; Druid and Warrior role resolution with confidence and overrides | Milestone A shipped |
| D — Class plugins | All nine Classic Era classes implemented; domain acceptance remains explicit | Shared category/duty/evidence contracts |
| E — More raids and variants | Other Classic Era raids, then Fresh/SoD/other sites | Stable analyzer contracts |

[Sign-in, resolution and acquisition](warcraft-logs.md) are implemented for
personal use. Snapshot v1 and end-to-end CLI integration have synthetic tests and an
[observed authenticated Windows run](live-validation.md), with explicit partial
pet coverage. The [opt-in live harness](live-acceptance.md) records repeatable
checks; domain correctness and product acceptance remain separate.

## Authorized next work

Public PKCE and installable-wheel engineering are implemented. Registered
public-client sign-in/callback, refresh rotation and current/archived query access
are observed on Windows. The product owner confirmed independent account/machine
acceptance and approved the version0.1.0 repository release. The personal Hunter/Naxxramas milestone is signed
off. All nine Classic Era classes have [shared class reports](class-analysis.md),
including supported healing/tank categories. Druid role analysis has
[documented validation limits](druid-validation.md); engineering checks do not
replace domain acceptance. Desktop UI and additional game/raid support remain
outside this delivery.

## Authentication and distribution

Public S256 PKCE is the default sign-in; personal confidential clients remain
explicitly supported. Both use the selected operating system credential store.
Public acquisition requires `--endpoint user`. [Installation](installation.md)
documents package verification and pending live release gates.
Offline analysis of a saved export needs no WCL credentials.

The [original architecture specification](origin/WCL_Forensics_App_Architecture_v0.1.md)
describes the wider design, including the proposed Tauri shell and local Python
analyzer. It is design history, not an inventory of available features.
The [current architecture](architecture.md) and
[accepted decisions](decisions/README.md) describe implemented behavior.
