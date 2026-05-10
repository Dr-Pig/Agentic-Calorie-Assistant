from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.offer_shadow_packet_parts import (
    backup_blockers,
    backup_candidate_ids,
    build_offer_packet_artifact,
    candidate_evaluation,
    candidate_summary,
    input_blockers,
    mapping,
    primary_blockers,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.offer_shadow_packet"
)

def build_recommendation_offer_shadow_packet(
    *,
    recommendation_quality_report: Mapping[str, Any],
    three_node_artifact: Mapping[str, Any],
    requested_surface: str = "chat",
) -> dict[str, Any]:
    blockers = input_blockers(recommendation_quality_report, three_node_artifact)
    selected_id = str(three_node_artifact.get("selected_candidate_id") or "")
    primary = candidate_evaluation(recommendation_quality_report, selected_id)
    offer = mapping(three_node_artifact.get("shadow_offer_packet"))
    blockers.extend(primary_blockers(primary, offer))
    blockers.extend(
        backup_blockers(
            recommendation_quality_report,
            backup_candidate_ids=backup_candidate_ids(offer),
        )
    )
    if not str(offer.get("explanation") or "").strip():
        blockers.append("offer_synthesis.explanation_missing")

    if blockers:
        return build_offer_packet_artifact(
            status="blocked",
            blockers=blockers,
            report=recommendation_quality_report,
            three_node_artifact=three_node_artifact,
            selected_primary=None,
            backup_candidates=[],
            offer_synthesis_trace={},
            ux_packet=None,
        )

    backup_candidates = [
        candidate_summary(candidate_evaluation(recommendation_quality_report, backup_id))
        for backup_id in backup_candidate_ids(offer)
    ]
    return build_offer_packet_artifact(
        status="pass",
        blockers=[],
        report=recommendation_quality_report,
        three_node_artifact=three_node_artifact,
        selected_primary=candidate_summary(primary),
        backup_candidates=backup_candidates,
        offer_synthesis_trace={
            "owner": "llm_fixture",
            "selected_candidate_id": selected_id,
            "backup_candidate_ids": backup_candidate_ids(offer),
            "explanation_present": True,
        },
        ux_packet={
            "surface": requested_surface,
            "serve_allowed": False,
            "primary_candidate_id": selected_id,
            "backup_candidate_ids": backup_candidate_ids(offer),
            "explanation": str(offer.get("explanation") or ""),
        },
    )


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_recommendation_offer_shadow_packet",
]
