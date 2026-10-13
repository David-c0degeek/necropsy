# Lessons — Necropsy Milestone A

> Append as they happen. Durable lessons migrate to `tasks/lessons.md` at the §7 gate.

- 2026-10-12 — Plan was first written with the template's guidance text shortened (§6 bodies, subject-file guidance blocks, §7 wording). An agent resuming cold relies on that text; copy the template verbatim and only splice plan content at its extension points.
- 2026-10-13 — WCL documentation hosts return HTTP 403 to the WebFetch tool (bot check). The vanilla schema pages fetch fine with `curl -A <browser UA>`; `www.warcraftlogs.com/api/docs` still needs a human browser.
- 2026-10-13 — Exporter JSON is pretty-printed and compresses ~20x. Size budgets for committed fixtures must be stated for the compressed archive, never for raw JSON (subset: ~290 MB raw vs ~12.8 MB compressed).
- 2026-10-13 — Windows console output in cp1252 crashes on non-ASCII player names. Any CLI or script that prints WCL names must force UTF-8 output.
- 2026-10-13 — Do not run `git stash` while staged review work is in flight: `--keep-index` still removes unstaged edits from the tree, and popping onto staged add/add files conflicts. Verify with `git diff stash@{0}` before dropping.
- 2026-10-13 — astral-sh/setup-uv publishes only full version tags (no floating `v10`); pin GitHub Actions to commit SHAs with a version comment.
- 2026-10-13 — Atomic file replacement: re-validate the target (sidecars, identity, size/mtime) immediately before the swap and never delete files the build does not own, such as the target's WAL.
- 2026-10-13 — DuckDB `read_json` with a `JSON` column stores whatever the NDJSON value is: pass objects, not pre-serialized JSON strings, or `json_extract` returns NULL.
- 2026-10-13 — DuckDB `executemany` inserts ~150 rows/s; bulk-load via NDJSON + `read_json(columns=…)` instead.
- 2026-10-13 — A read-only probe that scanned every death event in a pet's streams reported a second pet death that was really a mob dying. Fact probes must filter by target actor, exactly like the analyzer; verify facts only through registered checkers.
- 2026-10-13 — Realm names differ between rankings ("Pyrewood Village") and report actors ("PyrewoodVillage"); compare normalized keys.
- 2026-10-13 — WCL `guild.faction` in rankings does not use the combatant faction codes (a Shaman raid reported 1); never mix enumerations without data proof.
- 2026-10-13 — Validate a ranking-damage rule against every cohort row, not one boss: "hostile NPC targets" matched Patchwerk but failed KT, where WCL counts damage to mind-controlled players. The rule that holds is "exclude only self and own pets".
- 2026-10-13 — WCL ability names can differ from community references ("Demoralizing Screech" vs Petopia's "Screech"); keep aliases in rule data, keep raw names in output.
- 2026-10-13 — A test that resolves every recommendation's evidence path against the emitted document caught a path naming a field that the serializer had renamed (`kill_duration_ms` vs `kill_duration_s`). Cross-references inside one document need a resolution test, not review.
- 2026-10-13 — Every aggregate (median, projection, ceiling, split) needs a negative test feeding an UNKNOWN or INFERRED input and asserting the output grade; three blocking review findings in one subject were uncertainty silently becoming a confident value.
- 2026-10-13 — Lead setup docs with a checked command on the included subset, label the current output format before the product vision, and separate practical result-reading guidance from the schema reference. An atomic failed export can leave an older valid file: document that distinction so users check exit status.
