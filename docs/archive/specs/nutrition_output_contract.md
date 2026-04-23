# Nutrition Output Contract

## Primary truth
- Nutrition LLM owns:
  - `estimated_kcal`
  - `kcal_low`
  - `kcal_most_likely`
  - `kcal_high`
  - `components`
  - `component_breakdown`
  - `uncertainty_factors`
  - posture fields such as `exactness`, `estimate_mode`, `confidence`
- Conversational truth is `kcal + components + portion reasoning + uncertainty`.
- Macro is not conversational truth.

## Required component fields
Each `component_breakdown` item should include:
- `name`
- `estimated_kcal`
- `portion_basis`
- `reason`
- `evidence_ids`

Optional when supported:
- `protein_g`
- `carb_g`
- `fat_g`
- `quantity`
- `unit`
- `confidence`

## Macro policy
- Exact case: use exact label or official macro directly when macro exists in evidence; if the exact source is `kcal_only`, macro may remain `unavailable`.
- Anchored case: UI macro is derived deterministically from `component_breakdown`.
- Heuristic or unknown case: macro may be `unavailable` or `low_confidence_derived`.
- Detailed presentation rules are defined in:
  - [Macro Reconciliation Spec](C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/macro_reconciliation_spec.md)

## UI contract
- UI should read:
  - `estimated_kcal`
  - `component_breakdown`
  - `macro_breakdown`
- `macro_breakdown` must include:
  - `protein_g`
  - `carb_g`
  - `fat_g`
  - `macro_source`
  - `macro_confidence`
  - `macro_status`
