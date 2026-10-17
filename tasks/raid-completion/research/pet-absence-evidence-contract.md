# Pet absence recommendation guardrails

2026-10-18, before changing recommendation behavior. PM-1/PM-2/PM-3 apply.
Implementation follows the in-flight Feign Death checkpoint; do not mutate
production code while its full ordinary suite is running.

The shipped recommendation confused a known observation with a justified
change. In retained `aq40-hunter-expanded-context`, Temison's Sartura fight
`Jw7RDb43XKALngca/18` explicitly lists no pet. Five same-faction comparisons
have known pet measurements, with median0 DPS; three comparisons also list no
pet. The current engine nevertheless emits high-confidence/high-severity
`pet-absent`, instructing the player to bring a pet and keep it attacking.
Known absence is valid; this baseline does not justify that instruction.

Correct the shared recommendation seam, not a class-plugin boss-ID branch:

- Keep confirmed no-pet observations, pet-DPS zero, unknown classification and
  unresolved guardian ownership distinct. Suppressing an unsupported action
  must not erase the known no-pet fact from saved JSON or either page.
- Require a supported comparison before emitting this comparative absence
  recommendation: the existing three-known-value minimum and a positive known
  same-faction trained-pet median. Unknown, insufficient and zero baselines
  cannot justify a high-priority positive pet instruction. This is not a rule
  that Sartura forbids pets, nor proof of anyone's assignment.
- Preserve class/category/metric/faction eligibility and existing roster guards.
  No other-faction or guardian damage becomes trained-pet benchmark credit.
  Positive benchmark cases must still exercise the supported behavior.
- Freeze the real observed contradiction before implementation. Use synthetic
  known/unknown/zero/insufficient/positive baselines and actual Sartura replay.
  Check both actual pages and preserve all525 actor/322 recipient/41 pet facts.
- Verify historical Naxx. Direct inspection corrected the initial assumption
  that all four absence examples had positive medians: Sapphiron has only two
  known comparisons and an unknown median. Reanalysis intentionally removes
  that unsupported action, retaining the four historical absence observations
  and the three supported actions (Anub'Rekhan, Gluth, Heigan). Preserve the
  original fact register and raw archives; distinguish the historical absence
  fact from current recommendation policy in its checker and tests.

Actual-page verification found a second presentation issue: the condensed
Playbook did not display the no-pet observation once the action was withheld.
Keep a factual absence line from saved personal evidence in both pages, without
creating an instruction or borrowing a comparison player's participation.
Positive/negative/unknown/missing-personal render cases cover that boundary.
This changes rendered Naxx fact visibility as well as removing the unsupported
Sapphiron action; it does not change any other analysis JSON value. Old saved
JSON retains its exact bytes and saved advice when rendered by the new view.

This is a narrow evidence requirement, not full opportunity/duty-aware advice.
Those obligations remain open, including legitimate no-pet assignments, pet
safety, target access and conditional practice guidance. No whole subject or
matrix cell closes from this correction.
