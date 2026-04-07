# Text Meal Canary Open Issues

## Scope
This file tracks the next runtime fixes after the 4-pass refactor. It focuses on path logic, not special-case prompts.

## Repair Order
1. Correction/disagreement flow
2. Final-response fallback safety
3. Brand/search follow-up attachment
4. Provisional estimate policy for named dishes
5. Range vs. most-likely estimate discipline
6. Pass-level timeout and retry observability

## Issue 1: Correction / Disagreement Flow
- Symptom: `哪有這麼多呢` can collapse into empty clarification or `0 kcal`.
- Root cause: correction turns are not consistently treated as same-meal estimate revisions.
- Owner files:
  - `app/agent/task_meal_link_llm.py`
  - `app/agent/decision_llm.py`
  - `app/application/context_assembly.py`
  - `app/agent/final_response_llm.py`
- Fix direction:
  - detect correction/disagreement as a first-class turn type
  - carry current user input into decision payload
  - carry prior meal context only when attachment is explicit
  - allow nutrition resolution to revise prior estimate instead of dropping to empty clarify
- Acceptance:
  - disagreement does not produce `0 kcal`
  - disagreement remains attached to the same meal when supported by context
  - final response acknowledges the correction and either revises or asks one useful missing detail

## Issue 2: Final Response Must Not Present Empty Fallback as Nutrition Answer
- Symptom: replies can contain `0 kcal` / `0g` as if they were final.
- Root cause: fallback/degraded payloads leak through final response.
- Owner files:
  - `app/agent/final_response_llm.py`
  - `app/observability/payload_builders.py`
- Fix direction:
  - sanitize final response against `cannot_estimate_yet` and zero-valued nutrition payloads
  - never present zero macros as a valid answer unless explicitly intended
- Acceptance:
  - no reply says `0 kcal` or `0g` as the answer for unresolved meals
  - fallback text remains clarify-style only

## Issue 3: Brand / Search Follow-up Must Attach to the Open Meal
- Symptom: `你可以查查軟實力這家店` falls back to generic clarify instead of triggering search.
- Root cause: the current turn is not composed with the unresolved meal thread into a tool-worthy query.
- Owner files:
  - `app/application/context_assembly.py`
  - `app/agent/task_meal_link_llm.py`
  - `app/agent/decision_llm.py`
  - `app/application/evidence_assembly.py`
- Fix direction:
  - attach brand/store hints to the open unresolved meal when context supports it
  - feed decision pass both current turn and unresolved meal identity
  - compose tool queries from meal identity plus new brand hint
- Acceptance:
  - brand/search hint routes to `run_tool_lookup`
  - query includes both brand/store and dish identity
  - no generic food-portion clarify fallback on store-search turns

## Issue 4: Named Dish Without Exact Item Should Still Reach Provisional Estimate
- Symptom: a branded named dish without exact item coverage drops too early to `cannot_estimate_yet`.
- Root cause: decision and nutrition passes remain too conservative when dish identity is already meaningful.
- Owner files:
  - `app/agent/decision_llm.py`
  - `app/agent/nutrition_resolution_llm.py`
- Fix direction:
  - allow provisional estimate when dish identity and structure are already usable
  - reserve `cannot_estimate_yet` for cases where no meaningful model can be formed
- Acceptance:
  - named dish + store context can reach `provisional_estimate`
  - final response does not insist on exact nutrition before giving any estimate

## Issue 5: Most-Likely Estimate Must Not Collapse Into Risk Upper Bound
- Symptom: meals like `大碗滷肉飯` can jump to an obviously too-high number.
- Root cause: estimate range and most-likely value are not cleanly separated.
- Owner files:
  - `app/agent/nutrition_resolution_llm.py`
  - `app/agent/final_response_llm.py`
- Fix direction:
  - keep low/high/most-likely separate
  - final reply should surface most-likely, not worst-case
- Acceptance:
  - trace shows distinct range fields
  - final reply uses a reasonable central estimate

## Issue 6: Runtime Stability and Timeout Attribution
- Symptom: the same utterance can fail once and succeed on resend with no clear pass-level diagnosis.
- Root cause: timeout and retry attribution is still too opaque around nutrition/tool flow.
- Owner files:
  - `app/application/pass_runner.py`
  - `app/usecases/text_meal.py`
- Fix direction:
  - ensure every pass reports timeout/retry/degraded status clearly
  - make nutrition/tool path use the same protected execution envelope everywhere possible
- Acceptance:
  - trace shows which pass timed out or retried
  - repeated user resend is no longer required just to recover from hidden pass errors
