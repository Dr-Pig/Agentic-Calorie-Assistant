# Task Artifact

- `task_id`: `TASK-2026-04-12-025-CURRENT-BUDGET-READMODEL-DATE-FOLLOWTHROUGH`
- `slice_id`: `2.3a-current-budget-read-model`
- `status`: `COMPLETED`
- `owner`: `planner`
- `started_at`: `2026-04-12`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/L2_DATA_STATE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2_DATA_STATE_SPEC.md)
- [docs/specs/L3M_GUARDRAIL_MATH_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3M_GUARDRAIL_MATH_SPEC.md)
- [docs/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/BUILD_FILE_PLACEMENT_RULES.md)
- [docs/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/LAYER_DEPENDENCY_RULES.md)

## Goal

Reconfirm that the current-budget read model still reflects the correct active-version and local-date truth after `2.2a` continuation proof and `2.2c` cross-midnight attribution changes.

## Planned Touch Files

- `app/application/current_budget_read_model.py`
- `app/infrastructure/current_budget_read_model.py`
- `tests/test_current_budget_read_model.py`
- `tests/test_canonical_persistence.py` only if a direct read-side / canonical coupling regression is required
- `docs/exec-plans/active/tasks/TASK-2026-04-12-025-CURRENT-BUDGET-READMODEL-DATE-FOLLOWTHROUGH.md`

## Forbidden Files

- `app/routes.py`
- `app/usecases/text_meal.py`
- `app/schemas.py`
- `app/web/*`
- rescue / calibration / recommendation / proactive logic
- freeze-growth files unless a real re-plan trigger is hit and explicitly recorded

## New Files Expected

- none by default

## Completion Criteria

- current-budget read model remains active-version-only after continuation and cross-midnight changes
- read side attributes meals to the correct local day after late-night intake / correction flows
- regression coverage exists for both continuation-safe and cross-midnight-safe budget truth
- protected legacy files stay untouched

## Tests To Run

- `python -m pytest tests/test_current_budget_read_model.py -q`
- `python -m pytest tests/test_canonical_persistence.py -q -k "local_date or version"`
- `python scripts/check_layer_integrity.py` only if layer edges change

## Expected Re-plan Impact

Will determine whether the next best-next slice is `2.3b-low-fi-today-ui` follow-through or whether read-side truth still needs one more bounded correction before Today-surface work resumes.

## Completion Record

- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `tests/test_current_budget_read_model.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-12-025-CURRENT-BUDGET-READMODEL-DATE-FOLLOWTHROUGH.md`
- `tests_run[]`:
  - `python -m pytest tests/test_current_budget_read_model.py -q`
  - `python -m pytest tests/test_canonical_persistence.py -q -k "local_date or version"`
- `reality_drift_notes[]`:
  - `Current-budget read model stays active-version-only after continuation and cross-midnight changes, with a regression proving the corrected meal remains on the canonical local day and does not bleed into the next day.`
  - `No production read-model code changes were required; the existing read-side filters already preserved the canonical version/date truth.`
- `source_of_truth_updated`: `no`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`: `docs/handoff/completed/HANDOFF-2026-04-12-025-CURRENT-BUDGET-READMODEL-DATE-FOLLOWTHROUGH.md`
