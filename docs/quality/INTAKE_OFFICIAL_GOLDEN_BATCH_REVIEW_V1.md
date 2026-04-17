# Intake Official Golden Batch Review V1

## Purpose

This sheet is the batch-review surface for promoting intake candidate cases into Official Golden suites.

Source queue:

- [intake_candidate_review_queue_v1.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/benchmarks/intake/intake_candidate_review_queue_v1.json)

Review rule:

- approve or edit only the primary outcome
- do not review response wording here
- if a case is still ambiguous, keep it in candidate-only status

## Batch 1

| candidate_case_id | candidate_suite_id | utterance | candidate_target_object_type | candidate_target_workflow_family | candidate_disposition | candidate_workflow_effect | review_decision | approved_notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `intake_task_meal_link_candidate_001` | `intake_task_meal_link_golden_v1` | `午餐吃雞胸便當` | `meal_thread` | `intake` | `create` | `create_new_meal_thread` | `pending` | `` |
| `intake_decision_candidate_001` | `intake_decision_clarify_vs_proceed_golden_v1` | `喝了一杯手搖` | `meal_thread` | `intake` | `create` | `create_thread_and_request_clarify` | `pending` | `` |
| `intake_turn2_candidate_001` | `intake_followup_turn2_continuation_golden_v1` | `大杯，半糖，少冰` | `meal_thread` | `intake` | `continue` | `continue_followup_lane` | `pending` | `` |
| `intake_correction_candidate_001` | `intake_correction_action_golden_v1` | `剛剛那餐不是雞腿，是雞胸` | `meal_thread` | `intake` | `correct` | `correct_existing_meal_thread` | `pending` | `` |
| `intake_new_workflow_candidate_001` | `intake_open_new_workflow_boundary_golden_v1` | `先不管剛剛那杯，晚餐我吃牛肉麵` | `none` | `intake` | `open_new_workflow` | `open_new_workflow` | `pending` | `` |
