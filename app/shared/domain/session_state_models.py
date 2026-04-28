from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .conversation_archive_models import RetrievedContextChunk


class ConversationDigest(BaseModel):
    latest_user_turns: list[str] = Field(default_factory=list)
    latest_assistant_turns: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    recent_meal_ids: list[int] = Field(default_factory=list)


class DurableMemoryHit(BaseModel):
    source_type: str
    summary: str
    local_date: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"


class ActiveMealSummary(BaseModel):
    meal_id: int | None = None
    meal_thread_id: int | None = None
    title: str | None = None
    pending_question: str | None = None
    followup_status: str | None = None


class ActiveMealState(BaseModel):
    meal_id: int | None = None
    meal_thread_id: int | None = None
    meal_version_id: int | None = None
    title: str | None = None
    pending_question: str | None = None
    followup_status: str = "closed"
    correction_parent_meal_id: int | None = None
    last_updated_at_utc: str | None = None


class PendingFollowupState(BaseModel):
    is_open: bool = False
    question: str | None = None
    meal_id: int | None = None
    meal_thread_id: int | None = None
    asked_at_utc: str | None = None


class RecentTurnSummary(BaseModel):
    user_turn: str = ""
    assistant_turn: str = ""


class SessionSummary(BaseModel):
    latest_user_turns: list[str] = Field(default_factory=list)
    latest_assistant_turns: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    pending_followup: PendingFollowupState = Field(default_factory=PendingFollowupState)
    active_meal: ActiveMealSummary = Field(default_factory=ActiveMealSummary)


class SessionStateDigest(BaseModel):
    session_summary: SessionSummary = Field(default_factory=SessionSummary)
    active_meal: ActiveMealState = Field(default_factory=ActiveMealState)
    pending_followup: PendingFollowupState = Field(default_factory=PendingFollowupState)
    digest: ConversationDigest = Field(default_factory=ConversationDigest)


class ConversationState(BaseModel):
    session_id: str
    transcript_chunks: list[RetrievedContextChunk] = Field(default_factory=list)
    historical_meal_chunks: list[RetrievedContextChunk] = Field(default_factory=list)
    durable_memory_hits: list[DurableMemoryHit] = Field(default_factory=list)
    active_meal: ActiveMealState = Field(default_factory=ActiveMealState)
    pending_followup: PendingFollowupState = Field(default_factory=PendingFollowupState)
    latest_budget_remaining_kcal: int | None = None
    latest_budget_date: str | None = None
    latest_body_plan_summary: dict = Field(default_factory=dict)
    digest: ConversationDigest = Field(default_factory=ConversationDigest)
    retrieval_diagnostics: dict = Field(default_factory=dict)
    active_meal_time_gap_seconds: float | None = None


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
    body_plan_summary: dict = Field(default_factory=dict)
    retrieval_diagnostics: dict = Field(default_factory=dict)
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
