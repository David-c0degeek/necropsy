# Aura event-set consistency correction

2026-10-18, before implementation; base62e1ed7. Extends the existing PM-2
guardrail and the independently reviewed summon event-set proof.

Failed future: target aura counts and windows remain certified after an
actor/critical-only application, removal, death or extra occurrence enters
the merged fight. The complete All stream's transport metadata did not
establish that every queried row belonged to that read. The older aura caller
still used only `has_complete_encounter_coverage`; its SQL reads merged events.

Use the existing stronger helper, without changing ingestion or schemas.
The maximum-multiplicity union contains every All occurrence, so a trusted
All stream plus equal full-fight occurrence counts proves no extra identity
or copy was added. Missing or inconsistent count metadata withholds complete
counts/windows. Positive transitions remain observed, not certified absences
or durations. Preserve raw expectations, target/instance qualification,
genuine/feign lifecycle handling, existing source/cohort labels and Naxx.

Guard against a false fix that merely deletes extra positives, treats missing
count metadata as zero, or updates frozen expected values. Add adversarial
application/removal/death/copy and missing/inconsistent-count cases. Exercise
real MC/BWL/AQ aura callers and both pages, compare the previous checkpoint's
observations and all four Naxx artifacts, then record any actual differences.
Older incomplete derived metadata can legitimately become unknown; do not
silently advertise it as complete. This correction closes no full domain box.
