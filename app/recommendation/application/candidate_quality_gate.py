from __future__ import annotations

from app.recommendation.domain.candidate_quality import (
    RecommendationCandidatePoolDecisionResult,
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
    if candidate.estimated_kcal is not None and candidate.estimated_kcal <= 0:
        disqualifiers.append("invalid_kcal_estimate")
    if candidate.kcal_range_min is not None and candidate.kcal_range_min <= 0:
        disqualifiers.append("invalid_kcal_estimate")
    if candidate.kcal_range_max is not None and candidate.kcal_range_max <= 0:
        disqualifiers.append("invalid_kcal_estimate")
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


def decide_recommendation_candidate_pool(
    candidates: list[RecommendationCandidateQualityInput],
) -> RecommendationCandidatePoolDecisionResult:
    evaluations = [evaluate_recommendation_candidate_quality(item) for item in candidates]
    passed = [item for item in evaluations if item.passed]
    high = [item for item in passed if item.quality_tier == "high"]
    medium = [item for item in passed if item.quality_tier == "medium"]
    rejected_ids = [item.candidate_id for item in evaluations if not item.passed]

    if high:
        primary = high[0]
        backup_ids = [item.candidate_id for item in [*high[1:], *medium]][:2]
        if backup_ids:
            return RecommendationCandidatePoolDecisionResult(
                pool_decision="primary_plus_backup",
                primary_candidate_id=primary.candidate_id,
                backup_candidate_ids=backup_ids,
                rejected_candidate_ids=rejected_ids,
                candidate_quality=evaluations,
            )

    if passed:
        return RecommendationCandidatePoolDecisionResult(
            pool_decision="offer",
            offer_candidate_ids=[item.candidate_id for item in passed[:3]],
            rejected_candidate_ids=rejected_ids,
            candidate_quality=evaluations,
        )

    return RecommendationCandidatePoolDecisionResult(
        pool_decision="silent_no_qualified_candidate",
        rejected_candidate_ids=rejected_ids,
        candidate_quality=evaluations,
    )


def _over_budget(candidate: RecommendationCandidateQualityInput) -> bool:
    if candidate.remaining_budget_kcal is None:
        return False
    kcal_to_check = candidate.kcal_range_max or candidate.estimated_kcal
    if kcal_to_check is None:
        return False
    return kcal_to_check > candidate.remaining_budget_kcal


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "decide_recommendation_candidate_pool",
    "evaluate_recommendation_candidate_quality",
]
