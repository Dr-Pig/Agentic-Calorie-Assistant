# Task Artifact

- `task_id`: `TASK-2026-04-11-002-READMODEL-FOUNDATION`
- `slice_id`: `2.3a-current-budget-read-model`
- `status`: `COMPLETED`
- `owner`: `codex-current-worker`
- `started_at`: `2026-04-11`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/L2_DATA_STATE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2_DATA_STATE_SPEC.md)
- [docs/specs/L3M_GUARDRAIL_MATH_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3M_GUARDRAIL_MATH_SPEC.md)
- [docs/specs/L6B_BUILD_STRATEGY_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6B_BUILD_STRATEGY_SPEC.md)

## Goal

Create the first stable current-budget read-model foundation so the today surface can read canonical ledger truth without coupling UI directly to raw persistence tables.

## Planned Touch Files

- `app/application/current_budget_read_model.py`
- `app/infrastructure/current_budget_read_model.py`
- `app/domain/canonical_models.py`
- `app/domain/__init__.py`
- `app/application/__init__.py`
- `tests/test_current_budget_read_model.py`
- `docs/specs/*` only if read-model truth needs clarification

## Forbidden Files

- recommendation runtime modules
- proactive logic
- final UI styling/layout work
- external provider adapters unrelated to read models

## Completion Criteria

- a read helper or read-model service exposes current budget truth from canonical ledger state
- query semantics are test-covered
- today UI can depend on the read model instead of raw canonical tables
- no recommendation-specific behavior is introduced

## Tests To Run

- current budget read-model unit tests
- canonical ledger recompute regression tests
- smoke test for today-surface-facing query shape

## Expected Re-plan Impact

Will determine whether `2.3b-low-fi-today-ui` can start immediately or whether additional query helpers are still needed.

## Completion Notes

- Added a today-facing query-shape regression test that locks the `CurrentBudgetView` and `CurrentBudgetMealSummary` payload shape for the low-fi Today surface.
- Kept the read model within canonical ledger truth and active-version summaries only.
- Did not add UI, recommendation, calibration, rescue, or provider changes.
- The current-budget read model now exposes the minimum stable shape needed for `2.3b-low-fi-today-ui` to consume without reading raw persistence tables directly.
- Validation:
  - `python -m pytest tests/test_current_budget_read_model.py -q` -> `3 passed`
  - `python -m pytest tests/test_canonical_persistence.py tests/test_current_budget_read_model.py -q` -> `11 passed`
- Reality drift:
  - none beyond the expected Windows pytest temp cleanup warning on exit

## Completion Record

- `completed_at`: `2026-04-11`
- `actual_touch_files[]`:
  - `tests/test_current_budget_read_model.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-11-002-READMODEL-FOUNDATION.md`
- `tests_run[]`:
  - `python -m pytest tests/test_current_budget_read_model.py -q`
  - `python -m pytest tests/test_canonical_persistence.py tests/test_current_budget_read_model.py -q`
- `reality_drift_notes`:
  - none beyond the expected Windows pytest temp cleanup warning on exit
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`: `docs/handoff/active/HANDOFF-2026-04-11-002-READMODEL-FOUNDATION.md`
