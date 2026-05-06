from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke import (
    build_non_fooddb_read_only_tool_loop_fake_smoke_artifact,
)


REQUIRED_CASES = [
    "budget_remaining_read",
    "budget_day_meal_log_read",
    "body_active_plan_read",
    "body_latest_observation_read",
    "calibration_pending_proposal_read",
    "app_usage_help_read",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_non_fooddb_read_only_tool_loop_fake_smoke_covers_read_only_tool_results() -> None:
    artifact = build_non_fooddb_read_only_tool_loop_fake_smoke_artifact()

    assert artifact["artifact_type"] == "accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke"
    assert artifact["status"] == "non_fooddb_read_only_tool_loop_fake_smoke_pass"
    assert artifact["fixture_manager_used"] is True
    assert artifact["semantic_owner"] == "fixture_manager_structured_decision"
    assert artifact["tool_execution_owner"] == "deterministic_domain_read_model_fixture"
    assert artifact["responder_role"] == "mirror_allowed_facts_only"
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
    assert [case["case_id"] for case in artifact["cases"]] == REQUIRED_CASES

    for case in artifact["cases"]:  # type: ignore[index]
        result = case["tool_result_envelope"]
        assert result["read_only"] is True
        assert result["mutation_authority"] is False
        assert result["tool_execution_source"] == "deterministic_domain_read_model_fixture"
        assert case["responder_input"]["allowed_facts"] == result["allowed_facts"]
        assert case["accepted_response"]["verdict"] == "accepted"
        assert case["rejected_response"]["verdict"] == "blocked"


def test_non_fooddb_read_only_tool_loop_fake_smoke_maps_expected_tools_and_facts() -> None:
    cases = _by_id(build_non_fooddb_read_only_tool_loop_fake_smoke_artifact())

    assert cases["budget_remaining_read"]["selected_tool"] == "budget.get_remaining_calories"
    assert cases["budget_remaining_read"]["tool_result_envelope"]["truth_owner"] == "budget_domain"
    assert cases["budget_remaining_read"]["accepted_response"]["claims"][0]["claim_type"] == "remaining"

    assert cases["budget_day_meal_log_read"]["selected_tool"] == "budget.get_day_meal_log"
    assert cases["budget_day_meal_log_read"]["accepted_response"]["claims"][0]["claim_type"] == "meal_log_status"

    assert cases["body_active_plan_read"]["selected_tool"] == "body.get_active_plan"
    assert cases["body_latest_observation_read"]["selected_tool"] == "body.get_latest_observation"
    assert cases["calibration_pending_proposal_read"]["selected_tool"] == "calibration.get_pending_proposal"
    assert cases["app_usage_help_read"]["selected_tool"] == "app.answer_usage_question"


def test_non_fooddb_read_only_tool_loop_fake_smoke_blocks_missing_inputs_and_overclaims() -> None:
    artifact = build_non_fooddb_read_only_tool_loop_fake_smoke_artifact(
        tool_choice_wall={"status": "blocked", "cases": []},
        cases=[],
        overrides={"live_llm_invoked": True, "fooddb_used": True},
    )

    assert artifact["status"] == "blocked"
    assert "manager_tool_choice_regression_wall.not_pass" in artifact["blockers"]
    assert "missing_case:budget_remaining_read" in artifact["blockers"]
    assert "live_llm_invoked" in artifact["blockers"]
    assert "fooddb_used" in artifact["blockers"]


def test_non_fooddb_read_only_tool_loop_fake_smoke_blocks_mutating_or_unattributed_results() -> None:
    artifact = build_non_fooddb_read_only_tool_loop_fake_smoke_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[0]["tool_result_envelope"]["mutation_authority"] = True  # type: ignore[index]
    cases[1]["tool_result_envelope"]["allowed_facts"] = []  # type: ignore[index]

    blocked = build_non_fooddb_read_only_tool_loop_fake_smoke_artifact(cases=cases)

    assert blocked["status"] == "blocked"
    assert "budget_remaining_read.mutation_authority" in blocked["blockers"]
    assert "budget_day_meal_log_read.allowed_facts_missing" in blocked["blockers"]


def test_non_fooddb_read_only_tool_loop_fake_smoke_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke import main

    output_path = tmp_path / "non-fooddb-read-only-tool-loop-fake-smoke.json"
    exit_code = main(["--output", str(output_path)])
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "non_fooddb_read_only_tool_loop_fake_smoke_pass"
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASES)


def test_non_fooddb_read_only_tool_loop_fake_smoke_stays_out_of_forbidden_boundaries() -> None:
    for path in (
        Path("app/composition/accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke.py"),
        Path("scripts/build_accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke.py"),
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
