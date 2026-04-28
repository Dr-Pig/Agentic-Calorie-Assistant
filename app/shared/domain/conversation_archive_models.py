from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class ConversationArchiveRecord(BaseModel):
    record_id: int
    user_id: str
    local_date: str
    summary_text: str
    transcript_excerpt: list[ConversationMessage] = Field(default_factory=list)
    source_request_ids: list[str] = Field(default_factory=list)


class ConversationRetrievalHit(BaseModel):
    record_id: int
    summary_text: str
    local_date: str
    score: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)
    rationale: str | None = None


class SessionTranscriptRecord(BaseModel):
    turn_id: str
    role: str
    content: str
    timestamp: str
    linked_meal_id: int | None = None
    local_date: str | None = None
    source_request_id: str | None = None
    trace_id: str | None = None


class MealRecord(BaseModel):
    meal_id: int
    meal_thread_id: int | None = None
    meal_version_id: int | None = None
    status: str
    title: str
    raw_input: str
    timestamp: str
    local_date: str
    total_kcal: int | None = None
    protein_g: int | None = None
    carb_g: int | None = None
    fat_g: int | None = None
    pending_question: str | None = None
    parent_log_id: int | None = None
    source_request_id: str | None = None
    components: list[dict] = Field(default_factory=list)
    normalized_user_input: str | None = None
    resolved_food_items: list[str] = Field(default_factory=list)
    component_breakdown: list[dict] = Field(default_factory=list)
    followup_status: str = "closed"
    missing_slots: list[str] = Field(default_factory=list)
    conversation_id: str | None = None
    user_id: str | None = None
    created_at_utc: str | None = None
    updated_at_utc: str | None = None
    occurred_at_utc: str | None = None
    occurred_at_local: str | None = None
    timezone: str | None = None
    relative_time_label: str | None = None
    meal_type: str | None = None
    correction_parent_meal_id: int | None = None
    resolved_slots: list[str] = Field(default_factory=list)


class RetrievedContextChunk(BaseModel):
    chunk_id: str
    source_type: str
    source_id: int | str
    content: str
    timestamp: str | None = None
    linked_meal_id: int | None = None
    score: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
