from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.candidate_quality_gate import (
    decide_recommendation_candidate_pool,
)
from app.recommendation.application.summary_consumer_candidate import (
    quality_input_from_prepared_candidate,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.summary_pool_posture"
)
BLOCKED_POSTURE = {
    "pool_decision": "blocked",
    "primary_candidate_id": None,
    "backup_candidate_ids": [],
    "offer_candidate_ids": [],
    "rejected_candidate_ids": [],
}


def build_summary_pool_posture(
    *,
    prepared_candidates: list[Mapping[str, Any]],
    negative_preference_ids: set[str],
) -> dict[str, Any]:
    decision = decide_recommendation_candidate_pool(
        [
            quality_input_from_prepared_candidate(
                candidate,
                violates_negative_preference=_negative_match(
                    candidate,
                    negative_preference_ids,
                ),
            )
            for candidate in prepared_candidates
        ]
    )
    return {
        "pool_decision": decision.pool_decision,
        "primary_candidate_id": decision.primary_candidate_id,
        "backup_candidate_ids": list(decision.backup_candidate_ids),
        "offer_candidate_ids": list(decision.offer_candidate_ids),
        "rejected_candidate_ids": list(decision.rejected_candidate_ids),
    }


def _negative_match(
    candidate: Mapping[str, Any],
    negative_preference_ids: set[str],
) -> bool:
    source_refs = [str(ref) for ref in candidate.get("source_refs", [])]
    return any(
        ref == candidate_id or ref.endswith(f":{candidate_id}")
        for ref in source_refs
        for candidate_id in negative_preference_ids
    )


__all__ = [
    "BLOCKED_POSTURE",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_summary_pool_posture",
]
