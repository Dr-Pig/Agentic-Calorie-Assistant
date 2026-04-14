# L3T Typed Runtime Contract Spec

## 1. 目的

本文件是 `L3.x Runtime Contract` 的 typed 補件。

它回答：

- 各 pass / runtime 之間交換的 exact typed payload shape
- 哪些欄位是 required
- 哪些欄位是 optional
- 哪些欄位只允許 enum / constrained values
- 哪些欄位可以是 generic metadata

本文件的定位是：

- `L3.1 / L3.2 / L3.3 / L3.4 / L3.5` 定語意與責任邊界
- `L3T` 定 agent 實作時應落成的 typed contract

如果 `L3.x` 與 `L3T` 衝突，以 `L3T` 的 exact field contract 為實作基準。

---

## 2. Global Rules

### 2.1 Pass output must be typed

下列結構不得以裸 `dict[str, Any]` 長期存在：

- pass outputs
- commit request candidate
- proposal options
- rescue options
- response result

允許 `dict[str, Any]` 的地方只限：

- trace metadata
- provider raw excerpts
- constrained `*_payload` metadata fields

### 2.1A Decision-Mode Boundary

`L3T` defines typed payload contracts, not pass-selection policy.

Rules:

- `decision_mode` is governed by `L6E` and the domain-specific `L3.x` runtime specs, not by `L3T`
- a step may be `llm`, `deterministic`, or `hybrid`, but its output must still conform to the exact typed contract defined here
- raw provider output, hidden chain-of-thought, or unconstrained free-form blobs do not satisfy `L3T` merely because an LLM produced them
- if a step is deterministic, that does not relax its payload shape; if a step is LLM-backed, that does not permit schema drift

Use `L3T` to validate output shape after the decision mode has already been chosen elsewhere.

### 2.2 Typed contracts are additive-first

既有 typed contract 若要調整：

- 優先 additive fields
- breaking field rename / shape change 必須同步改 spec、tests、benchmark fixtures

### 2.3 Enum legality follows `L2A`

任何與 canonical enum 對齊的欄位，必須服從：

- [`L2A Data Dictionary Spec`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2A_DATA_DICTIONARY_SPEC.md)

---

## 3. Shared Primitive Contracts

### 3.1 `PassExecutionEnvelope`

最小欄位：

- `status: Literal["ok", "failed", "abstained"]`
- `payload: dict[str, Any]`
- `fallback_used: bool`
- `error: str | None`

規則：

- envelope 是 pass runner 外層包裝
- `payload` 內部仍應映射到下述 typed result

### 3.2 `CommitRequestCandidate`

最小欄位：

- `commit_kind: Literal["meal_commit"]`
- `request_id: str`
- `planner_intent: str`
- `meal_thread_id: int | None`
- `parent_version_id: int | None`
- `version_reason: Literal["new_intake", "clarification_completion", "correction", "historical_correction"]`
- `meal_title: str`
- `raw_input: str`
- `estimated_kcal: int`
- `protein_g: int`
- `carb_g: int`
- `fat_g: int`
- `resolution_status: Literal["candidate_meal", "draft_unresolved", "completed_meal"]`
- `occurred_at: datetime | None`
- `local_date: str`
- `items: list[MealItemPayload]`
- `trace_ref: dict[str, Any]`

規則：

- Phase 2 intake vertical slice 至少要能產生這個 payload
- application layer 再把它映射到 canonical persistence

### 3.3 `MealItemPayload`

最小欄位：

- `name: str`
- `quantity_hint: str | None`
- `source: Literal["llm", "retrieval", "lookup"]`
- `evidence_role: Literal["exact_truth", "ingredient_anchor", "meal_pattern_prior", "retailer_fallback", "unknown"]`
- `estimate_basis: Literal["exact", "anchored", "heuristic_only", "llm_only"]`
- `confidence_tier: Literal["high", "medium", "low"]`
- `estimated_kcal: int`
- `protein_g: int`
- `carb_g: int`
- `fat_g: int`
- `evidence_ids: list[str]`
- `classification: dict[str, Any]`

規則：

- `classification` 只能承載對應 `L2A` 的 canonical-friendly item metadata

---

## 4. Intake Typed Contracts

### 4.1 `TaskMealLinkResult`

最小欄位：

- `intent: Literal["food_estimation", "new_intake", "clarification", "modification", "correction", "general_chat"]`
- `scope: Literal["meal_specific", "food_general", "non_food"]`
- `meal_link_action: Literal["attach_to_existing_meal", "create_new_meal", "boundary_ambiguous", "none"]`
- `target_meal_id: int | None`
- `link_confidence: Literal["high", "medium", "low"]`
- `boundary_reason: str`
- `clarification_blocking: bool`
- `normalized_user_input: str`

### 4.2 `DecisionPassResult`

最小欄位：

- `next_action: Literal["run_nutrition_resolution", "clarify_user", "no_food_commit"]`
- `tool_plan: Literal["none", "local_only", "local_then_search", "search_only"]`
- `decision_confidence: Literal["high", "medium", "low"]`
- `clarify_priority: Literal["blocking", "important", "optional"] | None`
- `unresolved_info: list[str]`
- `response_mode_hint: Literal["exact_answer", "rough_estimate_ok", "clarify_first"]`
- `clarify_is_blocking: bool`
- `can_proceed_without_clarify: bool`

### 4.3 `NutritionResolutionResult`

最小欄位：

- `resolution_mode: Literal["cannot_estimate_yet", "needs_more_tooling", "resolved"]`
- `resolution_basis: Literal["component_model", "calibrated_component_model", "exact_item", "heuristic_only", "unknown"]`
- `confidence: Literal["high", "medium", "low"]`
- `exactness: Literal["exact_item", "near_exact", "calibrated_estimate", "component_grounded", "best_effort", "unknown"]`
- `answer_payload: dict[str, Any]`
- `unresolved_info: list[str]`
- `current_evidence_sufficiency: str`
- `why_no_more_tools: str`
- `reason_for_not_requesting_tool: str`
- `state_transition_hint: Literal["candidate_meal", "draft_unresolved", "completed_meal"] | None`

### 4.4 `FinalResponseResult`

最小欄位：

- `reply_text: str`
- `asked_follow_up: bool`
- `ui_hints: dict[str, Any]`

### 4.5 `EstimatePayload`

`EstimatePayload` 是 current Phase 2 vertical slice 的 assembled runtime artifact。

commit-critical 最小欄位：

- `request_id`
- `meal_title`
- `component_estimates`
- `estimated_kcal`
- `protein_g`
- `carb_g`
- `fat_g`
- `action_taken`
- `route_target`
- `debug_steps`
- `llm_traces`
- `trace_contract`
- `boundary_trace`

規則：

- `EstimatePayload` 可作 Phase 2 assembled runtime result
- 但 canonical write 仍應透過 `CommitRequestCandidate` 或等價 typed bridge

---

## 5. Recommendation Typed Contracts

### 5.1 `RecommendationContextResult`

最小欄位：

- `remaining_kcal: int | None`
- `budget_posture: Literal["on_track", "tight", "over_budget", "unknown"]`
- `preference_summary_ref: dict[str, Any]`
- `location_status: Literal["available", "unavailable", "unknown"]`
- `source_pool_summary: dict[str, Any]`

### 5.2 `RecommendationCandidate`

最小欄位：

- `candidate_id: str`
- `candidate_kind: Literal["golden_order", "nearby", "safe_fallback", "generic"]`
- `title: str`
- `store_name: str | None`
- `estimated_kcal: int | None`
- `protein_g: int | None`
- `fit_summary: str`
- `source_metadata: dict[str, Any]`

### 5.3 `HintPacket`

最小欄位：

- `candidate_id: str`
- `title: str`
- `store_name: str | None`
- `estimated_kcal: int | None`
- `protein_g: int | None`
- `source_metadata: dict[str, Any]`

規則：

- `HintPacket` 只作 recommendation -> intake handoff 線索
- 不等於 canonical state

### 5.4 `RecommendationResponseResult`

最小欄位：

- `top_pick: RecommendationCandidate | None`
- `backup_picks: list[RecommendationCandidate]`
- `hint_packet: HintPacket | None`
- `reply_text: str`
- `quick_actions: list[dict[str, Any]]`

---

## 6. Calibration Typed Contracts

### 6.1 `ObservationIngestResult`

最小欄位：

- `observation_type: Literal["weight", "none"]`
- `observation_payload: dict[str, Any]`
- `occurred_at_interpretation: dict[str, Any]`
- `observation_confidence: Literal["high", "medium", "low"]`
- `ingest_action: Literal["write_observation", "clarify", "ignore"]`
- `requires_clarification: bool`

### 6.2 `TrendAssessmentResult`

最小欄位：

- `trend_window_summary: dict[str, Any]`
- `trend_stability: Literal["stable", "noisy", "insufficient_data"]`
- `drift_signal: Literal["present", "absent", "uncertain"]`
- `noise_assessment: Literal["low", "medium", "high"]`
- `adherence_posture: Literal["good", "mixed", "poor", "unknown"]`
- `calibration_relevance: Literal["high", "medium", "low"]`

### 6.3 `CalibrationDecisionResult`

最小欄位：

- `decision_mode: Literal["no_action", "monitor", "propose_adjustment"]`
- `calibration_basis: dict[str, Any]`
- `proposal_needed: bool`
- `proposal_type: Literal["monitor_only", "logging_quality_first", "budget_adjustment", "pace_adjustment", "plan_reset"] | None`
- `proposal_options: list[CalibrationProposalOption]`
- `confidence: Literal["high", "medium", "low"]`
- `risk_notes: list[str]`

### 6.4 `CalibrationProposalOption`

最小欄位：

- `proposal_option_id: str`
- `option_label: str`
- `option_summary: str`
- `effect_type: Literal["monitor_only", "budget_adjustment", "pace_adjustment", "plan_reset", "logging_quality_first"]`
- `effect_payload: dict[str, Any]`
- `expected_effect_summary: str`
- `confidence: Literal["high", "medium", "low"]`
- `guardrail_summary: str`
- `reversibility_hint: str`

---

## 7. Rescue Typed Contracts

### 7.1 `RescueTriggerResult`

最小欄位：

- `triggered: bool`
- `trigger_reason: str`
- `overshoot_kcal: int`
- `current_local_date: str`
- `relevant_ledger_summary: dict[str, Any]`

### 7.2 `RescueAssessmentResult`

最小欄位：

- `rescue_horizon: Literal[1, 3, 5] | None`
- `recovery_viability: Literal["viable", "strained", "non_viable"]`
- `recommended_rescue_family: Literal["next_meal_protection", "short_horizon_spread", "logging_first_rescue", "rescue_stop_and_escalate"]`
- `compression_summary: dict[str, Any]`

### 7.3 `RescueOption`

最小欄位：

- `rescue_option_id: str`
- `option_family: Literal["next_meal_protection", "short_horizon_spread", "logging_first_rescue", "rescue_stop_and_escalate"]`
- `horizon_days: int | None`
- `daily_kcal_adjustments: list[int]`
- `activation_mode: Literal["immediate_next_meal", "today_lunch", "tomorrow_0000"]`
- `guardrail_summary: str`

### 7.4 `RescueResponseResult`

最小欄位：

- `top_option: RescueOption | None`
- `backup_options: list[RescueOption]`
- `reply_text: str`
- `quick_actions: list[dict[str, Any]]`

---

## 8. Prompt / Trace Typed Contracts

### 8.1 `TraceEnvelope`

最小欄位：

- `trace_meta: dict[str, Any]`
- `span_timeline: list[dict[str, Any]]`
- `decision_journal: dict[str, Any]`
- `evidence_journal: dict[str, Any]`
- `diagnosis: dict[str, Any]`

規則：

- trace 可先用 typed outer shell + flexible inner metadata
- `trace_meta` 至少應帶 `request_id`, `user_id`, `timestamp`, `provider`

### 8.2 `StageTraceEvent`

最小欄位：

- `request_id: str`
- `stage: str`
- `status: Literal["ok", "error"]`
- `attempt_index: int`
- `provider: str | None`
- `provider_role: str | None`
- `logical_model_role: Literal["fast_router_model", "strict_reasoner_model", "response_writer_model", "vision_parser_model"]`
- `model_id: str | None`
- `timestamp: str`
- `trigger_reason: str | None`
- `fallback_mode: str | None`

---

## 9. Validation Contracts

### 9.1 `DeterministicValidationResult`

**Severity**: P0 — listed in L3_1 Section 9 but never defined

```python
@dataclass
class DeterministicValidationResult:
    validation_id: str

    passed: bool
    failure_mode: Literal[
        "none",
        "schema_violation",
        "arithmetic_error",
        "invariant_violation",
        "version_conflict"
    ] | None = None

    checked_invariants: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)

    # For bounded self-correction
    can_self_correct: bool = False
    self_correction_attempted: bool = False
    self_correction_success: bool | None = None

    # Metadata
    checked_at: datetime = field(default_factory=datetime.utcnow)
    computation_time_ms: float = 0.0
```

規則：

- deterministic layer 對每個 pass output 執行 invariant check 後必須產生這個 result
- `passed=True` 時，`failure_mode` 應為 `"none"`
- `violations` 列出所有檢查失敗的 invariant 名稱
- `can_self_correct=True` 時，允許 deterministic layer 執行一次 bounded self-correction

### 9.2 `FeedbackSignal`

**Severity**: P1 — enables recommendation learning loop

```python
@dataclass
class FeedbackSignal:
    signal_id: str
    user_id: str

    # Source tracking
    recommendation_id: str | None = None  # If came from recommendation
    meal_thread_id: str | None = None     # If came from meal logging

    # Feedback content
    feedback_type: Literal["accept", "reject", "ignore", "modify"]
    feedback_target: str  # What was accepted/rejected
    feedback_detail: str | None = None  # User-provided reason if any

    # Context
    context: str  # e.g., "lunch", "snack", "evening"
    occurred_at: datetime

    # Signal path
    confidence_boost: float  # Positive for accept, negative for reject
    created_at: datetime = field(default_factory=datetime.utcnow)
```

規則：

- `FeedbackSignal` 是 recommendation → memory update 反饋閉環的正式橋樑
- `accept` → `confidence_boost > 0`
- `reject` → `confidence_boost < 0`
- `ignore` → `confidence_boost = 0`（被動信號，輕微降低 confidence）
- `modify` → 視為 partial accept，保留 modification detail

---

## 10. Implementation Rules

### 10.1 New pass/result code

任何新 pass implementation 若輸出穩定 contract：

- 必須先對照本文件
- 優先落成 Pydantic model

### 10.2 Legacy runtime allowance

若 Phase 2 仍沿用既有 assembled artifact（如 `EstimatePayload`）：

- 可暫時保留
- 但新 application bridge 應往 typed bridge 收斂

### 10.3 No shape drift

禁止：

- 同名 result 在不同模組出現不同欄位 shape
- list/string/object 來回漂移
- optional / required 隨 agent 自行變動
