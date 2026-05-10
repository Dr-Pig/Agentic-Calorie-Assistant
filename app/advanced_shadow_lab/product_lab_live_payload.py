from __future__ import annotations

from typing import Any, Mapping


def product_lab_live_provider_payload(
    summary_artifact: Mapping[str, Any],
    *,
    constraints: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "target_surface": "advanced_product_lab_operator_diagnostic",
        "session_id": str(summary_artifact.get("session_id") or ""),
        "turn_count": int(summary_artifact.get("turn_count") or 0),
        "visible_candidate_counts": list(
            summary_artifact.get("visible_candidate_counts") or []
        ),
        "product_runtime_summary": {
            "capabilities_exercised": list(
                summary_artifact.get("product_runtime_capabilities_exercised") or []
            ),
            "recommendation_selected_candidate_ids": list(
                summary_artifact.get("product_recommendation_selected_candidate_ids")
                or []
            ),
            "proactive_candidate_counts": list(
                summary_artifact.get("product_proactive_candidate_counts") or []
            ),
            "outputs_applied_to_chat_surface": bool(
                summary_artifact.get("product_outputs_applied_to_chat_surface")
            ),
            "recommendation_intake_handoff_created": bool(
                summary_artifact.get("product_recommendation_intake_handoff_created")
            ),
            "rescue_commit_handoff_created": bool(
                summary_artifact.get("product_rescue_commit_handoff_created")
            ),
            "proactive_delivery_packet_ready": bool(
                summary_artifact.get("product_proactive_delivery_packet_ready")
            ),
        },
        "chat_action_summary": {
            "action_outcome_count": int(
                summary_artifact.get("lab_chat_action_outcome_count") or 0
            ),
            "action_outcome_types": list(
                summary_artifact.get("lab_chat_action_outcome_types") or []
            ),
            "canonical_mutation_allowed": bool(
                summary_artifact.get("lab_chat_action_canonical_mutation_allowed")
            ),
            "blockers": list(summary_artifact.get("lab_chat_action_blockers") or []),
        },
        "product_loop_closure": {
            "closed": summary_artifact.get(
                "advanced_product_lab_product_loop_closed"
            )
            is True,
            "criteria": dict(
                summary_artifact.get("advanced_product_lab_closure_criteria") or {}
            ),
            "missing": list(
                summary_artifact.get("advanced_product_lab_closure_missing") or []
            ),
        },
        "constraints": dict(constraints),
    }


__all__ = ["product_lab_live_provider_payload"]
