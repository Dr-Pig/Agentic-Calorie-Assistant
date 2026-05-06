from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_non_fooddb_manager_tool_contract import (
    build_non_fooddb_manager_tool_contract_artifact,
    build_tool_contract_index,
)


def test_non_fooddb_manager_tool_contract_covers_read_only_proposal_and_guarded_mutation_surfaces() -> None:
    artifact = build_non_fooddb_manager_tool_contract_artifact()

    assert artifact["artifact_schema_version"] == "1.0"
    assert artifact["artifact_type"] == "accurate_intake_non_fooddb_manager_tool_contract"
    assert artifact["status"] == "non_fooddb_manager_tool_contract_ready_for_human_review"
    assert artifact["claim_scope"] == "plce_non_fooddb_manager_tool_contract_pre_live_diagnostic_only"
    assert artifact["summary"] == {
        "inventory_backed_tool_count": 10,
        "read_only_tool_count": 7,
        "proposal_tool_count": 1,
        "mutation_tool_count": 3,
        "legacy_direct_route_debt_count": 1,
        "direct_lane_bridge_count": 7,
    }
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["shared_contract_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["blockers"] == []


def test_non_fooddb_manager_tool_contract_marks_manual_target_pending_and_legacy_delta_as_debt() -> None:
    artifact = build_non_fooddb_manager_tool_contract_artifact()
    contract_by_tool = build_tool_contract_index(artifact)
    bridge_by_lane = {lane["direct_lane_id"]: lane for lane in artifact["direct_lane_bridge"]}

    body_record = contract_by_tool["body.record_observation"]
    assert body_record["contract_stage"] == "inventory_backed"
    assert body_record["guard_required"] is True
    assert body_record["raw_text_authorizes_mutation"] is False
    assert body_record["allowed_domain_effects"] == ["body_observation_write_only"]
    assert "body_plan_mutation" in body_record["forbidden_domain_effects"]
    assert "ledger_mutation" in body_record["forbidden_domain_effects"]

    preview = contract_by_tool["calibration.preview_proposal"]
    assert preview["tool_kind"] == "proposal_persisting"
    assert preview["stored_proposal_required"] is False
    assert preview["allowed_domain_effects"] == ["proposal_preview_optional_open_container"]

    apply_action = contract_by_tool["calibration.apply_stored_proposal_action"]
    assert apply_action["stored_proposal_required"] is True
    assert apply_action["explicit_request_fields"] == [
        "calibration_proposal_container_id",
        "calibration_action",
    ]

    manual_target = contract_by_tool["budget.set_manual_daily_target"]
    assert manual_target["contract_stage"] == "adjacent_pending_inventory_expansion"
    assert manual_target["manager_structured_target_required"] is True
    assert manual_target["tool_callable_by_manager"] is True

    legacy = contract_by_tool["legacy.calibration_delta_kcal_direct_route"]
    assert legacy["contract_stage"] == "legacy_direct_lane_debt"
    assert legacy["tool_callable_by_manager"] is False
    assert legacy["debt_marker"] == "direct_route_mutation_before_manager_tool_contract"

    assert bridge_by_lane["estimate_general_chat_budget_summary"]["contract_tool_names"] == [
        "budget.get_today_summary",
        "budget.get_remaining_calories",
    ]
    assert bridge_by_lane["estimate_calibration_budget_delta_direct_mutation"]["debt_marker"] == (
        "direct_route_mutation_before_manager_tool_contract"
    )


def test_non_fooddb_manager_tool_contract_blocks_inventory_drift_or_overclaims() -> None:
    artifact = build_non_fooddb_manager_tool_contract_artifact(
        inventory={"status": "blocked", "target_manager_tools": []},
        overrides={"live_llm_invoked": True, "fooddb_used": True},
    )

    assert artifact["status"] == "blocked"
    assert "manager_tool_surface_inventory.not_ready" in artifact["blockers"]
    assert "inventory_backed_contract_count_too_low" in artifact["blockers"]
    assert "live_llm_invoked" in artifact["blockers"]
    assert "fooddb_used" in artifact["blockers"]


def test_non_fooddb_manager_tool_contract_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_non_fooddb_manager_tool_contract import main

    output_path = tmp_path / "non-fooddb-manager-tool-contract.json"
    exit_code = main(["--output", str(output_path)])
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "non_fooddb_manager_tool_contract_ready_for_human_review"


def test_non_fooddb_manager_tool_contract_stays_out_of_forbidden_boundaries() -> None:
    for path in (
        Path("app/composition/accurate_intake_non_fooddb_manager_tool_contract.py"),
        Path("scripts/build_accurate_intake_non_fooddb_manager_tool_contract.py"),
    ):
        source = path.read_text(encoding="utf-8")
        for fragment in (
            "NutritionEvidenceStorePort",
            "FoodEvidenceRecord",
            "PacketReadyAnchor",
            "TavilyClient",
            "builderspace_adapter",
            "manager_context_packet_v1 =",
            "record_budget_adjustment_to_canonical(",
            "record_body_observation_to_canonical(",
            "apply_stored_calibration_proposal_action(",
            "live_llm_invoked = True",
            "product_readiness_claimed = True",
        ):
            assert fragment not in source
