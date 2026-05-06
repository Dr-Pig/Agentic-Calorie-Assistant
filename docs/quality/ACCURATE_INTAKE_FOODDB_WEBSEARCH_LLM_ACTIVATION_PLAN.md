# Accurate Intake FoodDB / WebSearch / LLM Activation Plan

This document is repo-truth for the next FoodDB evidence activation sequence. It is diagnostic-only. It does not approve self-use, production DB work, Kimi activation, WebSearch runtime truth, or product readiness.

## Strategic Classification

```yaml
current_mainline: Calorie Deficit Logging MVP local self-use foundation
is_detour: false
mainline_blocker_being_removed:
  - fooddb_manager_packet_seam
  - live_diagnostic_activation_order
  - websearch_truth_boundary
strategic_verdict: mainline
capability_layer: L5-L6 evidence_packet_and_nutrition_synthesis_seam
slice_mode:
  - diagnostic_only
  - offline_runtime
  - live_diagnostic_probe
user_facing_behavior_changed: false
runtime_truth_changed: false
mutation_changed: false
safe_to_proceed_now: true
why_not_local_next_step_trap: validates packet shape before expanding FoodDB or adding WebSearch uncertainty
```

## Best-Practice Basis

- [OpenAI Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals): evaluate workflow-level behavior with trace evidence, not only final text.
- [OpenAI Trace Grading](https://developers.openai.com/api/docs/guides/trace-grading): traces should identify model calls, tool calls, guardrails, and failure location.
- [OpenAI Function Calling](https://developers.openai.com/api/docs/guides/function-calling): tool loops should preserve request, tool execution, second request, and final response boundaries.
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs): schema boundaries must be explicit before live diagnostic expansion.
- Repo `L4B_RETRIEVAL_POLICY_SPEC`: retrieval is typed and metadata-first; semantic or vector search can recall candidates but cannot select runtime truth.

## Activation Ladder

```yaml
activation_ladder:
  1_deterministic_fooddb:
    name: deterministic FoodDB
    purpose: prove local aliases, fuzzy lookup, modifiers, bare/listed basket boundary, source/runtime truth separation
    live_provider: false
    output: compact FoodDB manager evidence packet

  2_grokfast_local_packet_smoke:
    name: GrokFast local packet smoke
    purpose: test whether a low-cost live Manager probe uses the provided FoodDB packet without inventing source truth
    live_provider: GrokFast only
    classification: live_diagnostic_only
    forbidden_claims:
      - readiness
      - self_use_approval
      - production_model_selection
      - runtime_mutation

  3_websearch_candidate_pipeline:
    name: WebSearch candidate pipeline
    purpose: build query, source-quality, provenance, and serving-basis gates before any live Manager use
    live_provider: false
    runtime_truth_allowed: false

  4_grokfast_websearch_packet_smoke:
    name: GrokFast WebSearch packet smoke
    purpose: verify Manager can consume WebSearch candidate packets without treating snippets as truth
    requires:
      - deterministic WebSearch packet tests
      - fixed WebSearch GrokFast live diagnostic case matrix
      - source provenance
      - serving-basis classification

  5_kimi_e2e_diagnostic:
    name: Kimi E2E diagnostic
    purpose: provider comparison and end-to-end diagnostic after local FoodDB and WebSearch packet seams are proven
    readiness_claimed: false
```

## Coverage Stop Rule

```yaml
coverage_stop_rule:
  common_serving_anchor_max_before_activation: 80
  listed_basket_components_max_before_activation: 60
```

## Modifier Priority

```yaml
modifier_priority:
  P0: sugar_level, cup_size, rice_portion
  P1: common add-ons
  P2: preparation method / fried-braised-grilled style metadata posture only
```

## Exact Lane Guard

```yaml
exact_lane_guard:
  - exact_card_candidate.runtime_truth_allowed == false
  - selected_extract.runtime_truth_allowed == false
  - no_ledger_mutation_from_exact_candidate
```

## Activation Gap Report

activation can proceed with known bounded gaps.

```yaml
activation_gap_report:
  known_unsupported_food_families: runtime_supported_but_basket_semantic_only
  known_ask_followup_cases: runtime_supported_but_require_clarification
  known_candidate_only_exact_cases: runtime_supported_candidate_only_exact_cards
  known_modifier_limitations: staged_modifier_priority_p0_p1_p2
  known_basket_limitations: bare_and_listed_basket_bounding_rules
```

## Manager Packet Boundary

Manager receives compact evidence packets only:

```yaml
manager_packet_allowed:
  - canonical_name
  - aliases or matched component label
  - runtime_role
  - runtime_truth_allowed
  - kcal_point
  - kcal_range
  - serving_basis
  - portion_basis
  - runtime_usage_boundary
  - followup_hints
  - compact source_provenance
  - approval_metadata

manager_packet_forbidden:
  - raw source rows
  - candidate-only records
  - full FoodDB dumps
  - dogfood review artifacts
  - WebSearch snippets as truth
  - FoodDB gap candidates as truth
```

## Integration Readiness Matrix

```yaml
integration_readiness_matrix_update:
  check_edges:
    - Manager decision -> retrieval intent from manager decision
    - retrieval router -> FoodDB local adapter
    - retrieval router -> SQLite FTS adapter
    - retrieval router -> WebSearch candidate
    - WebSearch candidate -> selected extract request
    - selected extract request -> extract result review candidate
    - extract result review candidate -> exact-card review packet
    - exact-card review packet -> live extract preflight
    - WebSearch GrokFast case matrix -> live extract preflight
    - exact candidate chain status -> live runner readiness packet
    - live extract preflight -> live runner readiness packet
    - live runner readiness packet -> GrokFast WebSearch packet live diagnostic runner
    - live extract preflight -> WebSearch live diagnostic report
    - WebSearch live diagnostic report -> Manager contract probe
    - WebSearch Manager contract probe -> repair pack
    - WebSearch Manager contract repair pack -> handoff
    - WebSearch Manager contract handoff -> candidate lane status
    - retriever output -> compact packet
    - packet -> Manager seam
    - packet -> mutation guard
    - exact candidate -> no mutation
    - basket listed components -> approved anchors only
```

This matrix is a dependency-inversion gate. It exists to stop single-slice green checks from hiding a broken integration seam.

## Diagnostic Evidence Log

```yaml
2026-05-05_grokfast_websearch_packet_live_diagnostic:
  artifact_path: artifacts/accurate_intake_grokfast_websearch_packet_smoke_live_rerun.json
  report_path: artifacts/accurate_intake_websearch_live_diagnostic_report_live_rerun.json
  classification: live_diagnostic_only
  live_provider_used: true
  live_websearch_used: false
  status: pass
  case_count: 1
  pass_count: 1
  fail_count: 0
  seam_status: live_diagnostic_pass
  can_expand_websearch_candidate_pipeline: true
  non_claims:
    - no_websearch_runtime_truth
    - no_exact_card_truth_promotion
    - no_runtime_mutation
    - no_readiness_claim
```

## LLM / Deterministic Boundary

```yaml
truth_owner:
  fooddb_runtime_truth: deterministic_validators_and_batch_policy
  source_quality: deterministic_validators
  user_intent_and_synthesis: Manager LLM
  mutation_legality: runtime_guard

deterministic_role:
  - retrieve candidates
  - validate source/runtime boundary
  - build compact packets
  - reject or downgrade invalid source evidence

llm_role:
  - synthesize from provided packet
  - choose follow-up vs grounded estimate
  - preserve uncertainty
  - never create FoodDB truth
```

## Non-Claims

```yaml
non_claims:
  - no readiness claim
  - no self-use approval
  - no production DB
  - no Kimi activation
  - no WebSearch runtime truth
  - no mutation authority
  - no Product Loop integration claim
```
