<p align="center">
  <img src="docs/assets/necropsy-banner.svg" alt="Necropsy — Warcraft Logs, with context." width="960">
</p>

<p align="center"><strong>Understand the log. Find the next improvement.</strong><br>
Offline forensics for Classic Era Hunters in Naxxramas.</p>

<p align="center">
<a href="docs/getting-started.md">Get started</a> ·
<a href="docs/reading-results.md">Read the results</a> ·
<a href="docs/README.md">Documentation</a> ·
<a href="CONTRIBUTING.md">Contribute</a>
</p>

Necropsy turns a saved Warcraft Logs export into boss-by-boss analysis: what
happened, how comparable Hunters played, and which improvements deserve a closer
look. Each finding keeps its evidence and uncertainty visible.

**Available today:** a local command-line workflow that turns the v6 Hunter
deep-export format (or the included fixture subset) into an offline HTML report,
a boss-by-boss playbook, `analysis.json`, and a shareable package.
**Planned:** paste a WCL character URL and let Necropsy acquire the logs. See the
[roadmap](docs/roadmap.md).

## Your first analysis

From the repository root, with [uv](https://docs.astral.sh/uv/) installed:

```sh
uv sync --locked
uv run necropsy offline tests/fixtures/haplina_naxx_subset.zip --out workspace/demo
```

Open **`workspace/demo/report.html`** in your browser; `playbook.html` next to it
is the review list. This small sample covers four bosses and runs without WCL
credentials or the full Git LFS fixture. The analysis command and the pages make
no network requests; dependency installation can.

For your own supported export, substitute its ZIP path.
[Getting started](docs/getting-started.md) explains the format, database reuse,
and common errors.

## What you get

| Question | Where Necropsy helps |
|---|---|
| How does my execution compare? | Same-faction shot cadence, pet DPS, build and gear comparisons |
| Does this leaderboard make a fair target? | Cohort size, inferred faction membership, and separate cross-faction context |
| What happened on this boss? | Cast timelines, pet activity, crowd control, and damage by target |
| Why is the kill-time gap so large? | Median and fastest same-faction comparisons, with the flag's basis shown |
| What should I investigate next? | Recommendations grouped by what you control, with confidence and evidence links |

An unknown value stays unknown. A small comparison sample stays visible.
Heuristic advice is a prompt to investigate, not a promise of extra DPS.
[Learn how to read the results →](docs/reading-results.md)

## Find your way

| I want to… | Start here |
|---|---|
| Run an analysis or solve a setup problem | [Getting started](docs/getting-started.md) |
| Understand benchmarks and recommendations | [Reading results](docs/reading-results.md) |
| Consume the JSON output | [Analysis JSON](docs/analysis-json.md) |
| Inspect events, coverage, or evidence | [Evidence model](docs/evidence-model.md) · [Database](docs/database.md) |
| Understand Hunter-specific rules | [Hunter analysis](docs/hunter-analysis.md) |
| Develop or review a change | [Contributing](CONTRIBUTING.md) |
| See what is coming next | [Roadmap](docs/roadmap.md) · [Changelog](CHANGELOG.md) |

This is a private development project. The full golden fixture contains real
player logs and is available to authorized collaborators. Its
[provenance record](tests/golden/haplina_naxx/PROVENANCE.md) documents the source
files. Keep credentials and private exports out of issues and patches.
