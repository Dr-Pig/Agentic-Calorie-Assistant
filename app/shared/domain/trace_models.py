from __future__ import annotations

from pydantic import BaseModel, Field


class TraceMeta(BaseModel):
    request_id: str
    user_id: str
    timestamp: str
    provider: str
    schema_signature: str | None = None
    source_page_version: str | None = None


class TraceSpan(BaseModel):
    step_name: str
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    provider: str | None = None
    status: str = "unknown"
    notes: list[str] = Field(default_factory=list)


class DecisionJournal(BaseModel):
    routing_decision: dict = Field(default_factory=dict)
    action_decision: dict = Field(default_factory=dict)
    fallback_decision: dict = Field(default_factory=dict)
    final_response_decision: dict = Field(default_factory=dict)


class EvidenceJournal(BaseModel):
    selected_sources: list[dict] = Field(default_factory=list)
    dropped_sources: list[dict] = Field(default_factory=list)
    why_exact_failed: list[str] = Field(default_factory=list)
    estimation_mode: str | None = None


class TraceDiagnosis(BaseModel):
    failed_layer: str | None = None
    primary_failure_reason: str | None = None
    repairability: str | None = None
    suggested_next_action: str | None = None
    north_star_evaluation: dict = Field(default_factory=dict)


class TraceSummary(BaseModel):
    request_id: str
    route_target: str | None = None
    estimated_kcal: int | None = None
    response_mode: str | None = None
    best_answer_source: str | None = None


class TraceEnvelope(BaseModel):
    trace_contract: dict = Field(default_factory=dict)
    multi_turn_context: dict = Field(default_factory=dict)
    token_usage: dict = Field(default_factory=dict)
    north_star_evaluation: dict = Field(default_factory=dict)
    trace_meta: dict = Field(default_factory=dict)
    span_timeline: list[dict] = Field(default_factory=list)
    decision_journal: dict = Field(default_factory=dict)
    evidence_journal: dict = Field(default_factory=dict)
    diagnosis: dict = Field(default_factory=dict)
    context_pack_trace: dict = Field(default_factory=dict)
    tool_decision_trace: dict = Field(default_factory=dict)
    boundary_trace: dict = Field(default_factory=dict)
    judge_trace: dict = Field(default_factory=dict)
    evidence_resolution_trace: dict = Field(default_factory=dict)
    memory_trace: dict = Field(default_factory=dict)
