# Architecture Change Checklist

Use this checklist before making any meaningful architecture change in the canary.

## Mandatory questions

1. What does the raw frontier LLM already do well enough here?
2. What durable value does the proposed mechanism add?
3. Which owner is this change for?
   - raw LLM
   - local truth
   - targeted guardrail
   - search
4. Is the gap one of these?
   - exact truth gap
   - systematic failure-family gap
   - product consistency gap
5. Would this mechanism still make sense if GPT-class frontier models improve materially in 1-3 years?

## Red-line checks

- Does this add search to the default estimation path?
- Does this add retrieval only because more evidence might help?
- Does this create a deterministic semantic layer that competes with the LLM?
- Does this increase planner, route, gate, or heuristic complexity beyond the main LLM path?
- Does this patch a temporary model weakness without creating durable product value?

If any answer is yes, stop and justify the exception explicitly.

## Required evaluation

Compare against:

- `raw frontier LLM`
- `LLM + local truth`
- `LLM + targeted guardrail`

Reject the change if complexity increases without measurable gain on the target failure family.

## Canonical scenario checks

The architecture should produce one unambiguous choice for each case:

1. common meal with no exact truth
2. exact convenience-store item with known nutrition
3. inaccessible official nutrition PDF already normalized into local data
4. Japanese ramen with known underestimation risk
5. vague portion request requiring stronger follow-up
