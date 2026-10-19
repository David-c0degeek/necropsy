# Review checklist

Run `uv run python scripts/pre_review.py` before a review request and paste its
header. A passing gate is mechanical evidence only; it never approves the
domain, the visuals or the review. Tick each item in the request, or say why it
does not apply.

Evidence and arithmetic

- [ ] Unknown stays unknown: no missing value, failed read or absent stream became a zero, an absence or a default.
- [ ] Identity: caster, owner, source and target come from raw events and pass the strict binding checks; numeric aliases and names are not identities.
- [ ] Sources: every cited page has real content (not boilerplate or an empty page), with retrieval date and verbatim support.
- [ ] Pins: every SHA-256 recorded anywhere, nested ones included, comes from committed Git blobs; no CRLF working copy was pinned.
- [ ] Expected values were frozen from raw evidence independently of the analyzer, before the change that uses them.

Wording

- [ ] Docs, pages, commit messages and release notes claim no more than the evidence: nothing called validated, complete or better without proof.

Unattended capture and recovery

- [ ] A quota stop before any checkpoint retries fresh, without `--resume`.
- [ ] A requested stop is saved before cleanup starts.
- [ ] Attempt directories are never reused, including after a crash.
- [ ] A clear request applies only to its queue and current incident, at most once.
- [ ] Finished with alerts still pending keeps the worker and the watchdog alive.
