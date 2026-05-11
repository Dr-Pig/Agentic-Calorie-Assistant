from __future__ import annotations

from typing import Any, Mapping


PRODUCT_CAPABILITIES = [
    "long_term_memory",
    "recommendation",
    "rescue",
    "calibration",
    "proactive",
    "chat_surface",
]


def turn_product_summary(turn_artifact: Mapping[str, Any]) -> dict[str, Any]:
    recommendation = _mapping(turn_artifact.get("product_lab_recommendation_artifact"))
    rescue = _mapping(turn_artifact.get("product_lab_rescue_artifact"))
    proactive = _mapping(turn_artifact.get("product_lab_proactive_artifact"))
    packet = _mapping(turn_artifact.get("lab_chat_response_packet"))
    selected = _mapping(_mapping(recommendation.get("offer_synthesis")).get("selected_primary"))
    intake = _mapping(recommendation.get("pending_intake_handoff_packet"))
    rescue_commit = _mapping(rescue.get("pending_rescue_commit_packet"))
    proactive_delivery = _mapping(proactive.get("delivery_packet"))
    proactive_review = _mapping(proactive.get("pre_delivery_review"))
    return {
        "product_recommendation_selected_candidate_id": str(
            selected.get("candidate_id") or ""
        ),
        "product_rescue_presented_to_lab": rescue.get("proposal_presented_to_lab") is True,
        "product_proactive_candidate_count": int(
            proactive_review.get("candidate_review_count")
            or proactive.get("candidate_count")
            or 0
        ),
        "product_proactive_delivered_candidate_count": int(
            proactive.get("candidate_count") or 0
        ),
        "product_outputs_applied_to_chat_surface": (
            packet.get("product_outputs_applied") is True
        ),
        "product_recommendation_intake_handoff_created": (
            intake.get("lab_intake_intent_created") is True
        ),
        "product_rescue_commit_handoff_created": (
            rescue_commit.get("lab_rescue_intent_created") is True
        ),
        "product_proactive_delivery_packet_ready": (
            proactive_delivery.get("chat_delivery_allowed") is True
        ),
    }


def session_product_summary(
    turn_summaries: list[Mapping[str, Any]],
) -> dict[str, Any]:
    outputs_applied = [
        item.get("product_outputs_applied_to_chat_surface") is True
        for item in turn_summaries
    ]
    return {
        "product_runtime_capabilities_exercised": list(PRODUCT_CAPABILITIES),
        "product_recommendation_selected_candidate_ids": [
            str(item.get("product_recommendation_selected_candidate_id") or "")
            for item in turn_summaries
        ],
        "product_proactive_candidate_counts": [
            int(item.get("product_proactive_candidate_count") or 0)
            for item in turn_summaries
        ],
        "product_outputs_applied_to_chat_surface": bool(outputs_applied)
        and all(outputs_applied),
        "product_recommendation_intake_handoff_created": all(
            item.get("product_recommendation_intake_handoff_created") is True
            for item in turn_summaries
        ),
        "product_rescue_commit_handoff_created": all(
            item.get("product_rescue_commit_handoff_created") is True
            for item in turn_summaries
        ),
        "product_proactive_delivery_packet_ready": all(
            item.get("product_proactive_delivery_packet_ready") is True
            for item in turn_summaries
        ),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "PRODUCT_CAPABILITIES",
    "session_product_summary",
    "turn_product_summary",
]
