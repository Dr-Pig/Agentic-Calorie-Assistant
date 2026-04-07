# Text Meal Next Phase Plan

## Current Priority

The current priority is not adding new capabilities.

It is:

- finish shrinking `text_meal.py`
- remove dead helper code after extraction
- keep deterministic inside the quality-gate boundary
- keep 4-pass ownership stable under further changes

## Near-Term Work

1. Continue physical cleanup of [`app/usecases/text_meal.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/usecases/text_meal.py)
   - delete dead helper code already replaced by `app/agent/*` and `app/application/*`
   - keep only orchestration helpers that are still truly usecase-local
2. Keep strengthening trajectory-first evaluation
   - compare pass outputs, not just final reply text
3. Keep exact-item and follow-up guards semantic-free
   - validate only
   - do not rewrite semantic decisions
4. Delay optimization work
   - no prompt caching
   - no fast path
   - no rolling summary
   until the runtime is easier to modify safely

## Explicitly Deferred

- prompt caching
- rolling summary
- fast path
- error clustering
- non-food full workflow expansion

These are intentionally deferred until the current runtime is simpler to hand off.
