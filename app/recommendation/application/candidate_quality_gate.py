from __future__ import annotations

from app.recommendation.domain.candidate_quality import (
    RecommendationCandidateQualityInput,
    RecommendationCandidateQualityResult,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("recommendation.application.candidate_quality_gate")


def evaluate_recommendation_candidate_quality(
    candidate: RecommendationCandidateQualityInput,
) -> RecommendationCandidateQualityResult:
    disqualifiers: list[str] = []
    signals: list[str] = []

    if candidate.violates_negative_preference:
        disqualifiers.append("negative_preference")
    if not candidate.realistic_executable:
        disqualifiers.append("not_realistic_executable")
    if not candidate.user_accessible:
        disqualifiers.append("not_user_accessible")
    if candidate.availability_posture == "unavailable":
        disqualifiers.append("unavailable")
    if candidate.estimated_kcal is None and candidate.kcal_range_max is None:
        disqualifiers.append("missing_kcal_estimate")
    if candidate.evidence_posture in {"generic", "unknown"}:
        disqualifiers.append(f"{candidate.evidence_posture}_evidence_not_proactive")
    if _over_budget(candidate):
        disqualifiers.append("budget_mismatch")

    if disqualifiers:
        return RecommendationCandidateQualityResult(
            candidate_id=candidate.candidate_id,
            passed=False,
            quality_tier="rejected",
            proactive_intensity="none",
            disqualifier_flags=disqualifiers,
            quality_signals=signals,
        )

    signals.append(f"evidence:{candidate.evidence_posture}")
    signals.append(f"availability:{candidate.availability_posture}")
    signals.append("budget_fit")

    if candidate.availability_posture in {"available", "likely"}:
        return RecommendationCandidateQualityResult(
            candidate_id=candidate.candidate_id,
            passed=True,
            quality_tier="high",
            proactive_intensity="primary_plus_backup",
            quality_signals=signals,
        )

    return RecommendationCandidateQualityResult(
        candidate_id=candidate.candidate_id,
        passed=True,
        quality_tier="medium",
        proactive_intensity="offer",
        quality_signals=signals,
    )


def _over_budget(candidate: RecommendationCandidateQualityInput) -> bool:
    if candidate.remaining_budget_kcal is None:
        return False
    kcal_to_check = candidate.kcal_range_max or candidate.estimated_kcal
    if kcal_to_check is None:
        return False
    return kcal_to_check > candidate.remaining_budget_kcal
