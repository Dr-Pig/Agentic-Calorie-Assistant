from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_bounded_react_runner import (
    run_context_engineering_bounded_react_trace,
)
from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)


def test_bounded_react_runner_executes_context_then_downstream_tools() -> None:
    trace = run_context_engineering_bounded_react_trace(
        case_id="ce-stress-001",
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    assert trace["artifact_type"] == "advanced_product_lab_bounded_react_replan_trace"
    assert trace["status"] == "pass"
    assert trace["case_id"] == "ce-stress-001"
    assert trace["manager_pass_count"] == 2
    assert trace["manager_pass_trace"][0]["tool_order"] == ["intake.run", "query.run"]
    assert trace["manager_pass_trace"][1]["manager_action"] == "replan_after_tool_results"
    assert trace["manager_pass_trace"][1]["tool_results_seen_count"] == 2
    assert trace["manager_pass_trace"][1]["tool_order"] == [
        "rescue.run",
        "recommendation.run",
    ]
    assert trace["tool_result_count"] == 4
    assert trace["final_response_deferred_to_slice13"] is True
    assert trace["raw_user_text_semantic_inference_performed"] is False
    assert trace["canonical_product_mutation_allowed"] is False
    assert trace["blockers"] == []


def test_bounded_react_runner_blocks_too_low_pass_budget() -> None:
    trace = run_context_engineering_bounded_react_trace(
        case_id="ce-stress-001",
        fixture_inputs=build_product_lab_fixture_inputs(),
        max_manager_passes=1,
    )

    assert trace["status"] == "blocked"
    assert trace["blockers"] == ["react_pass_budget.too_low_for_replan"]
    assert trace["manager_pass_trace"] == []


def test_bounded_react_runner_does_not_reclassify_fixture_provider_plan() -> None:
    trace = run_context_engineering_bounded_react_trace(
        case_id="ce-stress-001",
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    assert trace["semantic_decision_owner"] == "fixture_provider_manager_turn_plan"
    assert trace["deterministic_replan_role"] == "partition_validate_and_execute"
    assert trace["deterministic_semantic_rewrite_performed"] is False
