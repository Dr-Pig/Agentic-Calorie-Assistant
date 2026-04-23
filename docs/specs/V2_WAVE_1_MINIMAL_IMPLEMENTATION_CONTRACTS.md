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

Phase A does not require full Tavily or full evidence synthesis, but it must not block future Phase B.

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
