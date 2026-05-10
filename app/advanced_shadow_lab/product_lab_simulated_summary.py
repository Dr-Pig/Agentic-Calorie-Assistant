from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS


def build_simulated_dogfood_summary(
    session_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_simulated_dogfood_summary",
        "artifact_schema_version": "1.0",
        "status": str(session_artifact.get("status") or "blocked"),
        "owner": "scripts/run_advanced_product_lab_simulated_dogfood.py",
        "consumer": "advanced_product_lab_operator_review",
        "retirement_trigger": "approved_advanced_product_lab_live_diagnostic_plan",
        "session_id": str(session_artifact.get("session_id") or ""),
        "turn_count": int(session_artifact.get("turn_count") or 0),
        "visible_candidate_counts": [
            len(row.get("visible_candidate_ids") or [])
            for row in session_artifact.get("turn_summaries") or []
            if isinstance(row, Mapping)
        ],
        "product_runtime_capabilities_exercised": list(
            session_artifact.get("product_runtime_capabilities_exercised") or []
        ),
        "product_recommendation_selected_candidate_ids": list(
            session_artifact.get("product_recommendation_selected_candidate_ids") or []
        ),
        "product_proactive_candidate_counts": list(
            session_artifact.get("product_proactive_candidate_counts") or []
        ),
        "product_outputs_applied_to_chat_surface": bool(
            session_artifact.get("product_outputs_applied_to_chat_surface")
        ),
        "product_recommendation_intake_handoff_created": bool(
            session_artifact.get("product_recommendation_intake_handoff_created")
        ),
        "product_rescue_commit_handoff_created": bool(
            session_artifact.get("product_rescue_commit_handoff_created")
        ),
        "product_proactive_delivery_packet_ready": bool(
            session_artifact.get("product_proactive_delivery_packet_ready")
        ),
        "session_artifact_path": str(session_artifact.get("session_artifact_path") or ""),
        "turn_artifact_paths": list(session_artifact.get("turn_artifact_paths") or []),
        "lab_session_store_written": bool(
            session_artifact.get("lab_session_store_written")
        ),
        "lab_user_facing_behavior_changed": bool(
            session_artifact.get("lab_user_facing_behavior_changed")
        ),
        "lab_memory_store_written": bool(
            session_artifact.get("lab_memory_store_written")
        ),
        "lab_memory_context_injected": bool(
            session_artifact.get("lab_memory_context_injected")
        ),
        "memory_context_injected": bool(
            session_artifact.get("memory_context_injected")
        ),
        "lab_memory_record_ids": list(
            session_artifact.get("lab_memory_record_ids") or []
        ),
        "lab_memory_surface_paths": dict(
            session_artifact.get("lab_memory_surface_paths") or {}
        ),
        "lab_memory_tool_calls": list(
            session_artifact.get("lab_memory_tool_calls") or []
        ),
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "operator_review_artifact_written": True,
        "live_provider_invoked": False,
        "kimi_live_calls_allowed": False,
        "blockers": list(session_artifact.get("blockers") or []),
        "non_claims": [
            "not_live_provider_diagnostic",
            "not_product_readiness_evidence",
            "not_mainline_runtime_activation",
            "not_durable_product_memory",
            "not_canonical_mutation",
        ],
        **dict(FALSE_FLAGS),
    }


__all__ = ["build_simulated_dogfood_summary"]
