from __future__ import annotations

from typing import Any


def build_route_activation_contract() -> dict[str, Any]:
    return {
        "root_app_mounted": True,
        "root_mount_status": "activated_for_calibration_contract_routes",
        "router_module": "app.composition.calibration_routes.public_router",
        "router_contract_paths": [
            "/calibration/proposals/open",
            "/calibration/proposals/history",
            "/calibration/proposal/preview-from-history",
            "/calibration/proposal/stored-action",
        ],
        "internal_diagnostic_paths_not_root_mounted": [
            "/calibration/proposal/preview",
            "/calibration/proposal/action",
            "/calibration/proposals/expire-stale",
        ],
        "frontend_route_call_allowed_after_activation": True,
    }


def build_journey_smoke_gates() -> dict[str, Any]:
    return {
        "calibration_self_use_journey": {
            "script": "scripts/run_body_budget_calibration_self_use_journey_smoke.py",
            "test": "tests/test_body_budget_calibration_self_use_journey_smoke.py",
            "claim_scope": "local_deterministic_body_budget_calibration_smoke",
            "covers": [
                "estimate_route_history_to_calibration_preview",
                "estimate_route_raw_text_noop",
                "estimate_route_explicit_stored_action_accept",
                "persisted_open_proposal_inbox",
                "read_only_proposal_history",
                "active_body_plan_update",
                "current_budget_same_truth",
                "effective_budget_same_truth",
                "weekly_progress_weight_loop_read_model",
            ],
            "does_not_claim": [
                "product_readiness",
                "private_self_use_approval",
                "automatic_calibration",
                "live_provider_use",
                "rescue",
                "recommendation",
                "proactive",
            ],
        },
    }


def build_runtime_truth_changed_contract() -> dict[str, Any]:
    return {
        "scope": "readiness_contract_only",
        "does_not_change": [
            "meal_thread_truth",
            "nutrition_evidence_truth",
            "fooddb_truth",
            "manager_context_packet",
            "rescue_proposal_truth",
            "recommendation_truth",
            "proactive_trigger_truth",
            "body_plan_without_proposal_accept",
            "day_budget_ledger_without_proposal_accept",
        ],
    }


def build_non_claims() -> dict[str, bool]:
    return {
        "live_tool_calling": False,
        "automatic_calibration_enabled": False,
        "rescue_enabled": False,
        "recommendation_enabled": False,
        "proactive_enabled": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


def build_estimate_route_preview_bridge_contract() -> dict[str, Any]:
    return {
        "route": "/estimate",
        "request_contract": "app.shared.contracts.common.EstimateRequest",
        "mode": "calibration_preview",
        "requires": ["calibration_preview_requested", "preview_from_history_contract"],
        "optional_persistence_flag": "persist_calibration_proposal",
        "raw_text_authorized_preview": False,
        "raw_text_authorized_proposal_persistence": False,
        "manager_provider_invoked": False,
        "surfaces_proposal_response": True,
        "proposal_response_fields": [
            "surfaced",
            "proposal_family",
            "proposal_cards",
            "quick_actions",
            "ui_hints",
            "proposal_container_id",
            "stored_action_required",
            "raw_text_authorized_mutation",
        ],
        "body_plan_mutation_authorized": False,
        "day_budget_ledger_mutation_authorized": False,
        "mutation_legality_owner": "stored_action_contract_after_explicit_accept",
        "llm_role": "none_for_calibration_truth_judgment",
    }


def build_estimate_route_action_bridge_contract() -> dict[str, Any]:
    return {
        "route": "/estimate",
        "request_contract": "app.shared.contracts.common.EstimateRequest",
        "mode": "calibration_action",
        "requires": ["calibration_proposal_container_id", "calibration_action", "stored_action_contract"],
        "accepted_at_field": "calibration_action_accepted_at",
        "accepted_at_role": "optional_backend_effective_date_input",
        "accepted_at_format": "iso_datetime_with_date_and_time",
        "effective_from_owner": "stored_action_contract",
        "frontend_effective_date_calculation_authorized": False,
        "accepted_actions": [
            "accept_calibration_proposal",
            "defer_calibration_proposal",
            "reject_calibration_proposal",
        ],
        "raw_text_authorized_mutation": False,
        "manager_provider_invoked": False,
        "mutation_legality_owner": "stored_action_contract",
        "llm_role": "none_for_mutation_legality",
    }


__all__ = [
    "build_estimate_route_action_bridge_contract",
    "build_estimate_route_preview_bridge_contract",
    "build_journey_smoke_gates",
    "build_non_claims",
    "build_route_activation_contract",
    "build_runtime_truth_changed_contract",
]
