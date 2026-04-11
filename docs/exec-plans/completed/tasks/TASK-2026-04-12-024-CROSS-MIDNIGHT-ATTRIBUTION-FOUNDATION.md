# Task Artifact

- `task_id`: `TASK-2026-04-12-024-CROSS-MIDNIGHT-ATTRIBUTION-FOUNDATION`
- `slice_id`: `2.2c-cross-midnight-attribution`
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

Make late-night intake and correction flows resolve to the correct local ledger date so cross-midnight continuation and correction do not silently drift to the wrong day.

## Planned Touch Files

- `app/application/time_labels.py`
- `app/application/state_transition.py` only if a narrow local-date handoff is required
- `app/usecases/text_meal_service.py` only if a narrow entrypoint adapter is required
- `tests/test_text_meal.py`
- `tests/test_canonical_persistence.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-12-024-CROSS-MIDNIGHT-ATTRIBUTION-FOUNDATION.md`

## Forbidden Files

- `app/routes.py`
- `app/schemas.py`
- `app/usecases/text_meal.py`
- `app/infrastructure/meal_log_persistence.py` unless a real date-attribution blocker is proven and recorded as a re-plan trigger
- `app/application/canonical_commit_bridge.py` unless a real local-date lineage blocker is proven and recorded as a re-plan trigger
- calibration / recommendation / proactive logic
- rescue runtime semantics
- memory / retrieval selector logic
- freeze-growth files unless a real re-plan trigger is hit and explicitly recorded

## New Files Expected

- none by default

## Completion Criteria

- cross-midnight intake attributes to the correct local ledger date
- cross-midnight correction does not silently drift to the wrong day
- main-flow date-attribution regression is covered
- protected legacy files remain untouched

## Tests To Run

- `python -m pytest tests/test_text_meal.py -q -k "midnight or local_date or attribution"`
- `python -m pytest tests/test_canonical_persistence.py -q -k "local_date or correction"`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`

## Expected Re-plan Impact

Will determine whether `2.2` is stable enough to resume `2.3 / 2.5` progression cleanly or whether more intake-runtime alignment is still needed before leaving the multi-turn domain.

## Completion Record

- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `app/application/time_labels.py`
  - `app/usecases/text_meal_service.py`
  - `tests/test_text_meal.py`
  - `tests/test_canonical_persistence.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-12-024-CROSS-MIDNIGHT-ATTRIBUTION-FOUNDATION.md`
- `tests_run[]`:
  - `python -m pytest tests/test_text_meal.py -q -k "midnight or local_date or attribution"`
  - `python -m pytest tests/test_canonical_persistence.py -q -k "local_date or correction"`
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
- `reality_drift_notes`:
  - `Cross-midnight continuation and correction now derive the canonical local ledger date from the trace contract before persistence, so late-night flows do not silently drift to the next day.`
  - `The narrow entrypoint adapter in text_meal_service now backfills local attribution fields from occurred_at / trace timestamp when trace_contract.local_date is blank.`
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`:
  - `docs/handoff/completed/HANDOFF-2026-04-12-024-CROSS-MIDNIGHT-ATTRIBUTION-FOUNDATION.md`
