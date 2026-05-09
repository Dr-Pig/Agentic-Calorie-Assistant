from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_manager_tool_surface_inventory import (
    REQUIRED_DIRECT_LANE_IDS,
    REQUIRED_MANAGER_TOOLS,
    build_manager_tool_surface_inventory_artifact,
)


def test_manager_tool_surface_inventory_covers_non_fooddb_app_state_tools() -> None:
    artifact = build_manager_tool_surface_inventory_artifact()

    assert artifact["artifact_schema_version"] == "1.0"
    assert artifact["artifact_type"] == "accurate_intake_manager_tool_surface_inventory"
    assert artifact["status"] == "manager_tool_surface_inventory_ready_for_human_review"
    assert artifact["blockers"] == []
    assert artifact["scope"] == "plce_non_fooddb_app_state_tool_convergence"
    assert artifact["required_direct_lane_ids"] == list(REQUIRED_DIRECT_LANE_IDS)
    assert artifact["required_manager_tools"] == list(REQUIRED_MANAGER_TOOLS)
    assert artifact["summary"]["direct_lane_count"] >= 7
    assert artifact["summary"]["target_tool_count"] == len(REQUIRED_MANAGER_TOOLS)
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False

    tool_by_name = {tool["tool_name"]: tool for tool in artifact["target_manager_tools"]}
    assert tool_by_name["budget.get_today_summary"]["tool_kind"] == "read_only"
    assert tool_by_name["budget.get_remaining_calories"]["truth_owner"] == "budget_domain"
    assert tool_by_name["body.get_active_plan"]["truth_owner"] == "body_domain"
    assert tool_by_name["body.record_observation"]["tool_kind"] == "mutation_bearing"
    assert tool_by_name["calibration.preview_proposal"]["tool_kind"] == "proposal_persisting"
    assert tool_by_name["calibration.apply_stored_proposal_action"]["tool_kind"] == "mutation_bearing"
    assert tool_by_name["app.answer_usage_question"]["tool_kind"] == "read_only"


def test_manager_tool_surface_inventory_maps_current_direct_lanes_to_future_tools() -> None:
    artifact = build_manager_tool_surface_inventory_artifact()
    lane_by_id = {lane["direct_lane_id"]: lane for lane in artifact["current_direct_lanes"]}

    budget = lane_by_id["estimate_general_chat_budget_summary"]
    assert budget["current_entrypoint"] == "app.composition.intake_routes.estimate"
    assert budget["future_manager_tools"] == ["budget.get_today_summary", "budget.get_remaining_calories"]
    assert budget["tool_kind"] == "read_only"

    goal = lane_by_id["estimate_general_chat_goal_summary"]
    assert goal["future_manager_tools"] == ["body.get_active_plan"]

    body_record = lane_by_id["estimate_body_observation_record_weight"]
    assert body_record["future_manager_tools"] == ["body.record_observation"]
    assert body_record["tool_kind"] == "mutation_bearing"
    assert body_record["guard_required"] is True

    manual_target = lane_by_id["estimate_manual_daily_target_structured_update"]
    assert manual_target["future_manager_tools"] == ["budget.set_manual_daily_target"]
    assert manual_target["tool_kind"] == "mutation_bearing"
    assert manual_target["guard_required"] is True
    assert manual_target["manager_structured_target_required"] is True
    assert manual_target["raw_text_authorizes_mutation"] is False

    calibration_action = lane_by_id["estimate_explicit_calibration_action"]
    assert calibration_action["future_manager_tools"] == ["calibration.apply_stored_proposal_action"]
    assert calibration_action["stored_proposal_required"] is True
    assert calibration_action["raw_text_authorizes_mutation"] is False

    assert "estimate_calibration_budget_delta_direct_mutation" not in lane_by_id

    for lane in artifact["current_direct_lanes"]:
        assert lane["semantic_owner"] == "manager"
        assert lane["deterministic_role"] == "provide_context_validate_guard_execute_tool"
        assert lane["frontend_semantic_owner"] is False


def test_manager_tool_surface_inventory_blocks_missing_tools_or_overclaims() -> None:
    artifact = build_manager_tool_surface_inventory_artifact(
        target_tools=[{"tool_name": "budget.get_today_summary", "tool_kind": "read_only"}],
        overrides={"live_llm_invoked": True, "fooddb_used": True},
    )

    assert artifact["status"] == "blocked"
    assert "missing_manager_tool:budget.get_remaining_calories" in artifact["blockers"]
    assert "missing_manager_tool:calibration.apply_stored_proposal_action" in artifact["blockers"]
    assert "live_llm_invoked" in artifact["blockers"]
    assert "fooddb_used" in artifact["blockers"]


def test_manager_tool_surface_inventory_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    from scripts.build_accurate_intake_manager_tool_surface_inventory import main

    output_path = tmp_path / "manager-tool-surface-inventory.json"
    exit_code = main(["--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "manager_tool_surface_inventory_ready_for_human_review"


def test_manager_tool_surface_inventory_source_stays_out_of_fooddb_websearch_runtime_boundaries() -> None:
    for path in (
        Path("app/composition/accurate_intake_manager_tool_surface_inventory.py"),
        Path("scripts/build_accurate_intake_manager_tool_surface_inventory.py"),
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
        ):
            assert fragment not in source
