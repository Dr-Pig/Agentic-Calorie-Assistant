from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


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
    manager_brief: dict[str, Any] = Field(default_factory=dict)
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
