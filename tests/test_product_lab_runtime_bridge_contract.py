from __future__ import annotations

from app.advanced_shadow_lab.product_lab_runtime_bridge_contract import (
    bridge_product_lab_runtime_surface,
    build_product_lab_runtime_bridge_contract,
)


def test_product_lab_runtime_bridge_contract_marks_direct_runtime_bypass_as_transitional() -> None:
    artifact = build_product_lab_runtime_bridge_contract()

    assert artifact["artifact_type"] == "advanced_product_lab_runtime_bridge_contract"
    assert artifact["status"] == "pass"
    assert artifact["upstream_truth_branch"] == "main"
    assert artifact["upstream_truth_contract_family"] == "CurrentShell_ManagerRuntime"
    assert artifact["manager_script_tool_names_already_use_shared_vocabulary"] is True
    assert artifact["direct_runtime_bypass_is_transitional_not_upstream_truth"] is True


def test_product_lab_runtime_bridge_maps_manager_script_path_to_shared_turn_plan() -> None:
    artifact = bridge_product_lab_runtime_surface(
        turn={
            "surface": "chat",
            "semantic_intent_fixture": "advanced_recommendation_rescue_proactive_loop",
        },
        manager_script=[
            {
                "action": "call_tools",
                "tool_calls": [
                    {"tool_name": "memory.search"},
                    {"tool_name": "recommendation.run"},
                    {"tool_name": "rescue.run"},
                    {"tool_name": "proactive.run"},
                ],
            }
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["manager_script_present"] is True
    assert artifact["direct_runtime_bypass_present"] is False
    plan = artifact["shared_manager_turn_plan_preview"]
    assert plan["primary_workflow"] == "advanced_recommendation_rescue_proactive_loop"
    assert [item["capability_id"] for item in plan["requested_capabilities"]] == [
        "memory",
        "recommendation",
        "rescue",
        "proactive",
    ]
    assert [item["tool_name"] for item in plan["candidate_tool_calls"]] == [
        "memory.search",
        "recommendation.run",
        "rescue.run",
        "proactive.run",
    ]


def test_product_lab_runtime_bridge_maps_direct_runtime_path_without_faking_tool_calls() -> None:
    artifact = bridge_product_lab_runtime_surface(
        turn={
            "surface": "chat",
            "semantic_intent_fixture": "swap_suggestion",
        },
        manager_script=None,
    )

    assert artifact["status"] == "pass"
    assert artifact["manager_script_present"] is False
    assert artifact["direct_runtime_bypass_present"] is True
    plan = artifact["shared_manager_turn_plan_preview"]
    assert plan["primary_workflow"] == "swap_suggestion"
    assert [item["capability_id"] for item in plan["requested_capabilities"]] == [
        "recommendation"
    ]
    assert plan["candidate_tool_calls"] == []


def test_product_lab_runtime_bridge_blocks_unmapped_fixture_intent() -> None:
    artifact = bridge_product_lab_runtime_surface(
        turn={"surface": "chat", "semantic_intent_fixture": "unknown_fixture"},
        manager_script=[],
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "product_lab_fixture_intent_unmapped:unknown_fixture"
    ]


def test_product_lab_runtime_bridge_blocks_unmapped_manager_script_tool() -> None:
    artifact = bridge_product_lab_runtime_surface(
        turn={
            "surface": "chat",
            "semantic_intent_fixture": "weekly_insight_proactive_lab",
        },
        manager_script=[
            {
                "action": "call_tools",
                "tool_calls": [{"tool_name": "generic.workflow_engine.run"}],
            }
        ],
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "product_lab_manager_script_tool_unmapped:generic.workflow_engine.run"
    ]
