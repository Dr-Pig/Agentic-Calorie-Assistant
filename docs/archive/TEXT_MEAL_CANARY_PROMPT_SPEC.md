# Text Meal Canary Prompt Spec

## Purpose

This document defines the current prompt contract for the 4-pass `text_meal` runtime.

It exists to keep prompt iteration aligned with code ownership.

## Runtime Shape

The prompt system is organized as:

1. `task_meal_link_pass`
2. `decision_pass`
3. `nutrition_resolution_pass`
4. `final_response_pass`

Each pass has its own prompt, context contract, and schema.

## Pass Contracts

### `task_meal_link_pass`

Mission:

- determine intent
- determine whether this turn attaches to an existing meal, creates a new meal, or remains boundary ambiguous
- determine whether boundary clarification is blocking

Must not:

- estimate calories
- choose tools
- produce user-facing follow-up wording

### `decision_pass`

Mission:

- decide the next action
- decide whether tool lookup is needed
- decide whether the system can proceed without clarification

Must not:

- produce full nutrition answers
- produce final user-facing wording

### `nutrition_resolution_pass`

Mission:

- produce the nutrition result
- set `resolution_mode`
- set `resolution_basis`
- return answer payload and unresolved info

Must not:

- write the final user-facing reply

This is the only pass allowed to output:

- kcal
- protein/carbs/fat
- components

### `final_response_pass`

Mission:

- convert structured result into a natural assistant reply
- decide whether one unresolved info item becomes an outward follow-up

Must not:

- add new numbers
- add new boundary decisions
- add unresolved slots not already present upstream

## Context Isolation

Prompt inputs must stay minimal per pass.

`task_meal_link_pass`

- current user input
- minimal recent transcript
- open unresolved meal summaries
- meal log summaries
- boundary features

`decision_pass`

- canonical meal state
- meal-link result
- selected evidence summary

`nutrition_resolution_pass`

- target meal context
- normalized evidence
- optional calibration packet

`final_response_pass`

- decision result
- nutrition result
- active meal summary

Do not broadcast full transcript or raw tool output to every pass.

## Deterministic Rule

Prompts must assume that deterministic code does only:

- schema parsing
- transport/schema retry
- evidence normalization
- exact-label base-truth checks
- arithmetic sanity checks
- state bookkeeping
- observability

Prompts must not rely on deterministic post-processing to:

- fix meal linking
- suppress follow-up semantically
- re-route the turn
- rewrite the answer

## Prompt Change Safety

When changing any pass prompt, verify:

1. ownership stayed within the pass boundary
2. no hidden dependency on deterministic semantic rescue was added
3. the change is reflected in trajectory tests, not just final reply quality
