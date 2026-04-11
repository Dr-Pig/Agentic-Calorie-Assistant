# Task Artifact

- `task_id`: `TASK-2026-04-12-019-RESCUE-SAFETY-FLOOR-SOURCE-ALIGNMENT`
- `slice_id`: `2.5a-rescue-deterministic-overlay`
- `status`: `COMPLETED`
- `owner`: `planner`
- `started_at`: `2026-04-12`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md)
- [docs/specs/L2_DATA_STATE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2_DATA_STATE_SPEC.md)
- [docs/specs/L2A_DATA_DICTIONARY_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2A_DATA_DICTIONARY_SPEC.md)
- [docs/specs/L3M_GUARDRAIL_MATH_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3M_GUARDRAIL_MATH_SPEC.md)

## Goal

Align deterministic rescue runtime with the canonical `safety_floor(user)` source so rescue math can resolve `active BodyPlan.safety_floor_kcal` without relying on stale hidden assumptions.

## Planned Touch Files

- `app/application/rescue_overlay.py`
- `app/application/canonical_commit_bridge.py` only if rescue-overlay write-through needs the resolved safety-floor scalar carried more explicitly
- `app/domain/canonical_models.py` only if rescue-side type hints need a narrow scalar-carrying update
- `tests/test_rescue_overlay.py`
- `tests/test_canonical_persistence.py` only if the body-plan source path needs a persistence-backed regression
- `docs/exec-plans/active/tasks/TASK-2026-04-12-019-RESCUE-SAFETY-FLOOR-SOURCE-ALIGNMENT.md`

## Forbidden Files

- `app/routes.py`
- `app/usecases/text_meal.py`
- `app/schemas.py`
- recommendation / calibration / proactive logic
- rescue UI or response-surface code
- memory selector or retrieval logic
- freeze-growth files unless a re-plan trigger is hit and explicitly recorded

## New Files Expected

- none by default

## Completion Criteria

- deterministic rescue runtime can resolve `safety_floor(user)` from canonical state or an explicit override without hidden sex/profile heuristics
- rescue math remains deterministic and continues to enforce compression-cap and safety-floor checks
- rescue-side regressions cover canonical `BodyPlan.safety_floor_kcal` as the preferred source
- protected legacy files remain untouched

## Tests To Run

- `python -m pytest tests/test_rescue_overlay.py -q`
- `python -m pytest tests/test_canonical_persistence.py -q -k "body_plan_persists_safety_floor_kcal"`

## Expected Re-plan Impact

Will determine whether rescue work can stay in deterministic follow-through or whether the next planner step should shift back to intake/context-selection hardening.

## Completion Record
- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `app/application/rescue_overlay.py`
  - `tests/test_rescue_overlay.py`
  - `tests/test_canonical_persistence.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-12-019-RESCUE-SAFETY-FLOOR-SOURCE-ALIGNMENT.md`
- `tests_run[]`:
  - `python -m pytest tests/test_rescue_overlay.py -q`
  - `python -m pytest tests/test_canonical_persistence.py -q -k "body_plan_persists_safety_floor_kcal"`
- `reality_drift_notes`:
  - `Added the targeted persistence regression because the checked-in selector initially matched no tests.`
- `source_of_truth_updated`:
  - `yes`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`: `docs/handoff/completed/HANDOFF-2026-04-12-019-RESCUE-SAFETY-FLOOR-SOURCE-ALIGNMENT.md`
