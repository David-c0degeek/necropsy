# Necropsy documentation

[Product home](../README.md)

Get a working analysis, decide what to change, then inspect as much evidence as
you need. Necropsy supports all nine Classic Era classes in Naxxramas; the saved
Playbook and Report work offline.

## Start here

1. [Getting started](getting-started.md) — one-command install, guided sign-in,
   first report and continuation of saved analyses.
2. [Connect Warcraft Logs](warcraft-logs.md) — sign in and analyze your character.
3. [Reading your results](reading-results.md) — overview → priority → boss → action
   → explanation → evidence.

For a standalone installation, upgrades or removal, use
[Install and open Necropsy](installation.md).

## Understand your analysis

| Question | Guide |
|---|---|
| When should I use Playbook or Report? | [Choose your view](reading-results.md#choose-your-view) |
| What does limited sample, inferred or unknown mean? | [Read the quality labels](reading-results.md#read-the-quality-labels) |
| Why these comparison players? | [Choose a fair comparison](reading-results.md#choose-a-fair-comparison) |
| Which class/spec/category can I select? | [Classic Era class analysis](class-analysis.md) |
| What do the Hunter rules measure? | [Hunter analysis](hunter-analysis.md) |
| How do Druid categories and assignments work? | [Druid analysis](druid-analysis.md) |
| What is supported and what is still planned? | [Roadmap](roadmap.md) |

## Advanced users and reference

| Reference | Use it to… |
|---|---|
| [Evidence model](evidence-model.md) | Distinguish recorded facts, calculations, inferences and coverage-backed absence |
| [Analysis JSON](analysis-json.md) | Locate exact values and consume the versioned analytical output |
| [Database](database.md) | Inspect normalized events, coverage and provenance |
| [Authentication boundaries](auth.md) | Understand credential storage and public/personal client behavior |
| [Observed live validation](live-validation.md) | Check what was actually verified on authenticated logs |
| [Druid validation](druid-validation.md) | Understand the scope and limits of Druid acceptance |
| [Manual live check](live-acceptance.md) | Run an intentional authenticated acquisition check |

## Developers

- [Contributing](../CONTRIBUTING.md): development setup, checks and review.
- [Architecture](architecture.md): implemented data flows, rendering and operational limits.
- [Product design](product-design.md): theme tokens, presentation boundaries and screenshot regeneration.
- [Architecture decisions](decisions/README.md): reasons behind the contracts.
- [Changelog](../CHANGELOG.md): user-facing and engineering changes.
- [Fixture provenance](../tests/golden/haplina_naxx/PROVENANCE.md): recorded inputs.

## Design history

The [original architecture specification](origin/WCL_Forensics_App_Architecture_v0.1.md)
and [original investigation](origin/Haplina%20Analysis.md) explain the project's
origins. They are historical inputs; use the guides above for current behavior.
