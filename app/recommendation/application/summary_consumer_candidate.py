from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.domain.candidate_quality import (
    AvailabilityPosture,
    EvidencePosture,
    RecommendationCandidateQualityInput,
)


def quality_input_from_prepared_candidate(
    candidate: Mapping[str, Any],
    *,
    violates_negative_preference: bool,
) -> RecommendationCandidateQualityInput:
    return RecommendationCandidateQualityInput(
        candidate_id=str(candidate.get("candidate_id") or "unknown_candidate"),
        title=str(candidate.get("title") or ""),
        estimated_kcal=_optional_int(candidate.get("estimated_kcal")),
        kcal_range_min=_optional_int(candidate.get("kcal_range_min")),
        kcal_range_max=_optional_int(candidate.get("kcal_range_max")),
        remaining_budget_kcal=_optional_int(candidate.get("remaining_budget_kcal")),
        evidence_posture=_evidence_posture(candidate.get("evidence_posture")),
        availability_posture=_availability_posture(candidate.get("availability_posture")),
        realistic_executable=bool(candidate.get("realistic_executable")),
        violates_negative_preference=(
            violates_negative_preference
            or bool(candidate.get("violates_negative_preference"))
        ),
        user_accessible=bool(candidate.get("user_accessible")),
    )


def _evidence_posture(value: Any) -> EvidencePosture:
    allowed = {"exact", "anchored", "generic", "unknown"}
    return str(value) if value in allowed else "unknown"  # type: ignore[return-value]


def _availability_posture(value: Any) -> AvailabilityPosture:
    allowed = {"available", "likely", "unknown", "unavailable"}
    return str(value) if value in allowed else "unknown"  # type: ignore[return-value]


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


__all__ = ["quality_input_from_prepared_candidate"]
