# Text Meal Stage Map And Trace

## Stage Map

1. `task_meal_link_pass`
2. `decision_pass`
3. `nutrition_resolution_pass`
4. `final_response_pass`

## Why Trace Exists

Trace is the main way to understand regressions without reintroducing thick deterministic control.

The system should be observable enough to debug, without turning trace code into a second runtime.

## Minimum Trace Requirements

For each pass, record:

- input token usage
- output token usage
- latency
- stage status: `success / degraded / failed`
- selected evidence summary when relevant

## Key Runtime Fields

- `task_meal_link_result`
- `decision_result`
- `nutrition_result`
- `final_response_result`
- `meal_link_action`
- `target_meal_id`
- `clarification_blocking`
- `clarify_is_blocking`
- `can_proceed_without_clarify`
- `resolution_mode`
- `resolution_basis`
- `followup_loop_guard`

## Deterministic Trace Rule

Trace may describe what happened.

Trace may not become a place where semantic routing is silently recomputed.
