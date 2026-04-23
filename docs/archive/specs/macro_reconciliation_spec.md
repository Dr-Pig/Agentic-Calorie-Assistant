# Macro Reconciliation Spec

## Purpose
- Keep `estimated_kcal` as the primary conversational truth.
- Allow the UI to display macro only when it is consistent enough with the calorie estimate.
- Prevent the product from showing a calorie total and a macro breakdown that obviously contradict each other.

## Product truth hierarchy
### Primary truth
- `estimated_kcal`
- `kcal_low`
- `kcal_most_likely`
- `kcal_high`
- `components`
- `component_breakdown`
- `uncertainty_factors`

### Secondary truth
- `macro_breakdown`
- `macro_source`
- `macro_confidence`
- `macro_status`

Macro is a UI artifact. It must never override the primary calorie estimate.

## Inputs
- Nutrition LLM output:
  - `estimated_kcal`
  - `kcal_low`
  - `kcal_high`
  - `component_breakdown`
  - `exactness`
  - `estimate_mode`
- Deterministic macro derivation output:
  - `protein_g`
  - `carb_g`
  - `fat_g`
  - `macro_kcal`
  - `macro_source`
  - `macro_confidence`
  - `macro_status`

## Output model
The system should distinguish between:
- `raw_macro_breakdown`
  - direct output from exact evidence or deterministic component derivation
- `display_macro_breakdown`
  - the macro actually shown in the UI

The UI should always read `display_macro_breakdown`, not raw macro directly.

## Macro source categories
- `exact_label`
  - exact label / official evidence provided macro directly
- `derived_consistent`
  - derived from components and already consistent with calorie estimate
- `derived_reconciled`
  - derived from components, then proportionally adjusted for UI consistency
- `unavailable`
  - not reliable enough to show

## Reconciliation policy
### 1. Exact case
If exact or official evidence includes macro:
- use it directly
- `macro_source = exact_label`
- no reconciliation required unless exact evidence itself is internally broken

If exact evidence is `kcal_only`:
- do not invent exact macro
- `macro_source = unavailable`

### 2. Anchored case
If macro is derived from `component_breakdown`:
- compute `raw_macro_kcal = protein_g * 4 + carb_g * 4 + fat_g * 9`
- compare `raw_macro_kcal` against the calorie estimate

Decision thresholds:
- `delta_pct <= 10%`
  - show raw macro as-is
  - `macro_source = derived_consistent`
- `10% < delta_pct <= 20%`
  - UI may proportionally scale macro to match `estimated_kcal`
  - mark `macro_source = derived_reconciled`
  - keep original raw macro in trace only
- `delta_pct > 20%`
  - do not show macro
  - `macro_source = unavailable`

### 3. Heuristic or unknown case
For heuristic or unknown answers:
- if component coverage is weak or missing, macro is `unavailable`
- if derived macro falls outside the calorie band, macro is `unavailable`
- only show derived macro when component support is unusually strong and consistent

Default posture:
- prefer hiding macro over showing misleading macro

## Range-based consistency rule
If `kcal_low` and `kcal_high` exist:
- treat the calorie band as the first consistency check
- if `raw_macro_kcal` falls inside `[kcal_low, kcal_high]`, macro may be shown
- if it falls outside the band but within the reconciliation tolerance, UI may use `derived_reconciled`
- if it remains outside the band after reconciliation, macro must be `unavailable`

## Reconciliation math
When `derived_reconciled` is allowed:
- compute `scale = estimated_kcal / raw_macro_kcal`
- scale:
  - `protein_g`
  - `carb_g`
  - `fat_g`
- round to UI-safe values
- record:
  - `raw_macro_kcal`
  - `display_macro_kcal`
  - `reconciliation_scale`
  - `macro_reconciled = true`

This scaling is a presentation-layer correction.
It does not change:
- `estimated_kcal`
- `component_breakdown`
- `component semantics`

## UI rules
### UI must show
- `estimated_kcal`
- `component_breakdown`

### UI may show macro only if
- `macro_source` is one of:
  - `exact_label`
  - `derived_consistent`
  - `derived_reconciled`

### UI must hide macro if
- `macro_source = unavailable`
- `macro_confidence = low` and consistency checks failed
- component coverage is too weak

### Optional UI metadata
If product wants transparency later:
- exact label
- estimated from ingredients
- estimated and adjusted for consistency

This metadata is optional for first release.

## Guard and trace behavior
Deterministic guard should record:
- `raw_macro_kcal`
- `display_macro_kcal`
- `delta_kcal`
- `delta_pct`
- `macro_source`
- `macro_confidence`
- `macro_reconciled`
- `component_macro_coverage`

Guard may:
- add warnings
- downgrade confidence
- suppress macro display

Guard must not:
- overwrite `estimated_kcal`
- rewrite components
- turn heuristic answers into exact answers

## Recommended initial thresholds
- exact label: always show when available
- anchored:
  - show raw if `delta_pct <= 10%`
  - reconcile if `10% < delta_pct <= 20%`
  - hide if `delta_pct > 20%`
- heuristic / unknown:
  - default to hide unless consistency is unusually strong

These thresholds can be tuned later, but they should be fixed in runtime config rather than improvised in prompt logic.

## Implementation guidance
### Runtime
- Nutrition LLM continues to own calorie estimate and component semantics.
- Deterministic layer owns:
  - macro derivation
  - consistency checking
  - display/no-display decision
  - optional proportional reconciliation

### Trace
- Keep both raw and display macro in observability payload.
- UI consumes display macro only.

### Prompt
- Do not force the Nutrition LLM to perfectly balance macro and kcal.
- Ask the LLM to focus on:
  - calorie estimate
  - component structure
  - portion reasoning
- Treat macro as a derived artifact whenever exact label is absent.

## Final rule
If macro and calorie estimate disagree too much, trust the calorie estimate and hide macro.
