# Task Artifact

- `task_id`: `TASK-2026-04-12-021-CALIBRATION-POSTURE-FOUNDATION`
- `slice_id`: `2.6b-calibration-posture-foundation`
- `status`: `COMPLETED`
- `owner`: `worker`
- `started_at`: `2026-04-12`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md)
- [docs/specs/L2_DATA_STATE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2_DATA_STATE_SPEC.md)
- [docs/specs/L2A_DATA_DICTIONARY_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2A_DATA_DICTIONARY_SPEC.md)
- [docs/specs/L3M_GUARDRAIL_MATH_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3M_GUARDRAIL_MATH_SPEC.md)
- [docs/governance/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/BUILD_FILE_PLACEMENT_RULES.md)
- [docs/governance/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/LAYER_DEPENDENCY_RULES.md)

## Goal

Create the first bounded calibration-core implementation slice: a deterministic calibration model that classifies posture and emits an operating-expenditure estimate posture without entering proposal generation, UI, or recommendation wiring.

## Planned Touch Files

- `app/application/calibration_model.py`
- `app/application/target_calculation.py` only if baseline-target integration needs a narrow helper or import alignment
- `app/domain/canonical_models.py` only if a narrow typed output is required for the calibration model result
- `tests/test_calibration_model.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-12-021-CALIBRATION-POSTURE-FOUNDATION.md`

## Forbidden Files

- `app/routes.py`
- `app/usecases/text_meal.py`
- `app/schemas.py`
- calibration proposal runtime
- recommendation / proactive response logic
- rescue runtime semantics
- memory / retrieval selector logic
- freeze-growth files unless a re-plan trigger is hit and explicitly recorded

## New Files Expected

- `app/application/calibration_model.py`
- `tests/test_calibration_model.py`

## Completion Criteria

- deterministic calibration model emits posture classes from `L3.3A` without proposal generation
- v1 thresholds honor the `14-day / 5-observation / 80% intake coverage` defaults
- output distinguishes `operating_expenditure_estimate` from `intake_estimation_bias_posture`
- no canonical writeback, proposal creation, or UI coupling is introduced
- protected legacy files remain untouched

## Completion Record

- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `app/application/calibration_model.py`
  - `tests/test_calibration_model.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-12-021-CALIBRATION-POSTURE-FOUNDATION.md`
- `tests_run[]`:
  - `python -m pytest tests/test_calibration_model.py -q`
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
- `reality_drift_notes`:
  - `none`
- `source_of_truth_updated`:
  - `yes`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`:
  - `docs/exec-plans/completed/handoff/HANDOFF-2026-04-12-021-CALIBRATION-POSTURE-FOUNDATION.md`

## Tests To Run

- `python -m pytest tests/test_calibration_model.py -q`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`

## Expected Re-plan Impact

Will determine the next calibration-core slice boundary: either a canonical writeback / active-BodyPlan adoption slice or a separate proposal-policy slice under `L3.3B`.
