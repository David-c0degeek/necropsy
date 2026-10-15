# Lessons

- 2026-10-15: Mode is part of credential identity. Separate public/personal records
  even for the same client ID; commit selection last and reject incompatible
  endpoints before HTTP. Legacy untagged personal records remain readable.
- 2026-10-15: Installed verification needs both CLI/public HTTP behavior and a real
  offline replay, not only resource imports. Probe OS stores under unique synthetic
  service names and remove every probe value; never test against real user records.
- 2026-10-15: Package metadata deserves a dedicated public README; a source README
  can carry developer sample paths and instructions that do not exist after install.
- 2026-10-15: Python's Windows ZIP reader normalizes backslashes. Test traversal
  semantically (including backslash traversal) instead of assuming raw separators
  survive archive construction/readback. An initially overstrict test was corrected;
  traversal refusal and private-payload cases pass.
- 2026-10-15: Serialize large replay suites to avoid native resource contention.
  A duplicate baseline and prematurely overlapping golden run were cancelled;
  final golden/acceptance follows completion of fast regression checks.
