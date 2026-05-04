from __future__ import annotations

from collections import Counter
from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.review_artifacts import (
    _harm_if_wrong_level,
)
from app.memory.application.long_term_context_shadow.serialization import _list_of_dicts
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _context_value_scoring_v2_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    scores = [_context_value_score_v2(fixture, candidate) for candidate in candidates]
    action_rollups = Counter(score["recommended_action"] for score in scores)
    bucket_rollups = Counter(score["review_priority_bucket"] for score in scores)
    return _base_artifact(
        artifact_type="context_value_scoring_v2",
        fixture=fixture,
        extra={
            "runtime_effect_allowed": False,
            "scorecard_used_for_runtime_ranking": False,
            "score_dimensions": [
                "evidence_strength_score",
                "recency_score",
                "frequency_score",
                "consumer_value_score",
                "harm_if_wrong_score",
                "contradiction_penalty",
                "review_priority_score",
            ],
            "candidate_scores": scores,
            "action_rollups": dict(sorted(action_rollups.items())),
            "bucket_rollups": dict(sorted(bucket_rollups.items())),
            "all_candidates_have_product_capability_value": all(
                bool(score["product_capability_value"]) for score in scores
            ),
        },
    )


def _context_value_score_v2(
    fixture: dict[str, Any],
    candidate: LongTermContextCandidate,
) -> dict[str, Any]:
    evidence_strength_score = round(
        max(candidate.confidence, min(candidate.evidence_count / 3, 1.0)),
        3,
    )
    frequency_score = round(min(candidate.evidence_count / 5, 1.0), 3)
    recency_score = _recency_score(candidate)
    consumer_value_score = _consumer_value_score(candidate)
    harm_level = _harm_if_wrong_level(candidate)
    harm_if_wrong_score = _harm_score(harm_level)
    contradiction_penalty = _contradiction_penalty(fixture, candidate)
    review_priority_score = round(
        max(
            0.0,
            min(
                1.0,
                evidence_strength_score * 0.22
                + recency_score * 0.13
                + frequency_score * 0.15
                + consumer_value_score * 0.25
                + harm_if_wrong_score * 0.25
                - contradiction_penalty,
            ),
        ),
        3,
    )
    review_priority_bucket = _review_priority_bucket(review_priority_score)
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "intended_consumers": candidate.intended_consumers,
        "evidence_count": candidate.evidence_count,
        "confidence": candidate.confidence,
        "evidence_strength_score": evidence_strength_score,
        "recency_score": recency_score,
        "frequency_score": frequency_score,
        "consumer_value_score": consumer_value_score,
        "harm_if_wrong_score": harm_if_wrong_score,
        "harm_if_wrong_level": harm_level,
        "contradiction_penalty": contradiction_penalty,
        "review_priority_score": review_priority_score,
        "review_priority_bucket": review_priority_bucket,
        "recommended_action": _scoring_recommended_action(
            candidate,
            review_priority_bucket,
            contradiction_penalty,
        ),
        "product_capability_value": _product_capability_value(candidate),
        "runtime_effect_allowed": False,
    }


def _recency_score(candidate: LongTermContextCandidate) -> float:
    posture_scores = {
        "fresh": 1.0,
        "recent": 0.8,
        "unknown": 0.35,
        "stale": 0.15,
    }
    return posture_scores.get(candidate.freshness_posture, 0.35)


def _consumer_value_score(candidate: LongTermContextCandidate) -> float:
    consumers = set(candidate.intended_consumers)
    if consumers.intersection(
        {
            "recommendation",
            "intake_clarification",
            "calibration",
            "nutrition_clarify_priority",
        }
    ):
        return 0.9
    if consumers.intersection({"chat_context", "proactive", "response_generation"}):
        return 0.7
    if consumers.intersection({"rescue_later", "ux"}):
        return 0.55
    return 0.35


def _harm_score(harm_level: str) -> float:
    if harm_level == "high":
        return 0.9
    if harm_level == "medium":
        return 0.55
    return 0.2


def _contradiction_penalty(
    fixture: dict[str, Any],
    candidate: LongTermContextCandidate,
) -> float:
    if candidate.candidate_type != "negative_preference":
        return 0.0
    value = str(candidate.payload.get("value") or "").lower()
    if not value:
        return 0.0
    pool_names = [
        str(item.get("name") or "").lower()
        for item in _list_of_dicts(fixture.get("candidate_pool"))
    ]
    return 0.25 if any(value in name for name in pool_names) else 0.0


def _review_priority_bucket(score: float) -> str:
    if score >= 0.65:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _scoring_recommended_action(
    candidate: LongTermContextCandidate,
    bucket: str,
    contradiction_penalty: float,
) -> str:
    if not candidate.intended_consumers:
        return "discard"
    if contradiction_penalty > 0:
        return "ask_user_to_confirm"
    if candidate.candidate_type in {
        "negative_preference",
        "temporary_preference",
        "golden_order",
        "food_preference",
    }:
        return "ask_user_to_confirm" if bucket in {"high", "medium"} else "discard"
    if _harm_if_wrong_level(candidate) == "high":
        return "keep_shadowing"
    return "keep_shadowing" if bucket in {"high", "medium"} else "discard"


def _product_capability_value(candidate: LongTermContextCandidate) -> str:
    if candidate.candidate_type in {
        "golden_order",
        "food_preference",
        "negative_preference",
        "temporary_preference",
    }:
        return "direct_recommendation_or_intake_gain"
    if candidate.candidate_type in {
        "intake_estimation_bias",
        "logging_adherence_pattern",
    }:
        return "calibration_or_clarification_gain"
    if candidate.candidate_type in {
        "app_usage_style",
        "interaction_preference",
        "conversation_recall_context",
        "user_language_pattern",
    }:
        return "chat_or_proactive_experience_gain"
    return "broad_product_context_gain"
