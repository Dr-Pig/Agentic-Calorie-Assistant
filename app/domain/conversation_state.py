from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    id: int | None = None
    role: str
    content: str
    created_at: str | None = None


class ConversationArchiveRecord(BaseModel):
    id: int
    role: str
    content: str
    created_at: str
    linked_meal_log_id: int | None = None
    source: str = "message_buffer"


class ConversationRetrievalHit(BaseModel):
    message_id: int
    role: str
    content: str
    created_at: str
    score: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)
    linked_meal_log_id: int | None = None


class SessionTranscriptRecord(BaseModel):
    session_id: str
    turn_id: int
    role: str
    content: str
    timestamp: str
    trace_id: str | None = None
    linked_meal_id: int | None = None


class MealRecord(BaseModel):
    session_id: str
    meal_id: int
    title: str
    raw_input: str
    timestamp: str
    status: str
    kcal: int = 0
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    components: list[dict[str, Any]] = Field(default_factory=list)
    pending_question: str | None = None
    resolved_slots: list[str] = Field(default_factory=list)
    parent_log_id: int | None = None


class RetrievedContextChunk(BaseModel):
    chunk_id: str
    source_type: str
    source_id: int | None = None
    content: str
    timestamp: str | None = None
    linked_meal_id: int | None = None
    score: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationDigest(BaseModel):
    active_meal_title: str | None = None
    active_parent_log_id: int | None = None
    pending_question: str | None = None
    answered_driver_signals: list[str] = Field(default_factory=list)
    unresolved_driver_signals: list[str] = Field(default_factory=list)
    last_explicit_correction: str | None = None


class DurableMemoryHit(BaseModel):
    memory_type: str
    value: str
    confidence: str = "low"
    source: str = "transcript"


class ActiveMealSummary(BaseModel):
    meal_title: str | None = None
    status: str | None = None
    unresolved_slots: list[str] = Field(default_factory=list)
    accepted_corrections: list[str] = Field(default_factory=list)
    selected_evidence_titles: list[str] = Field(default_factory=list)


class RecentTurnSummary(BaseModel):
    user_messages: list[str] = Field(default_factory=list)
    assistant_messages: list[str] = Field(default_factory=list)


class SessionSummary(BaseModel):
    active_goal: str | None = None
    active_meal_title: str | None = None
    open_questions: list[str] = Field(default_factory=list)
    recent_corrections: list[str] = Field(default_factory=list)


class PlannerStateDigest(BaseModel):
    active_meal_log_id: int | None = None
    active_meal_title: str | None = None
    active_parent_log_id: int | None = None
    pending_question: str | None = None
    candidate_components: list[str] = Field(default_factory=list)
    recent_window_size: int = 0
    archive_hit_count: int = 0
    answered_driver_signals: list[str] = Field(default_factory=list)
    unresolved_driver_signals: list[str] = Field(default_factory=list)
    last_explicit_correction: str | None = None


class ConversationState(BaseModel):
    user_id: str
    latest_log_id: int | None = None
    latest_log_status: str | None = None
    active_unresolved_meal_id: int | None = None
    latest_meal_title: str | None = None
    latest_components: list[dict[str, Any]] = Field(default_factory=list)
    pending_question: str | None = None
    recent_messages: list[ConversationMessage] = Field(default_factory=list)
    active_parent_log_id: int | None = None
    conversation_archive_count: int = 0
    conversation_window_size: int = 0
    conversation_archive_hits: list[ConversationRetrievalHit] = Field(default_factory=list)
    conversation_digest: ConversationDigest = Field(default_factory=ConversationDigest)
    planner_state_digest: PlannerStateDigest = Field(default_factory=PlannerStateDigest)
    active_meal_summary: ActiveMealSummary = Field(default_factory=ActiveMealSummary)
    recent_turn_summary: RecentTurnSummary = Field(default_factory=RecentTurnSummary)
    session_summary: SessionSummary = Field(default_factory=SessionSummary)
    durable_memory_hits: list[DurableMemoryHit] = Field(default_factory=list)
    retrieved_transcript_chunks: list[RetrievedContextChunk] = Field(default_factory=list)
    retrieved_meal_records: list[RetrievedContextChunk] = Field(default_factory=list)
    retrieval_diagnostics: dict[str, Any] = Field(default_factory=dict)
    active_meal_time_gap_seconds: float | None = None
    boundary_clarification_open: bool = False
    boundary_clarification_source_meal_id: int | None = None

    @property
    def is_multi_turn_candidate(self) -> bool:
        return bool(
            self.latest_log_id
            or self.pending_question
            or self.recent_messages
            or self.conversation_archive_hits
        )


class PlannerContextPayload(BaseModel):
    raw_user_input: str
    thin_sanitized_input: str
    allow_search: bool
    implemented_routes: list[str] = Field(default_factory=lambda: ["food_estimation"])
    pending_question: str | None = None
    latest_meal_summary: str | None = None
    conversation_state_summary: dict[str, Any] = Field(default_factory=dict)
    planner_state_digest: dict[str, Any] = Field(default_factory=dict)
    retrieved_conversation_context: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_transcript_chunks: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_meal_records: list[dict[str, Any]] = Field(default_factory=list)
    active_meal_summary: dict[str, Any] = Field(default_factory=dict)
    session_summary: dict[str, Any] = Field(default_factory=dict)
    durable_memory_hits: list[dict[str, Any]] = Field(default_factory=list)
    active_meal_state: dict[str, Any] = Field(default_factory=dict)
    time_distance_features: dict[str, Any] = Field(default_factory=dict)
    boundary_state: dict[str, Any] = Field(default_factory=dict)


class TurnIntentResult(BaseModel):
    intent: str
    meal_boundary: str = "start_new_meal"
    active_meal_reference: int | None = None
    boundary_confidence: str = "low"
    resolved_query: str = ""
    resolution_mode: str = "none"
    normalized_user_input: str
    input_signals: dict[str, Any] = Field(default_factory=dict)
    missing_info: list[str] = Field(default_factory=list)
    route_hints: dict[str, Any] = Field(default_factory=dict)
    planning_brief: dict[str, Any] = Field(default_factory=dict)


class RouteDecision(BaseModel):
    route_target: str
    reason: str


class AnswerSourceDecision(BaseModel):
    source: str
    estimate_mode: str | None = None
    confidence_tier: str | None = None


class GroundingBundle(BaseModel):
    retrieval_query: str | None = None
    retrieved_knowledge: list[dict[str, Any]] = Field(default_factory=list)
    used_search: bool = False
    search_query: str | None = None
    search_quality: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)


class TraceMeta(BaseModel):
    request_id: str
    user_id: str = "anonymous"
    timestamp: str
    provider: str | None = None
    schema_signature: str | None = None
    source_page_version: str | None = None


class TraceSpan(BaseModel):
    span_id: str
    parent_span_id: str | None = None
    stage: str
    status: str = "ok"
    attempt_index: int = 1
    trigger_reason: str | None = None
    duration_ms: int | None = None
    input_ref: str | None = None
    output_ref: str | None = None
    stage_input_summary: dict[str, Any] = Field(default_factory=dict)
    stage_output_summary: dict[str, Any] = Field(default_factory=dict)
    handoff_contract: dict[str, Any] = Field(default_factory=dict)


class DecisionJournal(BaseModel):
    planner_intent: str | None = None
    route_family: str | None = None
    followup_policy_decision: str | None = None
    followup_decision: str | None = None
    best_answer_source: str | None = None
    retry_triggered: bool = False
    retry_reason: str | None = None


class EvidenceJournal(BaseModel):
    retrieval_query: str | None = None
    local_hit_count: int = 0
    search_query: str | None = None
    search_hit_count: int = 0
    evidence_passed_to_llm: bool = False
    exact_truth_candidate: dict[str, Any] | None = None
    grounding_contradiction: bool = False
    match_confidence: str | None = None
    db_hit_type: str | None = None


class TraceDiagnosis(BaseModel):
    failed_layer: str | None = None
    why: str = ""
    repairability: str = "unknown"
    suggested_next_action: str = "inspect_trace"
    trace_health: str = "healthy"


class TraceSummary(BaseModel):
    id: str
    timestamp: str
    intent: str = "unknown"
    verdict: str = "pending"
    tokens: int = 0
    user_id: str = "anonymous"
    text: str = ""
    is_multi_turn: bool = False
    failed_layer: str | None = None
    repairability: str = "unknown"
    trace_health: str = "healthy"
    planner_mode: str | None = None
    best_answer_source: str | None = None
    retry_triggered: bool = False


class TraceEnvelope(BaseModel):
    trace_contract: dict[str, Any] = Field(default_factory=dict)
    multi_turn_context: dict[str, Any] = Field(default_factory=dict)
    token_usage: dict[str, Any] = Field(default_factory=dict)
    north_star_evaluation: dict[str, Any] = Field(default_factory=dict)
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
