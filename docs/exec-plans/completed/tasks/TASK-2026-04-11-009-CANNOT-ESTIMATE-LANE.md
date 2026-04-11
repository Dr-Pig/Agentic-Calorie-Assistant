# Task Artifact

- `task_id`: `TASK-2026-04-11-009-CANNOT-ESTIMATE-LANE`
- `slice_id`: `2.1d-cannot-estimate-lane`
- `status`: `COMPLETED`
- `owner`: `delegated-worker`
- `started_at`: `2026-04-11`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md)
- [docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md)
- [docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md)

## Goal

Strengthen the cannot-estimate abstain lane so the system explicitly refuses commit when it cannot produce a safe estimate, and does so through a typed, no-canonical-write path.

## Planned Touch Files

- `app/agent/decision_llm.py`
- `app/agent/final_response_llm.py`
- `app/application/followup_policy.py`
- `app/usecases/text_meal_boundary_support.py`
- `app/usecases/text_meal_response_support.py`
- `tests/test_text_meal.py`
- `tests/test_pass_runner_and_invariants.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-11-009-CANNOT-ESTIMATE-LANE.md`

## Forbidden Files

- rescue logic
- calibration logic
- body observation logic
- recommendation logic
- today / weight UI
- canonical persistence bridge semantics
- `app/usecases/text_meal.py` unless a re-plan trigger is hit

## Completion Criteria

- cannot-estimate cases do not write canonical meal truth
- abstain / refusal response shaping stays explicit and aligned with typed contracts
- at least one regression proves a no-commit abstain path where the system refuses to estimate rather than silently continuing

## Tests To Run

- targeted cannot-estimate no-commit runtime tests
- targeted decision / abstain contract tests

## Expected Re-plan Impact

Will determine whether the next intake hardening step should move into web-search fallback ownership or whether more abstain/clarify boundary cleanup is still needed.

## Completion Notes

- Cannot-estimate inputs now carry an explicit abstain marker through finalization and persistence.
- The finalize path forces a follow-up reply and a `clarify_user_private` route when `resolution_mode=cannot_estimate_yet`.
- Canonical meal truth is blocked by a typed no-canonical-write decision before commit is attempted.

## Completion Record

- `completed_at`: `2026-04-11`
- `actual_touch_files[]`:
  - `app/agent/decision_llm.py`
  - `app/agent/final_response_llm.py`
  - `app/application/followup_policy.py`
  - `app/usecases/text_meal_boundary_support.py`
  - `app/usecases/text_meal_response_support.py`
  - `tests/test_text_meal.py`
  - `tests/test_pass_runner_and_invariants.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-11-009-CANNOT-ESTIMATE-LANE.md`
- `tests_run[]`:
  - `python -m pytest tests/test_pass_runner_and_invariants.py -q -k "cannot_estimate_abstain_policy or followup_policy_marks_followup_as_needed_when_blocking"`
  - `python -m pytest tests/test_text_meal.py -q -k "cannot_estimate_lane_refuses_canonical_commit_and_marks_abstain or clarify_required_lane_blocks_canonical_commit"`
- `reality_drift_notes`:
  - cannot-estimate safety is now enforced through the abstain lane rather than relying only on prompt-level caution
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`: ``
