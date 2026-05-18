# Current Shell Agentic EDD Standard

Status: active quality standard

Owner: SharedCurrentShell

Scope: Current Shell v1 Manager Runtime, AppShell browser E2E, FoodDB/WebSearch evidence seams

Golden Set is a measuring instrument, not an architecture source. It measures whether product behavior, Manager trace, mutation/read-model truth, UI state, and response quality match the canonical contracts. It must never become a prompt patch source, deterministic routing table, or fixture-shaped oracle.

## Required EDD Loop

Use this loop for every non-trivial Manager/AppShell/FoodDB evidence failure:

1. classify failure family
2. inspect trace owner
3. confirm product truth
4. fix capability mechanism
5. add holdout / variants
6. rerun targeted E2E
7. rerun full E2E

If full E2E fails, repeat from failure-family diagnosis. Do not patch the literal case.

## Fake-Pass Blockers

These patterns are blockers:

- runner infers intent, action, attach target, workflow effect, or response meaning from raw text
- deterministic verifier supplies a missing semantic decision
- fixture label decides workflow
- fixture output decides final answer meaning
- case ID changes runtime behavior
- isolated pass is reported as full-suite pass
- replay pass is reported as browser/UI pass
- recorded candidate packet is reported as live tool pass
- prompt patch directly targets a single Golden Set utterance
- response text is accepted while trace path is wrong
- UI displays correct-looking facts from frontend math

## Pass Claim Requirements

Every pass claim must state:

- suite/case IDs
- entrypoint
- provider mode
- live LLM flag
- live tool flag
- browser/UI flag
- artifact path
- failed count
- allowed claim
- forbidden claim

Example claim boundaries:

| Evidence | Allowed claim | Forbidden claim |
| --- | --- | --- |
| isolated case rerun | case probe passed once | full suite passed |
| replay trace | offline replay passed | browser self-use passed |
| browser scripted fixture | UI wiring projection passed | live LLM semantic behavior passed |
| recorded WebSearch packet | candidate packet grading passed | live Tavily behavior passed |
| live Tavily call | retrieval adapter produced live result | result content was deterministic oracle |

## Live Tool And Live Model Policy

Live LLM and live tool tests are necessary for closeout, but not every narrow PR must call them. A slice may be offline if it is locking a contract, schema, prompt section, or runner integrity rule.

When live tools are used:

- require `live_tool flag: true`
- record provider/adapter identity
- do not require Tavily or any live provider to return a specific snippet
- grade system response to volatile retrieval, not provider output determinism
- use recorded packets only for deterministic replay, not as live E2E proof

When live LLM is used:

- require `live LLM flag: true`
- record model profile and prompt versions
- grade trace path before response quality
- treat stochastic isolated pass as insufficient for full closeout
- keep Kimi or other models non-blocking until model profile promotion

## Failure-Family Diagnosis

Each failure must be classified before fixing:

- prompt architecture drift
- semantic ownership violation
- missing context packet field
- missing active workflow state
- stale or unreconstructable context
- target candidate insufficiency
- tool selection error
- tool result packet insufficiency
- guard legality failure
- mutation/read-model sync failure
- response-basis mismatch
- UI same-truth mismatch
- latency/call topology regression

The fix must target the family mechanism. If the change only makes the literal input pass, it is not an EDD fix.

## Trace As Repair Router

Trace must identify which layer should be fixed before code changes begin.

Layer map:

- `L1_prompt_architecture`: prompt version, section hashes, output schema hash, provider profile
- `L2_context_packet`: context generation, context packet hash, hard pins, active workflow, target candidates, queue state
- `L3_manager_semantics`: intent, active workflow resolution, slot updates, attach target, final action
- `L4_tool_selection`: requested tools, skipped-tools reason, tool args
- `L5_evidence_packets`: FoodDB/WebSearch hit or miss, source posture, admissibility, macro evidence
- `L6_validator_guard`: schema valid, source eligible, mutation allowed, repair requested
- `L7_mutation_read_model`: version transition, ledger recompute, active version only
- `L8_response`: final response basis, zh-TW natural wording, no debug/internal text
- `L9_ui_same_truth`: Chat/Today/Body/Feedback/Review match backend truth

Routing examples:

- wrong attach/correction -> `L2_context_packet` or `L3_manager_semantics`
- wrong WebSearch call -> `L4_tool_selection` or `L5_evidence_packets`
- fallback kcal or invented macro -> `L5_evidence_packets` or `L6_validator_guard`
- illegal commit -> `L6_validator_guard` or `L7_mutation_read_model`
- ugly or contradictory answer -> `L8_response`
- UI mismatch -> `L9_ui_same_truth`
- stochastic isolated pass/fail -> `L1_prompt_architecture`, `L2_context_packet`, schema, or provider profile

Do not infer the repair target from the final answer alone.

## Prompt Architecture Gate For EDD

Golden Set EDD must not use generic prompt line count as the primary prompt quality gate.

Required prompt-source checks:

- stable prompt sections have owner, cache role, section hash, and provider-overlay prohibition
- dynamic context is delivered through runtime payload/context packet, not interpolated into the stable prefix
- Golden Set literal utterances are absent from stable prompt source
- `if user says X then Y` case-routing patches are absent from stable prompt source
- prompt cache metrics are provider-reported only; missing cache metrics remain unknown, not zero

Executable gate:

- `scripts/check_manager_prompt_architecture_gate.py`

This gate protects against prompt-patch overfitting while allowing a long prompt source when it is sectioned, versioned, traceable, and cache-boundary-safe.

## Reference-Calibrated Implementation Standard

Code references are required for implementation-sensitive mechanisms.

Before broad EDD, compare the mechanism against code references:

- Codex context/history/version/diff/reinjection mechanisms
- Codex tool router/registry/orchestrator/dispatch trace mechanisms
- cc-haha stable prompt prefix, dynamic boundary, prompt section memoization, and cache-breaking annotation
- cc-haha tool-result budget, microcompact/autocompact, and queued command mechanisms

Reference code informs implementation shape. It does not override this product's domain ownership: nutrition truth remains FoodDB/evidence/read-model owned, and semantic food decisions remain Manager-owned.

## Development Order

Use this order when a failure family is broad:

1. inspect existing trace/logs and record failure family
2. inspect code reference for the mechanism class
3. define ideal mechanism and ownership
4. implement mechanism skeleton first
5. run targeted E2E for the failing family
6. add one to three holdouts for that family
7. run full Current Shell browser E2E

This order is mandatory when failures involve multi-turn context, prompt architecture, tool dispatch, retrieval, mutation boundaries, or fake-pass risk.
