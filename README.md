# Necropsy

**Know what to change next raid. Know why.**

Necropsy is a performance coach for **World of Warcraft Classic Era**, backed by
a combat-log forensics engine. Turn Warcraft Logs into a clear set of priorities,
a boss-by-boss plan, and the evidence behind every finding.

[Try the offline demo](docs/getting-started.md) ·
[Read your results](docs/reading-results.md) ·
[Documentation](docs/README.md) · [Install and open](docs/installation.md)

![Necropsy raid overview showing character identity, priorities, comparison quality and boss navigation](docs/images/overview.png)

For players improving after a raid, raid leaders reviewing assignments, and
parsers who want to inspect the exact numbers. Start with what deserves attention;
open the evidence when you want to investigate.

## From a log to your next pull

| Your question | Where to start |
|---|---|
| What should I work on first? | The raid overview brings existing findings to the front, ordered by severity |
| What should I do on this boss? | **Playbook** puts actions and your next-pull plan before supporting detail |
| Is this under my control? | Findings distinguish execution, gear/build, pets, raid assignments and external context |
| How do appropriate players compare? | **Report** exposes same-faction comparisons, class/category context and individual sources |
| How certain is this? | Confidence, limited samples, unknown values and coverage remain visible |
| Why was this flagged? | Expand the explanation and evidence; inspect exact measurements and WCL source links |

![Necropsy Playbook showing practical boss guidance with supporting evidence available below](docs/images/playbook.png)

The generated pages work directly from disk, with no server or automatic network
requests. Dark and light themes, restrained class identity, boss search and local
review marks make repeat review practical on desktop and mobile. Following a WCL
source link opens the online source deliberately.

## Install and open

Copy the command for your computer into a terminal. Setup installs Necropsy,
Python and its runtime automatically and opens the guided app. You do not need
Git, Python, uv, a GitHub account or an administrator account to get started.

**Windows** — open PowerShell and paste:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.ps1 | iex"
```

**macOS** — open Terminal and paste:

```sh
curl -fsSL https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.sh | sh
```

**Linux desktop** — open a terminal and paste:

```sh
sh -c 'u=https://raw.githubusercontent.com/David-c0degeek/necropsy/main/install.sh; if command -v curl >/dev/null; then curl -fsSL "$u"; else wget -qO- "$u"; fi' | sh
```

Windows gets a desktop/Start menu shortcut; macOS gets
`Applications/Necropsy.command`; Linux gets an applications-menu launcher.
You can also run `necropsy` in a new terminal. Repeating setup updates the app
and preserves your sign-in, saved runs and reports.

## Your first analysis

1. Paste your Warcraft Logs character link and choose **Find my character**.
2. Sign in through your browser when asked, then return to Necropsy.
3. Choose your spec and **Analyze my character**. Your faction, account endpoint,
   cache and output folder are handled for you.
4. Watch the live activity. The Playbook opens in your browser when ready.

When Warcraft Logs reaches its hourly allowance, Necropsy saves progress,
shows a countdown and automatically continues after the reset. You can choose
**Stop and save**, close the app and return later. Select the run under
**Your saved analyses** and choose **Continue analysis**. **Open report** opens
an existing report without contacting Warcraft Logs. Older CLI analyses can be
added from their saved folder; pre-checkpoint runs recover cached data into a
new run while preserving the original files.

A normal desktop password vault is needed for sign-in: Windows Credential
Manager, macOS Keychain, or Secret Service/KWallet on Linux. Private and archived
WCL reports still depend on your account permissions. See
[installation and recovery](docs/installation.md) for details and
[developer setup](CONTRIBUTING.md) for the sample and advanced CLI.

## Supported today

**Classic Era · Naxxramas · all nine classes.** Analysis follows the selected WCL
ranking category and evidenced encounter duty. Category labels are not talent
diagnoses, and healing or tanking numbers are not universal quality scores.

| Class | WCL ranking categories |
|---|---|
| Druid | Balance, Feral, Guardian (Tank), Restoration |
| Hunter | Marksmanship; legacy all-category exports |
| Mage | Fire, Frost |
| Paladin | Holy, Protection, Retribution |
| Priest | Holy, Shadow |
| Rogue | Assassination |
| Shaman | Elemental, Enhancement, Restoration |
| Warlock | Destruction |
| Warrior | Fury, Protection |

Hunter has dedicated shot, pet and weaving analysis. Druid and other class views
include role-aware measurements, ability use and recorded practice examples.
The exact [class support and validation boundaries](docs/class-analysis.md)
distinguish synthetic checks from real-log evidence, including the outstanding
real Holy Priest healing fixture. A supported category does not imply every
rotation or assignment has been independently validated.

Installers and the guided terminal app target Windows, macOS and Linux desktop.
Windows has real account/password-vault validation; platform automation and
real-account evidence are distinguished in [installation](docs/installation.md).
More raids and game variants remain [future work](docs/roadmap.md).

## Trust the evidence, including its limits

Unknown stays unknown. A median needs at least three known measurements;
individual sources remain useful without becoming an authoritative baseline.
Inferred faction or duty stays labelled. Cross-faction context never replaces the
appropriate same-faction comparison. Recommendations retain their evidence and
do not promise a DPS/HPS gain or invent an overall player score.

[How to read a finding](docs/reading-results.md) ·
[Evidence model](docs/evidence-model.md)

## Explore further

| I want to… | Guide |
|---|---|
| Get my first working analysis | [Getting started](docs/getting-started.md) |
| Understand comparisons, confidence or missing data | [Reading results](docs/reading-results.md) |
| Connect my account or recover acquisition | [Warcraft Logs connection](docs/warcraft-logs.md) |
| Select a class, category or encounter role | [Class analysis](docs/class-analysis.md) |
| Consume the data or verify a finding | [Analysis JSON](docs/analysis-json.md) · [Evidence model](docs/evidence-model.md) |
| Develop or review a change | [Contributing](CONTRIBUTING.md) · [Architecture](docs/architecture.md) |

Under the surface, Python performs analysis, `analysis.json` preserves the result,
and Jinja renders self-contained HTML with local CSS and JavaScript. The browser
does not recompute analytical truth. Snapshots and packages retain source
provenance; [the architecture guide](docs/architecture.md) describes the contracts.

Logs and generated output can contain real player identities. The full golden
fixture is available to authorized collaborators; its
[provenance record](tests/golden/haplina_naxx/PROVENANCE.md) identifies the inputs.

[Documentation home](docs/README.md) · [Changelog](CHANGELOG.md) · [Roadmap](docs/roadmap.md)
