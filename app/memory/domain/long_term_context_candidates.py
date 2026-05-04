from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.domain.long_term_context_candidates"
)

CandidateType = Literal[
    "memory",
    "pattern",
    "preference",
    "negative_preference",
    "temporary_preference",
    "golden_order",
    "user_language_pattern",
    "intake_estimation_bias",
    "app_usage_style",
    "interaction_preference",
    "food_preference",
    "logging_adherence_pattern",
    "conversation_recall_context",
    "proactive_trigger",
    "recommendation_shadow",
    "rescue_shadow",
]

ReviewStatus = Literal["pending", "accepted", "rejected", "expired"]
FreshnessPosture = Literal["fresh", "recent", "stale", "unknown"]


class SourceObjectRef(BaseModel):
    source_kind: str
    source_id: str


class LongTermContextCandidate(BaseModel):
    candidate_id: str
    candidate_type: CandidateType
    user_id: str
    source_trace_ids: list[str] = Field(default_factory=list)
    source_object_refs: list[str] = Field(default_factory=list)
    evidence_count: int
    evidence_window_start: datetime | None = None
    evidence_window_end: datetime | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    freshness_posture: FreshnessPosture = "unknown"
    staleness_note: str | None = None
    proposed_memory_text: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    scope_keys: dict[str, str] = Field(default_factory=dict)
    secret_scan: dict[str, Any] = Field(default_factory=dict)
    injection_eligibility: dict[str, Any] = Field(default_factory=dict)
    runtime_injection_allowed: Literal[False] = False
    intended_consumers: list[str] = Field(default_factory=list)
    consumer_use_hints: dict[str, str] = Field(default_factory=dict)
    risk_if_wrong: str
    reason_codes: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = "pending"
    human_review_required: Literal[True] = True
    runtime_effect_allowed: Literal[False] = False


class ContextValueReviewItem(BaseModel):
    review_item_id: str
    source_candidate_id: str
    context_found: str
    helps_capabilities: list[str]
    why_it_may_be_useful: str
    evidence_strength: Literal["low", "medium", "high"]
    possible_harm_if_injected_too_early: str
    recommended_next_action: Literal[
        "keep_shadowing",
        "ask_user_to_confirm",
        "promote_to_confirmed_memory_later",
        "discard",
    ]
    review_status: ReviewStatus = "pending"
    human_review_required: Literal[True] = True
    runtime_effect_allowed: Literal[False] = False


__all__ = [
    "ContextValueReviewItem",
    "LongTermContextCandidate",
    "SIDECAR_ACTIVATION_CONTRACT",
]
