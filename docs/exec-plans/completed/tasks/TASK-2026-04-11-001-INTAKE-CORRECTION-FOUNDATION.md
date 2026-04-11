# Task Artifact

- `task_id`: `TASK-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION`
- `slice_id`: `2.2b-historical-correction`
- `status`: `COMPLETED`
- `owner`: `codex-current-worker`
- `started_at`: `2026-04-11`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md)
- [docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md)
- [docs/specs/L2_DATA_STATE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2_DATA_STATE_SPEC.md)

## Goal

Stabilize the historical correction path so correction-target lookup, version supersession, and correction-safe canonical writes are explicit and do not leak back into legacy meal-log truth.

## Planned Touch Files

- `app/application/canonical_commit_bridge.py`
- `app/application/state_transition.py`
- `app/application/conversation_state_assembler.py`
- `app/application/text_meal_commit_service.py`
- `app/infrastructure/canonical_persistence.py`
- `app/infrastructure/meal_log_persistence.py` only if transitional mapping or legacy-bridge containment must be tightened
- `app/usecases/text_meal_service.py`
- `app/usecases/text_meal_orchestration_support.py`
- `app/usecases/text_meal_persistence_support.py`
- `app/usecases/text_meal_boundary_support.py`
- `tests/test_text_meal.py`
- `tests/test_canonical_persistence.py`
- `tests/test_current_budget_read_model.py` only if correction read-side effects need direct regression coverage

## Forbidden Files

- recommendation runtime modules
- calibration runtime modules
- rescue runtime modules
- proactive logic
- UI pages
- `app/usecases/text_meal.py` unless a re-plan trigger is hit
- `app/routes.py`
- `app/schemas.py`
- freeze-growth files unless the task records explicit justification:
  - `app/application/evidence_assembly.py`
  - `app/application/context_assembly.py`
  - `app/agent/knowledge_packets.py`

## New Files Expected

- none by default
- if a new module is required, it must follow:
  - [docs/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/BUILD_FILE_PLACEMENT_RULES.md)
  - [docs/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/LAYER_DEPENDENCY_RULES.md)

## Completion Criteria

- historical correction target resolution is explicit and test-covered
- correction writes produce a new `MealVersion` rather than in-place overwrite
- legacy meal-log path remains transitional and does not regain truth ownership
- any required truth-doc updates are made before completion
- protected legacy files stay thin and do not absorb new correction ownership
- no schema-sensitive ORM change lands without migration discipline review

## Tests To Run

- historical correction path
- version supersession path
- canonical persistence regression tests
- text meal regression tests
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`

## Expected Re-plan Impact

Should tighten the boundary between `2.2b-historical-correction` and `2.3a-current-budget-read-model`, making the next read-model task less ambiguous.

## Re-plan Notes

- This task was originally scoped before the repo's protected-legacy and freeze-growth rules were hardened.
- `app/usecases/text_meal.py` is no longer an acceptable default landing zone for correction work.
- Correction ownership should prefer `app/application/*`, `app/infrastructure/*`, and narrow `text_meal_*_support` / `text_meal_service` modules.
- Any worker taking this task must re-check [docs/FREEZE_GROWTH_EXTRACTION_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/FREEZE_GROWTH_EXTRACTION_MAP.md) before touching a freeze-growth file.

## Completion Notes

- Made historical correction target resolution explicit in the canonical commit resolver instead of inferring version supersession from legacy meal-log truth alone.
- Threaded the resolved correction target through both canonical and legacy text-meal commit paths so version reason, target, and supersession metadata are visible in trace payloads.
- Added regression coverage for historical-correction target resolution and supersession behavior.
- Kept the legacy meal-log path transitional; canonical write ownership remains in the application/infrastructure bridge.

## Completion Record

- `completed_at`: `2026-04-11`
- `actual_touch_files[]`:
  - `app/application/canonical_commit_bridge.py`
  - `app/application/text_meal_commit_service.py`
  - `app/infrastructure/canonical_persistence.py`
  - `app/infrastructure/meal_log_persistence.py`
  - `tests/test_canonical_persistence.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION.md`
  - `docs/handoff/active/HANDOFF-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION.md`
- `tests_run[]`:
  - `python -m pytest tests/test_canonical_persistence.py -q`
  - `python -m pytest tests/test_text_meal.py -k 'persistence or boundary or commit_request_candidate or canonical' -q`
  - `python -m pytest tests/test_text_meal.py -q`
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
- `reality_drift_notes`:
  - none beyond the expected longer runtime for the full `tests/test_text_meal.py` suite
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`: `docs/handoff/active/HANDOFF-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION.md`
