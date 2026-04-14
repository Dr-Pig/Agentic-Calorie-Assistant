# Handoff

- `handoff_id`: `HANDOFF-2026-04-12-017-EVIDENCE-TIER-POLICY-EXTRACTION`
- `task_id`: `TASK-2026-04-12-017-EVIDENCE-TIER-POLICY-EXTRACTION`
- `slice_id`: `2.1e-web-search-fallback-lane`
- `current_status`: `task completed; authority-policy seam extracted out of freeze-growth file`

## What Changed

- extracted `source_class_for_item` and `source_tier_for_item` into `app/application/evidence_normalizer.py`
- kept `app/application/evidence_assembly.py` shrink-only by switching it to import the extracted helpers
- added focused regression coverage for the extracted authority-policy seam

## What Did Not Change

- no search adapter behavior was changed in this task
- no protected legacy files were touched
- no recommendation, rescue, calibration, proactive, or UI behavior was changed

## Files Touched

- `app/application/evidence_normalizer.py`
- `app/application/evidence_assembly.py`
- `tests/test_retrieval_external_search.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-12-017-EVIDENCE-TIER-POLICY-EXTRACTION.md`

## Blockers

- none for this extraction slice

## Tests Run

- `python -m pytest tests/test_retrieval_external_search.py -q`
- `python -m pytest tests/test_text_meal.py -q -k "decision_stage_skips_search_when_exact_truth_is_present or decision_pass_can_trigger_search_before_nutrition"`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`

## Source Of Truth Docs Touched

- none

## Reality Drift

- the web-search fallback lane depended on a narrower authority-policy seam than the original `2.1e` task assumed
- freeze-growth discipline correctly forced the seam extraction before authority-tier behavior could change

## Next Recommended Action

Use the extracted `app/application/evidence_normalizer.py` seam as the only legal place for exact-vs-search authority refinement, then complete `TASK-2026-04-12-018-SEARCH-AUTHORITY-TIER-SEPARATION`.

## Unsafe Assumptions To Avoid

- do not reintroduce authority-tier policy back into `app/application/evidence_assembly.py`
- do not treat the extraction itself as equivalent to finishing the web-search fallback lane
- do not widen this seam into recommendation, rescue, calibration, or memory-selector logic
