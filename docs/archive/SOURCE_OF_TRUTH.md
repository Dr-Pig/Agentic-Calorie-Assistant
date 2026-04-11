# Project Source of Truth

## Product Goal

This is not a plain calorie calculator.

The product must:

- understand the user turn in conversation context
- attach the turn to the correct meal log or explicitly keep boundary ambiguity open
- decide whether to estimate now, estimate provisionally, use tools, or clarify first
- return a natural assistant-style response

The product is judged first by whether it feels like a helpful assistant, then by estimate quality.

## Core Product Philosophy

For food estimation:

- exact truth is best when identity is strong
- if the meal can be modeled meaningfully, `provisional estimate + 1 useful question` is preferred
- only when the meal cannot be modeled meaningfully should the system do `clarify only`

The system should not default to `always ask first`.

## Canonical Runtime

The canonical runtime is 4-pass:

1. `task_meal_link_pass`
2. `decision_pass`
3. `nutrition_resolution_pass`
4. `final_response_pass`

### Pass Responsibilities

`task_meal_link_pass`

- intent
- scope
- meal link action
- target meal id
- boundary reason
- `clarification_blocking`

`decision_pass`

- next action
- tool plan
- unresolved info
- `clarify_is_blocking`
- `can_proceed_without_clarify`

`nutrition_resolution_pass`

- the only layer allowed to produce kcal/macros/components
- `resolution_mode`
- `resolution_basis`
- answer payload
- unresolved info

`final_response_pass`

- the only layer that decides how to talk to the user
- may surface at most 1 outward follow-up
- may not add new numbers, new boundary, or new unresolved slots

## Deterministic Boundary

Deterministic code is a `quality gate`, not a reasoning layer.

Allowed:

- schema parsing
- one transport/schema retry per pass
- state persistence bookkeeping
- evidence normalization
- exact-label base-truth checks
- macro/kcal arithmetic sanity checks
- trace and observability

Disallowed:

- meal-link recalibration
- boundary recalibration
- tool-routing override
- exactness override
- semantic retry loops
- follow-up wording templates replacing model output
- semantic answer rewrite

If a deterministic rule needs to understand open-world language, it is in the wrong layer.

## Exact Item Rule

For exact-item cases:

- official label values are the `base nutrition truth`
- the model may still apply a valid `portion_multiplier`
- deterministic may verify `base truth`
- deterministic may not blindly force the final answer back to full serving size

Canonical interpretation:

`final answer = exact label base truth * portion_multiplier`

## Follow-Up Rule

Follow-up is model-owned.

Deterministic may only:

- record whether the same follow-up key has already been asked on the same meal thread
- stop the same follow-up from being surfaced repeatedly after the hard-stop threshold

Deterministic may not decide what the next question should be.

## Architectural Preference

Prefer:

- thin orchestration
- clear ownership per pass
- fewer, stronger layers

Avoid:

- God files
- duplicated routing logic
- fallback logic that silently becomes the real runtime
- piling more deterministic rules onto a broken ownership model
