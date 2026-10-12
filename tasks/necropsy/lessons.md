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
