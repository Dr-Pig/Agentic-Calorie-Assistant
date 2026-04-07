# Next Agent Checklist

Before changing runtime behavior:

1. Read:
   - [docs/SOURCE_OF_TRUTH.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/SOURCE_OF_TRUTH.md)
   - [docs/APP_LAYER_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/APP_LAYER_MAP.md)
   - [docs/handoff/TEXT_MEAL_RUNTIME_CURRENT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/TEXT_MEAL_RUNTIME_CURRENT.md)
2. Verify the change does not push deterministic code outside the quality-gate boundary.
3. Run targeted tests:
   - `python -m pytest tests/test_builderspace_adapter.py tests/test_text_meal.py tests/test_trace_observability_contract.py tests/test_text_meal_trace_eval.py tests/test_pass_runner_and_invariants.py -q`
4. Treat [`app/usecases/text_meal.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/usecases/text_meal.py) as orchestration-only. Do not reintroduce parsing, enrichment, follow-up policy, or renderer logic there.
5. If ownership changes, update:
   - [docs/APP_LAYER_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/APP_LAYER_MAP.md)
   - [docs/handoff/TEXT_MEAL_RUNTIME_CURRENT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/TEXT_MEAL_RUNTIME_CURRENT.md)
   - [docs/handoff/REFACTOR_COMPLETION_2026-04-06.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/REFACTOR_COMPLETION_2026-04-06.md)

Do not:

- add deterministic semantic routing without trace-backed justification
- put new hidden policy logic into `text_meal.py`
- leave architecture changes undocumented
