# Guided terminal and one-command installation

## Failed future

A new user installs the wrong version or cannot sign in, then loses their run by
closing the TUI during quota exhaustion. A polished menu hides broken recovery.

## Material risks

### TUI-PM-1 — High — UI blocks or resumes over an active worker

Failure: network/auth/analysis calls freeze input or two attempts modify one run.
Basis: [evidence: `wcl/analyze.py:run_analyze`, `wcl/client.py:WclClient.query`,
`wcl/auth.py:CallbackListener.wait`] are synchronous; run locks cover acquisition.
Detection: focused headless UI/worker tests before merge.
Guardrail: one worker owns a run; UI updates cross thread boundaries safely;
cooperative stop interrupts retry/reset/auth waits, retains checkpoints and waits
for the worker to finish before enabling another run. No plaintext credentials.

### TUI-PM-2 — High — quota waiting loops forever without useful progress

Failure: a partial report caused by missing permissions sleeps forever as though
it exhausted quota; a stopped run loses options or cannot be found later.
Basis: [evidence: `Outcome.code`, `Acquisition.stopped`, `AnalyzeError.code`]
distinguish partial coverage from actual quota stops. [inference] a UI using only
exit code 4 would misclassify sparse/archived data.
Guardrail: use typed quota exceptions and acquisition stop reason, preserve the
current WCL reset reading, wait with a visible countdown, and repeat resumable
attempts only for quota stops. Save history before work and on every transition.
Discover checkpoint-backed CLI runs and allow legacy cached-stream recovery.

### TUI-PM-3 — High — installer claims success but downloads old/unverified code

Failure: first run needs Git/Python/uv or restarts a shell, launcher points at a
failed upgrade, or an advertised install URL does not exist.
Basis: [evidence: v0.1.0 release predates the redesign; repository now public]
[inference] source pinning and PATH assumptions caused the prior install issue.
Guardrail: publish versioned wheel + SHA256SUMS + bootstrap assets; installers
provision a private uv and managed Python, verify wheel checksum and installed
version, preserve the prior launcher until success, and launch by absolute path.
Test bootstrap on Windows/macOS/Linux CI with isolated homes. Use OS vaults;
Linux desktop vault requirements must be explicit, never silently downgraded.

## Plan guardrails

Apply TUI-PM-1..3 through implementation and verification. Preserve advanced CLI
commands and existing snapshot/cache formats. Normal users paste a URL and choose
a class-appropriate spec, with automatic endpoint/cache/output choices. History
shows previous runs, supports report opening and resume, and defaults to waiting
and retrying after quota resets until the user stops. All three OS families get
one command that installs prerequisites and opens the TUI; subsequent launches
use an app shortcut/launcher or `necropsy`.

## Verdict

PROCEED WITH GUARDRAILS. Public distribution was confirmed by the owner. Existing
analysis and credential services remain the single implementation of their work.

## Sources checked

- https://textual.textualize.io/guide/workers/ — background thread UI discipline.
- https://textual.textualize.io/guide/testing/ — headless pilot tests.
- https://docs.astral.sh/uv/reference/installer/ — private install path / no PATH edits.
- https://docs.astral.sh/uv/guides/install-python/ — managed Python provisioning.

## Verification and dispositions

- TUI-PM-1 — Mitigated. Thread workers marshal UI updates through
  `call_from_thread`; one operation is enabled at a time and a per-run supervisor
  lock covers quota sleeps. Stop interrupts auth/retry/reset waits, waits for
  in-flight requests/offline stages, and retains the journal. Headless tests cover
  create/stop/reload and a real fake-server-to-HTML run. Browser callback cancellation
  has a direct regression. Abrupt process termination retains completed requests.
- TUI-PM-2 — Mitigated. Tests exercise multiple quota windows, stop during sleep,
  recovery after interrupted streams/finalization, and partial data without quota.
  The library restores saved options and imports CLI checkpoints; pre-checkpoint
  runs recover into a separate output. Explicit library roots isolate both history
  and cache, including a regression for a discovered test-isolation mistake.
- TUI-PM-3 — Mitigated. Fresh private-runtime/managed-Python bootstrap, launcher
  version, checksum refusal and failed-upgrade preservation passed on Windows,
  macOS and Ubuntu in [cross-platform CI](https://github.com/David-c0degeek/necropsy/actions/runs/38808380396).
  Installed-wheel checks verify embedded design assets and offline package integrity.
  Publication is a separate release step; draft PR #1 contains the reviewable work.
  Linux still needs its normal desktop password vault and an HTTPS downloader;
  real account/vault validation remains separate from automated installation.

Local broad verification reached 1,020 passing tests with one pre-existing browser
focus timing assertion. That assertion now waits for the scheduled focus change;
all 87 browser/auth/TUI cases subsequently passed. Ruff and strict mypy pass.
The terminal screenshot is captured from an empty isolated app; no real account,
private history or network-dependent font is included in the documentation image.
