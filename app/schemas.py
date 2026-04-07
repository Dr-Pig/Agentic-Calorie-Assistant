from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RouteTarget = Literal[
    "direct_answer",
    "retrieve_then_answer",
    "clarify_user_private",
    "retry_repair",
    "best_effort_answer",
]
SourceDecision = Literal["ready", "ask_user", "retrieve"]
AnswerMode = Literal["direct_answer", "answer_with_uncertainty", "best_effort"]
MealBoundary = Literal["continue_active_meal", "start_new_meal", "boundary_clarification"]
MealStatus = Literal["candidate_meal", "draft_unresolved", "completed_meal"]
TaskScope = Literal["meal_specific", "food_general", "non_food"]
MealLinkAction = Literal["attach_to_existing_meal", "create_new_meal", "boundary_ambiguous", "none"]
DecisionNextAction = Literal["run_tool_lookup", "run_clarify", "run_nutrition_resolution"]
ResolutionMode = Literal[
    "exact_label_finalize",
    "near_exact_finalize",
    "component_estimate",
    "provisional_estimate",
    "cannot_estimate_yet",
]
ResolutionBasis = Literal[
    "exact_item_evidence",
    "official_source_evidence",
    "component_model",
    "calibrated_component_model",
]
PassExecutionStatus = Literal["success", "degraded", "failed"]


class ComponentContext(BaseModel):
    name: str
    portion_hint: str | None = None


class EstimateSessionState(BaseModel):
    session_id: str
    original_input: str
    last_known_components: list[ComponentContext] = Field(default_factory=list)
    pending_questions: list[str] = Field(default_factory=list)


class EstimateRequest(BaseModel):
    text: str = Field(min_length=1)
    allow_search: bool = True
    user_id: str = "default_user"
    session_state: EstimateSessionState | None = None


class TurnState(BaseModel):
    active_meal_log_id: int | None = None
    pending_question: str | None = None
    last_estimate_mode: str | None = None
    candidate_components: list[str] = Field(default_factory=list)
    allowed_next_intents: list[str] = Field(default_factory=list)


class PlanningBrief(BaseModel):
    intent: Literal[
        "new_intake",
        "clarification",
        "modification",
        "correction",
        "general_chat",
        "food_estimation",
    ] = "new_intake"
    resolved_query: str = ""
    resolution_mode: Literal["exact_match", "delta_update", "component_rebuild", "clarify_first", "none"] = "none"
    entity_type: str = "unknown"
    state_link: str = "standalone"
    clarification_needed: bool = False
    clarification_targets: list[str] = Field(default_factory=list)
    risk_focus: list[str] = Field(default_factory=list)
    evidence_strategy: str = "local_retrieval_first"
    primary_prompt_hints: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    active_object: Literal["new_meal", "active_meal", "general_chat"] = "new_meal"
    slot_state: Literal["enough_to_estimate", "needs_clarification", "needs_external_evidence"] = "enough_to_estimate"
    candidate_tool_calls: list[str] = Field(default_factory=list)


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
    title: str = ""
    source_class: Literal[
        "exact_item_db",
        "base_nutrition_db",
        "meal_template_db",
        "web_search_official",
        "doc_read_fallback",
        "recent_turns",
        "session_summary",
        "durable_memory",
        "unknown",
    ] = "unknown"
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


class ContextPackTrace(BaseModel):
    sections: list[dict[str, Any]] = Field(default_factory=list)
    total_estimated_tokens: int = 0


class ToolDecisionTrace(BaseModel):
    available_tools: list[str] = Field(default_factory=list)
    candidate_tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    executed_tool_calls: list[ToolCallResult] = Field(default_factory=list)


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


class TurnIntentResult(BaseModel):
    intent: Literal[
        "new_intake",
        "clarification",
        "modification",
        "correction",
        "general_chat",
        "food_estimation",
    ] = "new_intake"
    meal_boundary: MealBoundary = "start_new_meal"
    active_meal_reference: int | None = None
    boundary_confidence: Literal["high", "medium", "low"] = "low"
    resolved_query: str = ""
    resolution_mode: Literal["exact_match", "delta_update", "component_rebuild", "clarify_first", "none"] = "none"
    normalized_user_input: str = ""
    input_signals: dict[str, Any] = Field(default_factory=dict)
    missing_info: list[str] = Field(default_factory=list)
    route_hints: dict[str, Any] = Field(default_factory=dict)
    planning_brief: PlanningBrief = Field(default_factory=PlanningBrief)


class TaskMealLinkResult(BaseModel):
    intent: Literal[
        "food_estimation",
        "new_intake",
        "clarification",
        "modification",
        "correction",
        "general_chat",
    ] = "food_estimation"
    scope: TaskScope = "meal_specific"
    meal_link_action: MealLinkAction = "create_new_meal"
    target_meal_id: int | None = None
    link_confidence: Literal["high", "medium", "low"] = "low"
    boundary_reason: str = ""
    clarification_blocking: bool = False
    normalized_user_input: str = ""


class DecisionPassResult(BaseModel):
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
    clarify_priority: str | None = None
    unresolved_info: list[str] = Field(default_factory=list)
    response_mode_hint: Literal["exact_answer", "rough_estimate_ok", "clarify_first"] = "rough_estimate_ok"
    clarify_is_blocking: bool = False
    can_proceed_without_clarify: bool = False


class NutritionResolutionResult(BaseModel):
    resolution_mode: ResolutionMode = "cannot_estimate_yet"
    resolution_basis: ResolutionBasis = "component_model"
    confidence: Literal["high", "medium", "low"] = "low"
    exactness: Literal[
        "exact_item",
        "near_exact",
        "calibrated_estimate",
        "component_grounded",
        "best_effort",
        "unknown",
    ] = "unknown"
    answer_payload: dict[str, Any] = Field(default_factory=dict)
    unresolved_info: list[str] = Field(default_factory=list)
    state_transition_hint: MealStatus | None = None


class PassExecutionEnvelope(BaseModel):
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
    context_pack_trace: dict[str, Any] = Field(default_factory=dict)
    tool_decision_trace: dict[str, Any] = Field(default_factory=dict)
    boundary_trace: dict[str, Any] = Field(default_factory=dict)
    judge_trace: dict[str, Any] = Field(default_factory=dict)
    evidence_resolution_trace: dict[str, Any] = Field(default_factory=dict)
    memory_trace: dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    request_id: str
    timestamp: str
    text: str
    raw_user_input: str | None = None
    normalized_user_input: str | None = None
    user_input_unicode_escape: str | None = None
    source_page_version: str | None = None
    allow_search: bool
    status: Literal["ok", "error"]
    route_target: str | None = None
    action_taken: str | None = None
    debug_steps: list[dict[str, Any]] = Field(default_factory=list)
    llm_traces: list[dict[str, Any]] = Field(default_factory=list)
    payload: dict[str, Any] | None = None
    error: str | None = None
    trace_artifact_path: str | None = None


class LegacyDecisionDraft(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    food_type: str = "unknown"
    decision: str = "DIRECT_ANSWER"
    ingredients: list[IngredientCandidate] = Field(default_factory=list)
    ingredients_known_enough: bool = False
    missing_info: list[str] = Field(default_factory=list)
    searchable: bool = False
    recommended_action: str = "ask_user"
    question_for_user: str | None = None
    search_queries: list[str] = Field(default_factory=list)
    retrieval_query: str = ""
    components: list[str] = Field(default_factory=list)
    dish_structure: Literal[
        "single_exact_item",
        "multi_component_simple",
        "composite_cooked_dish",
        "customizable_drink",
        "customizable_bowl",
    ] = "multi_component_simple"
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    estimated_kcal: int = 0
    uncertainty_factors: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    followup_question: str = ""
