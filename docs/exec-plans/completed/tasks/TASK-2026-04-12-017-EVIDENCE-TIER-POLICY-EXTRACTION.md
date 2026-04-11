# Task Artifact

- `task_id`: `TASK-2026-04-12-017-EVIDENCE-TIER-POLICY-EXTRACTION`
- `slice_id`: `2.1e-web-search-fallback-lane`
- `status`: `COMPLETED`
- `owner`: `delegated-worker`
- `started_at`: `2026-04-12`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/specs/retrieval_external_search_ownership_spec.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/retrieval_external_search_ownership_spec.md)
- [docs/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/BUILD_FILE_PLACEMENT_RULES.md)
- [docs/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/LAYER_DEPENDENCY_RULES.md)
- [docs/FREEZE_GROWTH_EXTRACTION_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/FREEZE_GROWTH_EXTRACTION_MAP.md)

## Goal

Extract the source-class and source-tier policy seam out of the freeze-growth `evidence_assembly` module so `2.1e-web-search-fallback-lane` can continue without treating web-search authority policy as a frozen-file edit.

## Planned Touch Files

- `app/application/evidence_normalizer.py`
- `app/application/evidence_assembly.py` as shrink-only extraction wiring only
- `tests/test_retrieval_external_search.py`
- `tests/test_text_meal.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-12-017-EVIDENCE-TIER-POLICY-EXTRACTION.md`

## Forbidden Files

- `app/routes.py`
- `app/usecases/text_meal.py`
- `app/schemas.py`
- recommendation / calibration / rescue / proactive logic
- search adapter behavior changes
- new tool packet shaping beyond the extracted source-tier seam

## New Files Expected

- `app/application/evidence_normalizer.py`

## Completion Criteria

- `source_class_for_item` and `source_tier_for_item` no longer originate in `app/application/evidence_assembly.py`
- `app/application/evidence_assembly.py` stays flat or shrinks
- existing behavior remains stable except that the authority-policy seam is now isolated for follow-on `2.1e` work
- targeted retrieval / intake tests remain green

## Tests To Run

- `python -m pytest tests/test_retrieval_external_search.py -q`
- `python -m pytest tests/test_text_meal.py -q -k "decision_stage_skips_search_when_exact_truth_is_present or decision_pass_can_trigger_search_before_nutrition"`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`

## Expected Re-plan Impact

Should unblock `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE` without granting a broad freeze-growth exception to `app/application/evidence_assembly.py`.

## Completion Notes

- Extracted `source_class_for_item` and `source_tier_for_item` into `app/application/evidence_normalizer.py`.
- Kept `app/application/evidence_assembly.py` shrink-only by importing the extracted policy helpers instead of defining them locally.
- Added focused regression coverage for the extracted source-class / source-tier policy seam.

## Completion Record

- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `app/application/evidence_normalizer.py`
  - `app/application/evidence_assembly.py`
  - `tests/test_retrieval_external_search.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-12-017-EVIDENCE-TIER-POLICY-EXTRACTION.md`
- `tests_run[]`:
  - `python -m pytest tests/test_retrieval_external_search.py -q`
  - `python -m pytest tests/test_text_meal.py -q -k "decision_stage_skips_search_when_exact_truth_is_present or decision_pass_can_trigger_search_before_nutrition"`
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
- `reality_drift_notes`:
  - none
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`: `docs/handoff/completed/HANDOFF-2026-04-12-017-EVIDENCE-TIER-POLICY-EXTRACTION.md`
