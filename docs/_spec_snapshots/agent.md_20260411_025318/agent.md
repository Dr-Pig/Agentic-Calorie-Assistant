# Text Meal Canary Agent Index

## Read First

Read these first, in order:

1. [docs/SOURCE_OF_TRUTH.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/SOURCE_OF_TRUTH.md)
2. [docs/LLM_OWNERSHIP_RULE.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/LLM_OWNERSHIP_RULE.md)
3. [docs/handoff/README.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/README.md)
4. [docs/APP_LAYER_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/APP_LAYER_MAP.md)
5. [docs/TEXT_MEAL_CANARY_PROMPT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TEXT_MEAL_CANARY_PROMPT_SPEC.md)

## Runtime Discipline

This repository is `LLM-first`.

The core product objective is:

- use the lowest-friction logging possible
- keep calibrating the user's operating total daily energy expenditure
- use recommendations and reminders that make adherence easier
- help the user sustain a real calorie deficit over time

The canonical food-estimation runtime is:

1. `task_meal_link_pass`
2. `decision_pass`
3. `nutrition_resolution_pass`
4. `final_response_pass`

These four passes own semantic understanding.

## Deterministic Boundary

Deterministic code is strictly downgraded to a `quality gate`.

The detailed ownership rule lives in:

- [docs/LLM_OWNERSHIP_RULE.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/LLM_OWNERSHIP_RULE.md)

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

## Product North Star

The system is not optimizing for generic wellness advice first.

It is optimizing for a sustained calorie deficit through:

- low-friction intake logging
- continuously calibrated expenditure estimates
- recommendation and proactive guidance that improve adherence

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

## Spec Editing Discipline

For architecture / spec files, content preservation is mandatory.

Hard rule:

- do not use delete-and-recreate for existing spec or architecture files
- do not replace a document wholesale unless the user explicitly approves a rewrite
- prefer minimal additive or surgical edits
- if a file has encoding or patch-anchor problems, stop and confirm before restructuring
- when a rewrite is explicitly approved, preserve the previous section map and prove no content domain was dropped

Required fallback:

- if a direct patch is hard, first produce a content inventory
- identify what is being added, what is being removed, and what is being preserved
- only then edit the file

## Encoding Discipline

Documentation encoding is part of the repository's context infrastructure.

Hard rule:

- do not rely on default shell encoding when reading Chinese markdown
- do not save docs in unknown or mixed encodings
- repository docs should use `UTF-8 with BOM`
- if a file is unreadable in terminal output, verify bytes / encoding first before editing content

Workflow:

- before high-risk spec or markdown editing, run [`scripts/check_encoding.ps1`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/check_encoding.ps1)
- if encoding drift is detected, normalize encoding before structural edits
- do not treat encoding normalization as permission to rewrite content

Required reference:

- [docs/ENCODING_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/ENCODING_POLICY.md)
