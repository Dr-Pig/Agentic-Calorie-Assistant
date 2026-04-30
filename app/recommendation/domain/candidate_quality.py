from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("recommendation.domain.candidate_quality")


EvidencePosture = Literal["exact", "anchored", "generic", "unknown"]
AvailabilityPosture = Literal["available", "likely", "unknown", "unavailable"]
QualityTier = Literal["high", "medium", "low", "rejected"]
ProactiveIntensity = Literal["primary_plus_backup", "offer", "none"]


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
