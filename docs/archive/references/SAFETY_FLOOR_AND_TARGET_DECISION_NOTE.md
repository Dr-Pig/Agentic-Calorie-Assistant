# Safety Floor And Target Decision Note

## Decision

Adopt a two-layer policy:

- `BodyPlan.safety_floor_kcal` = hard safety floor used by runtime guardrails
- `recommended_target_kcal` = separately computed deterministic daily target used for recommendation / calibration

## Hard Floor Policy

Current v1 baseline:

- female baseline hard floor: `1200 kcal/day`
- male baseline hard floor: `1500 kcal/day`

These values are treated as a product safety lower bound. Runtime must not go below them.

## Runtime Rule

- rescue / calibration / recommendation runtime should read `active BodyPlan.safety_floor_kcal` as the canonical hard floor
- runtime may accept an explicit override when a bounded workflow intentionally supplies one
- runtime must not silently infer a new floor from sex, gender, or profile fields when the canonical scalar is missing

## Personalized Target Rule

- the user's daily recommendation target should not be a fixed `1200 / 1500`
- it should be computed deterministically from personal inputs such as:
  - age
  - sex
  - height
  - weight
  - activity level
  - weekly loss target
- the resulting personalized target must still stay above the hard floor

## Product Reasoning

- `1200 / 1500` works well as a stable safety rail
- it does not work well as the user's everyday personalized target
- separating `hard floor` from `recommended target` prevents rescue/calibration/runtime from mixing safety policy with individualized planning math

## External Reference Direction

- MyFitnessPal publicly states that its initial goals use personal stats plus weight-change goals, while still warning against going below `1200` for women and `1500` for men
- MyPlate publicly states that adult plans are based on estimated energy requirement formulas and activity assumptions rather than a single fixed calorie number

These external references support the repository choice to:

- keep a fixed hard lower bound
- compute a separate personalized target

## Planner Recommendation

Keep this as the canonical policy:

1. `BodyPlan.safety_floor_kcal` is the persisted hard floor
2. `recommended_target_kcal` is a separate deterministic calculation task
3. rescue/runtime reads the hard floor, not the personalized target
