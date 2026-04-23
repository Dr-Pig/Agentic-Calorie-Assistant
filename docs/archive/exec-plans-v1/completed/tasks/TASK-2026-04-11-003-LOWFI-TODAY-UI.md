# Task Artifact

- `task_id`: `TASK-2026-04-11-003-LOWFI-TODAY-UI`
- `slice_id`: `2.3b-low-fi-today-ui`
- `status`: `COMPLETED`
- `owner`: `codex-today-ui-worker`
- `started_at`: `2026-04-11`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/L2_DATA_STATE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2_DATA_STATE_SPEC.md)
- [docs/specs/L6B_BUILD_STRATEGY_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6B_BUILD_STRATEGY_SPEC.md)

## Goal

Create the first low-fi Today surface that renders canonical current-budget truth without inventing recommendation, rescue, calibration, or proactive behavior.

## Planned Touch Files

- `app/routes.py`
- `static/dashboard.html`
- `app/application/current_budget_read_model.py` only if a route-facing adapter is needed
- `tests/test_routes_today_ui.py`
- `docs/specs/*` only if UI truth wording is genuinely unclear

## Forbidden Files

- recommendation runtime modules
- rescue, calibration, and proactive logic
- `text_meal.py`
- canonical persistence write paths
- weight/body observation write semantics

## Completion Criteria

- a low-fi today-facing route or surface reads from the current-budget read model instead of raw tables
- the UI remains additive and truthful to read-model state
- no recommendation-specific or proactive controls are introduced
- route or rendering behavior is test-covered at least at smoke level

## Tests To Run

- today UI rendering smoke test
- today route or response shape test
- current-budget read-model regression tests if the route adapter changes

## Expected Re-plan Impact

Will determine whether `2.4b-weight-ui` can reuse the same route or surface conventions, and whether a separate today-surface adapter is needed before richer UI work.

## Completion Notes

- Added a dedicated low-fi Today surface at `/today` that renders canonical current-budget truth.
- Added a route-facing JSON shape at `/today/current-budget` for smoke validation and future reuse.
- The Today surface reads from `build_current_budget_view(...)` and does not inspect raw legacy meal-log tables.
- Kept the change additive; no recommendation, rescue, calibration, or proactive behavior was introduced.

## Actual Touch Files

- `app/routes.py`
- `tests/test_routes_today_ui.py`

## Tests Run

- `python -m pytest tests/test_routes_today_ui.py -q`
- `python -m pytest tests/test_current_budget_read_model.py -q`

## Reality Drift

- The functional slice is complete for code and tests, but a checked-in handoff artifact was not created in this worker scope.
- The next closeout step should add the matching handoff doc and then mark the slice fully closed if the operating layer requires it.

## Completion Record

- `completed_at`: `2026-04-11`
- `actual_touch_files[]`:
  - `app/routes.py`
  - `tests/test_routes_today_ui.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-11-003-LOWFI-TODAY-UI.md`
- `tests_run[]`:
  - `python -m pytest tests/test_routes_today_ui.py -q`
  - `python -m pytest tests/test_current_budget_read_model.py -q`
- `reality_drift_notes`:
  - code and tests completed before the required handoff artifact existed; closeout now requires the matching handoff doc
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - `TASK-2026-04-11-005-WEIGHT-UI`
- `handoff_doc_path`: `docs/exec-plans/active/handoff/HANDOFF-2026-04-11-003-LOWFI-TODAY-UI.md`
