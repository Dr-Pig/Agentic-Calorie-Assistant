# Manager Runtime Prompt Architecture And Ownership Spec

Status: active source-of-truth addendum

Owner: ManagerRuntime

Scope: Current Shell v1 desktop self-use Manager agent

Reference identity:

- OpenAI Codex repo: `https://github.com/openai/codex.git`
- Inspected Codex commit: `a2802480211a6b28f3c00c0ca9bbb2838503eba4`
- Local Claude Code-style archive: `C:\Users\User\Desktop\agent runtime\cc-haha-main.zip`

This spec defines how Manager Runtime prompt, context, tool execution, and deterministic validation must be arranged before EDD work tries to make individual Golden Set cases pass. The goal is stable product behavior, not prompt patching.

## 0. Model-Independent Contract And Provider Profile Overlay

The product contract is model-independent. Grokfast, Kimi, OpenAI, or any later provider may require a different transport/profile overlay, but they must not change product semantics.

Provider profile overlays may tune only:

- structured-output strictness and repair attempt count
- timeout, retry, and backoff policy
- max context budget
- prompt wording density
- tool-call formatting tolerance
- response naturalness tuning
- latency and cost budget

Provider profile overlays must not change:

- whether exact items can use model memory as official truth
- whether generic estimates may invent macro facts
- whether deterministic code may decide follow-up need
- whether WebSearch candidates become runtime truth
- whether UI can compute kcal, macro, or remaining budget
- mutation legality

Generic-food policy:

- Exact item: model built-in knowledge may recognize an entity or lookup need, but it cannot become official kcal, macro, source, or label truth.
- Generic food with a FoodDB anchor: FoodDB anchor wins; model may help interpret portion language and uncertainty, but must not override the anchor as truth.
- Generic food without an adequate FoodDB anchor: Manager may use model generic prior only as an uncertain rough range. It must label the basis as a generic prior and must not claim official/exact/source-backed or macro truth.

## 1. Prompt Is Not Product Truth

Prompt text is a delivery mechanism for canonical runtime contracts. It may explain the role, expose tools, describe evidence policy, and instruct response style, but it must not become a hidden source of product truth.

Prompt sections must map to an owner and source of truth:

| Section | Owner | Cache role | Allowed change type | Source of truth | Trace hash |
| --- | --- | --- | --- | --- | --- |
| stable role and ReAct loop | ManagerRuntime | stable prefix | contract wording only | this spec and `L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md` | required |
| semantic ownership boundary | ManagerRuntime | stable prefix | invariant update only | `APP_ENGINEERING_OPERATING_ENTRY.md` | required |
| tool/result contract | ManagerRuntime + domain tool owner | stable prefix | schema/tool registry update | tool schemas and runtime contracts | required |
| evidence policy | FoodDB/WebSearch owner + ManagerRuntime | stable prefix | posture policy update | FoodDB/WebSearch packet contracts | required |
| response policy | ManagerRuntime | stable prefix | rubric update | Golden Set response contract | required |
| optional examples | ManagerRuntime | dynamic or late stable section | non-normative examples only | eval failure-family notes | required |
| current turn/context/evidence packets | runtime context owner | dynamic suffix | per-turn data only | runtime state/read models/tool packets | required |

## 2. Prompt Section Architecture

System prompt must be sectioned, versioned, and hashed. A prompt change must be trace-visible through:

- `manager_prompt_version`
- `manager_prompt_section_hashes`
- `tool_surface_version`
- `output_schema_version`
- `prompt_cache_profile`

The required section order is:

1. stable role / Manager ReAct loop
2. semantic ownership boundary
3. tool/result contract
4. evidence policy
5. response policy
6. optional examples
7. dynamic context suffix: current turn, context packet, read-model summaries, evidence packets, previous tool packets

Dynamic request values must not be interpolated into the stable prefix. If a value changes per user, date, session, FoodDB result, provider, or tool response, it belongs in the dynamic suffix or a model-visible context packet.

## 3. Prompt Cache Rule

Prompt cache optimization must follow product architecture rather than drive it:

- static prefix first
- dynamic context last
- tool order stable
- schema order stable
- prompt section hashes trace-visible
- provider-reported cached tokens are the only cache truth
- missing provider cache usage is `unknown`, not `0`, not failure
- do not move semantic rules into dynamic sections to chase cache hits

This follows the cc-haha mechanism in `cc-haha-main/src/constants/prompts.ts`, where `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` separates static/global prompt blocks from session-specific sections, and `cc-haha-main/src/constants/systemPromptSections.ts`, where `systemPromptSection(...)` is memoized while `DANGEROUS_uncachedSystemPromptSection(...)` requires an explicit reason because it can fragment the prompt cache.

Our parallel mechanism is `app/runtime/agent/manager_prompt_layer_contract.py`, which already tracks prompt layer identity. Future prompt work must extend that registry rather than adding free-form prompt strings.

## 3A. Prompt Source Gate Is Not A Line-Count Gate

Prompt source files are governed by prompt architecture gates, not by generic fat-file line count as the primary quality signal.

The normative basis is:

- OpenAI Prompt Caching: cache hits require exact prefix matches; static/repeated content belongs at the beginning, dynamic user-specific content belongs at the end; usage `cached_tokens` is the provider-reported cache truth.
- OpenAI Prompt Engineering / Reasoning guidance: instructions should be clear, direct, delimited, and specific; examples should align with instructions and not contradict them.
- Anthropic Prompt Caching: static content such as tools, system instructions, context, and examples should be placed before dynamic content; explicit cache breakpoints should end reusable content.
- LangSmith Prompt Management: prompts are versioned assets with owners, commit history, environments, and promotion/rollback semantics.

Therefore:

- prompt files may be long when they are sectioned, owner-mapped, hash-traced, and cache-boundary-safe
- line count is advisory for prompt sources, not the acceptance gate
- Python runtime files that assemble context, validate contracts, execute tools, or mutate state remain subject to the normal fat-file and responsibility-boundary gates; only prompt source quality is judged primarily by the prompt architecture gate
- compiled/generated prompt artifacts may exceed normal file-size expectations if they are not hand-edited
- stable prompt source must not contain Golden Set literal utterances
- stable prompt source must not contain English or zh-TW `if user says X then Y` routing patches, including `如果使用者說 X` or `當用戶輸入 X` variants
- stable prompt source must not contain dynamic runtime values such as user IDs, trace IDs, dates, session IDs, FoodDB packets, WebSearch extracts, or queued inputs
- provider profile overlays must not change stable prompt sections or product semantics

Executable gate:

- `scripts/check_manager_prompt_architecture_gate.py`

That gate checks section owner/hash/cache role, provider overlay immutability, absence of Golden Set literal utterances, absence of English/zh-TW `if user says X` routing patches, and absence of dynamic runtime values in stable prompt source. It intentionally does not fail solely because a prompt file is long.

Manager prompt content files under this gate:

- `app/runtime/agent/manager_system_prompt.py`
- `app/runtime/agent/manager_user_facing_reply_prompt.py`

Each stable prompt section must expose machine-readable architecture metadata:

- `section_kind`
- `owner`
- `cache_role`
- `allowed_change_type`
- `source_of_truth_refs`
- `dynamic_content_allowed=false`
- `provider_overlay_allowed=false`
- `sha256`

Prompt section metadata is a gate input, not documentation decoration. A section with no source-of-truth mapping or no allowed change type is not reviewable enough for Manager Runtime prompt work.

## 4. Case-Style Prompt Patch Ban

Golden Set cases are examples of failure families, not routing rules.

Any case-style patch that turns a literal user phrase into a hidden routing rule is forbidden.

Forbidden:

- adding the exact Golden Set utterance to system prompt
- adding `if the user says X then do Y`
- using case IDs, fixture labels, or manifest titles in prompt text
- adding a one-off prompt sentence for a single failing food
- letting examples define workflow effect

Allowed:

- family-level policy such as "estimate-basis inquiries answer basis and do not mutate"
- schema clarification that makes invalid mixed-branch outputs impossible or rejectable
- examples marked as non-normative and paraphrased away from Golden Set literal text
- response style examples that do not decide routing or mutation

## 5. LLM / Deterministic Ownership Boundary

LLM / Manager owns:

- composition sufficiency
- estimability
- whether to ask follow-up
- whether to call WebSearch
- exact/generic/component/basket posture
- attach target
- correction/removal target
- final workflow action
- user-facing response meaning

Deterministic code may only:

- validate schema
- validate source eligibility
- validate target existence / uniqueness
- enforce mutation legality
- hide unsupported kcal/macro/source facts
- reject/downgrade unsafe output
- request one bounded repair

Deterministic code must not:

- inspect raw user text or food name to decide semantic route
- classify a meal as unestimable before Manager output exists
- decide follow-up necessity
- decide WebSearch need
- create fallback kcal/macros
- rewrite Manager action to make a test pass

If the Manager output is unsafe or illegal, deterministic code must reject or repair after the Manager decision, not preempt it with a hidden semantic router.

## 6. Context Engineering Mechanism

Current Shell context pack must separate:

- current turn
- session summary
- pending follow-up
- recent committed meals
- active meal state
- target candidates
- read-model summary
- evidence packets
- feedback/review linkage

Rules:

- context supplies candidates only
- context does not choose final intent
- context does not choose target
- context does not infer correction from keywords
- session memory is not full transcript replay
- compaction must preserve pending state, active meal, tool/result pairing, and unresolved user intent

Adopted Codex mechanisms:

- `codex-rs/core/src/context_manager/history.rs`: `ContextManager` carries `history_version` and a `reference_context_item`; rollback/compaction changes bump history and can force full context reinjection instead of diffing against stale state.
- `codex-rs/core/src/context_manager/updates.rs`: `build_settings_update_items(...)` diffs the previous context snapshot against the next turn context and emits model-visible context update items.
- `codex-rs/core/src/codex_thread.rs`: thread APIs can inject session-prefix items and queue response items for the next turn without treating every injected item as a new semantic user turn.

Current Shell adoption:

- every Manager turn trace should carry `context_generation`
- every Manager turn trace should carry `context_packet_hash`
- every open multi-turn workflow should carry `active_workflow_id`
- compaction/history trimming must set `context_reinjected_after_compaction_or_history_trim`
- context packets should be reproducible from canonical state and read models, not from raw transcript guesses

## 7. ReAct Loop / Tool Runtime Contract

The runtime loop is:

```text
turn input
→ context pack
→ Manager pass
→ requested tool calls
→ runtime filters/executes tools
→ compact tool packets
→ Manager next pass
→ guard validation
→ mutation/read-model update
→ final response
→ UI same-truth
→ trace/review/feedback linkage
```

`pass1/pass2` is the minimum loop shape, not a separate architecture. More tool rounds are allowed only when trace shows bounded need.

Ownership:

- tool choice is Manager-owned
- tool execution is runtime-owned
- tool result truth is tool/domain-owned
- mutation legality is guard/domain-owned
- final response is response composer-owned, not debug renderer-owned

Adopted Codex mechanisms:

- `codex-rs/core/src/tools/orchestrator.rs`: centralizes approval, sandbox selection, execution attempt, and retry semantics without owning product semantics.
- `codex-rs/core/src/tools/router.rs` and `codex-rs/core/src/tools/registry.rs`: separate model-visible tool specs from dispatch registry.
- `codex-rs/core/src/tools/tool_dispatch_trace.rs`: records tool invocation/result lineage separately from the agent's final conclusion.

Current Shell adoption:

- `ToolDispatchTrace` equivalent must map Manager-requested tool call, runtime-filtered plan, executed tool, compact packet, and pass2 basis.
- FoodDB and WebSearch packets must not become mutation authority.
- WebSearch raw snippets and candidate packets remain candidate evidence until the Manager and evidence policy accept a turn-scoped packet.
- current-loop tool availability is runtime-owned: if the loop already has valid nutrition evidence, `estimate_nutrition` must leave the next pass's dynamic `available_tools` list, while the existing tool result remains visible as evidence for Manager final mapping.

## 8. Reference Mechanisms We Adopt / Do Not Adopt

Adopt:

- stable/dynamic prompt boundary
- section-level prompt registry
- trace hash per prompt section
- prompt cache identity
- tool schema stability
- centralized tool dispatch
- context history versioning
- context diff/reinjection
- compaction as normal runtime, not emergency only
- queued user input
- evidence-scope pass claims
- failure-family diagnosis before patching

Do not adopt blindly:

- coding-agent-specific approval UX
- subagent/fork orchestration as default product pattern
- codebase memory as nutrition/product memory
- terminal-first UI assumptions
- provider-specific cache APIs as product truth
- case-specific prompt examples as routing rules

## 9. Required Implementation Order

Before another broad EDD run:

1. lock prompt section registry, stable/dynamic boundary, and trace hashes
2. lock LLM/deterministic ownership guards
3. lock context lineage fields and active workflow state packet
4. lock tool dispatch trace shape
5. rerun targeted failing families
6. add a small holdout set for those families
7. rerun full browser E2E

If a case fails, return to failure-family diagnosis. Do not patch the literal utterance.
