# Task Artifact

- `task_id`: `TASK-2026-04-12-020-RECOMMENDED-TARGET-KCAL-FOUNDATION`
- `slice_id`: `2.6a-recommended-target-kcal-foundation`
- `status`: `COMPLETED`
- `owner`: `planner`
- `started_at`: `2026-04-12`

## Source Of Truth Refs

- [docs/references/SAFETY_FLOOR_AND_TARGET_DECISION_NOTE.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references/SAFETY_FLOOR_AND_TARGET_DECISION_NOTE.md)
- [docs/references/RECOMMENDED_TARGET_KCAL_DECISION_NOTE.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references/RECOMMENDED_TARGET_KCAL_DECISION_NOTE.md)
- [docs/specs/L2_DATA_STATE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2_DATA_STATE_SPEC.md)
- [docs/specs/L2A_DATA_DICTIONARY_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2A_DATA_DICTIONARY_SPEC.md)
- [docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md)
- [docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md)

## Goal

Define and implement a deterministic personalized daily target calculation that uses user/body inputs and weekly loss target while staying above `BodyPlan.safety_floor_kcal`.

## Planned Touch Files

- `app/application/target_calculation.py`
- `app/domain/canonical_models.py` only if a narrow target field must be added to BodyPlan-facing types
- `tests/test_target_calculation.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-12-020-RECOMMENDED-TARGET-KCAL-FOUNDATION.md`

## Forbidden Files

- `app/routes.py`
- `app/usecases/text_meal.py`
- `app/schemas.py`
- recommendation response surfaces
- proactive logic
- freeze-growth files unless a re-plan trigger is hit and explicitly recorded

## New Files Expected

- `app/application/target_calculation.py`
- `tests/test_target_calculation.py`

## Completion Criteria

- deterministic target calculation uses personal inputs and weekly loss target
- target result is explicitly separate from `BodyPlan.safety_floor_kcal`
- computed target never drops below hard floor
- tests cover both baseline floor clamping and larger-body personalized targets

## Tests To Run

- `python -m pytest tests/test_target_calculation.py -q`

## Expected Re-plan Impact

Will determine whether recommendation / calibration can consume a stable personalized target scalar without overloading rescue hard-floor semantics.

## Completion Record

- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `app/application/target_calculation.py`
  - `tests/test_target_calculation.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-12-020-RECOMMENDED-TARGET-KCAL-FOUNDATION.md`
- `tests_run[]`:
  - `python -m pytest tests/test_target_calculation.py -q`
- `reality_drift_notes`:
  - `none`
- `source_of_truth_updated`:
  - `yes`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`:
  - `docs/handoff/completed/HANDOFF-2026-04-12-020-RECOMMENDED-TARGET-KCAL-FOUNDATION.md`
