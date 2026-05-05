from __future__ import annotations

import json
from pathlib import Path


def test_body_budget_calibration_closeout_pack_freezes_backend_contract_scope() -> None:
    from app.composition.body_budget_calibration_closeout import (
        build_body_budget_calibration_closeout_pack,
    )

    pack = build_body_budget_calibration_closeout_pack()

    assert pack["artifact_type"] == "body_budget_calibration_closeout_pack"
    assert pack["status"] == "p0_backend_contract_closeout_ready"
    assert pack["claim_scope"] == "bodybudget_calibration_backend_contract_only"
    assert pack["local_only"] is True
    assert pack["diagnostic_only"] is True
    assert pack["readiness_claimed"] is False
    assert pack["product_readiness_claimed"] is False
    assert pack["stable_read_model_names"] == [
        "current_budget_view",
        "body_budget_deficit_summary",
        "body_budget_weekly_progress",
        "body_budget_effective_budget_view",
        "active_body_plan_view",
        "calibration_proposal_inbox",
        "calibration_proposal_history",
    ]
    assert pack["required_verification_gates"] == [
        "calibration_route_component_tests",
        "calibration_chat_action_component_tests",
        "bodybudget_readiness_artifact_tests",
        "bodybudget_plce_matrix_tests",
        "bodybudget_self_use_journey_smoke",
        "markdown_encoding_policy_docs",
        "pre_edd_readiness",
    ]
    assert pack["boundary_non_claims"] == {
        "fooddb_truth_changed": False,
        "manager_context_packet_changed": False,
        "live_tool_calling": False,
        "automatic_calibration_enabled": False,
        "rescue_enabled": False,
        "recommendation_enabled": False,
        "proactive_enabled": False,
        "private_self_use_approved": False,
    }
    assert pack["next_allowed_slices"] == [
        "calibration_acceptance_chat_surface_if_needed",
        "rescue_overlay_foundation_after_explicit_scope",
        "exercise_input_foundation_after_explicit_scope",
    ]


def test_body_budget_calibration_closeout_script_writes_artifact(tmp_path: Path) -> None:
    from scripts.run_body_budget_calibration_closeout_diagnostic import main

    output = tmp_path / "body_budget_calibration_closeout.json"

    exit_code = main(["--output", str(output)])

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "body_budget_calibration_closeout_pack"
    assert payload["status"] == "p0_backend_contract_closeout_ready"
