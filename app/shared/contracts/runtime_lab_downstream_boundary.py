from __future__ import annotations

from typing import Any, Mapping


CONSUMER_SUMMARY_ARTIFACT = "runtime_lab_memory_consumer_summary_projection"
CONSUMER_SUMMARY_CLAIM_FLAGS = (
    "runtime_effect_allowed",
    "durable_product_memory_written",
    "manager_context_packet_changed",
    "recommendation_served",
    "proactive_sent",
    "rescue_proposal_committed",
    "retrieval_ranking_changed",
)
ACTIVATION_BOUNDARIES = {
    "durable_memory_activation_ready": False,
    "manager_context_packet_memory_ready": False,
    "user_facing_memory_ready": False,
    "scheduler_or_proactive_send_ready": False,
    "recommendation_serving_ready": False,
    "rescue_proposal_commit_ready": False,
}
NEXT_ALLOWED_DOWNSTREAM_SLICES = [
    "recommendation_shadow_summary_consumer",
    "rescue_shadow_summary_consumer",
    "proactive_no_send_summary_consumer",
]


def consumer_summary_projection_blockers(
    consumer_summary_projection: Mapping[str, Any],
) -> list[str]:
    if not consumer_summary_projection:
        return []
    blockers: list[str] = []
    if consumer_summary_projection.get("artifact_type") != CONSUMER_SUMMARY_ARTIFACT:
        blockers.append("consumer_summary_projection.unsupported_artifact_type")
    if consumer_summary_projection.get("status") != "pass":
        blockers.append("consumer_summary_projection.status_not_pass")
    for flag in CONSUMER_SUMMARY_CLAIM_FLAGS:
        if consumer_summary_projection.get(flag) is True:
            blockers.append(f"consumer_summary_projection.{flag}")
    return blockers


def downstream_shadow_readiness(
    status: str,
    consumer_summary_projection: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    if status != "pass":
        return _readiness_for("blocked_by_claim_boundary")
    if consumer_summary_projection:
        value = {
            "status": "ready_for_shadow_build",
            "allowed_input": CONSUMER_SUMMARY_ARTIFACT,
        }
        return {
            "recommendation_read_only": dict(value),
            "rescue_read_only": dict(value),
            "proactive_read_only": dict(value),
        }
    return _readiness_for("ready_for_shadow_planning")


def next_allowed_downstream_slices(
    status: str,
    consumer_summary_projection: Mapping[str, Any],
) -> list[str]:
    if status != "pass" or not consumer_summary_projection:
        return []
    return list(NEXT_ALLOWED_DOWNSTREAM_SLICES)


def _readiness_for(status: str) -> dict[str, dict[str, str]]:
    return {
        "recommendation_read_only": {"status": status},
        "rescue_read_only": {"status": status},
        "proactive_read_only": {"status": status},
    }


__all__ = [
    "ACTIVATION_BOUNDARIES",
    "consumer_summary_projection_blockers",
    "downstream_shadow_readiness",
    "next_allowed_downstream_slices",
]
