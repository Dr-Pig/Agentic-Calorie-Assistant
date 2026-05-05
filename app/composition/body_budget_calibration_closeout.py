from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.composition.body_budget_calibration_readiness import (
    build_body_budget_calibration_readiness_artifact,
)


def build_body_budget_calibration_closeout_pack() -> dict[str, Any]:
    readiness = build_body_budget_calibration_readiness_artifact()
    stable_read_model_names = [read_model["name"] for read_model in readiness["stable_read_models"]]
    return {
        "artifact_schema_version": "body_budget_calibration_closeout.v1",
        "artifact_type": "body_budget_calibration_closeout_pack",
        "status": "p0_backend_contract_closeout_ready",
        "generated_at": datetime.now(UTC).isoformat(),
        "claim_scope": "bodybudget_calibration_backend_contract_only",
        "local_only": True,
        "diagnostic_only": True,
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "readiness_artifact_type": readiness["artifact_type"],
        "readiness_artifact_status": readiness["status"],
        "stable_read_model_names": stable_read_model_names,
        "required_verification_gates": [
            "calibration_route_component_tests",
            "calibration_chat_action_component_tests",
            "bodybudget_readiness_artifact_tests",
            "bodybudget_plce_matrix_tests",
            "bodybudget_self_use_journey_smoke",
            "markdown_encoding_policy_docs",
            "pre_edd_readiness",
        ],
        "verification_commands": {
            "calibration_route_component_tests": (
                "python -m pytest tests/test_calibration_routes.py "
                "tests/test_calibration_commit_bridge.py tests/test_calibration_proposal_inbox.py -q"
            ),
            "calibration_chat_action_component_tests": (
                "python -m pytest tests/test_calibration_chat_action_estimate_route.py "
                "tests/test_general_chat_workflow.py -q"
            ),
            "bodybudget_readiness_artifact_tests": (
                "python -m pytest tests/test_body_budget_calibration_readiness.py -q"
            ),
            "bodybudget_plce_matrix_tests": (
                "python -m pytest tests/test_bodybudget_plce_integration_matrix.py -q"
            ),
            "bodybudget_self_use_journey_smoke": (
                "python -m pytest tests/test_body_budget_calibration_self_use_journey_smoke.py -q"
            ),
            "markdown_encoding_policy_docs": "python scripts/check_markdown_encoding.py --policy-docs --require-bom",
            "pre_edd_readiness": "python scripts/pre_edd_readiness.py --timeout-seconds 180",
        },
        "boundary_non_claims": {
            "fooddb_truth_changed": False,
            "manager_context_packet_changed": False,
            "live_tool_calling": False,
            "automatic_calibration_enabled": False,
            "rescue_enabled": False,
            "recommendation_enabled": False,
            "proactive_enabled": False,
            "private_self_use_approved": False,
        },
        "next_allowed_slices": [
            "calibration_acceptance_chat_surface_if_needed",
            "rescue_overlay_foundation_after_explicit_scope",
            "exercise_input_foundation_after_explicit_scope",
        ],
    }


__all__ = ["build_body_budget_calibration_closeout_pack"]
