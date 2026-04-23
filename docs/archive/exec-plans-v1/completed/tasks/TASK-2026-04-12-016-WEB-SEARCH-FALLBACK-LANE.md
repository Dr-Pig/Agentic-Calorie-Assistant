# Task Artifact

- `task_id`: `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE`
- `slice_id`: `2.1e-web-search-fallback-lane`
- `status`: `COMPLETED`
- `owner`: `planner`
- `started_at`: `2026-04-12`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/retrieval_external_search_ownership_spec.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/retrieval_external_search_ownership_spec.md)
- [docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md)
- [docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md)
- [docs/governance/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/BUILD_FILE_PLACEMENT_RULES.md)
- [docs/governance/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/LAYER_DEPENDENCY_RULES.md)

## Goal

Add the controlled web-search fallback lane so external search activates only after local and exact paths are insufficient, and remains lower-authority than exact/local truth.

## Planned Touch Files

- `app/usecases/evidence/retrieval.py`
- `app/search/chain_retrieval.py`
- `app/search/tavily_adapter.py` only if the fallback adapter surface needs tightening
- `app/agent/decision_llm.py` only if decision-stage tool escalation vocabulary needs alignment
- `app/agent/nutrition_resolution_llm.py` only if second-stage tool request ownership needs alignment
- `tests/test_retrieval_external_search.py`
- `tests/test_text_meal.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE.md`

## Forbidden Files

- `app/routes.py`
- `app/usecases/text_meal.py`
- `app/schemas.py`
- recommendation / calibration / rescue / proactive logic
- memory selector logic
- freeze-growth files unless a re-plan trigger is hit and explicitly recorded

## New Files Expected

- none by default

## Completion Criteria

- web-search fallback activates only when local/exact evidence is insufficient
- search-derived evidence remains explicitly lower-authority than exact/local truth
- no-search-when-not-needed behavior is regression-covered
- protected legacy files remain untouched

## Tests To Run

- `python -m pytest tests/test_retrieval_external_search.py -q`
- `python -m pytest tests/test_text_meal.py -q -k "decision_stage_skips_search_when_exact_truth_is_present or decision_pass_can_trigger_search_before_nutrition"`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`

## Expected Re-plan Impact

Will determine whether intake hardening should next move into a context-selector slice or whether another retrieval-ownership cleanup is still needed.

## Completion Record
- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `app/usecases/evidence/retrieval.py`
  - `app/search/chain_retrieval.py`
  - `tests/test_retrieval_external_search.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE.md`
- `tests_run[]`:
  - `python -m pytest tests/test_retrieval_external_search.py -q`
  - `python -m pytest tests/test_text_meal.py -q -k "decision_stage_skips_search_when_exact_truth_is_present or decision_pass_can_trigger_search_before_nutrition"`
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
- `reality_drift_notes`:
  - `none`
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`: `docs/exec-plans/completed/handoff/HANDOFF-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE.md`
