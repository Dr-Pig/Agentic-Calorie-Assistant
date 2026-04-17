# Rescue Official Golden Batch Review V1

## Purpose

This sheet is the batch-review surface for promoting rescue candidate cases into Official Golden suites.

Source queue:

- [rescue_candidate_review_queue_v1.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/benchmarks/rescue/rescue_candidate_review_queue_v1.json)

Review rule:

- approve or edit only the primary outcome
- do not review response wording here
- if a case is still ambiguous, keep it in candidate-only status

## Batch 1

| candidate_case_id | candidate_suite_id | utterance | candidate_target_object_type | candidate_target_workflow_family | candidate_disposition | candidate_workflow_effect | review_decision | approved_notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `rescue_accept_candidate_001` | `rescue_accept_action_golden_v1` | `好，就照這個方案做` | `proposal` | `rescue` | `accept` | `accept_and_apply_current_proposal` | `pending` | `` |
| `rescue_reject_candidate_001` | `rescue_reject_action_golden_v1` | `不要這次，我先照原本節奏就好` | `proposal` | `rescue` | `reject` | `close_current_proposal` | `pending` | `` |
| `rescue_defer_candidate_001` | `rescue_defer_action_golden_v1` | `晚點再看，先不要現在決定` | `proposal` | `rescue` | `defer` | `defer_current_proposal` | `pending` | `` |
| `rescue_adjust_candidate_001` | `rescue_adjust_action_golden_v1` | `太硬了，拉長一點` | `proposal` | `rescue` | `adjust` | `mutate_current_proposal` | `pending` | `` |
| `rescue_answer_only_candidate_001` | `rescue_answer_only_boundary_golden_v1` | `如果照這個做，每天大概要少多少？` | `proposal` | `rescue` | `answer_only` | `answer_current_object` | `pending` | `` |
