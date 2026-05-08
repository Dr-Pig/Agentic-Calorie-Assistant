from __future__ import annotations

from typing import Any

from app.composition.calibration_commit_bridge import PLAN_CHANGING_CALIBRATION_FAMILIES
from app.composition.calibration_proposal_artifacts import ACTIVE_CALIBRATION_PROPOSAL_STATUSES
from app.composition.calibration_proposal_expiry import EXPIRABLE_CALIBRATION_PROPOSAL_STATUSES
from app.composition.body_budget_calibration_readiness_shell import (
    build_estimate_route_action_bridge_contract,
    build_estimate_route_preview_bridge_contract,
)


TERMINAL_CALIBRATION_PROPOSAL_STATUSES = [
    "accepted",
    "rejected",
    "expired",
    "dismissed",
]
LEGACY_TERMINAL_CALIBRATION_PROPOSAL_STATUSES = ["deferred_pending_reminder"]


def build_calibration_flow_contract() -> dict[str, Any]:
    return {
        "effective_budget_math": _effective_budget_math_contract(),
        "input_assembler": _input_assembler_contract(),
        "preview_from_history": _preview_from_history_contract(),
        "proposal_response_contract": _proposal_response_contract(),
        "proposal_inbox": _proposal_inbox_contract(),
        "proposal_history": _proposal_history_contract(),
        "stored_action": _stored_action_contract(),
        "proposal_expiry_bookkeeping": _proposal_expiry_bookkeeping_contract(),
        "chat_action_surface": _chat_action_surface_contract(),
        "chat_preview_surface": _chat_preview_surface_contract(),
        "estimate_route_preview_bridge": build_estimate_route_preview_bridge_contract(),
        "estimate_route_action_bridge": build_estimate_route_action_bridge_contract(),
    }


def _effective_budget_math_contract() -> dict[str, Any]:
    return {
        "service": "app.budget.application.effective_budget_math.summarize_budget_adjustment_layers",
        "sign_policy": "type_aware_signed_layers_to_legacy_subtractive_adjustment",
        "manual_adjustment_policy": "positive_delta_reduces_available_budget",
        "calibration_adjustment_policy": "signed_delta_adds_to_effective_budget",
        "rescue_overlay_policy": "signed_delta_adds_to_effective_budget",
        "canonical_l3m_formula_enabled": True,
        "llm_role": "none",
    }


def _input_assembler_contract() -> dict[str, Any]:
    return {
        "service": "app.composition.calibration_input_assembler."
        "assemble_calibration_model_inputs_from_history",
        "input_source": "real_body_intake_budget_history",
        "window_policy": "local_date_window_inclusive_end",
        "weight_delta_policy": "first_valid_then_last_valid_ordered_by_observed_at_then_id",
        "intake_coverage_policy": "weak_proxy_days_with_completed_meal_over_window_days",
        "llm_role": "none",
    }


def _preview_from_history_contract() -> dict[str, Any]:
    return {
        "service": "app.composition.calibration_preview_service.build_calibration_preview_from_history",
        "input_source": "real_body_intake_budget_history",
        "manual_model_inputs_payload_role": "diagnostic_only",
        "persist_proposal_default": False,
        "persist_proposal_requires": [
            "explicit_persist_proposal_true",
            "proposal_eligible_and_surfaced",
            "clean_sqlalchemy_session",
            "no_existing_active_calibration_proposal",
        ],
        "body_plan_mutation_authorized": False,
        "day_budget_ledger_mutation_authorized": False,
        "ledger_entry_calibration_adjustment_enabled": False,
        "llm_role": "none",
    }


def _proposal_response_contract() -> dict[str, Any]:
    return {
        "service": "app.body.application.calibration_proposal_response.build_calibration_proposal_response",
        "required_outputs": [
            "reply_text",
            "proposal_cards",
            "top_option",
            "backup_options",
            "quick_actions",
            "ui_hints",
        ],
        "presentation_policy": "single_primary_recommendation",
        "backup_options_default_visibility": "hidden",
        "quick_action_contract": {
            "stored_action_requires_proposal_container_id": True,
            "raw_text_authorized_mutation": False,
            "view_alternatives_mutation_authorized": False,
        },
        "llm_role": "explain_only_future_optional",
    }


def _proposal_inbox_contract() -> dict[str, Any]:
    return {
        "service": "app.composition.calibration_proposal_inbox.load_open_calibration_proposal_inbox",
        "active_statuses": sorted(ACTIVE_CALIBRATION_PROPOSAL_STATUSES),
        "mirror_only": True,
        "preserve_backend_order": True,
    }


def _proposal_history_contract() -> dict[str, Any]:
    return {
        "service": "app.composition.calibration_proposal_inbox.load_calibration_proposal_history",
        "route": "/calibration/proposals/history",
        "canonical_statuses": sorted(["accepted", "dismissed", "expired", "open", "rejected"]),
        "read_only": True,
        "public_route_mounted": True,
        "safe_projection_only": True,
        "exposes_effect_payload": False,
        "exposes_full_metadata": False,
        "mutation_authorized": False,
        "llm_role": "none",
    }


def _stored_action_contract() -> dict[str, Any]:
    return {
        "service": "app.composition.calibration_commit_bridge.apply_stored_calibration_proposal_action",
        "mutation_requires": "explicit_accept_on_active_stored_proposal",
        "active_statuses": sorted(ACTIVE_CALIBRATION_PROPOSAL_STATUSES),
        "terminal_statuses": TERMINAL_CALIBRATION_PROPOSAL_STATUSES,
        "legacy_terminal_status_aliases": LEGACY_TERMINAL_CALIBRATION_PROPOSAL_STATUSES,
        "conflict_status_code": 409,
        "unknown_user_status_code": 404,
        "user_creation_authorized": False,
        "accepted_at_request_validation": "iso_datetime_with_date_and_time",
        "plan_changing_families": sorted(PLAN_CHANGING_CALIBRATION_FAMILIES),
        "body_plan_mutation_authorized_on_accept": True,
        "day_budget_ledger_refresh_authorized_on_accept": True,
        "ledger_entry_calibration_adjustment_enabled": True,
        "ledger_entry_calibration_adjustment_requires": [
            "explicit_accept_on_active_stored_proposal",
            "explicit_effect_payload_calibration_adjustment_delta_kcal",
            "effective_budget_not_below_safety_floor",
        ],
        "llm_role": "none",
    }


def _proposal_expiry_bookkeeping_contract() -> dict[str, Any]:
    return {
        "service": "app.composition.calibration_proposal_expiry.expire_stale_calibration_proposals",
        "route": "/calibration/proposals/expire-stale",
        "route_scope": "internal_bookkeeping_only",
        "root_public_route_mounted": False,
        "expirable_statuses": sorted(EXPIRABLE_CALIBRATION_PROPOSAL_STATUSES),
        "proposal_status_after_expiry": "expired",
        "expires_at_source": "ProposalContainer.metadata_json.expires_at",
        "expired_at_source": "bookkeeping_execution_time",
        "body_plan_mutation_authorized": False,
        "day_budget_ledger_mutation_authorized": False,
        "ledger_entry_mutation_authorized": False,
        "proactive_trigger_authorized": False,
        "llm_role": "none",
    }


def _chat_action_surface_contract() -> dict[str, Any]:
    return {
        "service": "app.composition.general_chat_service.build_general_chat_response_pass",
        "mode": "calibration_action",
        "requires": ["explicit_proposal_container_id", "explicit_calibration_action", "stored_action_contract"],
        "does_not_keyword_attach": True,
        "chat_primary_surface": True,
        "ui_role": "mirror_or_confirm_surface",
        "llm_role": "none_for_mutation_legality",
    }


def _chat_preview_surface_contract() -> dict[str, Any]:
    return {
        "service": "app.composition.general_chat_service.build_general_chat_response_pass",
        "mode": "calibration_preview",
        "input_source": "real_body_intake_budget_history",
        "persist_proposal_default": False,
        "requires_for_persistence": [
            "explicit_persist_calibration_proposal_true",
            "preview_from_history_contract",
            "no_existing_active_calibration_proposal",
        ],
        "does_not_keyword_attach": True,
        "chat_primary_surface": True,
        "ui_role": "mirror_or_confirm_surface",
        "body_plan_mutation_authorized": False,
        "day_budget_ledger_mutation_authorized": False,
        "llm_role": "none_for_calibration_truth_judgment",
    }

__all__ = ["build_calibration_flow_contract"]
