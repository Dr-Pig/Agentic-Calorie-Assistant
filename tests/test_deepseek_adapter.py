import pytest

from app.providers.deepseek_adapter import DeepSeekAdapter


def test_readiness_exposes_only_single_manager_stage_models() -> None:
    adapter = DeepSeekAdapter()

    readiness = adapter.readiness()

    assert readiness["provider"] == "deepseek"
    assert readiness["manager_model"] == adapter.model
    assert readiness["stage_models"] == {
        "intake_manager_round": adapter.model,
    }
    assert readiness["timeout_seconds"] <= 15


def test_response_schema_only_exists_for_manager_stages() -> None:
    adapter = DeepSeekAdapter()

    assert adapter._response_schema_for_stage("intake_manager_round") is not None
    assert adapter._response_schema_for_stage("unknown_stage") is None


def test_extract_json_object_reads_fenced_manager_payload() -> None:
    adapter = DeepSeekAdapter()

    payload = adapter._extract_json_object("```json\n{\"workflow_effect\":\"ask_followup\"}\n```")

    assert payload["workflow_effect"] == "ask_followup"


def test_extract_json_object_rejects_non_json_content() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(RuntimeError):
        adapter._extract_json_object("not-json")


def test_manager_response_schemas_are_closed_contracts() -> None:
    adapter = DeepSeekAdapter()

    for stage in ("intake_manager_round",):
        schema = adapter._response_schema_for_stage(stage)
        assert schema is not None
        assert schema["additionalProperties"] is False


def test_validate_manager_payload_rejects_missing_required_fields() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(RuntimeError, match="missing required"):
        adapter._validate_manager_payload("intake_manager_round", {"workflow_effect": "commit"})


def test_validate_manager_payload_rejects_unknown_fields() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(RuntimeError, match="unknown fields"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "commit",
                "workflow_effect": "commit",
                "target_attachment": {},
                "exactness": "anchored",
                "confidence": "medium",
                "evidence_posture": "generic_with_uncertainty",
                "repair_ack": False,
                "answer_contract": {},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "generic",
                "unexpected": True,
            },
        )


def test_manager_schema_exposes_semantic_contract_fields_without_reasoning_dump() -> None:
    adapter = DeepSeekAdapter()
    schema = adapter._response_schema_for_stage("intake_manager_round")

    assert schema is not None
    assert "intent" in schema["properties"]
    assert "target_attachment" in schema["properties"]
    assert "exactness" in schema["properties"]
    assert "confidence" in schema["properties"]
    assert "evidence_posture" in schema["properties"]
    assert "repair_ack" in schema["properties"]
    assert "thoughts" not in schema["properties"]
    assert "reasoning" not in schema["properties"]
