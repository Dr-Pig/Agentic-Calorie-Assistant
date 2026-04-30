from __future__ import annotations

from app.providers.builderspace_runtime_contract import manager_loop_schema
from app.providers.builderspace_runtime_contract import validate_manager_payload
from app.runtime.agent.manager_branch_constraints import (
    B1_COMMON_FOOD_ITEM_CASE_FAMILY,
    B1_LISTED_INGREDIENT_CASE_FAMILY,
)
from app.runtime.agent.manager_branch_contract import validate_manager_pass1_branch
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE


def _forced_pass1_constraints(case_family: str) -> dict[str, str]:
    return {
        "phase_b1_manager_role": "pass_1_tool_request",
        "phase_b1_pass1_mode": "forced_tool_request_smoke",
        "phase_b1_case_family": case_family,
    }


def _canonical_tool_call_payload(tool_name: str = "lookup_generic_food") -> dict[str, object]:
    return {
        "manager_action": "call_tools",
        "interaction_family": "food_logging",
        "response_mode": "intake_result",
        "operations": [],
        "answer_contract": {},
        "tool_calls": [{"name": tool_name, "arguments": {"food_name": "tea egg"}}],
    }


def test_forced_b1_pass1_generic_tool_call_uses_tool_call_contract() -> None:
    constraints = _forced_pass1_constraints(B1_COMMON_FOOD_ITEM_CASE_FAMILY)
    schema = manager_loop_schema(constraints)

    assert schema["properties"]["manager_action"]["enum"] == ["call_tools"]
    assert schema["properties"]["operations"]["maxItems"] == 0
    assert "tool_calls" in schema["required"]
    assert "intent" not in schema["required"]

    validate_manager_payload(MANAGER_LOOP_STAGE, _canonical_tool_call_payload(), constraints=constraints)


def test_forced_b1_pass1_listed_ingredient_tool_call_uses_tool_call_contract() -> None:
    constraints = _forced_pass1_constraints(B1_LISTED_INGREDIENT_CASE_FAMILY)
    schema = manager_loop_schema(constraints)

    assert schema["properties"]["manager_action"]["enum"] == ["call_tools"]
    assert schema["properties"]["operations"]["maxItems"] == 0
    assert "tool_calls" in schema["required"]
    assert "intent" not in schema["required"]

    validate_manager_payload(MANAGER_LOOP_STAGE, _canonical_tool_call_payload(), constraints=constraints)


def test_b1_clarification_pass2_constraint_allows_trace_only_item_results() -> None:
    payload = {
        "manager_action": "final",
        "interaction_family": "food_logging",
        "response_mode": "clarification",
        "intent": "log_meal",
        "workflow_effect": "pause_for_clarification",
        "target_attachment": {},
        "final_action": "request_clarification",
        "exactness": "none",
        "confidence": "low",
        "evidence_posture": "insufficient",
        "repair_ack": False,
        "operations": [],
        "item_results": [
            {
                "food_name": "滷味",
                "kcal_range": [300, 450],
                "likely_kcal": 380,
                "uncertainty": "high",
                "evidence_used": ["trace_only_candidate"],
            }
        ],
        "uncertainty_posture": "composition_unknown_basket",
        "answer_contract": {"text": "Please list the specific items in the basket so I can estimate accurately."},
    }
    constraints = {
        "phase_b1_manager_role": "pass_2_synthesis",
        "phase_b1_pass1_mode": "natural_tool_selection_probe",
        "phase_b1_case_family": "composition_unknown_self_selected_basket",
    }

    schema = manager_loop_schema(constraints)

    assert schema["properties"]["response_mode"]["enum"] == ["clarification"]
    assert schema["properties"]["final_action"]["enum"] == ["request_clarification"]
    assert "item_results" in schema["properties"]
    assert "final_action" in schema["required"]

    validate_manager_pass1_branch(payload, constraints)


def test_manager_loop_schema_allows_manager_semantic_decision_contract() -> None:
    schema = manager_loop_schema(None)
    payload = {
        "manager_action": "final",
        "intent": "log_meal",
        "workflow_effect": "estimate_with_followup",
        "target_attachment": {"mode": "new_meal"},
        "exactness": "anchored",
        "confidence": "medium",
        "evidence_posture": "bounded_estimate",
        "repair_ack": False,
        "semantic_decision": {
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "target_attachment": {"mode": "new_meal"},
            "workflow_effect": "estimate_with_followup",
            "final_action_candidate": "commit",
            "estimation_posture": "estimable",
            "followup_posture": "refinement_not_commit_gate",
            "mutation_intent_candidate": "canonical_write",
            "uncertainty_posture": "bounded_estimate",
            "source": "single_manager_loop",
        },
    }

    assert "semantic_decision" in schema["properties"]
    validate_manager_payload(MANAGER_LOOP_STAGE, payload)


def test_constrained_manager_loop_schema_preserves_semantic_decision_field() -> None:
    constraints = {
        "phase_b1_manager_role": "pass_2_synthesis",
        "phase_b1_pass1_mode": "natural_tool_selection_probe",
        "phase_b1_case_family": "generic_food",
    }

    schema = manager_loop_schema(constraints)

    assert "semantic_decision" in schema["properties"]
