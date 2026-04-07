# Text Meal Canary Agent Index

## Read First

Read these first, in order:

1. [docs/SOURCE_OF_TRUTH.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/SOURCE_OF_TRUTH.md)
2. [docs/handoff/README.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/README.md)
3. [docs/APP_LAYER_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/APP_LAYER_MAP.md)
4. [docs/TEXT_MEAL_CANARY_PROMPT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TEXT_MEAL_CANARY_PROMPT_SPEC.md)

## Runtime Discipline

This repository is `LLM-first`.

The canonical food-estimation runtime is:

1. `task_meal_link_pass`
2. `decision_pass`
3. `nutrition_resolution_pass`
4. `final_response_pass`

These four passes own semantic understanding.

## Deterministic Boundary

Deterministic code is strictly downgraded to a `quality gate`.

Allowed deterministic behavior:

- schema parsing and shape validation
- one transport/schema retry per pass
- state persistence bookkeeping
- trace and observability recording
- evidence normalization
- exact-label base-truth consistency checks
- macro/kcal arithmetic sanity checks

Disallowed deterministic behavior:

- meal-link inference
- clarify/blocking recalibration
- tool routing override
- exactness override
- semantic retry or rebuild loops
- follow-up wording injection
- replacing model outputs with hand-authored semantic answers

Rule:

- deterministic may validate
- deterministic may downgrade confidence
- deterministic may mark a result unusable
- deterministic may not become a second planner, second decision layer, or second nutrition reasoner

## Implementation Bias

Prefer this build order:

1. `only LLM`
2. `LLM + minimal structure`
3. `LLM + narrow deterministic quality gates`
4. `LLM + observability`
5. `LLM + carefully justified optimization`

Do not invert this order.

If unsure whether a deterministic rule is needed, delete it first and inspect raw model behavior.

## Layering Rule

If one module starts doing more than one of these, split it:

- reasoning
- state transition
- wording
- retry semantics

## Current Ownership

- `task_meal_link_pass` owns intent, meal boundary, target meal, and `clarification_blocking`
- `decision_pass` owns next action, tool plan, and whether clarify is blocking
- `nutrition_resolution_pass` owns kcal/macros/components, `resolution_mode`, `resolution_basis`, and unresolved info
- `final_response_pass` owns the final natural-language reply and whether one unresolved item becomes an outward follow-up
- deterministic code owns validation, bookkeeping, and trace only

## Handoff Standard

When changing runtime behavior, update both:

- [docs/handoff/TEXT_MEAL_RUNTIME_CURRENT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/TEXT_MEAL_RUNTIME_CURRENT.md)
- [docs/handoff/NEXT_AGENT_CHECKLIST.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/NEXT_AGENT_CHECKLIST.md)

Do not leave architecture changes only in chat history.

## Debug Discipline

For dashboard failures:

- classify the `first_bad_pass` before patching
- classify one root-cause bucket before patching
- do not patch downstream behavior while the upstream pass is still broken
- turn every repaired live failure into a regression fixture
- do not use dish-specific prompt examples or hardcoded heuristics as a substitute for route fixes

Reference:

- [docs/handoff/LIVE_TRACE_TRIAGE_WORKFLOW.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/LIVE_TRACE_TRIAGE_WORKFLOW.md)
