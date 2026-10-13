# Roadmap

[Home](../README.md) · [Documentation](README.md) · [Changelog](../CHANGELOG.md)

The intended experience is simple: paste a Warcraft Logs character URL, select
the raid, and get a report and a practical boss-by-boss playbook. The analyzer
comes first, so every screen can explain the evidence behind its advice.

## Available now

Classic Era Hunter/Naxxramas analysis from a saved v6 deep-export ZIP:
`necropsy ingest` builds a database; `necropsy offline` writes `analysis.json`.
Same-faction comparisons, encounter context, and evidence-linked recommendations
are implemented. [Try the sample](getting-started.md).

## Planned milestones

| Milestone | Intended result | Dependency |
|---|---|---|
| A — Hunter/Naxxramas analysis | A browsable offline report and playbook, then live acquisition from a character URL | Offline analyzer underway; rendering and live fetching remain |
| B — Desktop app | Paste a URL, authenticate, choose raid/partition, follow acquisition progress, inspect bosses, export, and open cached analyses | Stable analysis JSON; public-client authentication before distribution |
| C — Broader classification | Class/spec/role taxonomy and build clusters; Druid and Warrior role resolution with confidence and overrides | Milestone A shipped |
| D — More class plugins | Druid, Warrior, Rogue, Mage, Warlock, then healers | Classification foundation |
| E — More raids and variants | Other Classic Era raids, then Fresh/SoD/other sites | Stable analyzer contracts |

The proposed `necropsy analyze <url>` command is future work. No live or auth
command exists today. HTML report and package generation are also planned.

## Authentication and distribution

The initial live client is planned for personal use with a confidential OAuth
client. Credentials belong to that local setup and must not be shared or shipped.
A PKCE public-client flow must replace it before any distributed desktop client.
Offline analysis of a saved export needs no WCL credentials.

The [original architecture specification](origin/WCL_Forensics_App_Architecture_v0.1.md)
describes the wider design, including the proposed Tauri shell and local Python
analyzer. It is design history, not an inventory of available features.
