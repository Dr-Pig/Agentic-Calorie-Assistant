from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import AnswerMode, MealStatus, RouteTarget, SourceDecision


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
        "manager",
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
