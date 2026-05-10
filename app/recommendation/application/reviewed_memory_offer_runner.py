from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.offer_shadow_packet import (
    build_recommendation_offer_shadow_packet,
)
from app.recommendation.application.reviewed_memory_candidate_bridge import (
    build_reviewed_memory_recommendation_three_node_payload,
)
from app.recommendation.application.three_node_shadow_contract import (
    run_recommendation_three_node_shadow,
)
from app.recommendation.application.three_node_summary_bridge import (
    build_summary_quality_report_from_three_node_shadow_artifact,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.reviewed_memory_offer_runner"
)


def build_reviewed_memory_recommendation_offer_packet(
    *,
    memory_summary_projection: Mapping[str, Any],
    remaining_budget_kcal: int,
    requested_surface: str = "chat",
) -> dict[str, Any]:
    payload = build_reviewed_memory_recommendation_three_node_payload(
        memory_summary_projection,
        remaining_budget_kcal=remaining_budget_kcal,
    )
    bridge_blockers = [
        f"reviewed_memory_bridge.{blocker}"
        for blocker in payload.get("bridge_blockers") or []
    ]
    three_node = run_recommendation_three_node_shadow(payload)
    report = build_summary_quality_report_from_three_node_shadow_artifact(
        memory_summary_projection=memory_summary_projection,
        three_node_artifact=three_node,
        source_payload=payload,
    )
    packet = dict(
        build_recommendation_offer_shadow_packet(
            recommendation_quality_report=report,
            three_node_artifact=three_node,
            requested_surface=requested_surface,
        )
    )
    if bridge_blockers:
        _block_for_bridge_claim_drift(packet, bridge_blockers)
    return _with_runner_trace(
        packet,
        memory_summary_projection=memory_summary_projection,
        payload=payload,
        three_node=three_node,
        report=report,
    )


def _block_for_bridge_claim_drift(
    packet: dict[str, Any],
    bridge_blockers: list[str],
) -> None:
    packet["status"] = "blocked"
    packet["blockers"] = [*bridge_blockers, *list(packet.get("blockers") or [])]
    packet["selected_primary"] = None
    packet["backup_candidates"] = []
    packet["offer_synthesis_trace"] = {}
    packet["ux_packet"] = None


def _with_runner_trace(
    packet: dict[str, Any],
    *,
    memory_summary_projection: Mapping[str, Any],
    payload: Mapping[str, Any],
    three_node: Mapping[str, Any],
    report: Mapping[str, Any],
) -> dict[str, Any]:
    packet.update(
        {
            "new_report_family_created": False,
            "reviewed_memory_offer_runner_used": True,
            "reviewed_memory_projection_used": bool(
                payload.get("reviewed_memory_projection_used")
            ),
            "source_memory_artifact_type": memory_summary_projection.get(
                "artifact_type"
            ),
        }
    )
    packet["runner_stage_trace"] = [
        _stage("reviewed_memory_projection", memory_summary_projection),
        _stage("recommendation_three_node_shadow", three_node),
        _stage("recommendation_summary_quality", report),
        _stage("recommendation_offer_shadow_packet", packet),
    ]
    return packet


def _stage(stage: str, artifact: Mapping[str, Any]) -> dict[str, str]:
    return {
        "stage": stage,
        "artifact_type": str(artifact.get("artifact_type") or ""),
        "status": str(artifact.get("status") or ""),
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_reviewed_memory_recommendation_offer_packet",
]
