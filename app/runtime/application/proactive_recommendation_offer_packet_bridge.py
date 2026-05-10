from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_recommendation_offer_packet_bridge"
)

SUPPORTED_PACKET = "recommendation_offer_shadow_packet"
CLAIM_FLAGS = (
    "runtime_effect_allowed",
    "mainline_runtime_connected",
    "mainline_route_or_api_mount_allowed",
    "production_scheduler_delivery_allowed",
    "production_db_migration_allowed",
    "canonical_product_mutation_allowed",
    "canonical_mutation_changed",
    "durable_product_memory_written",
    "manager_context_packet_changed",
    "manager_context_injected",
    "user_facing_behavior_changed",
    "live_provider_used",
    "recommendation_served",
    "proactive_sent",
    "intake_committed",
    "intake_handoff_created",
    "pending_meal_intent_created",
    "meal_thread_mutated",
    "day_budget_mutated",
    "body_plan_mutated",
    "mutation_changed",
    "product_readiness_claimed",
)
BASE_REVIEW = {
    "artifact_type": "recommendation_offer_packet_no_send_review",
    "source_report_used": False,
    "source_offer_packet_used": False,
    "source_offer_packet_artifact_type": None,
    "recommendation_pool_decision": "not_evaluated",
    "prompt_posture": "not_applicable",
    "actual_candidates_included": False,
    "candidate_ids_exposed": False,
    "source_ref_count": 0,
    "source_refs_preserved": False,
    "redaction": {
        "candidate_ids_removed": True,
        "candidate_titles_removed": True,
        "candidate_copy_removed": True,
    },
    "runtime_effect_allowed": False,
    "recommendation_served": False,
    "proactive_sent": False,
    "scheduler_enabled": False,
    "live_delivery_allowed": False,
    "scheduler_activation_allowed": False,
    "manager_context_injected": False,
    "canonical_product_mutation_allowed": False,
}


def build_recommendation_offer_packet_no_send_review(
    offer_packet: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = _packet_blockers(offer_packet)
    if blockers:
        return _review(
            status="blocked",
            packet=offer_packet,
            source_used=False,
            blockers=blockers,
            reviewer_next_step="fix_recommendation_offer_packet_before_review",
        )
    return _review(
        status="candidate_for_human_review",
        packet=offer_packet,
        source_used=True,
        blockers=[],
        reviewer_next_step="review_invitation_posture_without_serving_candidates",
    )


def _review(
    *,
    status: str,
    packet: Mapping[str, Any],
    source_used: bool,
    blockers: list[str],
    reviewer_next_step: str,
) -> dict[str, Any]:
    source_refs = _source_refs(packet) if source_used else []
    return {
        **dict(BASE_REVIEW),
        "status": status,
        "source_offer_packet_used": source_used,
        "source_report_used": source_used,
        "source_offer_packet_artifact_type": packet.get("artifact_type"),
        "recommendation_pool_decision": (
            "offer_packet_available" if source_used else "blocked"
        ),
        "prompt_posture": "invitation_only" if source_used else "not_applicable",
        "source_ref_count": len(source_refs),
        "source_refs_preserved": bool(source_refs),
        "blockers": blockers,
        "review_decision": {
            "status": status,
            "reviewer_next_step": reviewer_next_step,
        },
    }


def _packet_blockers(packet: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != SUPPORTED_PACKET:
        blockers.append("recommendation_offer_packet.unsupported_artifact_type")
    if packet.get("status") != "pass":
        blockers.append("recommendation_offer_packet.status_not_pass")
    if packet.get("ux_packet", {}).get("serve_allowed") is True:
        blockers.append("recommendation_offer_packet.ux_packet.serve_allowed")
    for flag in CLAIM_FLAGS:
        if packet.get(flag) is True:
            blockers.append(f"recommendation_offer_packet.{flag}")
    return blockers


def _source_refs(packet: Mapping[str, Any]) -> list[str]:
    primary = packet.get("selected_primary")
    if not isinstance(primary, Mapping):
        return []
    return [
        str(ref)
        for ref in primary.get("source_refs") or []
        if str(ref).startswith("memory_candidate:")
    ]


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_recommendation_offer_packet_no_send_review",
]
