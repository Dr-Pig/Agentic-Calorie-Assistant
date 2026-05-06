from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_manager_tool_surface_inventory import (
    REQUIRED_MANAGER_TOOLS,
)
from app.composition.accurate_intake_manager_tool_choice_regression_wall import (
    build_manager_tool_choice_regression_wall_artifact,
)


REQUIRED_CASES = [
    "budget_remaining_today_query",
    "budget_today_meal_log_query",
    "body_active_plan_query",
    "body_latest_weight_query",
    "body_record_weight_mutation_candidate",
    "calibration_preview_request",
    "calibration_apply_without_stored_proposal",
    "calibration_apply_with_stored_proposal",
    "app_usage_help_question",
    "food_logging_deferred_to_intake_fooddb_track",
    "ambiguous_general_health_chat_no_tool",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_manager_tool_choice_regression_wall_covers_non_fooddb_tool_postures() -> None:
    artifact = build_manager_tool_choice_regression_wall_artifact()

    assert artifact["artifact_schema_version"] == "1.0"
    assert artifact["artifact_type"] == "accurate_intake_manager_tool_choice_regression_wall"
    assert artifact["status"] == "manager_tool_choice_regression_wall_pass"
    assert artifact["required_manager_tools"] == list(REQUIRED_MANAGER_TOOLS)
    assert [case["case_id"] for case in artifact["cases"]] == REQUIRED_CASES
    assert artifact["fixture_manager_used"] is True
    assert artifact["semantic_owner"] == "fixture_manager_structured_decision"
    assert artifact["deterministic_selected_tool"] is False
    assert artifact["deterministic_selected_intent"] is False
    assert artifact["frontend_raw_text_semantic_router"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False


def test_manager_tool_choice_regression_wall_separates_tool_kinds_and_guards() -> None:
    cases = _by_id(build_manager_tool_choice_regression_wall_artifact())

    assert cases["budget_remaining_today_query"]["expected_tool_choice"] == "budget.get_remaining_calories"
    assert cases["budget_remaining_today_query"]["tool_kind"] == "read_only"
    assert cases["budget_remaining_today_query"]["mutation_allowed"] is False

    assert cases["body_record_weight_mutation_candidate"]["expected_tool_choice"] == "body.record_observation"
    assert cases["body_record_weight_mutation_candidate"]["tool_kind"] == "mutation_bearing"
    assert cases["body_record_weight_mutation_candidate"]["guard_required"] is True
    assert cases["body_record_weight_mutation_candidate"]["raw_text_authorizes_mutation"] is False

    assert cases["calibration_preview_request"]["expected_tool_choice"] == "calibration.preview_proposal"
    assert cases["calibration_preview_request"]["tool_kind"] == "proposal_persisting"
    assert cases["calibration_apply_without_stored_proposal"]["expected_tool_choice"] == "calibration.get_pending_proposal"
    assert cases["calibration_apply_without_stored_proposal"]["blocked_reason"] == "missing_stored_proposal"
    assert cases["calibration_apply_with_stored_proposal"]["expected_tool_choice"] == "calibration.apply_stored_proposal_action"
    assert cases["calibration_apply_with_stored_proposal"]["stored_proposal_required"] is True


def test_manager_tool_choice_regression_wall_defers_fooddb_and_preserves_ambiguity() -> None:
    cases = _by_id(build_manager_tool_choice_regression_wall_artifact())

    food = cases["food_logging_deferred_to_intake_fooddb_track"]
    assert food["expected_tool_choice"] == "intake_fooddb_track_deferred"
    assert food["fooddb_used"] is False
    assert food["web_tavily_used"] is False
    assert food["runtime_truth_changed"] is False

    ambiguous = cases["ambiguous_general_health_chat_no_tool"]
    assert ambiguous["expected_tool_choice"] == "none"
    assert ambiguous["ambiguity_preserved"] is True
    assert ambiguous["mutation_allowed"] is False


def test_manager_tool_choice_regression_wall_blocks_missing_cases_and_overclaims() -> None:
    artifact = build_manager_tool_choice_regression_wall_artifact(
        cases=[
            {
                "case_id": "budget_remaining_today_query",
                "expected_tool_choice": "budget.get_remaining_calories",
                "fixture_manager_decision": {"selected_tool": "budget.get_today_summary"},
            }
        ],
        overrides={"live_llm_invoked": True, "fooddb_used": True},
    )

    assert artifact["status"] == "blocked"
    assert "missing_case:budget_today_meal_log_query" in artifact["blockers"]
    assert "budget_remaining_today_query.fixture_selected_tool_mismatch" in artifact["blockers"]
    assert "live_llm_invoked" in artifact["blockers"]
    assert "fooddb_used" in artifact["blockers"]


def test_manager_tool_choice_regression_wall_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_manager_tool_choice_regression_wall import main

    output_path = tmp_path / "manager-tool-choice-regression-wall.json"
    exit_code = main(["--output", str(output_path)])
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "manager_tool_choice_regression_wall_pass"
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASES)


def test_manager_tool_choice_regression_wall_stays_out_of_forbidden_boundaries() -> None:
    for path in (
        Path("app/composition/accurate_intake_manager_tool_choice_regression_wall.py"),
        Path("scripts/build_accurate_intake_manager_tool_choice_regression_wall.py"),
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
            "deterministic_selected_tool = True",
            "deterministic_selected_intent = True",
        ):
            assert fragment not in source
