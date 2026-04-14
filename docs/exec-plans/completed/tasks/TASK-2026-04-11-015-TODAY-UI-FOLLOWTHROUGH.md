# Task Artifact

- `task_id`: `TASK-2026-04-11-015-TODAY-UI-FOLLOWTHROUGH`
- `slice_id`: `2.3b-low-fi-today-ui`
- `status`: `COMPLETED`
- `owner`: `delegated-worker`
- `started_at`: `2026-04-11`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/governance/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/BUILD_FILE_PLACEMENT_RULES.md)
- [docs/governance/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/LAYER_DEPENDENCY_RULES.md)
- [docs/specs/L2_DATA_STATE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2_DATA_STATE_SPEC.md)

## Goal

Follow through on the low-fi Today surface after read-model regression closure so the Today routes remain aligned with correction-safe canonical read truth and do not drift back toward legacy/raw coupling.

## Planned Touch Files

- `app/web/today_routes.py`
- `tests/test_routes_today_ui.py`
- `tests/test_current_budget_read_model.py` only if route/read-model coupling needs a direct regression
- `docs/exec-plans/active/tasks/TASK-2026-04-11-015-TODAY-UI-FOLLOWTHROUGH.md`

## Forbidden Files

- `app/routes.py`
- `app/usecases/text_meal.py`
- `app/schemas.py`
- recommendation / rescue / calibration / proactive logic
- weight UI work
- freeze-growth files unless a re-plan trigger is hit and explicitly recorded

## New Files Expected

- none by default

## Completion Criteria

- Today surface remains correction-safe after the read-model follow-through
- route behavior is regression-covered against canonical active-version-only truth
- no new product behavior is introduced beyond truthful current-budget rendering
- protected legacy files remain untouched

## Tests To Run

- `python -m pytest tests/test_routes_today_ui.py -q`
- `python -m pytest tests/test_current_budget_read_model.py -q` only if route/read-model coupling needs reconfirmation

## Expected Re-plan Impact

Will determine whether the next best step is `2.1e-web-search-fallback-lane` or a richer read-side/UI slice.

## Completion Notes

- The Today surface already stayed aligned with the current-budget read model, so no route behavior change was required.
- Added a regression test that drives a correction chain through canonical commit helpers and confirms `/today/current-budget` and `/today` both render only the final active version.
- Protected legacy files remain untouched.

## Completion Record

- `completed_at`: `2026-04-11`
- `actual_touch_files[]`:
  - `tests/test_routes_today_ui.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-11-015-TODAY-UI-FOLLOWTHROUGH.md`
  - `docs/exec-plans/active/handoff/HANDOFF-2026-04-11-015-TODAY-UI-FOLLOWTHROUGH.md`
- `tests_run[]`:
  - `python -m pytest tests/test_routes_today_ui.py -q`
- `reality_drift_notes`:
  - the Today route was already canonical-read-model backed, so the slice closed through regression coverage rather than implementation changes
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - none
- `handoff_doc_path`: `docs/exec-plans/active/handoff/HANDOFF-2026-04-11-015-TODAY-UI-FOLLOWTHROUGH.md`
