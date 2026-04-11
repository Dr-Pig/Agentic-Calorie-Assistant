# Task Artifact

- `task_id`: `TASK-2026-04-11-007-EXACT-DB-ITEM-LANE`
- `slice_id`: `2.1b-exact-db-item-lane`
- `status`: `COMPLETED`
- `owner`: `delegated-worker`
- `started_at`: `2026-04-11`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md)

## Goal

Strengthen the exact DB item lane so branded or exact-item queries resolve through local exact evidence first, without unnecessary web fallback or clarification drift.

## Planned Touch Files

- `app/agent/exact_item_index.py`
- `app/agent/knowledge_packets.py`
- `app/usecases/text_meal_runtime_support.py`
- `tests/test_knowledge_packets.py`
- `tests/test_text_meal.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-11-007-EXACT-DB-ITEM-LANE.md`

## Forbidden Files

- rescue logic
- calibration logic
- today / weight UI routes
- memory / retrieval deepening layers
- recommendation runtime
- `app/usecases/text_meal.py` unless a re-plan trigger is hit

## Completion Criteria

- exact DB lane prefers local exact evidence before web fallback
- exact branded queries do not spuriously escalate to search when exact local truth is sufficient
- tests cover at least one branded exact-item path and one no-search-needed path

## Tests To Run

- targeted exact-item knowledge packet tests
- targeted text-meal runtime exact-lane regression tests

## Expected Re-plan Impact

Will clarify whether the next intake hardening step should move into clarify-required or into web fallback ownership.

## Completion Notes

- Added an exact-item lane packet helper that preserves brand context before local exact resolution.
- Updated the exact-item grounding path to pass planner brand context into local exact lookup before any fallback logic.
- Added a canonical safety-floor accessor in runtime support that reads from active `BodyPlan.safety_floor_kcal` or an explicit override, without inferring from sex/gender in this task.
- Added regression coverage for exact-truth search suppression and brand-context propagation.

## Completion Record

- `completed_at`: `2026-04-11`
- `actual_touch_files[]`:
  - `app/agent/knowledge_packets.py`
  - `app/usecases/text_meal_runtime_support.py`
  - `tests/test_knowledge_packets.py`
  - `tests/test_text_meal.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-11-007-EXACT-DB-ITEM-LANE.md`
  - `docs/handoff/active/HANDOFF-2026-04-11-007-EXACT-DB-ITEM-LANE.md`
- `tests_run[]`:
  - `python -m pytest tests/test_knowledge_packets.py -q -k 'exact_item_lane_packet or exact_only_lane'`
  - `python -m pytest tests/test_text_meal.py -q -k 'decision_stage_skips_search_when_exact_truth_is_present or canonical_safety_floor_prefers_body_plan_source_or_explicit_override'`
- `reality_drift_notes`:
  - exact-db exactness is still grounded through local evidence first; the additional runtime helper simply makes the brand context explicit before lookup
  - canonical safety floor is explicit BodyPlan state, not inferred from user sex/gender in this slice
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`:
  - `docs/handoff/active/HANDOFF-2026-04-11-007-EXACT-DB-ITEM-LANE.md`
