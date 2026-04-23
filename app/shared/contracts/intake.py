from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import (
    AnswerMode,
    CommitVersionReason,
    DecisionNextAction,
    MealBoundary,
    MealLinkAction,
    MealStatus,
    PassExecutionStatus,
    ResolutionBasis,
    ResolutionMode,
    RouteTarget,
    SourceDecision,
    TaskScope,
)


class ToolCallRequest(BaseModel):
    tool_name: Literal[
        "resolve_exact_item",
        "get_meal_calibration",
        "resolve_ingredient_anchors",
        "search_official_nutrition",
        "read_official_doc_fragment",
        "extract_nutrition_table_fragment",
    ]
    query: str = ""
    identity_target: str | None = None
    reason: str = ""
    allowed_source_class: list[str] = Field(default_factory=list)
    extraction_target: str | None = None


class ToolCallResult(BaseModel):
    tool_name: str
    status: Literal["selected", "executed", "skipped", "not_needed"] = "selected"
    reason: str = ""
    latency_ms: int | None = None
    quality: Literal["high", "medium", "low", "unknown"] = "unknown"
    result_count: int = 0


class EvidenceCandidate(BaseModel):
    evidence_id: str = ""
    title: str = ""
    source_class: Literal[
        "exact_item_db",
        "base_nutrition_db",
        "meal_template_db",
        "web_search_official",
        "web_search_nonexact",
        "doc_read_fallback",
        "recent_turns",
        "session_summary",
        "durable_memory",
        "unknown",
    ] = "unknown"
    source_tier: str = "tier_6_model_context"
    retrieval_lane: str = "support_lane"
    record_role: str = "unknown"
    evidence_role: str = "unknown"
    identity_confidence: Literal["high", "medium", "low", "none"] = "none"
    portion_basis_quality: Literal["strong", "medium", "weak", "unknown"] = "unknown"
    provenance: dict[str, Any] = Field(default_factory=dict)
    conflict_status: Literal["none", "conflict", "shadowed"] = "none"
    selected: bool = False
    drop_reason: str | None = None


class EvidenceBundle(BaseModel):
    candidates: list[EvidenceCandidate] = Field(default_factory=list)
    selected_titles: list[str] = Field(default_factory=list)
    source_classes: list[str] = Field(default_factory=list)
    conflict_count: int = 0
    selected_count: int = 0


class JudgeRequest(BaseModel):
    user_input: str
    resolved_query: str = ""
    planning_brief: dict[str, Any] = Field(default_factory=dict)
    active_meal_summary: dict[str, Any] = Field(default_factory=dict)
    session_summary: dict[str, Any] = Field(default_factory=dict)
    top_local_candidates: list[dict[str, Any]] = Field(default_factory=list)
    top_search_candidates: list[dict[str, Any]] = Field(default_factory=list)
    doc_fragments: list[dict[str, Any]] = Field(default_factory=list)
    source_hierarchy_rules: list[str] = Field(default_factory=list)


class JudgeResult(BaseModel):
    decision: Literal["keep_best", "clarify", "search_more", "doc_read", "drop_all"] = "drop_all"
    selected_titles: list[str] = Field(default_factory=list)
    dropped: list[dict[str, str]] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str = ""
    search_more_query: str = ""
    doc_read_targets: list[str] = Field(default_factory=list)
    judge_confidence: Literal["high", "medium", "low"] = "low"


class JudgeTrace(BaseModel):
    judge_model: str | None = None
    candidate_count: int = 0
    selected_titles: list[str] = Field(default_factory=list)
    dropped_titles: list[str] = Field(default_factory=list)
    judge_decision: str = "drop_all"
    requested_action: str | None = None


class EvidenceResolutionTrace(BaseModel):
    local_exact_candidates: list[dict[str, Any]] = Field(default_factory=list)
    local_anchor_candidates: list[dict[str, Any]] = Field(default_factory=list)
    search_candidates: list[dict[str, Any]] = Field(default_factory=list)
    doc_read_fragments: list[dict[str, Any]] = Field(default_factory=list)
    final_kept_evidence: list[dict[str, Any]] = Field(default_factory=list)
    dropped_evidence: list[dict[str, Any]] = Field(default_factory=list)


class MemoryTrace(BaseModel):
    durable_memory_enabled: bool = True
    hits: list[dict[str, Any]] = Field(default_factory=list)
    write_candidates: list[dict[str, Any]] = Field(default_factory=list)


class ToolRoutingDecision(BaseModel):
    next_action: DecisionNextAction = "run_clarify"
    tool_plan: Literal[
        "none",
        "resolve_exact_item",
        "get_meal_calibration",
        "resolve_ingredient_anchors",
        "search_official_nutrition",
        "read_official_doc_fragment",
    ] = "none"
    decision_confidence: Literal["high", "medium", "low"] = "low"
    tool_query_override: str | None = None
    tool_goal: str = ""
    missing_evidence_type: str = ""
    expected_success_condition: str = ""
    clarify_priority: str | None = None
    unresolved_info: list[str] = Field(default_factory=list)
    response_mode_hint: Literal["exact_answer", "rough_estimate_ok", "clarify_first"] = "rough_estimate_ok"
    clarify_is_blocking: bool = False
    can_proceed_without_clarify: bool = False


class ExecutionEnvelope(BaseModel):
    status: PassExecutionStatus = "failed"
    payload: dict[str, Any] = Field(default_factory=dict)
    fallback_used: bool = False
    error: str | None = None


class PrimaryResult(BaseModel):
    action_taken: Literal[
        "direct_answer",
        "clarify_before_estimate",
        "answer_with_uncertainty",
        "request_tool",
    ] = "direct_answer"
    confidence: Literal["high", "medium", "low"] = "low"
    exactness: Literal[
        "exact_item",
        "near_exact",
        "calibrated_estimate",
        "component_grounded",
        "best_effort",
        "unknown",
    ] = "unknown"
    tool_request: Literal[
        "none",
        "resolve_exact_item",
        "get_meal_calibration",
        "resolve_ingredient_anchors",
        "search_official_nutrition",
        "read_official_doc_fragment",
    ] = "none"
    tool_request_reason: str = ""
    answer_payload: dict[str, Any] = Field(default_factory=dict)
    unresolved_info: list[str] = Field(default_factory=list)
    follow_up_needed: bool = False
    follow_up_reasoning: str = ""
    state_transition_hint: MealStatus | None = None
    response_mode_hint: Literal["exact_answer", "rough_estimate_ok", "clarify_first"] = "rough_estimate_ok"


class FinalResponseResult(BaseModel):
    reply_text: str = ""
    asked_follow_up: bool = False
    ui_hints: dict[str, Any] = Field(default_factory=dict)


class ComponentEstimate(BaseModel):
    name: str
    source: Literal["llm", "retrieval", "lookup"] = "llm"
    evidence_role: Literal["exact_truth", "ingredient_anchor", "meal_pattern_prior", "retailer_fallback", "unknown"] = "unknown"
    estimate_basis: Literal["exact", "anchored", "heuristic_only", "llm_only"] = "llm_only"
    confidence_tier: Literal["high", "medium", "low"] = "low"
    quantity_hint: str | None = None
    reason: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    estimated_kcal: int = 0
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    heuristic_dependencies: list[str] = Field(default_factory=list)


class MealItemPayload(BaseModel):
    name: str
    quantity_hint: str | None = None
    source: Literal["llm", "retrieval", "lookup"] = "llm"
    evidence_role: Literal["exact_truth", "ingredient_anchor", "meal_pattern_prior", "retailer_fallback", "unknown"] = "unknown"
    estimate_basis: Literal["exact", "anchored", "heuristic_only", "llm_only"] = "llm_only"
    confidence_tier: Literal["high", "medium", "low"] = "low"
    estimated_kcal: int = 0
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    evidence_ids: list[str] = Field(default_factory=list)
    classification: dict[str, Any] = Field(default_factory=dict)


class CommitRequestCandidate(BaseModel):
    commit_kind: Literal["meal_commit"] = "meal_commit"
    request_id: str
    planner_intent: str
    meal_thread_id: int | None = None
    parent_version_id: int | None = None
    version_reason: CommitVersionReason
    meal_title: str
    raw_input: str
    estimated_kcal: int
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    resolution_status: MealStatus
    occurred_at: datetime | None = None
    local_date: str
    items: list[MealItemPayload] = Field(default_factory=list)
    trace_ref: dict[str, Any] = Field(default_factory=dict)


class IngredientCandidate(BaseModel):
    name: str
    amount_hint: str = ""
    role: Literal[
        "main_carb",
        "main_protein",
        "fat_source",
        "broth",
        "sauce",
        "vegetable",
        "other",
    ] = "other"
    is_critical: bool = False
    confidence: float = 0.0


class EstimatePayload(BaseModel):
    request_id: str
    meal_title: str
    components: list[str] = Field(default_factory=list)
    quantity_hints: list[str] = Field(default_factory=list)
    component_estimates: list[ComponentEstimate] = Field(default_factory=list)
    component_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    macro_breakdown: dict[str, Any] = Field(default_factory=dict)
    raw_macro_breakdown: dict[str, Any] = Field(default_factory=dict)
    display_macro_breakdown: dict[str, Any] = Field(default_factory=dict)
    evidence_ids_used: list[str] = Field(default_factory=list)
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    estimated_kcal: int = 0
    uncertain_macro_areas: list[str] = Field(default_factory=list)
    source_decision: SourceDecision = "ask_user"
    answer_mode: AnswerMode | None = None
    action_taken: str = ""
    group_id: str | None = None
    route_target: RouteTarget = "clarify_user_private"
    route_reason: str = ""
    followup_question: str | None = None
    follow_up_needed: bool = False
    follow_up_reasoning: str = ""
    debug_steps: list[dict[str, Any]] = Field(default_factory=list)
    llm_traces: list[dict[str, Any]] = Field(default_factory=list)
    reply_text: str = ""
    retrieval_triggered: bool = False
    retrieval_query: str | None = None
    retrieved_knowledge: list[dict[str, Any]] = Field(default_factory=list)
    risk_packet: dict[str, Any] = Field(default_factory=dict)
    quality_signals: dict[str, Any] = Field(default_factory=dict)
    retry_triggered: bool = False
    retry_reason: str | None = None
    best_answer_source: str | None = None
    best_estimate_mode: Literal["exact_item", "anchored_component", "heuristic_fallback", "llm_only"] | None = None
    estimate_confidence_tier: Literal["high", "medium", "low"] | None = None
    retrieved_evidence_summary: list[dict[str, Any]] = Field(default_factory=list)
    failure_family: Literal[
        "parse_missed_component",
        "retrieval_hit_but_not_estimable",
        "kcal_only_anchor_overreach",
        "portion_missing_overestimate",
        "composite_role_misclassification",
        "exact_item_shadowed_by_generic_anchor",
        "heuristic_macro_distortion",
    ] | None = None
    used_search: bool = False
    search_query: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    search_quality: str | None = None
    stage_map_version: str = "text_meal_trace.v1"
    trace_contract: dict[str, Any] = Field(default_factory=dict)
    failed_layer: Literal[
        "planner",
        "normalizer",
        "risk_validator",
        "layer3_primary_llm",
        "grounding",
        "repair_rescue",
    ] | None = None
    primary_failure_reason: str | None = None
    north_star_evaluation: dict[str, Any] = Field(default_factory=dict)
    multi_turn_context: dict[str, Any] = Field(default_factory=dict)
    token_usage: dict[str, Any] = Field(default_factory=dict)
    trace_meta: dict[str, Any] = Field(default_factory=dict)
    span_timeline: list[dict[str, Any]] = Field(default_factory=list)
    decision_journal: dict[str, Any] = Field(default_factory=dict)
    evidence_journal: dict[str, Any] = Field(default_factory=dict)
    diagnosis: dict[str, Any] = Field(default_factory=dict)
    reasoning_state: dict[str, Any] = Field(default_factory=dict)
    context_pack_trace: dict[str, Any] = Field(default_factory=dict)
    tool_decision_trace: dict[str, Any] = Field(default_factory=dict)
    boundary_trace: dict[str, Any] = Field(default_factory=dict)
    judge_trace: dict[str, Any] = Field(default_factory=dict)
    evidence_resolution_trace: dict[str, Any] = Field(default_factory=dict)
    memory_trace: dict[str, Any] = Field(default_factory=dict)
