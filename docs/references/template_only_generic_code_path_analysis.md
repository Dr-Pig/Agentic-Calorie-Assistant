# Template-Only Generic Code Path Analysis

This note documents the remaining leak path for generic classes that still sometimes output a target kcal even when only template-level scaffold evidence is present.

## Intended rule
If all of the following are true:
- `exact_lane_count == 0`
- `anchor_lane_count == 0`
- `template_lane_count > 0` or `meal_template_hit == true`

then the system should default to `ask_followup_only` and should not emit a concrete target kcal.

## Current path
1. `match_meal_template()` can fire early in [`app/usecases/text_meal.py`](C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/usecases/text_meal.py).
2. `prepare_initial_grounding()` builds `partial_grounding` and `normalized_evidence`, which can still contain template-derived scaffold context.
3. `build_nutrition_resolution_payload()` packs:
   - `template_lane_hits`
   - `anchor_lane_candidates`
   - `exact_lane_candidates`
   - `reasoning_state`
4. [`_nutrition_repair_note()`](C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/usecases/text_meal_nutrition_support.py) already contains a guard that says template-only evidence should force `clarify_before_estimate`.
5. Leakage still happens when the initial nutrition output already contains a seemingly usable kcal and the repair path does not fire, or when a generic scaffold is accidentally treated as weak anchor context.

## What is already fixed
- Template-only generic cases are now much more conservative than before.
- `case_017_luwei_generic` no longer defaults to a template-driven kcal in the sampled v2 run.
- Exact candidate pollution has been removed, so this path is now easier to isolate.

## Remaining risk
- Some generic classes still arrive at nutrition with enough pseudo-structure to look "answerable" even though the structure is only a scaffold, not real grounded evidence.
- This mainly affects high-variance dishes where the template describes common components but not the user's actual selection.

## Required runtime rule
The final gate should stay mechanism-based:
- `exact lane present` -> exact or near-exact finalize is allowed
- `anchor lane present` -> anchored estimate is allowed
- `template lane only` -> ask follow-up only

The fix should continue to live in evidence-lane handling and nutrition repair policy, not as benchmark-specific case logic.
