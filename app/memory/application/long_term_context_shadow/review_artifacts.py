from __future__ import annotations

from collections import Counter
from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.utils import _model_dict
from app.memory.domain.long_term_context_candidates import (
    ContextValueReviewItem,
    LongTermContextCandidate,
)


def build_review_artifacts(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
    context_items: list[ContextValueReviewItem],
) -> dict[str, dict[str, Any]]:
    return {
        "long_term_memory_candidate_review": _memory_candidate_review_artifact(
            fixture,
            candidates,
        ),
        "context_value_review_queue": _context_value_review_queue_artifact(
            fixture,
            context_items,
        ),
        "context_signal_quality_scorecard": _context_signal_quality_scorecard_artifact(
            fixture,
            candidates,
        ),
    }


def _memory_candidate_review_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    candidate_dicts = [_model_dict(candidate) for candidate in candidates]
    return _base_artifact(
        artifact_type="long_term_memory_candidate_review",
        fixture=fixture,
        extra={
            "summary": {
                "candidate_count": len(candidates),
                "pattern_candidate_count": sum(
                    1
                    for candidate in candidates
                    if candidate.candidate_type == "pattern"
                ),
                "preference_candidate_count": sum(
                    1
                    for candidate in candidates
                    if candidate.candidate_type
                    in {
                        "preference",
                        "food_preference",
                        "temporary_preference",
                    }
                ),
                "negative_preference_candidate_count": sum(
                    1
                    for candidate in candidates
                    if candidate.candidate_type == "negative_preference"
                ),
                "golden_order_candidate_count": sum(
                    1
                    for candidate in candidates
                    if candidate.candidate_type == "golden_order"
                ),
                "durable_memory_written": False,
                "domain_candidate_counts": dict(
                    sorted(
                        Counter(
                            candidate.candidate_type for candidate in candidates
                        ).items()
                    )
                ),
            },
            "candidates": candidate_dicts,
        },
    )


def _context_value_review_queue_artifact(
    fixture: dict[str, Any],
    items: list[ContextValueReviewItem],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="context_value_review_queue",
        fixture=fixture,
        extra={
            "summary": {"review_item_count": len(items)},
            "items": [_model_dict(item) for item in items],
        },
    )


def _context_signal_quality_scorecard_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    scores = [_context_signal_score(candidate) for candidate in candidates]
    return _base_artifact(
        artifact_type="context_signal_quality_scorecard",
        fixture=fixture,
        extra={
            "runtime_effect_allowed": False,
            "scorecard_used_for_runtime_ranking": False,
            "score_dimensions": [
                "evidence_strength",
                "context_value",
                "harm_if_wrong",
                "expiry_sensitivity",
                "recommended_review_action",
            ],
            "candidate_scores": scores,
            "consumer_rollups": _consumer_score_rollups(scores),
        },
    )


def _context_signal_score(candidate: LongTermContextCandidate) -> dict[str, Any]:
    evidence_strength = _evidence_strength(candidate)
    context_value_level = _context_value_level(candidate, evidence_strength)
    harm_level = _harm_if_wrong_level(candidate)
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "intended_consumers": candidate.intended_consumers,
        "evidence_count": candidate.evidence_count,
        "confidence": candidate.confidence,
        "evidence_strength": evidence_strength,
        "context_value_level": context_value_level,
        "harm_if_wrong_level": harm_level,
        "expiry_sensitive": candidate.candidate_type == "temporary_preference",
        "recommended_review_action": _scorecard_review_action(
            candidate,
            context_value_level,
            harm_level,
        ),
        "runtime_effect_allowed": False,
    }


def _evidence_strength(candidate: LongTermContextCandidate) -> str:
    if candidate.confidence >= 0.75 or candidate.evidence_count >= 3:
        return "high"
    if candidate.confidence >= 0.5 or candidate.evidence_count >= 2:
        return "medium"
    return "low"


def _context_value_level(
    candidate: LongTermContextCandidate,
    evidence_strength: str,
) -> str:
    if candidate.candidate_type in {
        "golden_order",
        "negative_preference",
        "temporary_preference",
    }:
        return "high" if evidence_strength in {"medium", "high"} else "medium"
    if candidate.candidate_type in {
        "intake_estimation_bias",
        "user_language_pattern",
        "food_preference",
    }:
        return "medium" if evidence_strength == "low" else "high"
    if candidate.candidate_type in {
        "app_usage_style",
        "interaction_preference",
        "conversation_recall_context",
    }:
        return "medium"
    return evidence_strength


def _harm_if_wrong_level(candidate: LongTermContextCandidate) -> str:
    if candidate.candidate_type in {
        "intake_estimation_bias",
        "negative_preference",
        "temporary_preference",
        "conversation_recall_context",
    }:
        return "high"
    if candidate.candidate_type in {
        "app_usage_style",
        "interaction_preference",
        "logging_adherence_pattern",
        "golden_order",
    }:
        return "medium"
    return "low"


def _scorecard_review_action(
    candidate: LongTermContextCandidate,
    context_value_level: str,
    harm_level: str,
) -> str:
    if candidate.candidate_type in {
        "negative_preference",
        "temporary_preference",
        "golden_order",
        "food_preference",
    }:
        return "ask_user_to_confirm"
    if harm_level == "high" or context_value_level == "low":
        return "keep_shadowing"
    return "keep_shadowing"


def _consumer_score_rollups(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    consumers = sorted(
        {
            consumer
            for score in scores
            for consumer in score.get("intended_consumers", [])
        }
    )
    return [
        {
            "consumer_id": consumer,
            "candidate_count": sum(
                1 for score in scores if consumer in score.get("intended_consumers", [])
            ),
            "candidate_ids": [
                score["candidate_id"]
                for score in scores
                if consumer in score.get("intended_consumers", [])
            ],
            "runtime_effect_allowed": False,
        }
        for consumer in consumers
    ]
