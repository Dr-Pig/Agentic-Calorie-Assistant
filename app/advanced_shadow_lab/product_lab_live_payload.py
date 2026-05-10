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
        },
        "constraints": dict(constraints),
    }


__all__ = ["product_lab_live_provider_payload"]
