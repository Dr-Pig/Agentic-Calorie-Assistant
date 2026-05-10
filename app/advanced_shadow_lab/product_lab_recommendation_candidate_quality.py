from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.candidate_quality_gate import (
    evaluate_recommendation_candidate_quality,
)
from app.recommendation.domain.candidate_quality import (
    RecommendationCandidateQualityInput,
    RecommendationCandidateQualityResult,
)


def reviewed_candidate(
    candidate: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], RecommendationCandidateQualityResult]:
    scored = {**candidate, "quality_score": quality_score(candidate, payload)}
    quality = evaluate_recommendation_candidate_quality(_quality_input(scored, payload))
    return scored, candidate_review(scored, quality), quality


def quality_score(candidate: Mapping[str, Any], payload: Mapping[str, Any]) -> int:
    score = 50
    source_type = str(candidate.get("source_type") or "")
    if source_type in {"memory_golden_order", "reviewed_memory_golden_order"}:
        score += 50
    elif source_type == "golden_order":
        score += 25
    if candidate.get("evidence_posture") == "exact":
        score += 8
    if candidate.get("realistic_executable") is True:
        score += 5
    if candidate.get("user_accessible") is True:
        score += 5
    remaining = _remaining_kcal(payload)
    kcal_max = _int_or_none(_mapping(candidate.get("estimated_kcal_range")).get("max"))
    if remaining is not None and kcal_max is not None:
        score += max(min((remaining - kcal_max) // 50, 10), -10)
    return int(score)


def quality_signal(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "quality_score": int(candidate.get("quality_score") or 0),
        "source_type": str(candidate.get("source_type") or ""),
        "source_refs": [str(ref) for ref in candidate.get("source_refs") or []],
    }


def candidate_review(
    candidate: Mapping[str, Any],
    quality: RecommendationCandidateQualityResult,
) -> dict[str, Any]:
    return {
        **_review_base(candidate),
        "hard_gate_status": "allowed",
        "quality_tier": quality.quality_tier,
        "proactive_intensity": quality.proactive_intensity,
        "quality_signals": list(quality.quality_signals),
        "omission_reason_codes": list(quality.disqualifier_flags),
    }


def hard_rejected_review(
    candidate: Mapping[str, Any],
    reasons: list[str],
) -> dict[str, Any]:
    return {
        **_review_base(candidate),
        "hard_gate_status": "rejected",
        "quality_tier": "rejected",
        "proactive_intensity": "none",
        "quality_signals": [],
        "omission_reason_codes": list(reasons),
    }


def pool_decision(candidates: list[Mapping[str, Any]]) -> dict[str, Any]:
    high = [item for item in candidates if item.get("quality_tier") == "high"]
    medium = [item for item in candidates if item.get("quality_tier") == "medium"]
    if high:
        backup_ids = [
            str(item.get("candidate_id") or "") for item in [*high[1:], *medium]
        ][:2]
        if backup_ids:
            return {
                "pool_decision": "primary_plus_backup",
                "primary_candidate_id": str(high[0].get("candidate_id") or ""),
                "backup_candidate_ids": backup_ids,
                "offer_candidate_ids": [],
            }
    if candidates:
        return {
            "pool_decision": "offer",
            "primary_candidate_id": str(candidates[0].get("candidate_id") or ""),
            "backup_candidate_ids": [],
            "offer_candidate_ids": [
                str(item.get("candidate_id") or "") for item in candidates[:3]
            ],
        }
    return {
        "pool_decision": "silent_no_qualified_candidate",
        "primary_candidate_id": "",
        "backup_candidate_ids": [],
        "offer_candidate_ids": [],
    }


def omission_traces(rejected: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "candidate_id": str(item.get("candidate_id") or ""),
            "omission_reason": str((item.get("reason_codes") or [""])[0]),
            "source_node": "candidate_retrieval_guard_scoring",
        }
        for item in rejected
    ]


def sort_key(candidate: Mapping[str, Any]) -> tuple[int, int, str]:
    source_priority = 1 if "memory" in str(candidate.get("source_type") or "") else 0
    return (
        -int(candidate.get("quality_score") or 0),
        -source_priority,
        str(candidate.get("candidate_id") or ""),
    )


def _quality_input(
    candidate: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> RecommendationCandidateQualityInput:
    kcal_range = _mapping(candidate.get("estimated_kcal_range"))
    return RecommendationCandidateQualityInput(
        candidate_id=str(candidate.get("candidate_id") or ""),
        title=str(candidate.get("title") or ""),
        estimated_kcal=_int_or_none(candidate.get("estimated_kcal")),
        kcal_range_min=_int_or_none(kcal_range.get("min")),
        kcal_range_max=_int_or_none(kcal_range.get("max")),
        remaining_budget_kcal=_remaining_kcal(payload),
        evidence_posture=str(candidate.get("evidence_posture") or "unknown"),  # type: ignore[arg-type]
        availability_posture=str(candidate.get("availability_posture") or "unknown"),  # type: ignore[arg-type]
        realistic_executable=candidate.get("realistic_executable") is True,
        violates_negative_preference=False,
        user_accessible=candidate.get("user_accessible") is True,
    )


def _review_base(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "evidence_posture": str(candidate.get("evidence_posture") or "unknown"),
        "availability_posture": str(candidate.get("availability_posture") or "unknown"),
        "executable_posture": "realistic"
        if candidate.get("realistic_executable") is True
        else "not_realistic",
        "budget_fit_posture": _budget_fit_posture(candidate),
    }


def _budget_fit_posture(candidate: Mapping[str, Any]) -> str:
    max_kcal = _int_or_none(_mapping(candidate.get("estimated_kcal_range")).get("max"))
    return "estimated" if max_kcal is not None else "missing_estimate"


def _remaining_kcal(payload: Mapping[str, Any]) -> int | None:
    return _int_or_none(_mapping(payload.get("current_budget_view")).get("remaining_kcal"))


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "hard_rejected_review",
    "omission_traces",
    "pool_decision",
    "quality_signal",
    "reviewed_candidate",
    "sort_key",
]
