# Task Artifact

- `task_id`: `TASK-2026-04-11-010-LAYER-INTEGRITY-WARNING-CLEANUP`
- `slice_id`: `repo-governance-layer-integrity-warning-cleanup`
- `status`: `COMPLETED`
- `owner`: `codex-planner-local`
- `started_at`: `2026-04-11`

## Source Of Truth Refs

- [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
- [docs/governance/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/BUILD_FILE_PLACEMENT_RULES.md)
- [docs/governance/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/LAYER_DEPENDENCY_RULES.md)
- [docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)

## Goal

Remove the current `check_layer_integrity.py` warning set without widening scope into unrelated refactors.

## Planned Touch Files

- `app/web/*`
- `app/application/*`
- `app/infrastructure/*`
- `app/agent/*`
- `tests/*`
- `docs/exec-plans/active/tasks/TASK-2026-04-11-010-LAYER-INTEGRITY-WARNING-CLEANUP.md`

## Forbidden Files

- `app/routes.py`
- `app/schemas.py`
- `app/usecases/text_meal.py`
- recommendation workflow modules unrelated to the warning paths
- rescue / calibration / memory slices

## New Files Expected

- `app/application/*_db_provider.py` or equivalent focused DI helper only if route-level `Session` wiring needs extraction
- `app/infrastructure/*` module only if `app/agent/exact_item_index.py` needs a storage-backed lookup boundary

## Current Warning Set

- `app/agent/exact_item_index.py` importing `sqlalchemy`
- `app/web/intake_routes.py` importing `sqlalchemy.orm`
- `app/web/today_routes.py` importing `sqlalchemy.orm`
- `app/web/user_routes.py` importing `sqlalchemy.orm`
- `app/web/weight_routes.py` importing `sqlalchemy.orm`

## Completion Criteria

- `python scripts/check_layer_integrity.py` emits zero warnings for the current set
- route modules no longer directly import `sqlalchemy.orm`
- `app/agent/exact_item_index.py` no longer owns direct SQLAlchemy access
- resulting ownership follows placement rules and does not regress protected files

## Tests To Run

- `python scripts/check_layer_integrity.py`
- route and retrieval tests covering the touched modules

## Expected Re-plan Impact

Will determine whether `app/agent/*` can move from warning-only governance toward stricter hard-fail rules in a later pass.

## Completion Notes

- removed direct `sqlalchemy.orm` imports from `app/web/*` route modules by keeping route DI typed as boundary-agnostic `Any`
- moved exact-item FTS ownership into `app/infrastructure/exact_item_search.py`
- added a lightweight `app/search/exact_item_lookup.py` facade so `agent` and `search` callers do not need direct infrastructure imports
- updated database bootstrap to source `ensure_exact_item_fts()` from infrastructure rather than `app/agent`

## Completion Record

- `completed_at`: `2026-04-11`
- `actual_touch_files[]`:
  - `app/web/intake_routes.py`
  - `app/web/today_routes.py`
  - `app/web/user_routes.py`
  - `app/web/weight_routes.py`
  - `app/infrastructure/exact_item_search.py`
  - `app/search/exact_item_lookup.py`
  - `app/agent/knowledge_packets.py`
  - `app/search/chain_retrieval.py`
  - `app/database.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-11-010-LAYER-INTEGRITY-WARNING-CLEANUP.md`
- `tests_run[]`:
  - `python scripts/check_layer_integrity.py`
  - `python -m pytest tests/test_routes_today_ui.py tests/test_routes_weight_ui.py tests/test_text_meal.py -q`
  - `python -m pytest tests/test_knowledge_packets.py tests/test_base_nutrition_integration.py tests/test_search_ranking.py tests/test_text_meal.py tests/test_routes_today_ui.py tests/test_routes_weight_ui.py -q`
- `reality_drift_notes`:
  - `app/application/__init__.py` is still import-heavy, so exact-item lookup facade was placed under `app/search/*` instead of `app/application/*` to avoid package side effects during import
- `source_of_truth_updated`:
  - `yes`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`:
  - `none`
