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

## Reference-Calibrated Implementation Standard

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
