# LLM Ownership Rule

## Purpose

This repository is `LLM-first`.

The canonical semantic runtime is:

1. `task_meal_link_pass`
2. `decision_pass`
3. `nutrition_resolution_pass`
4. `final_response_pass`

These four passes own semantic understanding and semantic decisions.

## Hard Rule

Outside the four LLM passes, deterministic code must not make:

- knowledge decisions
- route decisions
- retrieval decisions
- search query decisions
- evidence winner decisions
- exactness decisions
- follow-up decisions
- final answer decisions

## Ownership

### `task_meal_link_pass`

Owns:

- meal boundary understanding
- same-meal vs new-meal linking
- whether clarification is boundary-blocking

### `decision_pass`

Owns:

- whether tool use is needed
- which tool to call
- what search or lookup query to use
- whether the flow should clarify or proceed

### `nutrition_resolution_pass`

Owns:

- exact vs anchored vs heuristic posture
- calorie and macro reasoning
- unresolved-info judgment
- whether missing information is actually blocking for nutrition

### `final_response_pass`

Owns:

- final natural-language response
- whether a follow-up should be surfaced to the user
- outward wording, brevity, and tone

## Evidence Tier Policy

Semantic trust order should not be treated as a single flat "DB beats all" rule.

The repository standard is:

1. `tier_1_exact_verified`
2. `tier_2_context_verified`
3. `tier_3_anchor_prior`
4. `tier_4_web_nonexact`
5. `tier_5_model_context`

Interpretation:

- `tier_1_exact_verified`
  - internal exact DB
  - verified exact label or exact doc fragment that has already been accepted as exact-local truth
- `tier_2_context_verified`
  - confirmed active-meal context
  - user-confirmed durable memory
  - accepted correction memory
- `tier_3_anchor_prior`
  - base nutrition DB
  - ingredient anchors
  - common dish priors
  - structured non-exact menu fragments
- `tier_4_web_nonexact`
  - official but non-exact web fragments
  - third-party snippets or weak web evidence
- `tier_5_model_context`
  - model internal knowledge with no stronger external grounding

Rules:

- `common dish priors` are part of DB / retrieval, but only as evidence blocks.
- `common dish priors` must never behave like deterministic answer rules.
- `web_search_official` must remain below `exact_item_db` unless it is explicitly promoted into accepted exact-local truth by a later canonical rule.
- official web evidence may support grounding and narrowing, but must not outrank exact/local truth by default.
- verified user or session memory should outrank generic priors.
- deterministic code may label tiers and provenance, but may not decide the winner semantically.

## Allowed Deterministic

Deterministic code may do only:

- schema parsing
- output normalization
- tool execution
- evidence packaging
- provenance labeling
- trace and observability recording
- transport retry and timeout handling
- arithmetic or physics guards
- consistency checks that mark results unusable without replacing them
- non-semantic text cleaning

## Disallowed Deterministic

Deterministic code may not:

- override the tool selected by `decision_pass`
- invent or rewrite a search query because it "looks better"
- trigger search because a heuristic thinks coverage is weak
- choose which evidence should win semantically
- downgrade or upgrade exactness because a heuristic thinks it is safer
- inject or suppress follow-up because deterministic code thinks it is better
- replace an LLM result with a hand-authored semantic answer

## Failure Handling Rule

If an LLM output is malformed, missing required fields, or violates an arithmetic invariant, deterministic code may:

- mark the result invalid
- retry the transport
- fall back to a declared fallback object
- lower confidence metadata
- expose the failure in trace output

Deterministic code may not silently replace the failed LLM judgment with a new semantic judgment.

## Current Audit

### Still Stealing Decision

These functions still contain semantic policy and should be reduced or removed in follow-up cleanup:

- `app/agent/nutrition_resolution_llm.py` prompt instructions that still rely on deterministic convenience flags such as `generic_drink_packaged_refs`
- `app/agent/decision_llm.py` prompt instructions that still rely on deterministic convenience flags such as `exact_title_match_present` and `size_missing_for_standardized_drink`
- any future helper that silently removes evidence instead of exposing it to the LLM

### Downgrade To Pure Execution Or Normalization

These should remain only if kept strictly structural:

- `app/application/evidence_assembly.py::search_result_quality`
- `app/application/context_assembly.py::has_generic_drink_packaged_refs`
- `app/application/evidence_assembly.py::infer_expected_components`
- `app/application/evidence_assembly.py::build_partial_grounding_packet`
- `app/application/evidence_assembly.py::normalize_tool_evidence`
- `app/application/evidence_assembly.py::execute_primary_tool_request`
- `app/agent/nutrition_resolution_llm.py::augment_followup_metadata`

### Delete

The first cleanup pass already removed these deterministic helpers from the tree:

- `app/application/evidence_assembly.py::build_search_query`
- `app/application/evidence_assembly.py::compose_decision_lookup_query`
- `app/agent/nutrition_resolution_llm.py::suppress_followup_for_exact_match`
- runtime `partial_grounding -> search_official_nutrition` auto-trigger
- `app/application/evidence_assembly.py::pre_rank_evidence_items`

## Structural Debt

The deterministic ownership boundary is cleaner now, but the main orchestration file is still too large.

Current unresolved god file:

- `app/usecases/text_meal.py`

This file still mixes:

- pass orchestration
- retrieval wiring
- tool execution flow
- invariant application
- final payload assembly
- trace assembly
- persistence handoff

That is a structural problem even if the logic inside becomes more `LLM-first`.

## Cleanup Standard

When removing deterministic behavior:

1. Prefer deleting the semantic helper entirely.
2. If deletion is not yet safe, reduce it to pure formatting or execution.
3. If a heuristic still exists, document it here as temporary debt.
4. Do not hide semantic policy inside evidence packaging or trace helpers.
