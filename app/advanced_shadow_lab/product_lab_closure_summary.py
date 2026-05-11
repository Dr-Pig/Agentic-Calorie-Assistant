from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_journey_coverage import (
    build_product_lab_journey_coverage_summary,
)


def build_product_lab_closure_summary(
    session_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    action_types = set(session_artifact.get("lab_chat_action_outcome_types") or [])
    criteria = {
        "session_passed": session_artifact.get("status") == "pass",
        "memory_store_written": session_artifact.get("lab_memory_store_written") is True,
        "memory_context_injected": (
            session_artifact.get("lab_memory_context_injected") is True
        ),
        "recommendation_selected": bool(
            [
                item
                for item in session_artifact.get(
                    "product_recommendation_selected_candidate_ids"
                )
                or []
                if item
            ]
        ),
        "recommendation_intake_action_replayed": (
            "recommendation_intake_draft" in action_types
        ),
        "pending_intake_terminal_replayed": (
            "pending_intake_confirmed_lab" in action_types
        ),
        "rescue_commit_action_replayed": "rescue_commit_confirmation" in action_types,
        "rescue_negotiation_posture_replayed": (
            _rescue_negotiation_posture_replayed(session_artifact)
        ),
        "calibration_effect_replayed": (
            int(session_artifact.get("lab_calibration_effect_applied_count") or 0) > 0
        ),
        "proactive_chat_delivery_ready": (
            session_artifact.get("product_proactive_delivery_packet_ready") is True
        ),
        "chat_surface_outputs_applied": (
            session_artifact.get("product_outputs_applied_to_chat_surface") is True
        ),
        "activation_wall_intact": _activation_wall_intact(session_artifact),
        "no_chat_action_blockers": not bool(
            session_artifact.get("lab_chat_action_blockers") or []
        ),
    }
    missing = [key for key, value in criteria.items() if value is not True]
    return {
        "advanced_product_lab_product_loop_closed": not bool(missing),
        "advanced_product_lab_closure_criteria": criteria,
        "advanced_product_lab_closure_missing": missing,
        **build_product_lab_journey_coverage_summary(session_artifact),
    }


def _activation_wall_intact(session_artifact: Mapping[str, Any]) -> bool:
    return (
        session_artifact.get("mainline_activation_enabled") is False
        and session_artifact.get("canonical_product_mutation_allowed") is False
        and session_artifact.get("durable_product_memory_written") is False
        and session_artifact.get("production_scheduler_delivery_allowed") is False
    )


def _rescue_negotiation_posture_replayed(session_artifact: Mapping[str, Any]) -> bool:
    decision_kinds = set(session_artifact.get("lab_rescue_action_decision_kinds") or [])
    return bool(
        {
            "request_gentler_variant",
            "request_shorter_variant",
            "request_explanation",
        }
        & decision_kinds
    )


__all__ = ["build_product_lab_closure_summary"]
