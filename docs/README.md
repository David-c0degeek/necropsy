# Documentation

[Home](../README.md) · [Get started](getting-started.md) · [Read the results](reading-results.md)

Start with a runnable sample, then choose how far into the evidence you want to go.
Necropsy writes analysis JSON and reports for all Classic Era classes in Naxxramas.
Each run also writes an offline HTML report and playbook. `necropsy analyze`
connects character-URL acquisition to those outputs. An authenticated Windows
run is verified with explicit partial pet coverage; see [live validation](live-validation.md).

## Run and understand

| Guide | What it answers |
|---|---|
| [Getting started](getting-started.md) | How do I run it, where are my results, and what if a command fails? |
| [Reading results](reading-results.md) | Which comparisons are fair, and how should I act on findings? |
| [Warcraft Logs connection](warcraft-logs.md) | How do I sign in, acquire logs, and recover a stopped run? |
| [Manual live check](live-acceptance.md) | How do I deliberately verify authenticated acquisition and inspect its receipt? |
| [Roadmap](roadmap.md) | What works today and what comes next? |

## Go deeper

| Reference | Use it when… |
|---|---|
| [Analysis JSON](analysis-json.md) | You are consuming the output or looking up a field |
| [Evidence model](evidence-model.md) | You need to distinguish facts, calculations, inferences, and unknown data |
| [Hunter analysis](hunter-analysis.md) | You want the shot, pet, gear, and weaving rules |
| [Database](database.md) | You are inspecting normalized events, coverage, or provenance |
| [Authentication boundaries](auth.md) | You need the credential-storage and public/personal contract |
| [Current architecture](architecture.md) | You want the implemented flows, module map and operational limits |
| [Architecture decisions](decisions/README.md) | You need the reasons behind the accepted acquisition and storage contracts |
| [Contributing](../CONTRIBUTING.md) | You want to run checks, change code, or review a pull request |

## Background and history

The [architecture specification](origin/WCL_Forensics_App_Architecture_v0.1.md)
describes the intended product. The [original investigation](origin/Haplina%20Analysis.md)
explains why it exists. These are historical design inputs; the guides above
describe the current implementation.

[Changelog](../CHANGELOG.md) · [Fixture provenance](../tests/golden/haplina_naxx/PROVENANCE.md)

- [Druid analysis](druid-analysis.md): explicit WCL categories, encounter duties, role-specific measurements and assignment overrides.
- [Druid validation](druid-validation.md): observed real-log scope and remaining acceptance gates.

- [All class analysis](class-analysis.md): supported ranking categories, roles and shared execution/ability comparisons.

[Install the CLI](installation.md): Python/OS requirements, public login, upgrades,
logout/uninstall, recovery and isolated artifact checks.
