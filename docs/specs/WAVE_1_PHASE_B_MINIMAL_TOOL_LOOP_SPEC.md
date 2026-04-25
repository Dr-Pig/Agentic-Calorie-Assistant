# Wave 1 Phase B-1 Minimal Tool Loop Spec

## Purpose

Phase B-1 establishes the smallest executable gate for the Wave 1 manager-controlled bounded tool loop.

This document is an execution contract, not a full nutrition implementation spec. It references the canonical Wave 1 nutrition workflow and tunable governance documents, and it must not redefine the Manager as an autonomous nutrition subagent.

## Phase B-1 Scope

Phase B-1 verifies the tool-loop scaffold:

1. Manager Pass 1 produces semantic decision and requested read tools.
2. Runtime validates and filters requested read tools.
3. Read tools return data-only outputs.
4. Raw tool outputs are traced.
5. Packetizer creates compact candidate packets.
6. Manager Pass 2 performs nutrition synthesis from packets.
7. Deterministic guard runs before mutation.
8. Mutation, when allowed, happens only through deterministic mutation layer.
9. Renderer mirrors truth packet only.

Phase B-1 does not optimize nutrition accuracy. It verifies ownership boundaries, trace completeness, and anti-fake-pass invariants.

Passing Phase B-1 does not mean nutrition accuracy is production-ready. It only means tool-loop ownership, trace, guard, mutation, and renderer boundaries are clean enough to proceed to Phase B-2.

## Non-Scope

Phase B-1 must not implement:

- full DB/RAG
- Tavily extract
- Grok renderer
- macro deep synthesis
- rescue / recommendation / memory
- UI redesign
- big folder migration
- autonomous nutrition subagent
- LLM evidence normalizer

## Provider Params Logging

Every Manager Pass 1 and Manager Pass 2 trace must include:

- `provider`
- `model`
- `temperature`
- `max_tokens`
- `response_format`
- `timeout`
- `retry_policy`
- `tool_choice`
- `request_id`

If a provider does not return a value, the field must still be present with `null` and a reason in provider metadata.

## Pass Boundary

Manager Pass 1 may request read tools, but must not output final nutrition truth.

Manager Pass 2 may synthesize:

- item result candidates
- `kcal_range`
- `likely_kcal`
- `uncertainty`
- `evidence_used`

Manager Pass 2 must not mutate ledger state. Mutation can only happen through deterministic mutation tools after guard passes.

## Packet Truth Levels

Read tool and packetizer outputs must include `truth_level`.

Allowed read/packetizer truth levels:

- `candidate`
- `hint`
- `rule_hint`

Forbidden read/packetizer truth levels:

- `final`
- `mutation_result`

`mutation_result` belongs only to the deterministic mutation step.

## Hybrid Canary Policy

Phase B-1 uses Hybrid Canary:

- Core smoke cases use deterministic stub fixtures.
- Live Tavily canary cases are trace canaries only.

Live Tavily canary may produce `SearchCandidatePacket` and Manager Pass 2 evidence-use trace. It must not create ledger mutation based on live search results.

Phase B-1 live canary uses Tavily search only. Tavily extract is deferred.

Live canary `SearchCandidatePacket` must include `source_quality_label`.

Allowed source quality labels:

- `official`
- `brand_menu`
- `trusted_database`
- `third_party`
- `irrelevant`
- `unknown`

## Core Smoke Cases

Required core smoke cases:

- `我吃了一顆茶葉蛋`
- `我喝了一杯珍珠奶茶`
- `我吃了一個便當`
- `我吃了滷味`
- `我吃了豆干、海帶、貢丸的滷味`
- `珍珠奶茶大概多少熱量？`

The no-mutation query may use read tools to support answer synthesis, but ledger mutation is forbidden.

`我吃了滷味` tests a self-selected basket without listed ingredients. Runtime must block generic DB and Tavily estimate tools for this case.

`我吃了豆干、海帶、貢丸的滷味` tests the contrast case. Listed ingredients should be split into item-level lookup candidates for `豆干`, `海帶`, and `貢丸`.

## ToolLoopTrace Requirements

Every Phase B-1 case must produce a trace with:

- `manager_pass_1`
- `runtime_tool_router`
- `read_tool_executions`
- `packetizer`
- `manager_pass_2`
- `guard`
- `mutation`
- `renderer`

ToolLoopTrace is an acceptance artifact, not an optional debug log.

`runtime_tool_router` must include:

- `requested_read_tools`
- `allowed_tools`
- `blocked_tools`
- `block_reasons`

For `self_selected_basket_without_ingredients`, generic DB and Tavily estimate tools must be blocked with rule `self_selected_basket_without_ingredients_blocks_estimate_tools`.

`mutation` must always be present. No-mutation cases must use:

```json
{
  "mutation_attempted": false,
  "reason": "no_mutation_intent",
  "mutation_result": null
}
```

`renderer.input` must include:

- `allowed_facts`
- `forbidden_claims`
- `item_results`
- `ledger_mutation_result`

`final_response`, when present in trace, must not contain kcal, budget, or logged-status claims that are not supported by `renderer.input`.

## Readiness Gate

`scripts/verify_wave1_phase_b_tool_loop_readiness.py` verifies:

- provider params are logged for Manager Pass 1 and Pass 2
- Manager Pass 1 has no final nutrition truth
- Manager Pass 2 does not mutate
- requested tools and filtered tool plan are traced
- allowed tools, blocked tools, and block reasons are traced
- self-selected baskets without listed ingredients block generic DB and Tavily estimate tools
- read tools and packetizer do not output final truth
- guard runs before mutation
- renderer does not invent facts
- deterministic stub fixtures are not generated by LLM
- Tavily canary has query/search/latency/raw-result/packet trace
- Tavily canary does not mutate ledger
- required core smoke cases are present
- no-mutation trace is explicit rather than omitted
- renderer input includes allowed facts and forbidden claims
- Tavily canary source quality label uses the Phase B-1 enum
- active Phase B surfaces do not depend on legacy manager vocabulary

Forbidden legacy terms: `thread_result`, `target_thread_action`, `clarify_mode`, `commit_status`, `canonical_commit`.

## Exit Criteria

Phase B-1 gate passes only when:

- readiness report has zero blockers
- core stub path demonstrates complete ToolLoopTrace
- live Tavily canary trace is complete or explicitly unavailable without claiming truth
- packetizer produces candidates / hints only
- Manager Pass 2 is the only synthesis owner
- guard runs before mutation
- renderer mirrors allowed facts only
