from __future__ import annotations

from app.shared.contracts.current_shell_runtime_bridge import (
    bridge_current_shell_manager_output,
    build_current_shell_runtime_bridge_contract,
)


def test_current_shell_runtime_bridge_contract_declares_mainline_as_upstream_truth() -> None:
    artifact = build_current_shell_runtime_bridge_contract()

    assert artifact["artifact_type"] == "current_shell_runtime_bridge_contract"
    assert artifact["status"] == "pass"
    assert artifact["upstream_truth_branch"] == "main"
    assert artifact["upstream_truth_contract_family"] == "CurrentShell_ManagerRuntime"
    assert artifact["reparse_raw_user_input_for_semantics"] is False
    assert artifact["llm_output_is_bridge_source_of_semantic_truth"] is True
    assert "persist_meal_log" in artifact["forbidden_manager_tools"]


def test_current_shell_runtime_bridge_maps_estimate_flow_to_shared_turn_plan() -> None:
    artifact = bridge_current_shell_manager_output(
        {
            "manager_action": "call_tools",
            "intent": "estimate",
            "workflow_effect": "food_log_candidate",
            "tool_calls": [
                {"name": "estimate_nutrition", "arguments": {"meal_text": "tea egg"}},
                {"name": "compare_against_budget", "arguments": {}},
            ],
            "final_action": None,
        }
    )

    assert artifact["status"] == "pass"
    assert artifact["source_intent"] == "estimate"
    plan = artifact["shared_manager_turn_plan_preview"]
    assert plan["primary_workflow"] == "intake_estimate_with_optional_budget_reflection"
    assert [item["capability_id"] for item in plan["requested_capabilities"]] == [
        "intake",
        "query",
    ]
    assert [item["tool_name"] for item in plan["candidate_tool_calls"]] == [
        "intake.run",
        "query.run",
    ]
    assert plan["mutation_posture"] == "mutation_guarded"


def test_current_shell_runtime_bridge_maps_budget_answer_to_read_only_query() -> None:
    artifact = bridge_current_shell_manager_output(
        {
            "manager_action": "final",
            "intent": "answer_budget",
            "workflow_effect": "query_only",
            "tool_calls": [],
            "final_action": "no_commit",
        }
    )

    assert artifact["status"] == "pass"
    plan = artifact["shared_manager_turn_plan_preview"]
    assert plan["primary_workflow"] == "budget_query"
    assert [item["capability_id"] for item in plan["requested_capabilities"]] == ["query"]
    assert plan["mutation_posture"] == "read_only"
    assert "answer_budget_from_runtime_truth_only" in plan["response_obligations"]


def test_current_shell_runtime_bridge_preserves_onboarding_without_fake_capability_mapping() -> None:
    artifact = bridge_current_shell_manager_output(
        {
            "manager_action": "final",
            "intent": "onboarding",
            "workflow_effect": "no_mutation",
            "tool_calls": [],
            "final_action": "no_commit",
        }
    )

    assert artifact["status"] == "pass"
    plan = artifact["shared_manager_turn_plan_preview"]
    assert plan["primary_workflow"] == "onboarding_bootstrap_required"
    assert plan["requested_capabilities"] == []
    assert plan["mutation_posture"] == "read_only"


def test_current_shell_runtime_bridge_blocks_deterministic_write_tools_from_manager_surface() -> None:
    artifact = bridge_current_shell_manager_output(
        {
            "manager_action": "call_tools",
            "intent": "estimate",
            "workflow_effect": "food_log_candidate",
            "tool_calls": [{"name": "write_ledger", "arguments": {}}],
            "final_action": None,
        }
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["current_shell_forbidden_manager_tool:write_ledger"]
