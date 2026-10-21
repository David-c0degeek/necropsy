# Handoff to Codex (with LocalPilot), 2026-10-21

The owner instructed Claude to hand over: "codex will take it from here with localpilot".
Codex accepted ownership at pair epoch 2 and is the only tree writer. LocalPilot stays an adviser only (D009).
Claude remains required reviewer in the harness until an explicit authorized transfer.

## State

- origin/main = **8fc5b19**. Subject 00 is DONE. Boxes 01.1, 01.2, 01.3 and 01.4 are done.
  The 01.5 code is done and reviewed (#15, #16, #19). The full gate and the browser suite (92 tests) passed at 8fc5b19.
- Local and **unpushed**:
  - **10ba2f2**, which adds ledger conflicts and open items (Codex #18/#19 findings). Codex reviewed and approved it as first-pass storage in its round-2 verdict replying to claude:12, before this handoff was consumed. Subject 04.1 remains open.
- **Uncommitted working tree**: the v0.6.0 release bump the owner approved ("Cut v0.6.0 release").
  - The version was changed from 0.5.2 to 0.6.0 in pyproject.toml, uv.lock (line 691), desktop/package.json, desktop/package-lock.json, desktop/src-tauri/Cargo.toml, Cargo.lock (line 1844), tauri.conf.json, install.ps1, install.sh and docs/installation.md.
  - CHANGELOG.md has a `## 0.6.0 - 2026-10-21` section: Naxx encounter context, the register, `--raid` and the cell-scoped ranking rule.
  - The Lucifron items moved into 0.5.2, where they actually shipped: 7930e66 and d6a2efd are ancestors of v0.5.2.
  - Claude started `uv sync --locked` and the version/distribution tests in the background; their result was not seen. Rerun them.

## Release steps (01.5 closes when the release ships)

1. Verify the bump with `uv sync --locked`, `uv run pytest tests/unit -k "version or distribution or release or bootstrap"` and `check_docs`. Commit as "Release Necropsy 0.6.0".
2. Run `pre_review.py --full` and `uv run pytest -m browser`, then push main.
3. The Desktop packages workflow (.github/workflows/desktop.yml) runs on push. Download its `workspace/release` artifact, which holds the wheel, sdist, 4 desktop bundles, install scripts and SHA256SUMS.
4. Create the release with `gh release create v0.6.0 --title "Necropsy 0.6.0"`, with notes copied from the CHANGELOG plus "Verify downloads with SHA256SUMS". Upload every artifact, as v0.5.2 did (`gh release view v0.5.2` shows the pattern).
5. Tick 01.5, log the release, then run 01's Captain Hindsight.

## Next work (plan order)

- **03.2:** build the Tower image from the 0.6.0 wheel. The smoke must assert a v2 archive with encounter and critical streams (PM-2).
- **03.1:** before the bulk queue, make one measured normal v2 capture: a short fight plus Horsemen, Gothik or Kel'Thuzad, recording quota (research/quota-estimate.md).
- **03.3:** the owner must approve the Tower restart. That is an owner gate.
- **04.1:** add capability sources. The draft is at Claude's scratchpad `ledger/capabilities.yaml`, which you cannot reach, so in summary:
  - **Classic tooltip and level only (classicdb):** Tranquilizing Shot 19801, Shackle Undead 9484, Mind Control 605, Remove Lesser Curse 475, Druid Remove Curse 2782, Cleanse 4987 (Classic level 42; the wiki says level 10 for the current game) and Abolish Poison 2893.
  - **Class attribution recorded (warcraft.wiki.gg):** Frost Resistance Totem is Shaman, Frost Resistance Aura is Paladin, and Fear Ward is Priest and Dwarf-only.
  - **Wowhead:** Tranquilizing Shot is Hunter, from its range line.
  - The wiki returned 502 errors for Shackle Undead, Mind Control, Remove Lesser Curse and Abolish Poison.
- Also redo the targeted fetches listed under `open` in tests/golden/raids/naxx-boss-source-review.json.
- **04.2 to 04.4, 05 and 06:** these follow the plan. Your oracle draft (workspace/codex-naxx/oracle-tool) needs a real v2 fixture before promotion. Claude's asks: record the interpreter version and file digests in each result, and add a negative test where a critical row is not in encounter-All.
- **LocalPilot:** the 02.3 guidance-draft trial needs its pass threshold set in §4 first. Raw discovery stays out of its hands (D009).

## Things to know

- D010: the 17 MC batch cells stay stale under engine edits. Audit Naxx with `check_raid_coverage.py --raid naxxramas`.
- D011: ranking needs a validated policy for that exact cell.
- The compatibility harness is workspace/naxx-compat/naxx_outputs.py (54 v1 outputs) and haplina_full.py. Rerun both after any engine change that touches the v1 path.
- Lessons (tasks/naxx-completion/lessons.md):
  - never commit while a gate runs;
  - run the browser suite at rendering or rule checkpoints;
  - commit text must be plan-agnostic.
- The localbox model server is stopped, and the LocalPilot user config is restored from its backup.
- The pair session is 20261021T120145Z-a4a14bde. Claude goes idle after this; take ownership with a handoff or takeover as your protocol allows.
