# General Chat Official Golden Batch Review V1

## Purpose

This sheet is the batch-review surface for promoting general_chat candidate cases into Official Golden suites.

Source queue:

- [general_chat_candidate_review_queue_v1.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/benchmarks/general_chat/general_chat_candidate_review_queue_v1.json)

Review rule:

- approve or edit only the primary outcome
- do not review response wording here
- if a case is still ambiguous, keep it in candidate-only status

## Batch 1

| candidate_case_id | candidate_suite_id | utterance | candidate_target_workflow_family | candidate_disposition | candidate_workflow_effect | candidate_required_read_surfaces | review_decision | approved_notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `general_chat_budget_candidate_001` | `general_chat_budget_query_golden_v1` | `??憭拚??拙?撠??` | `general_chat` | `answer_only` | `answer_budget_summary_without_state_mutation` | `CurrentBudgetView, ActiveBodyPlanView` | `approve` | `approved by user plan approval` |
| `general_chat_goal_candidate_001` | `general_chat_goal_query_golden_v1` | `??函??格??臭?暻潘?` | `general_chat` | `answer_only` | `answer_goal_summary_without_state_mutation` | `ActiveBodyPlanView` | `approve` | `approved by user plan approval` |
| `general_chat_open_workflow_candidate_001` | `general_chat_open_workflow_boundary_golden_v1` | `??????暻琛 | `general_chat` | `open_new_workflow` | `handoff_to_formal_workflow` | `` | `approve` | `approved by user plan approval` |
