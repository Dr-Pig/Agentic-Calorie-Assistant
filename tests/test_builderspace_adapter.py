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

    serialized = adapter._format_user_message("intake_manager_round", payload)
    parsed = json.loads(serialized)
    assert parsed["stage"] == "intake_manager_round"
    assert parsed["payload"]["original_answer"]["component_estimates"][0]["name"] == "Test"


def test_stage_temperatures_only_expose_single_manager_stages() -> None:
    adapter = BuilderSpaceAdapter()

    assert adapter._temperature_for_stage("intake_manager_round") == 0.0
    assert adapter.timeout_seconds <= 15


def test_manager_round_schema_exposes_react_fields() -> None:
    adapter = BuilderSpaceAdapter()
    schema = adapter._response_schema_for_stage("intake_manager_round")

    assert schema is not None
    assert "manager_action" in schema["properties"]
    assert "tool_calls" in schema["properties"]
    assert "workflow_effect" in schema["properties"]
    assert "intent" in schema["properties"]
    assert "target_attachment" in schema["properties"]
    assert "exactness" in schema["properties"]
    assert "confidence" in schema["properties"]
    assert "evidence_posture" in schema["properties"]
    assert "repair_ack" in schema["properties"]
    assert "thoughts" not in schema["properties"]


def test_manager_stages_use_manager_model_and_schema() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    assert adapter._model_for_stage("intake_manager_round") == "deepseek"
    assert adapter._response_schema_for_stage("intake_manager_round") is not None


def test_readiness_exposes_manager_model_stage_mapping() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")
    readiness = adapter.readiness()

    assert readiness["manager_model"] == "deepseek"
    assert readiness["stage_models"]["intake_manager_round"] == "deepseek"
    assert set(readiness["stage_models"].keys()) == {
        "intake_manager_round",
    }
