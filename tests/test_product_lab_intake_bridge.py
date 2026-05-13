from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_intake_bridge import (
    build_advanced_lab_intake_bridge_trace,
)
from app.advanced_shadow_lab.product_lab_manager_tool_dispatch import (
    execute_product_lab_manager_tool_call,
)
from app.advanced_shadow_lab.product_lab_manager_tool_spine import (
    build_product_lab_manager_tool_registry,
    run_product_lab_manager_tool_loop,
)


def test_intake_bridge_consumes_current_shell_manager_result_without_lab_mutation() -> None:
    trace = build_advanced_lab_intake_bridge_trace(
        turn=_turn(),
        arguments={"intake_manager_result": _intake_result()},
    )

    assert trace["artifact_type"] == "advanced_product_lab_intake_bridge_trace"
    assert trace["status"] == "pass"
    assert trace["current_shell_contract_ref"] == (
        "app.runtime.agent.manager_result_builder.IntakeManagerResult"
    )
    assert trace["intake_bridge_contract_backed"] is True
    assert trace["current_shell_intake_result"]["final_action"] == "commit"
    assert trace["current_shell_intake_result"]["workflow_effect"] == "meal_logged"
    assert trace["current_shell_intake_result"]["estimated_kcal"] == 720
    assert trace["manager_style_tool_result_returned"] is True
    assert trace["canonical_product_mutation_allowed"] is False
    assert trace["meal_thread_mutated"] is False
    assert trace["ledger_entry_created"] is False
    assert trace["durable_product_memory_written"] is False


def test_intake_bridge_blocks_missing_contract_fields_and_mutation_overclaim() -> None:
    missing = build_advanced_lab_intake_bridge_trace(
        turn=_turn(),
        arguments={"intake_manager_result": {"intent": "log_meal"}},
    )
    overclaim = build_advanced_lab_intake_bridge_trace(
        turn=_turn(),
        arguments={
            "intake_manager_result": _intake_result(),
            "ledger_entry_created": True,
        },
    )

    assert missing["status"] == "blocked"
    assert "intake_manager_result.manager_action.missing" in missing["blockers"]
    assert "intake_manager_result.workflow_effect.missing" in missing["blockers"]
    assert overclaim["status"] == "blocked"
    assert "arguments.ledger_entry_created_forbidden" in overclaim["blockers"]
    assert overclaim["canonical_product_mutation_allowed"] is False


def test_intake_run_is_registered_and_dispatches_through_manager_tool_envelope() -> None:
    registry = build_product_lab_manager_tool_registry()
    tool_by_name = {tool["tool_name"]: tool for tool in registry["tool_specs"]}

    assert "intake.run" in registry["tool_names"]
    assert tool_by_name["intake.run"]["capability_family"] == "intake"
    assert tool_by_name["intake.run"]["tool_mode"] == "contract_backed_intake_handoff"
    assert tool_by_name["intake.run"]["canonical_mutation_allowed"] is False

    result = execute_product_lab_manager_tool_call(
        turn=_turn(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        tool_call={
            "call_id": "intake-1",
            "tool_name": "intake.run",
            "arguments": {"intake_manager_result": _intake_result()},
        },
        store=None,
    )

    assert result["status"] == "pass"
    assert result["capability_family"] == "intake"
    assert result["result_artifact_type"] == "advanced_product_lab_intake_bridge_trace"
    assert result["result_artifact"]["canonical_product_mutation_allowed"] is False
    assert result["returned_to_manager"] is True


def test_manager_tool_loop_can_place_intake_before_query_and_rescue(tmp_path: Path) -> None:
    artifact = run_product_lab_manager_tool_loop(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        manager_script=[
            {
                "pass_id": "manager-pass-1",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "call_id": "intake-1",
                        "tool_name": "intake.run",
                        "arguments": {"intake_manager_result": _intake_result()},
                    },
                    {"call_id": "query-1", "tool_name": "query.run", "arguments": {}},
                    {"call_id": "rescue-1", "tool_name": "rescue.run", "arguments": {}},
                ],
            },
            {
                "pass_id": "manager-pass-2",
                "action": "final",
                "final_response": {
                    "copy": "intake first, then query and rescue",
                    "source_tool_call_ids": ["intake-1", "query-1", "rescue-1"],
                },
            },
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["product_capabilities_exercised"] == ["intake", "query", "rescue"]
    assert artifact["tool_result_trace"][0]["tool_name"] == "intake.run"
    assert artifact["canonical_product_mutation_allowed"] is False


def _turn() -> dict[str, object]:
    return {
        "session_id": "intake-bridge-session",
        "turn_id": "turn-1",
        "surface": "chat",
        "user_utterance": "I ate ramen, then check budget and rescue if needed",
        "semantic_intent_fixture": "intake_query_rescue",
    }


def _intake_result() -> dict[str, object]:
    return {
        "intent": "log_meal",
        "manager_action": "final",
        "final_action": "commit",
        "workflow_effect": "meal_logged",
        "exactness": "estimated",
        "confidence": "medium",
        "evidence_posture": "tool_estimated",
        "answer_contract": {
            "reply_text": "Ramen estimated around 720 kcal.",
            "estimated_kcal": 720,
        },
        "tool_calls": ["estimate_nutrition"],
        "tool_results": [
            {
                "tool_name": "estimate_nutrition",
                "evidence": {"nutrition_payload": {"estimated_kcal": 720}},
            }
        ],
    }
