# Text Meal Runtime Current

## Runtime

The current canonical runtime is:

1. `task_meal_link_pass`
2. `decision_pass`
3. `nutrition_resolution_pass`
4. `final_response_pass`

## Ownership

`task_meal_link_pass`

- intent
- scope
- meal link action
- target meal id
- boundary reason
- clarification blocking

`decision_pass`

- next action
- tool plan
- unresolved info
- whether clarify is blocking
- whether the system can proceed without clarify

`nutrition_resolution_pass`

- resolution mode
- resolution basis
- exactness
- kcal/macros/components
- unresolved info

`final_response_pass`

- final natural-language reply
- whether to surface one follow-up outward

## Deterministic Boundary

Deterministic code is only a quality gate.

Allowed:

- schema/shape validation
- pass retry for transport/schema only
- state bookkeeping
- evidence normalization
- exact-label base-truth checks
- macro/kcal sanity checks
- trace recording

Not allowed:

- semantic routing override
- boundary recalibration
- exactness override
- follow-up wording injection
- semantic retry loops
- answer rewriting

## Debug Workflow

Real dashboard failures must use the live trace triage workflow before patching:

- classify a single `first_bad_pass`
- classify a single root-cause bucket
- fix the upstream owner only
- add a regression fixture before considering the case closed

Reference:

- [`docs/handoff/LIVE_TRACE_TRIAGE_WORKFLOW.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/LIVE_TRACE_TRIAGE_WORKFLOW.md)

## Current Important Files

- [`app/usecases/text_meal.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/usecases/text_meal.py)
- [`app/agent/task_meal_link_llm.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/task_meal_link_llm.py)
- [`app/agent/decision_llm.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/decision_llm.py)
- [`app/agent/nutrition_resolution_llm.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/nutrition_resolution_llm.py)
- [`app/agent/final_response_llm.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/final_response_llm.py)
- [`app/application/pass_runner.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/pass_runner.py)
- [`app/application/evidence_assembly.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/evidence_assembly.py)
- [`app/application/state_transition.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/state_transition.py)
- [`app/application/nutrition_invariants.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/nutrition_invariants.py)
- [`app/domain/meal_state.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/domain/meal_state.py)
- [`docs/MODEL_ALLOCATION.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/MODEL_ALLOCATION.md)

## Current Model Allocation

Current default BuilderSpace allocation is:

- `task_meal_link_pass = grok-4-fast`
- `decision_pass = grok-4-fast`
- `nutrition_resolution_pass = grok-4-fast`
- `final_response_pass = grok-4-fast`

Pass-specific env keys now exist and should be preferred over the legacy planner/primary aliases.

## Orchestration Status

[`app/usecases/text_meal.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/usecases/text_meal.py) is now restricted to orchestration-local functions only:

- `_trace_with_request_id`
- `_debug_step`
- `_run_text_stage`
- `_pass_envelope`
- `run_text_meal_canary`
- `record_success`
- `record_error`

It no longer owns:

- answer parsing helpers
- evidence merge/ranking helpers
- follow-up loop logic
- deterministic enrichment
- reply rendering logic
- legacy primary/judge/router behavior

## Retired Legacy Modules

The following legacy modules are retired and should not be revived:

- [`app/agent/decision_resolver.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/decision_resolver.py)
- [`app/agent/primary_llm.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/primary_llm.py)
- [`app/application/reply_renderer.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/reply_renderer.py)
- [`app/application/followup_policy.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/followup_policy.py)
- [`app/application/context_rendering.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/context_rendering.py)
