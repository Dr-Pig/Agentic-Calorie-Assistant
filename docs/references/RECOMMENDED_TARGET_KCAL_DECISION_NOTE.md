# Recommended Target Kcal Decision Note

## Decision

For v1 deterministic personalized target calculation, the repository adopts:

- `Mifflin-St Jeor` as the baseline BMR formula
- fixed activity multipliers for coarse activity posture
- weekly loss target converted to daily deficit using `7700 kcal / kg`
- final target clamped so it never drops below `BodyPlan.safety_floor_kcal`

## Scope

This decision applies to:

- deterministic `recommended_target_kcal` calculation
- recommendation / calibration target foundation

It does not redefine:

- `BodyPlan.safety_floor_kcal`
- rescue hard-floor guardrail math
- later calibration overrides from observed body-weight and logging history

## Product Posture

- `recommended_target_kcal` is a v1 baseline operating target, not a medical prescription
- `BodyPlan.safety_floor_kcal` remains the hard lower bound
- later calibration may revise the operating target, but should not silently lower the hard floor

## Why This Formula Family

- it is a common practical baseline when indirect calorimetry is unavailable
- it matches the repository decision to keep v1 deterministic and explainable
- it separates `hard floor` from `personalized target`

## Follow-on Rule

- future calibration work may revise the operating target based on weight trend and intake quality
- such calibration should consume this baseline, not replace the hard floor concept
