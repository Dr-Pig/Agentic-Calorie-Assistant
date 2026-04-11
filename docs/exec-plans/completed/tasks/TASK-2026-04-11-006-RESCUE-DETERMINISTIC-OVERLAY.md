# Task Artifact

- `task_id`: `TASK-2026-04-11-006-RESCUE-DETERMINISTIC-OVERLAY`
- `slice_id`: `2.5a-rescue-deterministic-overlay`
- `status`: `COMPLETED`
- `owner`: `codex-planner-local`
- `started_at`: `2026-04-11`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md)
- [docs/specs/L3M_GUARDRAIL_MATH_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3M_GUARDRAIL_MATH_SPEC.md)

## Goal

Introduce deterministic short-horizon rescue math plus canonical rescue-overlay persistence without adding rescue proposals, memory-aware recommendation, or rescue UI.

## Planned Touch Files

- `app/application/rescue_overlay.py`
- `app/application/canonical_commit_bridge.py`
- `app/application/__init__.py`
- `tests/test_rescue_overlay.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-11-006-RESCUE-DETERMINISTIC-OVERLAY.md`

## Forbidden Files

- recommendation runtime
- memory selector or retrieval modules
- proactive logic
- `app/usecases/text_meal.py`
- rescue response UI surfaces
- calibration proposal logic

## Completion Criteria

- deterministic rescue math enforces the `15%` compression cap and safety floor
- a short-horizon spread plan can classify `viable`, `strained`, and `non_viable`
- accepted overlay days can write `rescue_overlay` ledger entries through canonical persistence
- recomputed ledgers reflect rescue overlay effects without touching recommendation or UI surfaces

## Tests To Run

- rescue math classification tests
- rescue plan viability tests
- overlay persistence and ledger recompute tests

## Expected Re-plan Impact

Will determine whether the next rescue work should move into proposal generation / response handling or return to intake-lane hardening first.

## Completion Notes

- Added deterministic rescue math in `app/application/rescue_overlay.py`.
- Explicitly kept `safety_floor_kcal` as an input to avoid inventing a hidden sex/profile fallback that does not yet exist in canonical state.
- Extended rescue overlay persistence to carry `source_type` and structured metadata.
- Kept the slice free of recommendation, rescue UI, and proactive behavior.
- Validation:
  - `python -m pytest tests/test_rescue_overlay.py tests/test_canonical_persistence.py -q`

## Completion Record

- `completed_at`: `2026-04-11`
- `actual_touch_files[]`:
  - `app/application/rescue_overlay.py`
  - `app/application/canonical_commit_bridge.py`
  - `app/application/__init__.py`
  - `tests/test_rescue_overlay.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-11-006-RESCUE-DETERMINISTIC-OVERLAY.md`
- `tests_run[]`:
  - `python -m pytest tests/test_rescue_overlay.py tests/test_canonical_persistence.py -q`
- `reality_drift_notes`:
  - v1 deterministic rescue cannot infer a canonical sex-based safety floor from current state, so `safety_floor_kcal` stays explicit instead of hidden behind a guessed fallback
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`: `docs/handoff/active/HANDOFF-2026-04-11-006-RESCUE-DETERMINISTIC-OVERLAY.md`
