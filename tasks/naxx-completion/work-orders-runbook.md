# Bounded guidance work orders

## Current hold

The owner has stopped local inference until the raid is finished. Keep LocalBox
off. Do not start the server or run model orders until the owner says the raid
is finished. WCL maintenance is a separate hold; this workflow never calls WCL.

## Contract and verification

Ten JSON orders in `work-orders/` freeze class, WCL category, metric, faction,
Sapphiron encounter, source-review path/hash, allowed excerpt keys and caps.
`scripts/guidance_work_order.py` validates the input pin and configuration before
building a prompt. Its generated `packet.json` contains the exact output schema,
input bundle, allowed driver output path and reproducible verifier command.
The model uses native tool-free `localpilot ask`, with a per-order loopback-only
provider configuration. It receives no raw capture, credential, shell, editing
or web tool. No permissions bypass or user-level LocalPilot config change is used.

Before a trial, run:

```powershell
uv run pytest tests/unit/test_guidance_work_order.py tests/unit/test_guidance_lint.py -q
```

The verifier requires exact identity, all eight categories, at least two items,
exact quotes for every support key, no conflicting/unknown/empty support,
correct class/metric/citation/date and no new unsupported numeric claim.
Removal capabilities are unavailable in these orders. Positioning advice needs
the no-position-recording boundary. Unsupported categories use the exact
no-evidence reason, without hiding extra advice in free-form notes.

`guidance_lint` supplies additional known-pattern checks. Its existing healer
loadout requirement remains the default for old callers; this draft contract
explicitly accounts for unknown loadout evidence for both DPS and HPS. None of
these checks proves the semantic correctness of free text. Coordinator review
must reject any fabricated or misattributed material claim before acceptance.

## Serve and run after the hold is lifted

Restore the already downloaded, tuned model using the same reviewed profile:

```powershell
localbox serve q3635ba3bapex --quant apex-i-quality --context 256k --agent none
```

Verify server readiness, then run one frozen order from the repository root:

```powershell
uv run python scripts/guidance_work_order.py run tasks/naxx-completion/work-orders/guidance-trial-01.json --workspace workspace/naxx-drafts --model Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Quality.gguf
```

The directory `workspace/naxx-drafts/guidance-trial-01/` must be fresh. It retains
the copied order, prompt, packet, isolated provider config, raw `draft.json`,
stderr and `run.json`. A timeout retains partial output and fails the order.
Tracked and nonignored untracked files are fingerprinted before/after; any
change fails the order. This is a repository mutation check, not a claim of
OS-level filesystem confinement. No tool loop exists on the chosen ask path.

An independent rerun of its verifier is:

```powershell
uv run python scripts/guidance_work_order.py verify tasks/naxx-completion/work-orders/guidance-trial-01.json --draft workspace/naxx-drafts/guidance-trial-01/draft.json
```

Run the ten frozen orders once each. Keep failures and their reasons; do not
repair them by hand or retry until one passes and count that as the trial.
The frozen threshold is at least 9/10 mechanical passes, zero fabricated or
misattributed material claims after coordinator review, zero out-of-scope tree
mutations and zero unreviewed promotions. Every order caps wall time at 600
seconds and native provider output at 4096 tokens. The actual installed CLI
passed a loopback mock probe proving that cap is sent and no tools are exposed
(`research/localpilot-runtime-probe.json`). Actual usage stays unknown because
native `ask` does not emit usage events to its output.

## Discard and stop

A failed draft stays in its ignored directory as rejected evidence. It never
enters a production rule file or a completion register. Accepted machine output
also stays a draft until content review; the model never reviews or promotes
its own work and never becomes the pair's reviewer of record.

Stop LocalBox when local inference is no longer authorized or needed. If startup
is still running, end that launcher first: it can retry a stopped child. Then
run `localbox stop` and `localbox status`, and confirm no `llama-server` process
remains. An interrupted startup reply check is not evidence of model quality.
