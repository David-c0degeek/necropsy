# Roadmap

[Home](../README.md) · [Documentation](README.md) · [Changelog](../CHANGELOG.md)

The intended experience is simple: paste a Warcraft Logs character URL, select
the raid, and get a report and a practical boss-by-boss playbook. The graphical app provides that entry path, saved-run history and
automatic quota continuation, backed by the same evidence-preserving analyzer.

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

## Current delivery and future work

| Area | State | Boundary |
|---|---|---|
| Hunter/Naxxramas analysis and live acquisition | Implemented | Personal-use milestone accepted; source and coverage limits remain |
| All nine Classic Era classes | Implemented | Category/duty-aware reports; see [validation boundaries](class-analysis.md#contracts-and-validation) |
| Browser application experience | Implemented in current development | Priority overview, boss triage, Playbook/Report, class themes, responsive offline output; see [Changelog](../CHANGELOG.md) |
| Guided TUI and OS launchers | Implemented | Browser sign-in, saved analyses, safe stop/resume and automatic quota waiting |
| One-command bootstrap | Implemented | Windows, macOS and Linux scripts verify/install the native GUI and CLI runtime, then open the GUI; `necropsy tui` stays explicit |
| Graphical desktop shell | Implemented in current development | Tauri/React + Python sidecar; themed embedded reports, setup, saved analyses, offline example and safe close; [platform verification boundaries](desktop.md#verification-and-platform-boundaries) |
| More raids and game variants | Planned | Raid styling tokens are not analytical support for additional raids |
| Further domain validation | Ongoing | Engineering tests do not replace real-log validation for every class and encounter |

## Authorized next work

Public PKCE and installable-wheel engineering are implemented. Registered
public-client sign-in/callback, refresh rotation and current/archived query access
are observed on Windows. The product owner confirmed independent account/machine
acceptance and approved the version0.1.0 repository release. The personal Hunter/Naxxramas milestone is signed
off. All nine Classic Era classes have [shared class reports](class-analysis.md),
including supported healing/tank categories. Druid role analysis has
[documented validation limits](druid-validation.md); engineering checks do not
replace domain acceptance. The graphical desktop shell is additive current
development; signed distribution and macOS/Linux runtime acceptance remain open.
Additional game/raid support remains future work. The guided terminal app and
per-OS launchers are implemented.

## Authentication and distribution

Public S256 PKCE is the default sign-in; personal confidential clients remain
explicitly supported. Both use the selected operating system credential store.
The TUI selects the public user endpoint automatically; advanced CLI public
acquisition uses `--endpoint user`. [Installation](installation.md)
documents bootstrap, updates, recovery and platform verification boundaries.
Offline analysis of a saved export needs no WCL credentials.

The [original architecture specification](origin/WCL_Forensics_App_Architecture_v0.1.md)
describes the wider design, including the proposed Tauri shell and local Python
analyzer. It is design history, not an inventory of available features.
The [current architecture](architecture.md) and
[accepted decisions](decisions/README.md) describe implemented behavior.
