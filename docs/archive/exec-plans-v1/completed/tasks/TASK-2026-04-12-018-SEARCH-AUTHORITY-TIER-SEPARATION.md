# Task Artifact

- `task_id`: `TASK-2026-04-12-018-SEARCH-AUTHORITY-TIER-SEPARATION`
- `slice_id`: `2.1e-web-search-fallback-lane`
- `status`: `COMPLETED`
- `owner`: `planner`
- `started_at`: `2026-04-12`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/specs/retrieval_external_search_ownership_spec.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/retrieval_external_search_ownership_spec.md)
- [docs/governance/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/BUILD_FILE_PLACEMENT_RULES.md)
- [docs/governance/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/LAYER_DEPENDENCY_RULES.md)
- [docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md)

## Goal

Complete the authority-tier follow-through after the extraction seam by ensuring `web_search_official` no longer shares the same tier as `exact_item_db`.

## Planned Touch Files

- `app/application/evidence_normalizer.py`
- `tests/test_retrieval_external_search.py`
- `tests/test_text_meal.py` only if a targeted authority regression is needed
- `docs/exec-plans/active/tasks/TASK-2026-04-12-018-SEARCH-AUTHORITY-TIER-SEPARATION.md`

## Forbidden Files

- `app/application/evidence_assembly.py`
- `app/routes.py`
- `app/usecases/text_meal.py`
- `app/schemas.py`
- search adapter behavior changes
- recommendation / calibration / rescue / proactive logic

## Completion Criteria

- `source_tier_for_item` distinguishes exact/local truth from `web_search_official`
- `exact_item_db` remains top authority for exact resolution
- extraction seam remains in `app/application/evidence_normalizer.py`; no new freeze-growth writeback is introduced
- targeted retrieval / intake regressions remain green

## Tests To Run

- `python -m pytest tests/test_retrieval_external_search.py -q`
- `python -m pytest tests/test_text_meal.py -q -k "decision_stage_skips_search_when_exact_truth_is_present or decision_pass_can_trigger_search_before_nutrition"`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`

## Expected Re-plan Impact

Should let `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE` resume without reopening a freeze-growth exception for `app/application/evidence_assembly.py`.

## Completion Record

- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `app/application/evidence_normalizer.py`
  - `tests/test_retrieval_external_search.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-12-018-SEARCH-AUTHORITY-TIER-SEPARATION.md`
- `tests_run[]`:
  - `python -m pytest tests/test_retrieval_external_search.py -q`
  - `python -m pytest tests/test_text_meal.py -q -k "decision_stage_skips_search_when_exact_truth_is_present or decision_pass_can_trigger_search_before_nutrition"`
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
- `reality_drift_notes`:
  - `CURRENT_EXECUTION_PLAN.md` still lists this task as active until planner closeout runs
- `source_of_truth_updated`:
  - `yes`
- `followup_task_ids[]`:
  - `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE`
- `handoff_doc_path`: `docs/exec-plans/completed/handoff/HANDOFF-2026-04-12-018-SEARCH-AUTHORITY-TIER-SEPARATION.md`
