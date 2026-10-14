# Roadmap

[Home](../README.md) · [Documentation](README.md) · [Changelog](../CHANGELOG.md)

The intended experience is simple: paste a Warcraft Logs character URL, select
the raid, and get a report and a practical boss-by-boss playbook. The analyzer
comes first, so every screen can explain the evidence behind its advice.

## Available now

Classic Era Hunter/Naxxramas analysis from a saved v6 deep-export ZIP:
`necropsy ingest` builds a database; `necropsy offline` writes `analysis.json`, an
offline HTML report and playbook, and a package; `necropsy render` rebuilds the
pages from an existing `analysis.json`. `necropsy auth` signs in to Warcraft Logs for
personal use and `necropsy resolve` looks up a character URL. Acquisition
orchestration is available as a library alongside benchmark selection, report/event
fetching and the immutable cache. The library can finalize acquired report bundles
and write a snapshot v1 for the existing offline analysis and rendering commands.
`necropsy analyze URL --cache DIR --out DIR` connects these pieces into one
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
| D — More class plugins | Druid, Warrior, Rogue, Mage, Warlock, then healers | Classification foundation |
| E — More raids and variants | Other Classic Era raids, then Fresh/SoD/other sites | Stable analyzer contracts |

[Sign-in, resolution and acquisition](warcraft-logs.md) are implemented for
personal use. Snapshot v1 and end-to-end CLI integration have synthetic tests and an
[observed authenticated Windows run](live-validation.md), with explicit partial
pet coverage. The [opt-in live harness](live-acceptance.md) records repeatable
checks; domain correctness and product acceptance remain separate.

## Authorized next work

The next implementation scopes are public-client PKCE with an installable local
CLI, followed by class-aware analysis with Druid first: feral DPS, balance DPS,
restoration healing, feral tanking and hybrid/mixed encounter duties. Role-specific
comparisons and preserved Hunter compatibility are required. These scopes are
planned, not implemented; the personal Hunter/Naxxramas milestone is signed off.
They do not imply the desktop UI or broader class support is available.

## Authentication and distribution

The current WCL connection is for personal use with a confidential OAuth
client. Credentials stay in the selected operating system credential store.
A PKCE public-client flow must replace it before any distributed desktop client.
Offline analysis of a saved export needs no WCL credentials.

The [original architecture specification](origin/WCL_Forensics_App_Architecture_v0.1.md)
describes the wider design, including the proposed Tauri shell and local Python
analyzer. It is design history, not an inventory of available features.
The [current architecture](architecture.md) and
[accepted decisions](decisions/README.md) describe implemented behavior.
