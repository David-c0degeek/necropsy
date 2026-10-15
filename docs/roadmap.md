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

## Current delivery and future work

| Area | State | Boundary |
|---|---|---|
| Hunter/Naxxramas analysis and live acquisition | Implemented | Personal-use milestone accepted; source and coverage limits remain |
| All nine Classic Era classes | Implemented | Category/duty-aware reports; see [validation boundaries](class-analysis.md#contracts-and-validation) |
| Browser application experience | Implemented in current development | Priority overview, boss triage, Playbook/Report, class themes, responsive offline output; see [Unreleased](../CHANGELOG.md#unreleased) |
| Native desktop launcher | Planned | Authentication, acquisition progress and cached-analysis management in a desktop shell |
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
