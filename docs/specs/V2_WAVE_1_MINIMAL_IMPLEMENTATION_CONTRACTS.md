# V2 Wave 1 Minimal Implementation Contracts

## 目的

本文件定義 **V2 Wave 1 的最小 implementation contracts**。

它不是完整 tool spec、observability spec、security spec、memory spec。

它的目標是：

- 補上 coding agent 開始 Phase A / Wave 1 implementation 時最需要的 input/output contracts
- 吃掉 Kiro 提到的最急缺口：tool contract、guardrail、fake-pass prevention
- 避免在開始建置前再新增過多大文件

本文件應由 `V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md` 引用。

---

## Scope

### In scope
- Manager decision envelope
- Phase A minimal outputs
- Evidence-path minimal fields
- Tool/workflow result shape
- Guard result shape
- Trace/artifact minimal shape
- Fake-pass blocking rules

### Out of scope
- Full observability SLO
- Full memory architecture
- Full production security spec
- Full Tavily provider implementation
- Wave 2 / Wave 3 contracts

---

## Contract 1 — Manager Decision Envelope

Manager 不應直接輸出所有 domain 細節。
它應先輸出一個可觀察、可驗證的 decision envelope。

```yaml
manager_decision:
  request_id: string
  interaction_type: intake_logging | same_meal_followup | correction | info_query | other
  target_thread_action: create_new | attach_existing | target_committed | no_meal_mutation
  target_thread_id: string | null
  target_item_candidate: string | null
  clarify_mode: direct_commit | estimate_with_followup | clarify_before_estimate | none
  selected_evidence_path: exact_db | generic_db | tavily_retrieval | ask_user | heuristic_fallback | none
  commit_intent: commit | draft | no_mutation
  required_tools:
    - tool_name
  response_mode: intake_result | clarification | correction_ack | info_answer | degraded_answer
```

### Hard rules
- `info_query` must use `target_thread_action: no_meal_mutation`
- `clarify_before_estimate` must not set `commit_intent: commit`
- `selected_evidence_path: tavily_retrieval` requires retrieval artifact later
- no active body plan + budget question must use `response_mode: degraded_answer`

---

## Contract 2 — Intake / Thread Result

Compatibility note:
- `AttachmentDecision` is the canonical Phase A attachment surface for active runtime ownership.
- `thread_result` remains legacy / compatibility vocabulary for existing Phase A docs, trace presence checks, and older test oracles.
- new runtime logic should not be authored under the `thread_result` name; if emitted, it should be a projection from `AttachmentDecision`.

```yaml
thread_result:
  request_id: string
  thread_id: string | null
  thread_action: created | attached | targeted | none
  thread_status: open | needs_clarification | committed | corrected | superseded | none
  target_item_id: string | null
  meal_version_delta: none | new_version_created | superseded_previous
  non_target_items_preserved: boolean | null
```

### Hard rules
- correction must identify `target_item_id` when possible
- correction must set `non_target_items_preserved: true`
- same-meal followup must not create a new unrelated thread

---

## Contract 3 — Nutrition Evidence Result

所有 DB / Tavily / generic estimate 的結果，都應轉成 evidence packet。

```yaml
evidence_packet:
  request_id: string
  source_type: internal_exact_db | internal_generic_db | tavily | heuristic | user_provided
  source_id: string | null
  source_url: string | null
  matched_entity: string | null
  serving_basis: string | unknown | null
  extracted_kcal: number | null
  extracted_macros:
    protein_g: number | null
    carbs_g: number | null
    fat_g: number | null
  identity_confidence: high | medium | low | unknown
  uncertainty_level: low | medium | high | unknown
  usability: usable_for_exact | usable_for_anchor | unusable
```

### Hard rules
- Tavily snippet cannot become final truth without normalization
- `usable_for_exact` requires matched entity + serving basis + extracted kcal or reliable exact internal DB source
- unknown serving basis must not be classified as `usable_for_exact`

---

## Contract 4 — Estimate Result

```yaml
estimate_result:
  request_id: string
  exactness_posture: exact | anchored_estimate | heuristic_estimate | insufficient_info
  kcal_value: number | null
  kcal_range:
    low: number | null
    high: number | null
  likely_kcal: number | null
  uncertainty_level: low | medium | high
  identity_confidence: high | medium | low
  canonical_commit_allowed: boolean
```

### Hard rules
- `exactness_posture: exact` requires exact evidence
- `insufficient_info` must set `canonical_commit_allowed: false`
- anchored / heuristic estimate may give range, but must not claim exactness

---

## Contract 5 — Commit / Ledger Result

```yaml
commit_result:
  request_id: string
  canonical_commit: boolean
  ledger_delta_kcal: number
  consumed_kcal_before: number | null
  consumed_kcal_after: number | null
  remaining_kcal_after: number | null
  overshoot_amount: number | null
  ledger_source: day_budget_ledger | none
```

### Hard rules
- `canonical_commit: false` requires `ledger_delta_kcal: 0`
- draft must not mutate consumed kcal
- overshoot amount must come from `day_budget_ledger`
- renderer must not invent a different remaining / overshoot value

---

## Contract 6 — Macro Visibility Result

```yaml
macro_visibility:
  request_id: string
  show_macro: boolean
  reason: committed_and_aligned | draft | macro_alignment_fail | high_uncertainty | low_identity_confidence | no_macro_data
```

### Hard rules
- draft => `show_macro: false`
- macro alignment fail => `show_macro: false`
- high uncertainty => `show_macro: false`

---

## Contract 7 — Guard Result

Compatibility note:
- `TransitionGuardResult` is the canonical Phase A guard surface for active runtime ownership.
- `guard_result` remains legacy / compatibility vocabulary for existing Phase A docs, trace presence checks, and older test oracles.
- new runtime logic should not be authored under the `guard_result` name; if emitted, it should be a projection from `TransitionGuardResult`.

All hard guards should return structured results.

```yaml
guard_result:
  request_id: string
  guard_name: string
  verdict: pass | block | downgrade | repair_required
  reason: string
  affected_fields:
    - field_name
```

### Required Wave 1 guards
- no_plan_honesty
- draft_isolation
- evidence_path_honesty
- tavily_candidate_discipline
- macro_visibility_discipline
- overshoot_source_truth
- no_rescue_sneak_in
- no_pass_without_artifact

---

## Contract 8 — Trace / Artifact Result

```yaml
trace_artifact:
  request_id: string
  case_id: string | null
  suite_id: string | null
  artifacts:
    manager_decision: present | missing
    thread_result: present | missing | not_applicable
    evidence_packet: present | missing | not_applicable
    estimate_result: present | missing | not_applicable
    commit_result: present | missing | not_applicable
    guard_results: present | missing
    final_response: present | missing
  retrieval_artifact_path: string | null
  case_level_verdict: pass | fail | not_evaluable | null
```

### Hard rules
- mutating cases require trace artifact
- Tavily cases require retrieval artifact path
- bundle pass requires case-level verdicts
- missing artifact => not evaluable or fail, not pass

---

## Phase A Minimum Contracts

For Phase A, coding agent should implement or expose enough structure for:

- `manager_decision`
- `thread_result`
- `commit_result`
- `guard_result`
- `trace_artifact`

Active runtime canonical Phase A baseline names are:

- `CurrentTurnContextV1`
- `InteractionEvent`
- `AttachmentDecision`
- `TransitionGuardResult`

These are current-turn/runtime diagnostics only. They are not durable memory, cross-session conversation summary, recommendation memory, renderer truth, or Phase C mutation truth.

Phase A does not require full Tavily or full evidence synthesis, but it must not block future Phase B.

---

## Phase A Context Direction Lock

Wave 1 Phase A context engineering should stay `structured-state-first`, `meal-first`, and `staged-retrieval`.

Canonical Phase A context rules:

- Structured state is truth. Transcript is evidence.
- `CurrentTurnContextV1` is short-term, thread-scoped, current-run state only.
- `CurrentTurnContextV1` must not auto-promote into long-term memory.
- transcript may support language interpretation, but it must not override explicit structured target identity or mutation authority
- whole history may be retrievable, but it must not be default prompt injection

Wave 1 Phase A should formalize:

- `chat_freeform` and `ui_anchored_action` as first-class surface modes
- `ContextInjectionPolicy` as the manager-input allowlist / exclusion contract
- `HistoryExpansionRequest` / `HistoryExpansionResult` as typed, bounded retrieval contracts
- `ShadowHypothesis` as tentative runtime-only interpretation

Hard rules:

- `ShadowHypothesis` may guide dialogue, but it must not authorize canonical write
- history expansion should return structured meal candidates and conversation atomic blocks first
- raw transcript snippets are support evidence only, not primary state truth
- no automatic memory promotion inside the Phase A resolver
- explicit UI target identity overrides text-only guessing
- during manager-input rewiring, `phase_a_manager_context_pack` is the forward structured manager-input path
- during the same cutover, `resolved_state` may remain in provider payload for compatibility only, but it must be explicitly marked as compatibility and must not continue as primary structured context truth

### Context Contract Lock

The first multi-turn intake MVP context slice strengthens the existing `CurrentTurnContextV1` and `ManagerContextPack` surfaces. It must not introduce a parallel `ContextSnapshotV1` truth surface unless a future test proves the current contracts cannot safely carry the required bounded fields.

Allowed bounded context fields:

- `current_budget_snapshot`
- `active_body_plan_snapshot`
- `recent_item_targets`
- `target_resolution_posture`
- `context_freshness`

These fields are read-only assembled evidence. They may help the manager interpret the current turn, select among candidate targets, or explain budget posture, but they do not own product truth.

Truth and authority remain:

- meal and item identity: canonical `MealThread` / active `MealVersion` / active item records
- budget math and remaining budget: budget/body read models
- mutation legality: deterministic guards and Phase C UnitOfWork
- transcript/session state: support evidence only

Hard lock:

- context pack must not compute budget truth
- context pack must not infer or invent target ids
- context pack must not authorize mutation
- multi-item ambiguity must remain explicit candidate/ambiguity evidence, not auto-selection

### Runtime Assembly Lock

The second multi-turn intake MVP context slice may connect the contract fields to runtime read models, but only as read-only assembly:

- `resolve_intake_state` may enrich recent committed meal summaries with active item candidate metadata.
- single-item meals may expose stable `meal_item_id` and `canonical_name`.
- multi-item meals may expose `item_candidates` and `item_resolution_source: ambiguous_active_items`.
- multi-item meals must not expose a selected item target or mutation-authoritative `meal_item_id`.
- budget/body snapshots may carry freshness, no-plan posture, overshoot posture, and ledger presence from the owning read models.
- `current_turn_context_assembler` must copy resolver-provided budget/body values; it must not recompute consumed, remaining, active plan, or ledger truth.

Stop conditions:

- schema migration is required
- item target metadata is unavailable without changing persistence truth
- budget snapshot can only be produced by recomputing truth in the assembler
- target ambiguity requires a product decision
- manager runtime mutation behavior would need to change

### Policy-Aware Visibility Lock

The third multi-turn intake MVP context slice may promote selected read-only context fields from `available_if_needed` into `manager_context` when the current turn already has a structured posture:

- follow-up / correction posture may promote `recent_item_targets`, `target_resolution_posture`, `context_freshness`, and `session_atomic_blocks`
- budget-query posture may promote `active_body_plan_snapshot`, `context_freshness`, and `session_atomic_blocks` only when the caller explicitly requests that promotion mode
- default chat context must not keyword-route budget queries or infer new product semantics just to promote fields

Promotion is visibility only. It must not:

- upgrade `final_action`
- authorize mutation
- bypass deterministic guards
- choose among multi-item candidates
- move raw transcript into default manager context

Session atomic blocks are support evidence only. They may preserve current-turn continuity for clarification, pending follow-up, or target references, but canonical meal state, budget/body read models, deterministic guards, and Phase C UnitOfWork always win on contradiction.

Wave 1 remains meal-first:

- primary target objects are `meal_thread`, `meal_item`, and intake pending-followup targets
- budget / body / proposal inputs may remain secondary read-model context or handoff-oriented inputs
- do not turn Phase A into a universal workflow resolver

### Phase A Boundary Lock

Wave 1 Phase A meal-first behavior owner is `intake/application`.

Current type-home posture may remain split for now:

- `runtime/contracts/phase_a.py` may remain the current type home
- `InteractionEvent` / `CurrentTurnContextV1` contracts may remain in runtime contracts during this stage
- meal-first behavior ownership belongs to intake-owned modules

Intake-owned behavior boundaries:

- `current_turn_context_assembler`
  - assembles owner read-model outputs only
  - must not decide attachment
- `attachment_resolver`
  - decides attachment only
  - must not retrieve full history
  - must not mutate state
- `transition_guard`
  - decides transition posture only
  - must not perform persistence
- `context_injection_policy`
  - builds manager context pack only
  - must not decide attachment or mutation

Deleted facade rule:

- the Phase A compatibility facade has been removed
- active callers must import intake-owned Phase A runtime modules directly
- no new compatibility facade may own meal-first semantics, context injection policy, history expansion, shadow hypothesis, or fallback semantics

Sequencing gate for the next split:

- `Slice 1`: active caller reroute + facade shrink
- `Gate`: reroute tests green, active caller import boundary verified, diff review confirms facade shrink
- `Slice 2`: history expansion / shadow hypothesis ownership split
- `Slice 2` must not be mixed into the same slice or PR as `Slice 1`

### Phase A Runtime Enforcement Lock

Runtime enforcement is now active through the Phase A output-honesty boundary. Future slices must treat these as current baseline behavior, not optional diagnostics.

Implemented runtime posture:

- `Slice 3`: pre-manager history expansion is live for bounded meal-first target resolution. It may run at most one expansion before manager. Manager-triggered history expansion remains disabled.
- `Slice 4`: `TransitionGuardResult` is an active pre-persistence mutation gate. Manager final actions must not bypass `answer_only` or `clarify_required` guard verdicts.
- `Slice 5`: final-action persistence effect mapping is intake-owned and centralized in `final_action_mutation_classifier`.
- `Slice 6`: `CommitBoundaryDecision` is an active narrow persistence preflight. It blocks contradictions before persistence and must not rewrite payload or persistence logic.
- `Slice 7`: output honesty is active for structured state, sidecar state summaries, and budget fallback output.
- `Slice 10A`: `ShadowHypothesis` is active as non-authoritative manager payload and trace evidence only. It must use candidate-target vocabulary, carry `mutation_authority=false`, and must not upgrade attachment, guard, final-action, persistence, or memory state.
- `Slice 10B`: chat-visible tentative-understanding dialogue cues are active only for medium-uncertainty, uncertainty-visible shadow hypotheses. They are reply cues only and must not create mutation authority or state truth.
- `Slice 11`: manager-triggered history expansion is active as one bounded local manager tool, `phase_a_expand_history`. Manager may request expansion, but intake owns execution, structured candidate normalization, attachment/guard rerun, trace, and payload refresh.

Owner boundaries:

- `history_expansion_runtime` may activate one bounded pre-manager expansion; `history_expansion_policy` remains policy-only and must not perform retrieval.
- `final_action_mutation_classifier` owns final-action effect semantics. Persistence and guard paths must consume this owner rather than duplicating action sets.
- `commit_boundary_preflight` only blocks persistence contradictions. It must not become a commit engine, renderer, payload rewriter, or persistence owner.
- `boundary_output_honesty` validates normalized structured surfaces first: `state_delta`, sidecar state summary, preflight trace, boundary projection, budget answer contract, and persistence result.
- reply text inspection in `boundary_output_honesty` is fallback safety only for clear forbidden claims. It is not the primary truth mechanism.
- `boundary_output_honesty` is not a renderer. It must reuse existing safe no-commit or degraded-budget wording and must not generate new product copy.
- `shadow_hypothesis_runtime` may create at most one tentative, non-authoritative shadow for manager payload and trace. It must not mutate context, attachment, guard, persistence, reply rendering, or memory.
- `shadow_hypothesis_dialogue` may add a lightweight tentative-understanding cue after output honesty. It is not a mutation gate, not a persistence owner, and not a replacement renderer.
- `history_expansion_manager_runtime` may execute one manager-requested expansion using existing resolved-state surfaces only. It must return structured candidates / atomic blocks first and keep transcript support trace-only.
- `run_intake_manager` may refresh structured Phase A payload fields between rounds after `phase_a_expand_history`, but it must not become a Phase A resolver or own attachment semantics.

Deferred runtime capabilities:

- provider-side history tools and provider/tool-loop protocol redesign remain deferred. Current manager-triggered history expansion is local-only through `phase_a_expand_history`.
- manager-authorized or mutation-bearing `ShadowHypothesis` usage remains deferred. Current live usage is limited to non-authoritative manager context, trace evidence, and guarded dialogue cues.
- full same-truth UI / ledger / Phase C enforcement remains outside this Phase A lock.

---

## Phase B Minimum Contracts

For Phase B, coding agent should implement or expose:

- `selected_evidence_path`
- `evidence_packet`
- `estimate_result`
- Tavily retrieval artifact when called

---

## Phase C Minimum Contracts

For Phase C, coding agent should implement or expose:

- correction `meal_version_delta`
- ledger mutation result
- macro visibility result
- same-truth read result
- full case-level trace artifact

### Phase C Mutation Projection Baseline

`phase_c_trace` is the active diagnostic surface for Phase C mutation outcome and same-truth read projection.

Current active baseline:

- `mutation_outcome` projects existing persistence, state-delta, sidecar, boundary-projection, budget, and macro surfaces into canonical commit, draft, meal-version, ledger-mutation, and macro-visibility statuses.
- `same_truth_read_result` compares structured surfaces and reports `aligned`, `contradictory`, or `not_applicable`.
- missing Phase C values must be emitted as `not_available`, not coerced to `false`.
- contradictions must be reported through consistency flags, not fixed by the projection helper.

Hard boundaries:

- Phase C projection must not rewrite persistence, ledger state, sidecar output, reply text, manager final action, or Phase A guards.
- Phase C projection must not compute new ledger or macro truth; it may only read existing structured owner outputs.
- Phase C projection must keep `phase_c_trace` separate from `phase_a_trace`.
- Phase C enforcement and UI same-truth remain deferred.

### Phase C Structured Same-Truth Closure Gate

`same_truth_closure_gate` is active as hard-fail evidence inside `phase_c_trace`.

Gate output shape:

```yaml
same_truth_closure_gate:
  checked: true
  status: pass | flagged | hard_fail
  failure_family: phase_c_same_truth_contradiction | null
  consistency_flags:
    - string
  compared_surfaces:
    - string
```

Current active baseline:

- the gate compares structured runtime surfaces only: `persistence_result`, `state_delta`, sidecar state summary, `phase_c_trace`, and already-available `state_after.current_budget_view`
- contradictions may add `phase_c_same_truth_contradiction` to `hard_fail_conditions`
- the gate must not rewrite, repair, or block runtime output
- missing values remain `not_available` or trace flags; the gate must not invent ledger, macro, or read-model truth

Still deferred:

- full UI same-truth
- later-query same-truth
- runtime repair / output blocking based on Phase C contradictions
- owner-resolution when two canonical owners disagree

### Live Eval Readiness Harness Lock

Slice 14 aligns live eval harnesses with the active Phase C trace surface before formal live readiness claims.

Live testing ladder:

- L0 deterministic regression: local unit / integration / closure gates only.
- L1 local diagnostic live smoke: server `/ping` is healthy and live scripts may run for evidence, but this is not a bundle or Wave 1 readiness claim.
- L2 bundle live readiness: Bundle live runners must use an explicit `--base-url`, record server ping / provider readiness, and verify Phase C same-truth closure evidence where Bundle 2 mutation occurs.
- L3 founder / human E2E: allowed only when bootstrap verdict inputs are complete, including runner pass, coverage complete, founder realism pass, architecture purity pass, encoding pass, text integrity healthy, and trace roundtrip.
- L4 provider / Tavily / B2 canary: remains a separate trace-first canary path, not a reason to bypass Phase A / Phase C closure.

Bundle 2 mutating live cases must check structured Phase C evidence:

- `phase_c_trace` exists.
- `same_truth_closure_gate.checked=true`.
- `same_truth_closure_gate.status` is not `hard_fail`.
- `hard_fail_conditions` does not contain `phase_c_same_truth_contradiction`.
- `mutation_outcome` and `same_truth_read_result` are present or explicitly `not_available`.

Hard boundaries:

- `Bundle 1` / `Bundle 2` names in live runner files remain acceptance-package compatibility vocabulary, not implementation order or capability owner truth.
- live eval readiness must prefer structured trace / response surfaces over reply-text assertions.
- a hard-fail Phase C gate may be reported as diagnostic evidence, but it must fail bundle readiness.
- live scripts must report `live_test_mode`, `base_url`, `server_ping_status`, `provider_readiness`, `phase_c_gate_status`, and `readiness_claim_scope`.
- default localhost script settings are diagnostic unless `--base-url` is explicitly provided for readiness.
- Slice 14 does not change runtime behavior, provider adapters, Phase C enforcement, UI same-truth, B2 rollout, or `ShadowHypothesis` authority.

### Live Diagnostic Evidence And Product Semantics Decision Pack Lock

The next live-readiness macro-batch may collect evidence and prepare product decisions, but it must not canonize unresolved product semantics.

The batch has three separate outputs:

- live diagnostic report: records live preflight, provider readiness, Phase C gate status, and readiness claim scope.
- B2 live LLM diagnostic lane: records packet-based synthesis candidate evidence only; it must not create ledger truth, mutation authority, source-priority truth, or product semantic truth.
- product semantic decision pack: records pending decisions, options, recommendations, and affected surfaces for user approval.

Diagnostic verdict categories are:

- `diagnostic_observation`: useful evidence, not a blocker by itself.
- `readiness_blocker`: technical or trace evidence blocks readiness, such as Phase C hard fail or provider/schema failure.
- `product_decision_required`: product semantics require explicit user approval before becoming canonical.

Hard boundaries:

- pending product decisions must not be written into canonical behavior, guard behavior, prompt policy, test oracles, or copy without explicit approval.
- the decision pack is not a canonical spec.
- B2 live LLM diagnostic output is candidate evidence only and must remain non-mutating.
- Bundle names remain acceptance-package compatibility vocabulary, not implementation order or capability owner truth.

---

## Fake Pass Blocking Rules

Do not claim pass if:

1. response says logged but `canonical_commit` / ledger artifact missing
2. Tavily called but retrieval artifact missing
3. snippet used as final exact truth
4. correction modifies unrelated item
5. draft changes ledger
6. chat and UI numbers disagree
7. bundle report lacks case-level verdicts
8. fix only targets case id / benchmark phrase

---

## How to Use With Coding Agent

Coding agent should read this file after:

1. `V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`
2. `V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`
3. `V2_WAVE_1_CAPABILITY_MICRO_SUITES.md`
4. `V2_WAVE_1_MICRO_SUITE_CASES.md`

This file answers: what minimum structured outputs must exist so the cases can be verified?

---

## 歷史

- 2026-04-24: v1 初始版本，建立 Wave 1 最小 implementation contracts，避免在建置前產出過多大型 production specs
