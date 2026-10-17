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
- Verify historical Naxx. Its existing pet-absence examples have positive
  recorded medians; do not silently change their expected behavior or update
  frozen artifacts to hide an unrelated difference.

This is a narrow evidence requirement, not full opportunity/duty-aware advice.
Those obligations remain open, including legitimate no-pet assignments, pet
safety, target access and conditional practice guidance. No whole subject or
matrix cell closes from this correction.
