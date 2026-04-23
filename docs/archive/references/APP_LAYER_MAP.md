# App Layer Map

> **⚠️ V2 架構注意：** 本文件描述的是 V1 的 4-pass 架構（`run 4 passes`、`task_meal_link_llm.py`、`decision_llm.py` 等）。V2 架構下這些模組將被重組為 manager + tools 架構。
>
> **V2 設計真相：** `APP_V2_TARGET_ARCHITECTURE_SPEC.md`
> **V2 遷移計畫：** `APP_V2_IMPLEMENTATION_PLAN.md`

## Goal

Keep the external API stable while separating runtime ownership cleanly.

## Current Runtime Ownership

### `app/usecases/`

- [`app/usecases/text_meal.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/usecases/text_meal.py)
  - top-level orchestration only
  - load request/session state
  - run 4 passes
  - run bounded tool loop
  - persist result
  - emit trace envelope

### `app/agent/`

- `task_meal_link_llm.py`
  - task + meal-link prompt and schema fallback/normalize helpers
- `decision_llm.py`
  - decision prompt and schema fallback/normalize helpers
- `nutrition_resolution_llm.py`
  - nutrition prompt and nutrition-result shaping helpers
- `final_response_llm.py`
  - final-response prompt and final-response stage runner

### `app/application/`

- `pass_runner.py`
  - one pass execution contract
  - one transport/schema retry
  - `success / degraded / failed`
- `context_assembly.py`
  - per-pass minimal payload builders
- `evidence_assembly.py`
  - evidence summary
  - tool evidence normalization
  - tool execution support
- `state_transition.py`
  - canonical meal-state bookkeeping
  - follow-up loop bookkeeping
- `nutrition_invariants.py`
  - exact-label base-truth checks
  - macro/kcal arithmetic sanity checks

### `app/domain/`

- `meal_state.py`
  - `CanonicalMealState`
- `conversation_state.py`
  - broader conversation/session state

## Hard Boundaries

- `usecases/text_meal.py` must not become a second planner or second nutrition engine
- `agent/*` owns semantic reasoning
- `application/*` owns validation, bookkeeping, assembly, and execution contracts
- `domain/*` owns state models only

## Deterministic Rule

Anything in `application/*` must remain inside the deterministic quality-gate boundary.

If an `application` module starts making open-world semantic decisions, move that logic back into the relevant LLM pass.
