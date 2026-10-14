# Druid review packet

Implementation is on `main`; domain acceptance is pending. These reports are
generated local artifacts. Portable raw snapshots, manifests, provenance and
independent arithmetic checks live in `tests/golden/druid/`.

## Open these examples

| Example | Practice page | Full evidence | Facts to review |
|---|---|---|---|
| Your Balance Patchwerk | [Playbook](../../workspace/druid-balance/playbook.html) | [Report](../../workspace/druid-balance/report.html) | 37/0/14; 68,395 damage; 40 balance casts; only two exact-build comparators, so median stays unknown |
| Public Feral Patchwerk | [Playbook](../../workspace/druid-feral/playbook.html) | [Report](../../workspace/druid-feral/report.html) | Stinkface; 166,047 damage over 108.1 s; form/resources/cast cadence and targets retain evidence limits |
| Your Restoration Patchwerk | [Playbook](../../workspace/druid-restoration/playbook.html) | [Report](../../workspace/druid-restoration/report.html) | 43,558 effective healing; missing overheal stays unknown; HPS is not healing quality |
| Tank and mixed Four Horsemen | [Playbook](../../workspace/druid-mixed/playbook.html) | [Report](../../workspace/druid-mixed/report.html) | Suncat tank: 107,140 incoming damage; Mìlfurion cohort: 24 cat + 92 bear casts and direct hits, hybrid, excluded from aggregate single-role comparisons |
| Your Sapphiron assignment | [Playbook](../../workspace/druid-sapphiron-restoration/playbook.html) | [Report](../../workspace/druid-sapphiron-restoration/report.html) | `arYtVP9kgnjBJp7K/48`; 24/0/27; 66 healing casts; 84,631 effective healing in 174.912 s; zero actor damage |
| Category is not duty | [Playbook](../../workspace/druid-guardian/playbook.html) | [Report](../../workspace/druid-guardian/report.html) | Suncat's Guardian Patchwerk parse has no tank hits; Harryjam's cohort entry has tank hits despite missing usable form intervals |

For another checkout, run `git lfs pull`, then
`uv run necropsy offline tests/golden/druid/raw/NAME.zip --out workspace/EXAMPLE`.
Use `druid-mixed.zip` for Four Horsemen and
`druid-sapphiron-restoration.zip` for your Sapphiron example.

## Decisions David owns

These mirror the domain/product boxes. Supplying logs and authorizing fixtures
did not approve the resulting findings.

1. **01.4 — taxonomy:** accept or correct the separation of build, WCL category,
   query metric, actions, inferred duty and assignment. Provisional inference
   needs three recognized casts and at least 20% of categorized casts for a
   non-tank duty. Tank duty additionally needs repeated bear-only actions plus
   three direct encounter-enemy hits. Minor signals stay visible. Cast share is
   not time share or a proven raid assignment.
2. **03.4 / 04.4 — findings and advice:** review the damage, healing, tank and
   mixed examples. Correct misleading roles or advice. Your stated Sapphiron
   assignment agrees with the selected healing performance; public players'
   assignments remain unknown.
3. **06.3 — limits:** accept or correct sparse exact-build baselines, missing
   overheal/resources/threat/form intervals, low-confidence practice notes, and
   no whole-fight hybrid comparison. Activity spans are first/last action
   evidence, not continuous assignment phases. No requested role is deferred.
   Selected fights across three bosses do not certify full-raid live acceptance
   or universal optimal rotations.

Balance/HPS Sapphiron acquisition found public rows but no matching personal
Balance-category row; the subject correctly stays absent. The separate
Restoration/HPS capture supplies your actual healing example.

## Engineering evidence

- Fast suite: 855 passed. Full Hunter-plus-initial-Druid golden/acceptance:
  233 passed, four existing expected failures. Expanded six-Druid replay:
  six passed with independent arithmetic and package member hashes.
- Browser suite: 23 passed. Final real-artifact checks: 24 page/viewport cases,
  zero automatic remote requests, no overflow or script errors; all six outputs
  passed the existing acceptance artifact checker and output secret scans.
- Ruff lint/format, strict mypy and wheel/sdist build passed. Hunter JSON, both
  pages and shareable ZIP match the saved baseline byte for byte.
- Gitleaks found no leaks in 169,740,861 initial extracted bytes or 62,401,552
  added extracted bytes. Raw ZIPs stay immutable.
- Claude core round 1 approved with an incidental-duty finding subsequently
  fixed; output round 2 approved without findings. Final targeted round 3 approved with zero blocking/important findings; its
  exclusions remain explicit in the subject receipts. Linux/Windows CI db89d3a
  passed. Agent implementation and verification are complete; the decisions
  above remain yours.

Agent checks never substitute for your domain decision.
