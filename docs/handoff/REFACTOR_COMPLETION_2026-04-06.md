# Refactor Completion 2026-04-06

## What Is Done

The canonical food-estimation runtime is now fully aligned to:

1. `task_meal_link_pass`
2. `decision_pass`
3. `nutrition_resolution_pass`
4. `final_response_pass`

The runtime is `LLM-first`.

## Deterministic Boundary

Deterministic code is now restricted to `quality gate` behavior only.

Allowed:

- schema/shape validation
- one transport/schema retry per pass
- state bookkeeping
- evidence normalization
- exact-label base-truth checks
- macro/kcal arithmetic sanity checks
- trace and persistence recording

Not allowed:

- meal-link inference override
- decision override
- tool-routing override
- follow-up wording policy
- semantic retry loops
- answer rewriting
- heuristic semantic enrichment

## `text_meal.py` Status

[`app/usecases/text_meal.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/usecases/text_meal.py) has been reduced to orchestration-local functions only:

- `_trace_with_request_id`
- `_debug_step`
- `_run_text_stage`
- `_pass_envelope`
- `run_text_meal_canary`
- `record_success`
- `record_error`

It no longer owns local parsing, evidence ranking, follow-up policy, reply rendering, or semantic fallback logic.

## Active Owners

- [`app/agent/task_meal_link_llm.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/task_meal_link_llm.py)
- [`app/agent/decision_llm.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/decision_llm.py)
- [`app/agent/nutrition_resolution_llm.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/nutrition_resolution_llm.py)
- [`app/agent/final_response_llm.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/final_response_llm.py)
- [`app/application/pass_runner.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/pass_runner.py)
- [`app/application/context_assembly.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/context_assembly.py)
- [`app/application/evidence_assembly.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/evidence_assembly.py)
- [`app/application/state_transition.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/state_transition.py)
- [`app/application/nutrition_invariants.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/nutrition_invariants.py)
- [`app/application/answer_support.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/answer_support.py)
- [`app/observability/payload_builders.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/observability/payload_builders.py)

## Retired Legacy Modules

These were intentionally retired and should not be reintroduced:

- [`app/agent/decision_resolver.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/decision_resolver.py)
- [`app/agent/primary_llm.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/primary_llm.py)
- [`app/application/reply_renderer.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/reply_renderer.py)
- [`app/application/followup_policy.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/followup_policy.py)
- [`app/application/context_rendering.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/context_rendering.py)

## Validation Snapshot

Targeted regression suite passed after the final slimming pass:

- `tests/test_text_meal.py`
- `tests/test_builderspace_adapter.py`
- `tests/test_pass_runner_and_invariants.py`
- `tests/test_base_nutrition_integration.py`
- `tests/test_real_world_regression_fixture.py`
- `tests/test_search_ranking.py`

Result:

`45 passed`

## Still Intentionally Deferred

These are not missing refactor work. They are explicitly deferred:

- prompt caching
- rolling summary
- fast path
- error clustering
- non-food workflow expansion
- open-ended self-correction loops
