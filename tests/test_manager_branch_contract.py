from __future__ import annotations

from app.providers.builderspace_runtime_contract import manager_loop_schema
from app.runtime.agent.manager_branch_contract import validate_manager_pass1_branch


def test_b1_clarification_pass2_constraint_allows_trace_only_item_results() -> None:
    payload = {
        "manager_action": "final",
        "interaction_family": "food_logging",
        "response_mode": "clarification",
        "final_action": "request_clarification",
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
