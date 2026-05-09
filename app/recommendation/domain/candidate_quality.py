from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("recommendation.domain.candidate_quality")


EvidencePosture = Literal["exact", "anchored", "generic", "unknown"]
AvailabilityPosture = Literal["available", "likely", "unknown", "unavailable"]
QualityTier = Literal["high", "medium", "low", "rejected"]
ProactiveIntensity = Literal["primary_plus_backup", "offer", "none"]
CandidatePoolDecision = Literal[
    "primary_plus_backup",
    "offer",
    "silent_no_qualified_candidate",
]


class RecommendationCandidateQualityInput(BaseModel):
    candidate_id: str
    title: str
    estimated_kcal: int | None = None
    kcal_range_min: int | None = None
    kcal_range_max: int | None = None
    remaining_budget_kcal: int | None = None
    evidence_posture: EvidencePosture = "unknown"
    availability_posture: AvailabilityPosture = "unknown"
    realistic_executable: bool = False
    violates_negative_preference: bool = False
    user_accessible: bool = False
    source_kind: Literal["prepared_candidate"] = "prepared_candidate"


class RecommendationCandidateQualityResult(BaseModel):
    candidate_id: str
    passed: bool
    quality_tier: QualityTier
    proactive_intensity: ProactiveIntensity
    disqualifier_flags: list[str] = Field(default_factory=list)
    quality_signals: list[str] = Field(default_factory=list)


class RecommendationCandidatePoolDecisionResult(BaseModel):
    pool_decision: CandidatePoolDecision
    primary_candidate_id: str | None = None
    backup_candidate_ids: list[str] = Field(default_factory=list)
    offer_candidate_ids: list[str] = Field(default_factory=list)
    rejected_candidate_ids: list[str] = Field(default_factory=list)
    candidate_quality: list[RecommendationCandidateQualityResult] = Field(
        default_factory=list
    )
    runtime_effect_allowed: Literal[False] = False
    recommendation_served: Literal[False] = False
    intake_hint_packet_created: Literal[False] = False
    manager_context_injected: Literal[False] = False
    proactive_sent: Literal[False] = False
    mutation_changed: Literal[False] = False
    meal_thread_mutated: Literal[False] = False
    day_budget_mutated: Literal[False] = False
    body_plan_mutated: Literal[False] = False
    live_search_used: Literal[False] = False
    ranking_llm_invoked: Literal[False] = False
    durable_memory_written: Literal[False] = False
    user_facing_behavior_changed: Literal[False] = False
