from __future__ import annotations

import json
from pathlib import Path

from app.shared.contracts.readiness_claim import validate_readiness_claim_integrity


ROOT = Path(__file__).resolve().parents[1]


def test_body_budget_calibration_readiness_artifact_freezes_plce_read_model_contract() -> None:
    from app.composition.body_budget_calibration_readiness import (
        build_body_budget_calibration_readiness_artifact,
    )

    artifact = build_body_budget_calibration_readiness_artifact()

    assert artifact["artifact_type"] == "body_budget_calibration_readiness"
    assert artifact["claim_scope"] == "local_body_budget_calibration_contract"
    assert artifact["diagnostic_only"] is True
    assert artifact["local_only"] is True
    assert artifact["readiness_claimed"] is False
    assert validate_readiness_claim_integrity(artifact)["passed"] is True

    stable_names = [read_model["name"] for read_model in artifact["stable_read_models"]]
    assert stable_names == [
        "current_budget_view",
        "body_budget_deficit_summary",
        "body_budget_weekly_progress",
        "body_budget_effective_budget_view",
        "active_body_plan_view",
        "calibration_proposal_inbox",
        "calibration_proposal_history",
    ]
    deficit_summary = artifact["stable_read_models"][1]
    assert deficit_summary["aliases"] == ["deficit_summary"]
    assert deficit_summary["canonical_name_required_for_plce"] is True
    assert artifact["plce_contract"]["frontend_math_allowed"] is False
    assert artifact["plce_contract"]["manager_context_packet_changed"] is False
    integration_matrix = artifact["plce_contract"]["integration_readiness_matrix"]
    assert integration_matrix["doc_path"] == (
        "docs/specs/UI_CANONICAL_TRUTH_SURFACE_MATRIX.md#BodyBudget PL/CE Integration Readiness Matrix"
    )
    assert integration_matrix["canonical_read_model_names"] == stable_names
    assert integration_matrix["frontend_fallback_calculation_authorized"] is False
    assert integration_matrix["manager_context_packet_changed"] is False
    assert integration_matrix["missing_field_policy"] == "extend_backend_read_model_first"
    assert integration_matrix["backend_routes"] == {
        "current_budget_view": "/today/current-budget",
        "body_budget_deficit_summary": "/today/deficit-summary",
        "body_budget_weekly_progress": "/today/weekly-progress",
        "body_budget_effective_budget_view": "/today/effective-budget",
        "active_body_plan_view": "/body-plan/active",
        "calibration_proposal_inbox": "/calibration/proposals/open",
        "calibration_proposal_history": "/calibration/proposals/history",
    }
    assert integration_matrix["read_functions"] == {
        "current_budget_view": "app.composition.current_budget_read_model.build_current_budget_view",
        "body_budget_deficit_summary": (
            "app.composition.body_budget_deficit_summary.build_body_budget_deficit_summary"
        ),
        "body_budget_weekly_progress": "app.composition.body_budget_weekly_progress.build_body_budget_weekly_progress",
        "body_budget_effective_budget_view": (
            "app.composition.body_budget_effective_budget.build_body_budget_effective_budget_view"
        ),
        "active_body_plan_view": "app.body.application.active_body_plan_read_model.build_active_body_plan_view",
        "calibration_proposal_inbox": "app.composition.calibration_proposal_inbox.load_open_calibration_proposal_inbox",
        "calibration_proposal_history": "app.composition.calibration_proposal_inbox.load_calibration_proposal_history",
    }
    assert "estimated_daily_deficit_kcal" in deficit_summary["stable_fields"]
    assert "latest_weight_kg" in deficit_summary["stable_fields"]
    weekly_progress = artifact["stable_read_models"][2]
    assert weekly_progress["backend_route"] == "/today/weekly-progress"
    assert weekly_progress["read_function"] == "app.composition.body_budget_weekly_progress.build_body_budget_weekly_progress"
    assert "estimated_weekly_deficit_kcal" in weekly_progress["stable_fields"]
    assert "weight_delta_kg" in weekly_progress["stable_fields"]
    assert "compute_weekly_deficit" in weekly_progress["plce_forbidden"]
    assert "infer_calibration_eligibility" in weekly_progress["plce_forbidden"]
    effective_budget = artifact["stable_read_models"][3]
    assert effective_budget["backend_route"] == "/today/effective-budget"
    assert "runtime_effective_budget_kcal" in effective_budget["stable_fields"]
    assert "adjustment_layers.runtime_adjustment_total_from_entries_kcal" in effective_budget["stable_fields"]
    assert "sign_policy" in effective_budget["stable_fields"]
    assert "calculate_effective_budget" in effective_budget["plce_forbidden"]
    assert artifact["calibration_flow_contract"]["effective_budget_math"]["canonical_l3m_formula_enabled"] is True
    proposal_history = artifact["stable_read_models"][6]
    assert proposal_history["backend_route"] == "/calibration/proposals/history"
    assert proposal_history["read_function"] == "app.composition.calibration_proposal_inbox.load_calibration_proposal_history"
    assert "expired_at" in proposal_history["stable_fields"]
    assert "primary_option_summary" in proposal_history["stable_fields"]
    assert "effect_payload" in proposal_history["plce_forbidden"]


def test_body_budget_calibration_readiness_artifact_records_preview_and_action_mutation_boundaries() -> None:
    from app.composition.body_budget_calibration_readiness import (
        build_body_budget_calibration_readiness_artifact,
    )

    artifact = build_body_budget_calibration_readiness_artifact()

    preview = artifact["calibration_flow_contract"]["preview_from_history"]
    assert preview["input_source"] == "real_body_intake_budget_history"
    assert preview["manual_model_inputs_payload_role"] == "diagnostic_only"
    assert preview["persist_proposal_default"] is False
    assert preview["body_plan_mutation_authorized"] is False
    assert preview["day_budget_ledger_mutation_authorized"] is False
    assert preview["ledger_entry_calibration_adjustment_enabled"] is False
    assert "clean_sqlalchemy_session" in preview["persist_proposal_requires"]
    response_contract = artifact["calibration_flow_contract"]["proposal_response_contract"]
    assert response_contract["presentation_policy"] == "single_primary_recommendation"
    assert response_contract["backup_options_default_visibility"] == "hidden"
    assert "proposal_cards" in response_contract["required_outputs"]
    assert response_contract["quick_action_contract"]["raw_text_authorized_mutation"] is False
    assert response_contract["quick_action_contract"]["view_alternatives_mutation_authorized"] is False

    stored_action = artifact["calibration_flow_contract"]["stored_action"]
    assert stored_action["mutation_requires"] == "explicit_accept_on_active_stored_proposal"
    assert stored_action["conflict_status_code"] == 409
    assert stored_action["body_plan_mutation_authorized_on_accept"] is True
    assert stored_action["ledger_entry_calibration_adjustment_enabled"] is True
    assert "explicit_effect_payload_calibration_adjustment_delta_kcal" in stored_action[
        "ledger_entry_calibration_adjustment_requires"
    ]
    assert stored_action["active_statuses"] == ["open"]
    assert "accepted" in stored_action["terminal_statuses"]
    assert "dismissed" in stored_action["terminal_statuses"]
    assert "deferred_pending_reminder" not in stored_action["terminal_statuses"]
    assert stored_action["legacy_terminal_status_aliases"] == ["deferred_pending_reminder"]
    expiry_bookkeeping = artifact["calibration_flow_contract"]["proposal_expiry_bookkeeping"]
    assert expiry_bookkeeping["service"] == "app.composition.calibration_proposal_expiry.expire_stale_calibration_proposals"
    assert expiry_bookkeeping["route"] == "/calibration/proposals/expire-stale"
    assert expiry_bookkeeping["root_public_route_mounted"] is False
    assert expiry_bookkeeping["expirable_statuses"] == ["open"]
    assert expiry_bookkeeping["proposal_status_after_expiry"] == "expired"
    assert expiry_bookkeeping["body_plan_mutation_authorized"] is False
    assert expiry_bookkeeping["day_budget_ledger_mutation_authorized"] is False
    assert expiry_bookkeeping["proactive_trigger_authorized"] is False
    chat_action = artifact["calibration_flow_contract"]["chat_action_surface"]
    assert chat_action["mode"] == "calibration_action"
    assert chat_action["chat_primary_surface"] is True
    assert chat_action["does_not_keyword_attach"] is True
    assert "explicit_proposal_container_id" in chat_action["requires"]
    chat_preview = artifact["calibration_flow_contract"]["chat_preview_surface"]
    assert chat_preview["mode"] == "calibration_preview"
    assert chat_preview["chat_primary_surface"] is True
    assert chat_preview["does_not_keyword_attach"] is True
    assert chat_preview["body_plan_mutation_authorized"] is False
    assert chat_preview["day_budget_ledger_mutation_authorized"] is False
    estimate_preview = artifact["calibration_flow_contract"]["estimate_route_preview_bridge"]
    assert estimate_preview["route"] == "/estimate"
    assert estimate_preview["mode"] == "calibration_preview"
    assert estimate_preview["optional_persistence_flag"] == "persist_calibration_proposal"
    assert estimate_preview["raw_text_authorized_preview"] is False
    assert estimate_preview["raw_text_authorized_proposal_persistence"] is False
    assert estimate_preview["manager_provider_invoked"] is False
    assert "calibration_preview_requested" in estimate_preview["requires"]
    estimate_bridge = artifact["calibration_flow_contract"]["estimate_route_action_bridge"]
    assert estimate_bridge["route"] == "/estimate"
    assert estimate_bridge["mode"] == "calibration_action"
    assert estimate_bridge["raw_text_authorized_mutation"] is False
    assert estimate_bridge["manager_provider_invoked"] is False
    assert estimate_bridge["accepted_at_field"] == "calibration_action_accepted_at"
    assert estimate_bridge["accepted_at_format"] == "iso_datetime_with_date_and_time"
    assert estimate_bridge["effective_from_owner"] == "stored_action_contract"
    assert estimate_bridge["frontend_effective_date_calculation_authorized"] is False
    assert "calibration_proposal_container_id" in estimate_bridge["requires"]
    assert "accept_calibration_proposal" in estimate_bridge["accepted_actions"]
    stored_action = artifact["calibration_flow_contract"]["stored_action"]
    assert stored_action["accepted_at_request_validation"] == "iso_datetime_with_date_and_time"

    non_claims = artifact["non_claims"]
    assert non_claims["automatic_calibration_enabled"] is False
    assert non_claims["rescue_enabled"] is False
    assert non_claims["recommendation_enabled"] is False
    assert non_claims["proactive_enabled"] is False
    assert non_claims["live_tool_calling"] is False


def test_body_budget_calibration_readiness_artifact_records_calibration_router_activation() -> None:
    from app.composition.body_budget_calibration_readiness import (
        build_body_budget_calibration_readiness_artifact,
    )

    artifact = build_body_budget_calibration_readiness_artifact()
    route_activation = artifact["route_activation"]

    assert route_activation["root_app_mounted"] is True
    assert route_activation["root_mount_status"] == "activated_for_calibration_contract_routes"
    assert "/calibration/proposals/open" in route_activation["router_contract_paths"]
    assert "/calibration/proposals/history" in route_activation["router_contract_paths"]
    assert "/calibration/proposal/stored-action" in route_activation["router_contract_paths"]
    assert "/calibration/proposals/expire-stale" in route_activation["internal_diagnostic_paths_not_root_mounted"]

    root_routes_source = (ROOT / "app" / "routes.py").read_text(encoding="utf-8")
    assert "from app.composition.calibration_routes import public_router as calibration_router" in root_routes_source
    assert "router.include_router(calibration_router)" in root_routes_source


def test_body_budget_calibration_readiness_artifact_names_self_use_journey_smoke_gate() -> None:
    from app.composition.body_budget_calibration_readiness import (
        build_body_budget_calibration_readiness_artifact,
    )

    artifact = build_body_budget_calibration_readiness_artifact()

    gate = artifact["journey_smoke_gates"]["calibration_self_use_journey"]
    assert gate["script"] == "scripts/run_body_budget_calibration_self_use_journey_smoke.py"
    assert gate["test"] == "tests/test_body_budget_calibration_self_use_journey_smoke.py"
    assert "estimate_route_history_to_calibration_preview" in gate["covers"]
    assert "estimate_route_raw_text_noop" in gate["covers"]
    assert "estimate_route_explicit_stored_action_accept" in gate["covers"]
    assert "automatic_calibration" in gate["does_not_claim"]
    assert "private_self_use_approval" in gate["does_not_claim"]


def test_body_budget_calibration_readiness_script_writes_artifact(tmp_path: Path) -> None:
    from scripts.run_body_budget_calibration_readiness_diagnostic import main

    output = tmp_path / "body_budget_calibration_readiness.json"
    exit_code = main(["--output", str(output)])

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "body_budget_calibration_readiness"
    assert payload["plce_contract"]["stable_backend_read_models_required"] is True
