# V2 Wave 1 Coding Agent Bootstrap

## 目的

本文件是 coding agent 執行 **V2 Wave 1** 工作時的 phase-specific bootstrap。

使用方式：

> Start here. Do not begin implementation from legacy Bundle Version 1 / Bundle Version 2 cases directly.

進入本文件前，先讀：

`docs/specs/APP_V2_ENGINEERING_OPERATING_ENTRY.md`

本文件不是完整規格本身，而是：

- reading order
- execution order
- anti-fake-pass rules
- Wave 1 implementation guardrails
- micro-suite-first working protocol

coding agent 應先讀 product-wide operating entry，再讀本文件，之後依本文件列出的順序閱讀必要文件。

---

## 核心指令

Wave 1 的目標不是把 legacy Bundle Version 1 / Bundle Version 2 直接 patch 到 green。

Wave 1 的目標是建立：

> plan-or-fallback + meal-thread resolution + evidence-grounded nutrition resolution + ledger sync + same-truth surfaces + trace/artifact governance

請依 system-capability build order 建置，而不是依 product journey 或 bundle case 順序建置。

---

## 必讀文件順序

請按順序閱讀，不要跳過。

### 0. Product-wide operating entry
`docs/specs/APP_V2_ENGINEERING_OPERATING_ENTRY.md`

目的：在進入 Wave 1 phase-specific build order 前，先鎖定 product-wide anti-drift rules、owner docs、required planning fields、forbidden shortcut patterns。

### 1. Execution overview
`docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md`

目的：理解 manager style、domain workflows/tools、wave plan、test layering。

### 2. Wave 1 deep spec
`docs/specs/V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`

目的：理解 Wave 1 closure、must-deliver capabilities、must-not-sneak-in boundaries、state transitions、guards、harness contract。

### 3. Micro-suite design
`docs/quality/V2_WAVE_1_CAPABILITY_MICRO_SUITES.md`

目的：理解 Wave 1 system capabilities 如何拆成 micro-suites。

### 4. Micro-suite MVP cases
`docs/quality/V2_WAVE_1_MICRO_SUITE_CASES.md`

目的：理解第一批應實作與驗證的 case-level contracts。

### 5. Minimal implementation contracts
`docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md`

目的：理解 manager decision envelope、tool/workflow result shape、guard result、trace/artifact 最小輸出契約。

### 6. Failure taxonomy
`docs/quality/V2_FAILURE_TAXONOMY.md`

目的：修任何 failure 時，必須標記 primary failure family。

### 7. Grading rubric
`docs/quality/V2_GRADING_RUBRIC.md`

目的：理解 hard fail、soft pass、quality review、founder review 的分層。

### 8. Foundation patch addendum
`docs/quality/V2_FOUNDATION_DOCS_EXECUTION_PATCH.md`

目的：補充 evidence-path、Tavily、fake-pass、tool-correctness 的新增規則。

### 9. Manager-style E2E diagnostics
只在 micro-suite phase 有初步進展後閱讀與執行目前的 Manager-style diagnostics / Founder E2E harness。

目的：作為 active runtime acceptance evidence，不作為 build order，也不引用已刪除的 legacy Bundle oracle。

---

## Wave 1 implementation order

請依下列順序建置與驗證。

## Phase A — Routing & Boundary
先實作與驗證：

1. MS1 Intent / Thread Resolution
2. MS2 Clarify Mode Selection
3. MS7 Draft vs Commit Boundary
4. MS14 No-Plan Fallback Honesty

要求：
- 先讓 system routing / state boundary 穩定
- 不要先 patch Bundle 2 response wording
- 至少暴露 `manager_decision`、`thread_result`、`commit_result`、`guard_result`、`trace_artifact` 的必要欄位

Phase A naming note:
- active runtime canonical names may use `CurrentTurnContextV1`、`InteractionEvent`、`AttachmentDecision`、`TransitionGuardResult`
- `thread_result` / `guard_result` may remain only as legacy Phase A compatibility vocabulary in docs, traces, or older test expectations
- do not create new runtime owner logic under the old `thread_result` / `guard_result` names

Phase A context direction note:
- keep Phase A `structured-state-first`, not transcript-first
- treat structured current-turn state as truth and transcript as support evidence
- `chat_freeform` and `ui_anchored_action` should be treated as different surface modes
- whole history may be retrievable through a bounded typed seam, but it must not become default prompt injection
- tentative interpretation may guide dialogue, but it must not authorize canonical write

Phase A runtime enforcement status:
- runtime enforcement through output honesty is now active
- pre-manager history expansion, transition-guard preflight, final-action effect ownership, commit-boundary preflight, and output-honesty guard are the current Phase A baseline
- `ShadowHypothesis` payload/trace activation is active as non-authoritative manager context only
- `ShadowHypothesis` dialogue cues are active only as medium-uncertainty tentative-understanding reply cues
- manager-triggered history expansion is active only as the bounded local `phase_a_expand_history` manager tool; intake owns execution, normalization, attachment/guard rerun, and trace
- Phase C projection baseline is active through `phase_c_trace` for mutation outcome and same-truth diagnostic reads
- Phase C structured same-truth closure gate is active as trace / `hard_fail_conditions` evidence, not runtime repair
- next runtime work must not bypass these guards or duplicate their ownership
- provider-side history tools and provider/tool-loop protocol redesign remain deferred
- mutation-authoritative or manager-triggered `ShadowHypothesis` usage remains deferred

Phase A closure evidence gate:
- before planning provider-side history tools, mutation-authoritative `ShadowHypothesis`, or deeper B2 rollout, run `tests/test_phase_a_runtime_closure_gate.py`
- this gate is capability evidence only; it is not a legacy acceptance-package or Wave 1 readiness claim
- prefer structured output assertions; reply-text assertions should only check forbidden concrete claims

Live eval readiness ladder:
- local diagnostic live smoke may start after server `/ping` is healthy, but it is not a readiness claim
- live readiness requires explicit `--base-url`, server ping / provider readiness metadata, and deterministic runner reports
- mutating live cases must verify `phase_c_trace.same_truth_closure_gate` and fail readiness on `phase_c_same_truth_contradiction`
- founder / human E2E readiness requires the bootstrap verdict inputs, including runner pass, coverage complete, founder realism pass, architecture purity pass, encoding pass, text integrity healthy, and trace roundtrip
- provider / Tavily / B2 live canaries remain trace-first diagnostics and must not bypass Phase A / Phase C closure

Founder live strictness / model inversion note:
- first-pass strictness must target invariant compliance, not provider-specific trace imitation
- 3 serialized GrokFast strict live runs prove single-profile diagnostic stability only; they do not prove model-inverted shadow readiness
- model diversity evidence is required before a live diagnostic can become a pre-shadow candidate
- pre-shadow candidate planning requires repeated strict evidence plus provider robustness evidence from at least one alternate capable model/profile, or an explicit `model_diversity_missing` blocker
- shared manager contracts may define schema and invariant requirements; provider profiles own transport and prompt rendering adaptation
- if an alternate model regresses because the shared prompt/contract is GrokFast-shaped, classify `contract_overfit_risk` and split shared invariant policy from provider-specific rendering

Accurate Intake live sidecar anti-overfit note:
- live full-suite failure unlocks attribution/audit only
- live failure alone cannot justify prompt/schema/contract hardening
- prompt, schema, or Manager contract hardening must be backed by a canonical product rule, legal-flow matrix, holdout tests, no raw-text routing risk, no high provider-overfit risk, and no broken legal flows
- `contract_hardening_debt` blocks private self-use candidate preparation even when live evidence is otherwise clean
- basket holdout and target-evidence guards must be green before further live full-suite hardening proceeds

Post-PR88 phase checkpoint:
- GrokFast remains a diagnostic contract probe only
- PR85-PR88 establish portable harness governance, not live closure
- stop GrokFast full-suite hardening and return to the Accurate Intake local self-use shell
- the next live provider work should be a future target-model diagnostic slice after local self-use shell evidence is green and a human explicitly chooses the target profile
- this checkpoint is not a private self-use approval and does not claim product readiness, model portability, production model selection, shadow/canary, or mutation rollout

Slice 14 live harness status:
- live scripts report `live_test_mode`, `base_url`, `server_ping_status`, `provider_readiness`, `phase_c_gate_status`, and `readiness_claim_scope`
- default localhost script runs are diagnostic unless `--base-url` is explicitly supplied
- any historical bundle names in active runtime files remain compatibility vocabulary, not implementation order or capability owner truth
- hard-fail Phase C evidence may be recorded for diagnosis, but it blocks bundle readiness
- this status does not change runtime behavior, provider adapters, Phase C enforcement, UI same-truth, B2 rollout, or `ShadowHypothesis` authority

Wave 1 current mainline rebaseline:
- Current Wave 1 mainline is B2 / Phase B semantic closure.
- Completed Context Engineering, Phase A, Phase C, and live harness work is now baseline guardrail support, not the current mainline.
- No further Phase A, Phase C, or live harness expansion should proceed unless it removes a proven blocker for B2 semantic closure.
- The next mainline order is B2 final mapping closure, B2 evidence / packet / synthesis contract alignment, deterministic B2 semantic closure tests, packet-based B2 live LLM diagnostic, then exact-brand web trace-only canary.

Product semantic decision pack status:
- the live diagnostic macro-batch may collect evidence and prepare pending product decisions
- the decision pack is not a canonical spec
- canonical B2 product-semantic decisions live in `docs/specs/WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER.md`
- pending product decisions must not be converted into guard behavior, test oracle truth, prompt policy, copy, or runtime semantics without explicit user approval
- User-approved product semantic decisions supersede stale eval expectations; when they conflict, realign the case/oracle/report instead of forcing runtime to satisfy stale fixture shape
- pearl milk tea missing sugar/size is approved as logged estimate plus follow-up; follow-up is a precision/refinement request and not a hidden commit gate
- report verdicts should distinguish `diagnostic_observation`, `readiness_blocker`, and `product_decision_required`
- B2 live LLM diagnostic output may be packet-based synthesis candidate evidence only; it must not become ledger truth, mutation authority, source-priority truth, or product semantic truth

### Phase A extra boundary: ownership selection

Before Phase B evidence-stack work grows, keep manager contract selection and provider/profile selection behind a single trace-visible ownership surface.

At minimum, selection state must identify:

- `case_family`
- `manager_role`
- `probe_mode`
- `payload_id / constraint_id / schema_branch`
- `provider_profile_id` when model routing is involved

Selection must be driven by raw state, not prompt wording. B-1 `case_id` usage is allowed only when it is explicitly marked as local diagnostic debt.

### Pre-slice architecture triage

Before any Wave 1 task proceeds, planning and review for the slice must inspect:

- current task architecture impact
- dependency-direction impact
- whether a thin infrastructure seam should be built first
- whether existing local helper or policy code would become accidental ownership if reused directly

Slice framing must identify:

- `slice_goal`
- `mainline_gate_protected`
- `owners_touched`
- `dependency_direction_changed: true|false`
- `observed_debt_or_optimization`
- `required_infrastructure_gap`
- `decision: build_now | thin_seam_now | defer_with_reason`
- `forbidden_promotions`
- `verification_gate`

For B-2 work:

- if `B2-004` would make old lookup/scoring code become the new ownership surface, stop and build a thin seam first
- if a task can reuse static records but not policy logic, reuse data only
- if a task would force product semantics into retrieval or provider layers, stop and re-scope

### B-2 retrieval / provider dependency inversion rule

For B-2 retrieval, evidence, web/search, and Pass 2 work:

- application-layer code must depend on app-owned ports and contracts, not concrete provider adapters
- Tavily, BuilderSpace, OpenAI-compatible transports, and model/provider quirks are infrastructure details, not product semantics
- provider-specific knobs such as `search_depth`, `extract_depth`, `chunks_per_source`, `include_raw_content`, transport retries, or JSON recovery behavior must stay in provider/profile policy, not B-2 product contracts
- `WebSearchCandidateProducer`-style normalization must consume provider-agnostic search hits and emit candidate-only app objects
- search candidates must not carry final truth, exactness posture, packet acceptance, source-priority verdict, or mutation authority before packetization / hard recheck / packet consumption

For high-impact B-2 slices that touch retrieval, packetization, provider seams, or evidence ownership, planning and review must also record:

- `repo_truth_used`
- `external_references_checked`
- `adopted_guidance`
- `rejected_guidance`
- `why_this_slice_is_still_narrow`
- `stop_conditions`

If a high-impact B-2 slice skips current best-practice / official-reference review, it is not ready for worker implementation.

### High-impact semantic-owner hard gate

For any Wave 1 slice that touches runtime, retrieval, tool orchestration, evaluation, semantic routing, mutation, provider seams, structured extraction, final mapping, or architecture ownership, planning must include these fields before implementation:

```yaml
best_practice_evidence:
  required: true
  sources_checked:
    - official_or_primary_source:
  adopted_guidance:
  rejected_guidance:
  conflict_with_repo_habits:
  how_the_design_changed:
llm_deterministic_boundary:
  decision_surface:
  truth_owner: LLM | deterministic | hybrid | human
  deterministic_role: validate | derive | reject | downgrade | repair | none
  llm_role: judge | synthesize | classify | explain | none
  do_not_override:
semantic_owner:
  user_intent:
  food_semantics:
  routing_or_workflow_effect:
  mutation_legality:
  persistence_truth:
```

Hard rules:

- deterministic diagnostic mode means offline, reproducible, and no live provider call; it does not grant deterministic semantic ownership
- deterministic code must not create, rewrite, or default semantic fields such as `intent`, `workflow_effect`, `action_taken`, `response_mode_hint`, `follow_up_needed`, `followup_question`, `route_target`, `exactness`, or `resolution_mode` after an LLM / manager pass
- deterministic layers may validate, reject, downgrade, derive, or request one bounded repair round, but may not silently replace ambiguous language understanding, food semantics, workflow effect, final mapping, or product truth
- fake providers in deterministic diagnostics may simulate LLM / manager structured outputs; diagnostic harnesses must not infer user intent or food semantics from keyword rules, stale artifacts, or compatibility oracles

If any of `best_practice_evidence`, `llm_deterministic_boundary`, or `semantic_owner` is missing for a high-impact slice, the slice is not ready for implementation.

---

## Phase B — Evidence Stack
再實作與驗證：

1. MS3 Evidence Path Selection
2. MS4 Tavily Retrieval Usage
3. MS5 Evidence Normalization
4. MS6 Estimate / Grounding Synthesis

要求：
- Tavily is candidate retrieval, not truth oracle
- Exact DB hit should not go to web search
- Homemade / composition-ambiguous food should usually clarify first, not search
- Retrieved evidence must be normalized before estimate synthesis
- 至少暴露 `selected_evidence_path`、`evidence_packet`、`estimate_result`、Tavily retrieval artifact

---

## Phase C — Mutation & Projection
再實作與驗證：

1. MS8 Correction Integrity & Versioning
2. MS9 Ledger Mutation & Overshoot Truth
3. MS10 Macro Visibility Policy
4. MS11 Same-Truth Read Path
5. MS12 Trace / Artifact Contract
6. MS13 Intake Response Realization

要求：
- Draft must not mutate ledger
- Correction must preserve non-target items
- Overshoot must come from ledger truth
- Chat / UI / later query must reflect the same truth
- No pass claim without artifacts
- 至少暴露 correction version delta、ledger mutation result、macro visibility result、same-truth read result

Current baseline:
- `phase_c_trace` now exposes diagnostic `mutation_outcome` and `same_truth_read_result`
- `same_truth_closure_gate` now checks structured surface alignment and emits `status: pass | flagged | hard_fail`
- missing mutation / ledger / macro values stay `not_available`
- contradictions are trace-visible only; Phase C enforcement and UI same-truth remain deferred
- projection must read structured surfaces only and must not parse reply text as same-truth source
- same-truth closure must not rewrite, repair, or block runtime output

---

## Acceptance order

### During daily implementation
Run only relevant micro-suites for the changed capability.

### To claim intake-entry ready
Run at least:

- MS1
- MS7
- MS9
- MS11
- MS12
- MS14
- Manager-style intake-entry diagnostics

### To claim intake-depth ready
Run at least:

- MS2
- MS3
- MS4
- MS5
- MS6
- MS7
- MS8
- MS9
- MS10
- MS11
- MS12
- MS13
- Manager-style intake-depth diagnostics

### To claim Wave 1 ready
Run:

1. all MVP micro-suite cases
2. intake-entry diagnostics
3. intake-depth diagnostics
4. selected benchmark v1/v2 regression set
5. selected turn2 replay regression set

---

## Anti-fake-pass rules

Do not claim pass if any of the following is true:

1. Response text looks correct but product state mutation is missing
2. UI looks correct but ledger / meal_thread artifact is missing
3. Tavily was called but retrieval artifact is missing
4. Search snippet was used directly as final nutrition truth
5. A summary says pass but case-level verdicts are missing
6. A fix targets a benchmark phrase / case id instead of a generalized capability rule
7. A hidden rewrite / repair layer changes output without updating product truth

Every fix should state:

```yaml
primary_failure_family:
changed_capability:
generalized_rule:
affected_micro_suites:
expected_bundle_impact:
```

---

## Manager / workflow / tool stance

Wave 1 should follow:

> single manager orchestration + domain-owned tools/workflows + guards + trace

Manager should own:
- multi-intent coordination
- thread / interaction classification
- clarify posture
- evidence-path selection
- commit decision
- final response planning

Tools / workflows should own:
- exact DB lookup
- generic DB lookup
- Tavily retrieval
- evidence normalization
- estimate synthesis
- ledger read/write
- correction mutation
- trace/artifact writing

Guards should enforce:
- no-plan honesty
- draft isolation
- evidence-path honesty
- Tavily candidate discipline
- macro visibility discipline
- overshoot source truth
- no rescue sneak-in
- no pass without artifacts

---

## Do not sneak in later-wave semantics

Wave 1 must not implement committed semantics for:

- rescue proposal negotiation
- future-day rescue overlays
- calibration proposal acceptance
- recommendation ranking / memory writes
- proactive outreach

Wave 1 may preserve boundaries for these future capabilities, but should not use them to make Wave 1 cases pass.

---

## What to do when an E2E case fails

Do not patch the E2E case directly.

Instead:

1. Identify the failed product behavior
2. Map it to a micro-suite
3. Map it to a failure family
4. Fix the generalized capability contract
5. Rerun the relevant micro-suite
6. Then rerun the E2E case

---

## Minimum implementation report format

When submitting a Wave 1 implementation step, report:

```yaml
implemented_phase:
implemented_micro_suites:
changed_files:
primary_failure_families_addressed:
runner_or_manual_checks:
artifacts:
known_gaps:
next_recommended_step:
```

---

## Definition of Done for this bootstrap

This bootstrap is complete when coding agent can answer:

- What should I read first?
- What should I build first?
- Which tests should I run first?
- What counts as fake pass?
- When can I run manager-style E2E diagnostics?
- What should not be implemented in Wave 1?
- What minimal structured contracts must be exposed for verification?

---

## 歷史

- 2026-04-24: v1 初始版本，建立 Wave 1 coding-agent entrypoint、reading order、execution order、anti-fake-pass protocol
- 2026-04-24: v1.1 補入 `V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md` 作為必讀文件與各 phase 的最小 contract 要求
