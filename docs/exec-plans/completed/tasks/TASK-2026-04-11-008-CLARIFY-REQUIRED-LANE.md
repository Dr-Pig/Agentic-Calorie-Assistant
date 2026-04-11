# Task Artifact

- `task_id`: `TASK-2026-04-11-008-CLARIFY-REQUIRED-LANE`
- `slice_id`: `2.1c-clarify-required-lane`
- `status`: `COMPLETED`
- `owner`: `delegated-worker`
- `started_at`: `2026-04-11`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md)
- [docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md)

## Goal

Strengthen the clarify-required single-turn lane so the system cleanly blocks commit when a safe estimate cannot proceed without a follow-up question.

## Planned Touch Files

- `app/agent/decision_llm.py`
- `app/agent/final_response_llm.py`
- `app/application/followup_policy.py`
- `app/usecases/text_meal_boundary_support.py`
- `app/usecases/text_meal_response_support.py`
- `tests/test_text_meal.py`
- `tests/test_pass_runner_and_invariants.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-11-008-CLARIFY-REQUIRED-LANE.md`

## Forbidden Files

- rescue logic
- calibration logic
- body observation logic
- recommendation logic
- today / weight UI
- `app/usecases/text_meal.py` unless a re-plan trigger is hit

## Completion Criteria

- blocking clarify cases do not write canonical meal truth
- `clarify_is_blocking`, `unresolved_info`, and response shaping stay aligned with current typed contracts
- at least one regression proves a safe abstain / ask-user path where commit does not happen

## Tests To Run

- targeted clarify/no-commit runtime tests
- targeted decision/follow-up contract tests

## Expected Re-plan Impact

Will determine whether the next intake hardening step should move into cannot-estimate abstain behavior or web-search fallback ownership.

## Completion Notes

- Added a blocking-clarify no-proceed coherence guard so `clarify_is_blocking=true` forces `can_proceed_without_clarify=false`.
- Added a focused clarify regression proving the system stays on the clarify route and does not write canonical meal truth.
- Kept clarify handling inside the intake lane boundary; no rescue, calibration, body observation, or recommendation work was introduced.

## Completion Record

- `completed_at`: `2026-04-11`
- `actual_touch_files[]`:
  - `app/agent/decision_llm.py`
  - `app/application/followup_policy.py`
  - `app/usecases/text_meal_boundary_support.py`
  - `app/usecases/text_meal_response_support.py`
  - `tests/test_pass_runner_and_invariants.py`
  - `tests/test_text_meal.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-11-008-CLARIFY-REQUIRED-LANE.md`
  - `docs/handoff/active/HANDOFF-2026-04-11-008-CLARIFY-REQUIRED-LANE.md`
- `tests_run[]`:
  - `python -m pytest tests/test_pass_runner_and_invariants.py -q -k "normalize_decision_result_forces_blocking_clarify_to_stop_proceeding or annotate_followup_policy_marks_followup_as_needed_when_blocking"`
  - `python -m pytest tests/test_text_meal.py -q -k "clarify_required_lane_blocks_canonical_commit or boundary_clarification_short_circuit_skips_log_creation"`
- `reality_drift_notes`:
  - clarify blocking needs an explicit normalization guard because `clarify_is_blocking` and `can_proceed_without_clarify` can otherwise drift apart in provider output
  - the no-commit guarantee is now regression-backed at the payload and persistence levels
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`:
  - `docs/handoff/active/HANDOFF-2026-04-11-008-CLARIFY-REQUIRED-LANE.md`
