# 07 - Product Acceptance

## Goal
The completed Naxx analysis works for users: pages, desktop app, installed
build, saved analyses and legacy views, released and accepted by the owner.

## Integration analysis
Use the existing normal-acquisition integration harness, saved-document
renderer and `run_offline` for analysis.json, both pages and packaged output.
Naxx v1 must retain its existing output: the encounter block is gated by v2
format. Rendering an old saved document consumes its stored strategy; it must
not fetch current rules to add new advice. Category applicability is selected
before serialization, without changing the saved strategy schema.

Keep the 18-archive/54-output v1 comparison and the separate full Haplina export
as distinct controls. Synthetic v2 acquisition proves wiring, not real WCL
acceptance. The real short/complex capture receipts and reviewed content are
prerequisites to final acceptance samples. Existing browser checks cover
rendered behavior and overflow helpers; they do not replace inspecting new
content at desktop/mobile/print sizes per class.

Reuse `scripts/build_release.py`, the Desktop workflow and distribution checks
for the eventual reviewed candidate. Install/replay that candidate outside the
checkout and test live, saved and legacy paths before owner acceptance. The
published 0.6.0 release is the acquisition baseline, not proof that unfinished
Naxx content is accepted. Do not recut it or publish a new release early.

## Boxes
- [ ] **07.1** (agent) Naxx controls: legacy/live/saved replays, both pages, package; intended changes listed and reviewed.
- [ ] **07.2** (agent) Visual review at desktop, mobile and print for a sample of every class; findings fixed.
- [ ] **07.3** (agent) Release candidate built from the reviewed commit; installed replay outside the checkout.
- [ ] **07.4** (product-owner) Product acceptance of Naxx completion. Mirrored.
- [ ] **07.5** (agent) Publish the release after acceptance; Tower image updated if still capturing.

## Hindsight checkpoint
- [ ] Captain Hindsight review recorded
- [ ] Verdict is `CLOSE`

## Progress log

2026-10-22 · Compatibility checkpoint, not final acceptance · Optional strategy
category selection preserves all 57 controlled legacy outputs byte-for-byte;
92 existing browser tests pass. Four synthetic normal acquisition/render cases
exercise category selection and v1/v2 boundaries. The source proposals remain
research, and no new class-content visual acceptance, installed release
candidate or owner acceptance is claimed. 07.1–07.5 stay open.

2026-10-22 · Operational patch checks, not final Naxx acceptance · Released
0.6.1 preserves the earlier 0.6.0 acquisition baseline and fixes resume scheduling.
The release commit passes 2698 tests/29 skips, all four native fresh-install and
failed-upgrade checks, installed synthetic three-window recovery and offline replay.
A separate installed-wheel probe passed read/replace/delete on real Windows
WinVaultKeyring with disposable synthetic values and confirmed cleanup. All nine
release files passed fresh-download comparison. The fixed Tower image is bound
to the published wheel and passed network-disabled preflight; real capture/smoke
remains pending. These checks do not establish independent-user/live-account
acceptance, class-content visual review or final Naxx content approval. No 07
completion box is checked by this operational patch.

2026-10-23 · Draft layout preparation and mobile navigation correction ·
All 34 legal configurations now have reproducible, explicitly synthetic previews
of both pages with all 15 bosses and the unpromoted general/tank proposals.
The portable research recipe passes 272 desktop/mobile/narrow/print-CSS checks;
two generations reproduce all 104 files byte-for-byte. Author inspection covers
nine class samples at desktop/mobile/print CSS, with print pagination excluded.
This found a real shared mobile defect: fragment/keyboard jumps placed pull-step
headings beneath the sticky picker. Adding that target to the existing mobile
scroll-margin selector fixes the observed flow. The regression fails at four
mobile widths before the fix and passes at all five tested widths afterward;
all 96 browser tests pass. The same saved analysis rendered across 19 legacy
archives yields 38 pages differing only by the intended CSS substitution;
18 desktop/print sample images are byte-identical before/after. See
`research/guidance-layout-20261023/README.md` and its hashed receipt.
Installed parity and the checkpoint gate are recorded separately when complete.
These draft previews do not activate production guidance or replace independent
content/loadout review and real capture-specific acceptance. All 07 boxes stay open.
