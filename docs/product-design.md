# Product design and screenshot maintenance

[Documentation](README.md) · [Architecture](architecture.md) · [Reading results](reading-results.md)

Necropsy's interface follows **understand → prioritize → act → investigate → verify**.
Playbook emphasizes preparation; Report emphasizes comparisons and forensic detail.
Both read the same immutable analytical result and use the same shell.

## Presentation boundaries

`render/experience.py` formats the shared character overview and boss triage.
It sorts saved recommendations by existing severity, keeps stable order for ties,
and shows one representative per rule in the three-item raid shortlist. It does
not recompute confidence, invent a score, estimate a gain or change `analysis.json`.
Boss actions use the same severity order; Hunter actions retain their original
anchors and review keys. No finding and no personal data are separate states.

Comparison counts describe eligible sources. Known samples and missing medians
remain measurement-specific. Coverage describes acquired inputs, not all possible
fights. See the [evidence vocabulary mapping](evidence-model.md#how-the-interface-names-these-concepts).

## Composable visual identity

The root HTML carries `data-theme`, `data-class`, `data-raid` and `data-faction`.
The stylesheet is embedded in each page. There are no external fonts, raster
backgrounds, icon downloads, libraries, analytics or network-dependent assets.

| Layer | Tokens and purpose |
|---|---|
| Mode | `--surface-app`, `--surface-panel`, `--surface-raised`, `--surface-muted`, `--text-primary`, `--text-muted`, `--border-default` |
| Class | `--class-primary`, `--class-text`, `--class-ink`, `--class-primary-hover`, `--class-primary-muted`, `--class-surface`, `--class-border`, `--class-glow` |
| Raid | `--raid-accent`: cold necropolis, dark iron, ember or ancient stone atmosphere |
| Faction | `--faction-primary`: a secondary identity marker, always accompanied by text and evidence qualification |
| Status | `--status-good`, `--status-warning`, `--status-critical`, `--status-unknown`; labels carry the meaning |

All nine classes have restrained recognizable accents. Light mode uses darker
class ink on stone/ivory surfaces rather than applying bright canonical colors
to pale backgrounds. Unknown identities fall back to neutral tokens. The raid
palette supports Naxxramas, Blackwing Lair, Molten Core and Ahn'Qiraj names; these
visual tokens do **not** add analytical support for those other raids.

The geometric N monogram and engraved diamond/line background are original SVG
and CSS. No Blizzard artwork is redistributed. The ornament is decorative,
isolated behind an opaque readable surface, and removed in print.
The [repository banner](assets/necropsy-banner.svg) uses the same identity.

Typography uses system fonts for analytical content and a local Georgia serif
for character and boss identity. Spacing ranges from quarter-rem increments to
three-rem section separation. Compatibility aliases keep retained forensic
components on the same semantic colors.

## Components and interaction

- Overview: character identity, snapshot, coverage, a short priority list and
  compact linked encounter rows. Priorities expose a short explanation on demand.
- Actions: action and observed finding, distinct severity/confidence/control,
  visible meaningful limitations, expandable comparison and evidence paths.
- Comparisons: aligned numeric groups before full tables. Unknown remains text;
  an individual reference is never labelled a median.
- Preparation: a next-pull panel, loadout/execution disclosure and separate raid help.
- Evidence: native `details` retains complete cohorts, equipment, source links,
  measurements and timelines. Direct jumps reveal enclosing disclosures.
- Navigation: desktop sidebar, sticky compact boss picker below 1050px, search,
  findings/limited/reviewed filters and a view switch that retains the boss.
- Review: existing analysis-keyed browser marks update navigation and triage.
  They never change findings or the JSON. Blocked storage leaves the page usable.

Tables either stack on narrow screens or scroll inside a focusable container.
The document itself must not scroll horizontally, including with long log names.
Native links, labels, headings and disclosures support keyboard use. Focus is
visible; jump links move it to the target heading. Print expands disclosures and
restores the reader's prior state afterward. No animation is required.

## Reproduce the screenshots

Use the included sample, not hand-authored screenshot data:

```sh
uv run necropsy offline tests/fixtures/haplina_naxx_subset.zip --out workspace/demo
uv run playwright install chromium
uv run python -m scripts.capture_product workspace/demo/analysis.json --out docs/images
```

The helper renders current templates and captures 1440, 1280, 900 and 390px states,
light mode, a boss Playbook, next-pull guidance and evidence. It asserts no remote requests and no
page overflow. The checked-in screenshots show Haplina's four-boss historical
sample, including its real limits; they do not claim full-raid or live coverage.
Review captures visually before replacing published images.

[Light mode](images/light.png) · [Evidence detail](images/evidence.png) ·
[1280px layout](images/width-1280.png) · [900px layout](images/width-900.png)

```sh
uv run ruff check .
uv run mypy
uv run pytest -m "not live"
```

Browser coverage includes all supported class/category fixtures, missing personal
data, sparse comparisons, hostile names, keyboard navigation, local persistence,
light mode, reduced motion, no-JavaScript use, print and zero remote requests.
Screenshots are maintained product illustrations rather than pixel-perfect CI
baselines, avoiding platform-font snapshot noise.

## Guided terminal entry

`necropsy` opens the Textual app; advanced commands remain explicit subcommands.
The same dark surfaces and restrained gold accent frame a short flow: character
link, browser authorization, class-appropriate spec, Analyze. Faction/endpoint
and storage paths are automatic. The worker uses the existing acquisition and
offline-report services; the terminal never recomputes analytical findings.

Activity stays visible while work runs. Quota waits show a live countdown and
retry automatically until completion or cooperative Stop. The saved-run library
lists previous analyses, opens reports offline, resumes checkpoints and imports
older CLI output folders. Tab/Enter, mouse and Ctrl+C/Ctrl+Q are supported.
The scrolling layout supports small terminals; status text carries meaning
alongside the spinner and button colors. Authentication URLs stay transient;
tokens remain exclusively in the approved OS vault.

Regenerate the terminal screenshot with `uv run python scripts/capture_tui.py`.
The capture uses an isolated empty library and blocks remote font/network requests.

## Default desktop entry

The graphical shell is now the default first-run and launcher experience. It
imports the Playbook's stylesheet, including mode, class, raid, typography and
focus tokens. New analysis and the searchable library keep paths and endpoint
choices out of the normal flow. Native shortcuts open a GUI without a terminal.
`necropsy tui` retains the terminal experience above as an explicit option.

Capture the Windows release window with `scripts/check_desktop_window.py`, using
its temporary profile/library. The same check exercises the actual report frame,
review marks, links, invalid-input recovery and save-before-quit. See the
[desktop guide](desktop.md) for per-platform verification limits.
