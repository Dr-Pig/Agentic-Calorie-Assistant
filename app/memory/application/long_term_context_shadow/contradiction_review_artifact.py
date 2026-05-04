from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.serialization import _list_of_dicts
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _context_quality_contradiction_review_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    review_items = _contradiction_review_items(fixture, candidates)
    return _base_artifact(
        artifact_type="context_quality_contradiction_review_queue",
        fixture=fixture,
        extra={
            "runtime_blocking_claimed": False,
            "contradiction_count": sum(
                1 for item in review_items if item["contradiction_detected"]
            ),
            "quality_dimensions": [
                "evidence_strength",
                "freshness",
                "consumer_scope",
                "contradiction_risk",
                "promotion_readiness",
            ],
            "review_items": review_items,
        },
    )


def _contradiction_review_items(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> list[dict[str, Any]]:
    pool_names = [
        str(item.get("name") or "").lower()
        for item in _list_of_dicts(fixture.get("candidate_pool"))
    ]
    negative_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_type == "negative_preference"
    ]
    conflicting_negative_ids: list[str] = []
    for candidate in negative_candidates:
        value = str(candidate.payload.get("value") or "").lower()
        if value and any(value in name for name in pool_names):
            conflicting_negative_ids.append(candidate.candidate_id)

    items = [
        {
            "check_id": "negative_preference_vs_candidate_pool",
            "candidate_ids": conflicting_negative_ids,
            "contradiction_detected": bool(conflicting_negative_ids),
            "review_status": "pending",
            "recommended_action": "keep_shadowing",
            "risk_if_wrong": (
                "Could recommend or suppress a food based on conflicting preference evidence."
            ),
            "runtime_effect_allowed": False,
        },
        {
            "check_id": "temporary_preference_expiry_review",
            "candidate_ids": [
                candidate.candidate_id
                for candidate in candidates
                if candidate.candidate_type == "temporary_preference"
            ],
            "contradiction_detected": False,
            "review_status": "pending",
            "recommended_action": "verify_expiry_before_future_promotion",
            "risk_if_wrong": "Could keep expired temporary context active too long.",
            "runtime_effect_allowed": False,
        },
    ]
    return items
