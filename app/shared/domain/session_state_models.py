from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .conversation_archive_models import ConversationMessage, ConversationRetrievalHit, MealRecord, RetrievedContextChunk


class ConversationDigest(BaseModel):
    latest_user_turns: list[str] = Field(default_factory=list)
    latest_assistant_turns: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    recent_meal_ids: list[int] = Field(default_factory=list)
    active_meal_title: str | None = None
    active_parent_log_id: int | None = None
    pending_question: str | None = None
    answered_driver_signals: list[str] = Field(default_factory=list)
    unresolved_driver_signals: list[str] = Field(default_factory=list)
    last_explicit_correction: str | None = None


class DurableMemoryHit(BaseModel):
    source_type: str | None = None
    summary: str | None = None
    local_date: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"
    memory_type: str | None = None
    value: str | None = None
    source: str | None = None


class ActiveMealSummary(BaseModel):
    meal_id: int | None = None
    meal_thread_id: int | None = None
    meal_version_id: int | None = None
    title: str | None = None
    meal_title: str | None = None
    status: str | None = None
    pending_question: str | None = None
    followup_status: str | None = None
    unresolved_slots: list[str] = Field(default_factory=list)
    accepted_corrections: list[str] = Field(default_factory=list)
    selected_evidence_titles: list[str] = Field(default_factory=list)


class ActiveMealState(BaseModel):
    meal_id: int | None = None
    meal_thread_id: int | None = None
    meal_version_id: int | None = None
    title: str | None = None
    meal_title: str | None = None
    status: str | None = None
    estimate_mode: str | None = None
    confidence: str | None = None
    pending_question: str | None = None
    followup_status: str = "closed"
    correction_parent_meal_id: int | None = None
    last_updated_at_utc: str | None = None
    missing_slots: list[str] = Field(default_factory=list)
    resolved_slots: list[str] = Field(default_factory=list)
    resolved_food_items: list[str] = Field(default_factory=list)
    accepted_corrections: list[str] = Field(default_factory=list)
    relative_time_label: str | None = None
    local_date: str | None = None


class PendingFollowupState(BaseModel):
    is_open: bool = False
    question: str | None = None
    pending_question: str | None = None
    meal_id: int | None = None
    meal_thread_id: int | None = None
    source_meal_id: int | None = None
    asked_at_utc: str | None = None
    missing_high_impact_slots: list[str] = Field(default_factory=list)


class RecentTurnSummary(BaseModel):
    user_turn: str = ""
    assistant_turn: str = ""


class SessionSummary(BaseModel):
    latest_user_turns: list[str] = Field(default_factory=list)
    latest_assistant_turns: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    pending_followup: PendingFollowupState = Field(default_factory=PendingFollowupState)
    active_meal: ActiveMealSummary = Field(default_factory=ActiveMealSummary)
    current_session_preferences: list[str] = Field(default_factory=list)


class SessionStateDigest(BaseModel):
    session_summary: SessionSummary = Field(default_factory=SessionSummary)
    active_meal: ActiveMealState = Field(default_factory=ActiveMealState)
    pending_followup: PendingFollowupState = Field(default_factory=PendingFollowupState)
    digest: ConversationDigest = Field(default_factory=ConversationDigest)


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
    session_id: str | None = None
    user_id: str | None = None
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
    active_meal_state: ActiveMealState = Field(default_factory=ActiveMealState)
    pending_followup_state: PendingFollowupState = Field(default_factory=PendingFollowupState)
    recent_turn_summary: RecentTurnSummary = Field(default_factory=RecentTurnSummary)
    session_summary: SessionSummary = Field(default_factory=SessionSummary)
    durable_memory_hits: list[DurableMemoryHit] = Field(default_factory=list)
    retrieved_transcript_chunks: list[RetrievedContextChunk] = Field(default_factory=list)
    retrieved_meal_records: list[RetrievedContextChunk] = Field(default_factory=list)
    recent_relevant_turns: list[ConversationMessage] = Field(default_factory=list)
    retrieval_diagnostics: dict[str, Any] = Field(default_factory=dict)
    active_meal_time_gap_seconds: float | None = None
    boundary_clarification_open: bool = False
    boundary_clarification_source_meal_id: int | None = None
    transcript_chunks: list[RetrievedContextChunk] = Field(default_factory=list)
    historical_meal_chunks: list[RetrievedContextChunk] = Field(default_factory=list)
    active_meal: ActiveMealState = Field(default_factory=ActiveMealState)
    pending_followup: PendingFollowupState = Field(default_factory=PendingFollowupState)
    latest_budget_remaining_kcal: int | None = None
    latest_budget_date: str | None = None
    latest_body_plan_summary: dict[str, Any] = Field(default_factory=dict)
    digest: ConversationDigest = Field(default_factory=ConversationDigest)


class SessionContextPayload(BaseModel):
    active_meal: ActiveMealState = Field(default_factory=ActiveMealState)
    pending_followup: PendingFollowupState = Field(default_factory=PendingFollowupState)
    session_summary: SessionSummary = Field(default_factory=SessionSummary)
    digest: ConversationDigest = Field(default_factory=ConversationDigest)
    transcript_context: list[RetrievedContextChunk] = Field(default_factory=list)
    historical_meal_context: list[RetrievedContextChunk] = Field(default_factory=list)
    durable_memory_hits: list[DurableMemoryHit] = Field(default_factory=list)
    budget_remaining_kcal: int | None = None
    budget_local_date: str | None = None
    body_plan_summary: dict[str, Any] = Field(default_factory=dict)
    retrieval_diagnostics: dict[str, Any] = Field(default_factory=dict)
    active_meal_time_gap_seconds: float | None = None


class RouteDecision(BaseModel):
    route: Literal["budget", "active_meal", "historical_meal", "conversation_summary", "none"] = "none"


class AnswerSourceDecision(BaseModel):
    source: Literal["current_budget_view", "active_meal", "historical_meal", "conversation_summary", "none"] = "none"


class GroundingBundle(BaseModel):
    active_meal: ActiveMealState = Field(default_factory=ActiveMealState)
    pending_followup: PendingFollowupState = Field(default_factory=PendingFollowupState)
    route_decision: RouteDecision = Field(default_factory=RouteDecision)
    answer_source_decision: AnswerSourceDecision = Field(default_factory=AnswerSourceDecision)
