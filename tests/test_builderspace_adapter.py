import json

from app.providers.builderspace_adapter import BuilderSpaceAdapter
from app.schemas import ComponentEstimate


def test_format_user_message_serializes_pydantic_objects() -> None:
    adapter = BuilderSpaceAdapter()
    payload = {
        "original_answer": {
            "component_estimates": [
                ComponentEstimate(
                    name="Test",
                    source="lookup",
                    evidence_role="ingredient_anchor",
                    estimate_basis="anchored",
                    confidence_tier="medium",
                    estimated_kcal=100,
                    protein_g=5,
                    carb_g=10,
                    fat_g=3,
                )
            ]
        }
    }

    serialized = adapter._format_user_message("final_response_pass", payload)
    parsed = json.loads(serialized)
    assert parsed["original_answer"]["component_estimates"][0]["name"] == "Test"


def test_stage_temperatures_default_to_independent_values() -> None:
    adapter = BuilderSpaceAdapter()

    assert adapter._temperature_for_stage("task_meal_link_pass") == 0.0
    assert adapter._temperature_for_stage("planner_pass_initial") == 0.0
    assert adapter._temperature_for_stage("decision_pass") == 0.0
    assert adapter._temperature_for_stage("nutrition_resolution_pass_initial") == 0.1
    assert adapter._temperature_for_stage("primary_answer_pass_initial") == 0.1
    assert adapter._temperature_for_stage("final_response_pass") == 0.5


def test_decision_schema_exposes_react_fields() -> None:
    adapter = BuilderSpaceAdapter()
    schema = adapter._response_schema_for_stage("decision_pass")

    assert schema is not None
    assert "tool_goal" in schema["properties"]
    assert "missing_evidence_type" in schema["properties"]
    assert "expected_success_condition" in schema["properties"]
