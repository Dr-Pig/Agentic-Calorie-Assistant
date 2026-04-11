# Old Semantic Path Cleanup

## Goal

Keep the current dashboard entrypoint on [text_meal.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/usecases/text_meal.py), but remove or downgrade legacy deterministic semantic paths so the runtime stays LLM-first.

## Removed

- [answer_support.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/answer_support.py)
  - `meal_template_as_answer()`
  - `_meal_template_kcal_mismatch()`
  - `derive_failure_family()`
  - `template_override_blocked()`
  - `followup_decision()`
  - `followup_reason()`
- [state_transition.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/state_transition.py)
  - `looks_like_pending_question_followup()`
  - `calibrate_boundary_confidence()`
- [nutrition_invariants.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/nutrition_invariants.py)
  - semantic veto path `fallback_to_cannot_estimate_yet`

## Downgraded To Context Or Quality Gate Only

- [knowledge_packets.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/knowledge_packets.py)
  - `match_meal_template()` still exists, but it no longer returns a routing score.
  - Meal template is treated as prompt context only.
- [text_meal.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/usecases/text_meal.py)
  - `meal_template` is still passed into prompt/trace assembly.
  - `template_override_blocked` is no longer used as a runtime decision signal.
- [payload_builders.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/observability/payload_builders.py)
  - `followup_decision` and `followup_reason` are now trace reflections of pass outputs, not deterministic policy outputs.
- [answer_support.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/answer_support.py)
  - `apply_evidence_hard_gate()` remains as source-floor evidence filtering only.
  - `meal_template_context()` remains as prompt context rendering only.
  - `evaluate_answer()` remains as quality-signal extraction only.

## Still Intentionally Retained

- [build_gate_packet()](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/agent/knowledge_packets.py)
  - Retained as risk/context packet builder for prompt context.
  - It must not become routing override logic.
- [apply_evidence_hard_gate()](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/answer_support.py)
  - Retained only to prefer strong exact local evidence and drop obviously weak exact-truth candidates.
  - If it starts changing semantic answer strategy, it must be removed.

## Current Rule

Deterministic code may only:

- validate or normalize structure
- enforce source-floor evidence safety
- perform arithmetic or exact-label consistency checks
- handle bookkeeping, persistence, and trace recording

Deterministic code may not:

- create semantic answers
- override meal linking
- override decision routing
- decide follow-up policy wording
- veto nutrition resolution mode
