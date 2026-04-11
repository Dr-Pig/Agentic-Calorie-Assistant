# Handoff

- `handoff_id`: `HANDOFF-2026-04-12-018-SEARCH-AUTHORITY-TIER-SEPARATION`
- `task_id`: `TASK-2026-04-12-018-SEARCH-AUTHORITY-TIER-SEPARATION`
- `slice_id`: `2.1e-web-search-fallback-lane`
- `current_status`: `task completed; search authority tier now distinguishes exact/local truth from web fallback`

## What Changed

- updated `app/application/evidence_normalizer.py` so `web_search_official` no longer shares the same authority tier as `exact_item_db`
- added targeted regression coverage to keep exact/local truth above official web fallback
- recorded the follow-up link back to `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE`

## What Did Not Change

- no freeze-growth file was reopened
- no search adapter behavior or retrieval activation policy was changed here
- no protected legacy files, UI, rescue, calibration, or recommendation code was touched

## Files Touched

- `app/application/evidence_normalizer.py`
- `tests/test_retrieval_external_search.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-12-018-SEARCH-AUTHORITY-TIER-SEPARATION.md`

## Blockers

- none for this authority-tier slice

## Tests Run

- `python -m pytest tests/test_retrieval_external_search.py -q`
- `python -m pytest tests/test_text_meal.py -q -k "decision_stage_skips_search_when_exact_truth_is_present or decision_pass_can_trigger_search_before_nutrition"`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`

## Source Of Truth Docs Touched

- `docs/specs/retrieval_external_search_ownership_spec.md`
- `docs/specs/LLM_OWNERSHIP_RULE.md`

## Reality Drift

- authority separation required a source-of-truth sync because code-level semantics moved ahead of canonical wording
- once the spec sync landed, `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE` could safely resume without reopening freeze-growth files

## Next Recommended Action

Resume and close `TASK-2026-04-12-016-WEB-SEARCH-FALLBACK-LANE` on the narrowed retrieval/search scope.

## Unsafe Assumptions To Avoid

- do not treat `web_search_official` as exact truth
- do not move authority behavior back into `app/application/evidence_assembly.py`
- do not assume the authority-tier follow-through alone changes fallback activation conditions
