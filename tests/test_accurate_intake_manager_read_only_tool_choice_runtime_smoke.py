from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.composition.accurate_intake_manager_read_only_tool_choice_runtime_smoke import (
    build_manager_read_only_tool_choice_runtime_smoke_artifact,
)


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_manager_read_only_tool_choice_runtime_smoke_covers_current_shell_read_only_cases() -> None:
    artifact = asyncio.run(build_manager_read_only_tool_choice_runtime_smoke_artifact())

    assert artifact["artifact_schema_version"] == "1.0"
    assert artifact["artifact_type"] == "accurate_intake_manager_read_only_tool_choice_runtime_smoke"
    assert artifact["status"] == "manager_read_only_tool_choice_runtime_smoke_pass"
    assert artifact["backing_class"] == "runtime_backed"
    assert artifact["semantic_owner"] == "fixture_manager_structured_decision"
    assert artifact["tool_execution_owner"] == "non_fooddb_read_tool_executor"
    assert artifact["finalizer_owner"] == "non_fooddb_read_only_turn"
    assert artifact["summary"]["case_count"] == 6
    assert artifact["summary"]["runtime_backed_case_count"] == 6
    assert artifact["deterministic_selected_tool"] is False
    assert artifact["deterministic_selected_intent"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False


def test_manager_read_only_tool_choice_runtime_smoke_uses_public_tool_results_and_no_mutation() -> None:
    cases = _by_id(asyncio.run(build_manager_read_only_tool_choice_runtime_smoke_artifact()))

    assert cases["budget_remaining_runtime_read"]["tool_result_summary"]["tool_name"] == (
        "budget.get_remaining_calories"
    )
    assert cases["budget_day_meal_log_runtime_read"]["tool_result_summary"]["tool_name"] == (
        "budget.get_day_meal_log"
    )
    assert cases["body_active_plan_runtime_read"]["tool_result_summary"]["tool_name"] == "body.get_active_plan"
    assert cases["body_latest_observation_runtime_read"]["tool_result_summary"]["tool_name"] == (
        "body.get_latest_observation"
    )
    assert cases["calibration_pending_proposal_runtime_read"]["tool_result_summary"]["tool_name"] == (
        "calibration.get_pending_proposal"
    )
    assert cases["app_usage_help_runtime_read"]["tool_result_summary"]["tool_name"] == (
        "app.answer_usage_question"
    )

    for case in cases.values():
        summary = case["tool_result_summary"]
        assert summary["canonical_tool_name"] == case["selected_tool"]
        assert summary["tool_kind"] == "read_only"
        assert summary["mutation_authority"] is False
        assert case["state_mutation"] == {
            "canonical_commit": False,
            "ledger_updated": False,
            "meal_logged": False,
        }


def test_manager_read_only_tool_choice_runtime_smoke_exercises_runtime_finalizer_outputs() -> None:
    cases = _by_id(asyncio.run(build_manager_read_only_tool_choice_runtime_smoke_artifact()))

    budget = cases["budget_remaining_runtime_read"]
    assert budget["finalizer_mode"] == "remaining_budget"
    assert budget["finalizer_output"]["remaining_budget"]["remaining_kcal"] >= 0
    assert budget["trace_events"][0]["stage"] == "v2_remaining_budget_read"

    latest_weight = cases["body_latest_observation_runtime_read"]
    assert latest_weight["finalizer_mode"] == "assistant_message_override"
    assert latest_weight["finalizer_output"]["assistant_message_override"] == (
        "Latest weight is available from the body read model."
    )

    app_usage = cases["app_usage_help_runtime_read"]
    assert app_usage["finalizer_output"]["assistant_message_override"] == (
        "I can answer general product questions here, but I will not change state from this path."
    )


def test_manager_read_only_tool_choice_runtime_smoke_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.run_accurate_intake_manager_read_only_tool_choice_runtime_smoke import main

    output_path = tmp_path / "manager-read-only-tool-choice-runtime-smoke.json"
    exit_code = main(["--output", str(output_path)])
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "manager_read_only_tool_choice_runtime_smoke_pass"
    assert artifact["summary"]["runtime_backed_case_count"] == 6
