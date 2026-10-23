# Draft guidance layout review

These recipes render the existing source-bound general proposal and separate
tank overlay through the real report/playbook templates. They do not acquire
WCL data, run a model, activate production guidance or approve source content.
The inputs are 34 synthetic missing-data documents, each containing all 15 bosses.
Unknown observations, absent capture scope and the draft warning remain visible.

Run from the repository root with the development environment and Playwright
Chromium installed. Choose a fresh output directory under `workspace/`:

```powershell
uv run python tasks/naxx-completion/research/guidance-layout-20261023/generate.py --out workspace/guidance-layout-review
uv run python tasks/naxx-completion/research/guidance-layout-20261023/check_layout.py workspace/guidance-layout-review
```

Open `workspace/guidance-layout-review/index.html` to browse all configurations.
Each configuration has both pages and its strictly validated synthetic analysis.
The overlay exists only in the preview view model; the analysis is not an accepted
capture or a saved production strategy. Proposal digests are included in the
synthetic document so changed content receives different review keys.

The manifest binds proposal, recipe, renderer and output hashes and records the
exact selected strategy for every boss. The checker verifies output hashes,
then inspects both pages at desktop 1440px, mobile 390px, narrow 320px and print
CSS 794px: 272 views. It checks all boss sections, text/source projection,
horizontal clipping, draft identification, browser errors and remote requests.
It saves desktop/mobile/print screenshots for one configuration of every class
(the boss with the most selected guidance text). Print CSS screenshots do not
establish physical pagination. Generated files stay ignored and are not packaged.

The dated receipt records the actual author inspection and the shared mobile
navigation defect found and fixed. Automated layout checks and author inspection
do not replace independent source/content review, loadout applicability checks,
real capture-specific render receipts or owner acceptance. All acceptance boxes
remain open. The tank overlay remains a separate unpromoted proposal.
