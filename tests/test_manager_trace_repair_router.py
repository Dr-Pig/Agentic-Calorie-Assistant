from __future__ import annotations

from app.runtime.agent.manager_react_trace import build_manager_react_trace
from app.runtime.agent.manager_trace_repair_router import MANAGER_TRACE_REPAIR_ROUTER_VERSION


def _round(decision: dict[str, object]) -> dict[str, object]:
    return {
        "round_index": 0,
        "stage": "intake_manager_round",
        "latency_ms": 12,
        "decision": decision,
        "trace": {"provider": "fake"},
        "prompt_registry": {"manager_prompt_version": "test"},
        "prompt_layer_contract": {
            "contract_version": "manager_prompt_layer_contract.v1",
            "runtime_payload_layer_plan": {"uncategorized_dynamic_keys": []},
        },
        "phase_a_input": {
            "manager_loop_scope": "intake_execution",
            "manager_context_packet_v1": {"context_packet_hash": "abc"},
        },
    }


def test_react_trace_routes_complete_success_without_primary_repair_layer() -> None:
    trace = build_manager_react_trace(
        manager_rounds=[
            _round(
                {
                    "manager_action": "final",
                    "final_action": "commit",
                    "workflow_effect": "commit",
                    "tool_calls": [],
                    "answer_contract": {"reply_text": "ok"},
                    "semantic_decision": {
                        "active_workflow_resolution": {
                            "current_turn_relation": "none",
                            "slot_updates": [],
                            "still_missing_slots": [],
                            "attach_target": {},
                            "final_action": "commit",
                            "resolution_basis": ["current_turn"],
                            "selection_owner": "manager",
                            "deterministic_role": "validate_only",
                        }
                    },
                }
            )
        ],
        tool_results=[{"tool_name": "estimate_nutrition", "failure_family": None}],
        guard_outcome={"ok": True},
        failure_family=None,
    )

    router = trace["repair_router"]

    assert router["router_version"] == MANAGER_TRACE_REPAIR_ROUTER_VERSION
    assert router["primary_repair_layer"] is None
    assert router["layers"]["L1_prompt_architecture"]["present"] is True
    assert router["layers"]["L2_context_packet"]["present"] is True
    assert router["layers"]["L3_manager_semantics"]["evidence"]["active_workflow_resolution_present"] is True
    assert router["deterministic_role"] == "trace_attribution_only_no_semantic_rewrite"
    assert "L9_ui_same_truth" in router["layer_order"]
    assert router["layers"]["L9_ui_same_truth"]["present"] is False
    assert router["layers"]["L9_ui_same_truth"]["evidence"]["ui_same_truth_trace_present"] is False


def test_react_trace_routes_missing_active_workflow_resolution_to_manager_semantics() -> None:
    trace = build_manager_react_trace(
        manager_rounds=[
            _round(
                {
                    "manager_action": "final",
                    "final_action": "correction_applied",
                    "workflow_effect": "correction",
                    "tool_calls": [],
                    "answer_contract": {"reply_text": "ok"},
                    "semantic_decision": {"current_turn_intent": "correct_meal"},
                }
            )
        ],
        tool_results=[],
        guard_outcome={},
        failure_family=None,
    )

    router = trace["repair_router"]

    assert router["primary_repair_layer"] == "L3_manager_semantics"
    assert router["layers"]["L3_manager_semantics"]["present"] is True
    assert router["layers"]["L3_manager_semantics"]["evidence"]["active_workflow_resolution_present"] is False


def test_react_trace_routes_contract_violation_to_prompt_schema_layer() -> None:
    trace = build_manager_react_trace(
        manager_rounds=[_round({"manager_action": "final", "tool_calls": []})],
        tool_results=[],
        guard_outcome={},
        failure_family="manager_output_contract_violation",
    )

    router = trace["repair_router"]

    assert router["primary_repair_layer"] == "L1_prompt_architecture"
    assert router["blocking_failure_family"] == "manager_output_contract_violation"


def test_react_trace_routes_ui_mismatch_to_ui_same_truth_layer() -> None:
    trace = build_manager_react_trace(
        manager_rounds=[
            _round(
                {
                    "manager_action": "final",
                    "final_action": "commit",
                    "workflow_effect": "commit",
                    "semantic_decision": {
                        "active_workflow_resolution": {
                            "current_turn_relation": "none",
                            "slot_updates": [],
                            "still_missing_slots": [],
                            "attach_target": {},
                            "final_action": "commit",
                            "resolution_basis": ["current_turn"],
                            "selection_owner": "manager",
                            "deterministic_role": "validate_only",
                        }
                    },
                    "ui_same_truth": {
                        "chat_matches_backend": False,
                        "today_matches_read_model": True,
                    },
                }
            )
        ],
        tool_results=[],
        guard_outcome={},
        failure_family="ui_same_truth_mismatch",
    )

    router = trace["repair_router"]

    assert router["primary_repair_layer"] == "L9_ui_same_truth"
    assert router["layers"]["L9_ui_same_truth"]["present"] is True
    assert router["layers"]["L9_ui_same_truth"]["evidence"]["ui_same_truth_trace_present"] is True
