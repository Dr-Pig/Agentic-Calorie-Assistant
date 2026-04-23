# Deterministic Macro Derivation Spec

## Goal
Produce UI macro from stable structure without letting deterministic logic overwrite conversational kcal.

See also:
- [Macro Reconciliation Spec](C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/macro_reconciliation_spec.md)

## Inputs
- `answer_payload.component_breakdown`
- `answer_payload.estimated_kcal`
- normalized evidence
- final nutrition posture (`exactness`, `estimate_mode`)

## Output
- `protein_g`
- `carb_g`
- `fat_g`
- `macro_source`
  - `exact_label`
  - `derived_from_components`
  - `unavailable`
- `macro_confidence`
- `macro_status`
- `macro_kcal`

## Rules
- If exact label macros exist in exact or official evidence, use them as `exact_label`.
- If an exact case only has `kcal_only` evidence and no component macros, return `unavailable`.
- Otherwise derive by summing per-component macro values from `component_breakdown`.
- If component macros are missing in heuristic or unknown cases, return `unavailable`.
- If only partial component macros exist, return `derived_from_components` with low confidence.
- Deterministic macro never rewrites the conversational kcal result.

## Guard behavior
- Compare `macro_kcal` against total kcal with wide tolerance.
- Compare summed component kcal against total kcal.
- On mismatch:
  - add warning
  - downgrade confidence
  - emit trace
- Do not rewrite component semantics or kcal.
