from __future__ import annotations

from typing import Any, Mapping


def build_allowed_pool_trace(
    *,
    allowed_candidates: list[Mapping[str, Any]],
    filtered_candidates: list[Mapping[str, Any]],
    quality_rejected_candidates: list[Mapping[str, Any]],
    candidate_reviews: list[Mapping[str, Any]],
    scoring_trace: list[Mapping[str, Any]],
) -> dict[str, Any]:
    reviews = {
        str(item.get("candidate_id") or ""): item
        for item in candidate_reviews
    }
    scores = {
        str(item.get("candidate_id") or ""): item
        for item in scoring_trace
    }
    return {
        "artifact_type": "recommendation_allowed_pool_trace",
        "artifact_schema_version": "1.0",
        "node": "candidate_retrieval_guard_scoring",
        "owner": "deterministic",
        "llm_semantic_authority": False,
        "allowed_candidate_ids": [
            str(candidate.get("candidate_id") or "")
            for candidate in allowed_candidates
        ],
        "allowed_candidate_trace": [
            _allowed_trace(candidate, reviews, scores)
            for candidate in allowed_candidates
        ],
        "omitted_candidate_trace": [
            *[
                _omitted_trace(item, "hard_blocker")
                for item in filtered_candidates
            ],
            *[
                _omitted_trace(item, "quality_gate")
                for item in quality_rejected_candidates
            ],
        ],
        "scoring_reason_trace": [
            _scoring_trace(candidate, reviews, scores)
            for candidate in allowed_candidates
        ],
        "runtime_effect_allowed": False,
        "recommendation_served": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "raw_transcript_included": False,
        "blockers": [],
    }


def _allowed_trace(
    candidate: Mapping[str, Any],
    reviews: Mapping[str, Mapping[str, Any]],
    scores: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id") or "")
    review = reviews.get(candidate_id, {})
    score = scores.get(candidate_id, {})
    return {
        "candidate_id": candidate_id,
        "pool_status": "allowed",
        "quality_tier": str(review.get("quality_tier") or ""),
        "quality_score": int(score.get("quality_score") or 0),
        "source_node": "candidate_retrieval_guard_scoring",
    }


def _omitted_trace(item: Mapping[str, Any], stage: str) -> dict[str, Any]:
    return {
        "candidate_id": str(item.get("candidate_id") or ""),
        "omission_stage": stage,
        "reason_codes": [str(reason) for reason in item.get("reason_codes") or []],
        "source_node": "candidate_retrieval_guard_scoring",
    }


def _scoring_trace(
    candidate: Mapping[str, Any],
    reviews: Mapping[str, Mapping[str, Any]],
    scores: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id") or "")
    review = reviews.get(candidate_id, {})
    score = scores.get(candidate_id, {})
    return {
        "candidate_id": candidate_id,
        "quality_score": int(score.get("quality_score") or 0),
        "quality_tier": str(review.get("quality_tier") or ""),
        "scoring_reasons": [
            *[str(item) for item in review.get("quality_signals") or []],
            *[str(item) for item in review.get("soft_penalty_codes") or []],
        ],
        "source_node": "candidate_retrieval_guard_scoring",
    }


__all__ = ["build_allowed_pool_trace"]
