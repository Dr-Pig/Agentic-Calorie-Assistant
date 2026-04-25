import json
from json import JSONDecodeError

import pytest

import app.providers.builderspace_adapter as builderspace_adapter_module
from app.providers.builderspace_adapter import BuilderSpaceAdapter, BuilderSpaceResponseError
from app.schemas import ComponentEstimate


class _FakeResponse:
    def __init__(self, *, payload: object = None, text: str = "", status_code: int = 200, json_error: Exception | None = None) -> None:
        self._payload = payload
        self._json_error = json_error
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *, response: _FakeResponse, **_: object) -> None:
        self._response = response

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, *args: object, **kwargs: object) -> _FakeResponse:
        return self._response


def _configure_adapter(monkeypatch: pytest.MonkeyPatch, response: _FakeResponse) -> BuilderSpaceAdapter:
    monkeypatch.setenv("AI_BUILDER_TOKEN", "test-token")
    monkeypatch.setenv("AI_BUILDER_BASE_URL", "https://example.test/backend/v1")
    monkeypatch.setattr(
        builderspace_adapter_module.httpx,
        "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(response=response, **kwargs),
    )
    return BuilderSpaceAdapter(manager_model_override="deepseek")


def _json_envelope(content: object) -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "status": "ok",
        "usage": {"prompt_tokens": 10, "completion_tokens": 12},
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "text", "observed_type"),
    (
        (["not", "object"], "[\"not\",\"object\"]", "array"),
        ("not-object", "not-object", "string"),
    ),
)
async def test_complete_with_trace_response_json_shape_error(payload: object, text: str, observed_type: str, monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=text))

    with pytest.raises(BuilderSpaceResponseError) as exc_info:
        await adapter.complete_with_trace(
            system_prompt="Return JSON.",
            user_payload={"foo": "bar"},
            stage="intake_manager_round",
        )

    trace = exc_info.value.trace
    assert trace["failure_family"] == "response_json_shape_error"
    assert trace["failing_component"] == "builderspace_adapter.response_json"
    assert trace["observed_type"] == observed_type
    assert trace["raw_response_excerpt"]


@pytest.mark.asyncio
async def test_complete_with_trace_response_json_decode_error_is_shape_error(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _configure_adapter(
        monkeypatch,
        _FakeResponse(
            text="plain text body",
            json_error=JSONDecodeError("Expecting value", "plain text body", 0),
        ),
    )

    with pytest.raises(BuilderSpaceResponseError) as exc_info:
        await adapter.complete_with_trace(
            system_prompt="Return JSON.",
            user_payload={"foo": "bar"},
            stage="intake_manager_round",
        )

    trace = exc_info.value.trace
    assert trace["failure_family"] == "response_json_shape_error"
    assert trace["failing_component"] == "builderspace_adapter.response_json"
    assert trace["raw_response_excerpt"] == "plain text body"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    (
        {},
        {"choices": {}},
        {"choices": []},
        {"choices": ["bad-choice"]},
    ),
)
async def test_complete_with_trace_choices_shape_error(payload: dict[str, object], monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=json.dumps(payload)))

    with pytest.raises(BuilderSpaceResponseError) as exc_info:
        await adapter.complete_with_trace(
            system_prompt="Return JSON.",
            user_payload={"foo": "bar"},
            stage="intake_manager_round",
        )

    trace = exc_info.value.trace
    assert trace["failure_family"] == "choices_shape_error"
    assert trace["failing_component"] == "builderspace_adapter.extract_choices"


@pytest.mark.asyncio
@pytest.mark.parametrize("message_value", ("bad-message", ["bad-message"]))
async def test_complete_with_trace_message_shape_error(message_value: object, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"choices": [{"message": message_value, "finish_reason": "stop"}]}
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=json.dumps(payload)))

    with pytest.raises(BuilderSpaceResponseError) as exc_info:
        await adapter.complete_with_trace(
            system_prompt="Return JSON.",
            user_payload={"foo": "bar"},
            stage="intake_manager_round",
        )

    trace = exc_info.value.trace
    assert trace["failure_family"] == "message_shape_error"
    assert trace["failing_component"] == "builderspace_adapter.extract_message"


@pytest.mark.asyncio
async def test_complete_with_trace_content_shape_error_for_malformed_content_list(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _json_envelope([{"text": "{\"ok\":true}"}, "bad-part"])
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=json.dumps(payload)))

    with pytest.raises(BuilderSpaceResponseError) as exc_info:
        await adapter.complete_with_trace(
            system_prompt="Return JSON.",
            user_payload={"foo": "bar"},
            stage="intake_manager_round",
        )

    trace = exc_info.value.trace
    assert trace["failure_family"] == "content_shape_error"
    assert trace["failing_component"] == "builderspace_adapter.extract_text_content"


@pytest.mark.asyncio
async def test_complete_with_trace_strict_json_success(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _json_envelope("{\"manager_action\":\"final\",\"target_attachment\":{}}")
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=json.dumps(payload)))

    parsed, trace = await adapter.complete_with_trace(
        system_prompt="Return JSON.",
        user_payload={"foo": "bar"},
        stage="intake_manager_round",
    )

    assert parsed["manager_action"] == "final"
    assert trace["parse_contract_status"] == "strict_json"
    assert trace["parse_recovery_used"] is False
    assert trace["parse_recovery_strategy"] is None
    assert trace["parse_recovery_ambiguous"] is False


@pytest.mark.asyncio
async def test_complete_with_trace_fenced_json_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _json_envelope("```json\n{\"manager_action\":\"final\",\"target_attachment\":{}}\n```")
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=json.dumps(payload)))

    parsed, trace = await adapter.complete_with_trace(
        system_prompt="Return JSON.",
        user_payload={"foo": "bar"},
        stage="intake_manager_round",
    )

    assert parsed["manager_action"] == "final"
    assert trace["parse_contract_status"] == "fenced_json_recovered"
    assert trace["parse_recovery_used"] is True
    assert trace["parse_recovery_strategy"] == "fenced_json"
    assert any(attempt.get("status") == "recovered" for attempt in trace["parse_attempts"])


@pytest.mark.asyncio
async def test_complete_with_trace_prose_json_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _json_envelope("Here is the result:\n{\"manager_action\":\"final\",\"target_attachment\":{}}\nThanks.")
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=json.dumps(payload)))

    parsed, trace = await adapter.complete_with_trace(
        system_prompt="Return JSON.",
        user_payload={"foo": "bar"},
        stage="intake_manager_round",
    )

    assert parsed["manager_action"] == "final"
    assert trace["parse_contract_status"] == "prose_json_recovered"
    assert trace["parse_recovery_used"] is True
    assert trace["parse_recovery_strategy"] == "last_valid_json_object"
    assert trace["parse_recovery_ambiguous"] is False
    assert any(attempt.get("status") == "recovered" for attempt in trace["parse_attempts"])


@pytest.mark.asyncio
async def test_complete_with_trace_multiple_json_objects_is_ambiguous_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _json_envelope("{\"a\":1}\n{\"b\":2}")
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=json.dumps(payload)))

    with pytest.raises(BuilderSpaceResponseError) as exc_info:
        await adapter.complete_with_trace(
            system_prompt="Return JSON.",
            user_payload={"foo": "bar"},
            stage="intake_manager_round",
        )

    trace = exc_info.value.trace
    assert trace["failure_family"] == "malformed_json"
    assert trace["parse_recovery_ambiguous"] is True
    assert trace["parse_recovery_strategy"] == "last_valid_json_object"


@pytest.mark.asyncio
async def test_complete_with_trace_non_json_text_is_explicit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _json_envelope("I am ready to help, please send more information.")
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=json.dumps(payload)))

    with pytest.raises(BuilderSpaceResponseError) as exc_info:
        await adapter.complete_with_trace(
            system_prompt="Return JSON.",
            user_payload={"foo": "bar"},
            stage="intake_manager_round",
        )

    trace = exc_info.value.trace
    assert trace["failure_family"] == "non_json_model_output"
    assert trace["failing_component"] == "builderspace_adapter.extract_json_object"
    assert trace["raw_content_excerpt"]
    assert isinstance(trace, dict)


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


def test_stage_temperatures_only_expose_single_manager_stages(monkeypatch) -> None:
    monkeypatch.delenv("AI_BUILDER_TIMEOUT_SECONDS", raising=False)
    adapter = BuilderSpaceAdapter()

    assert adapter._temperature_for_stage("intake_manager_round") == 0.0
    assert adapter.timeout_seconds == 30


def test_timeout_env_45_is_honored_without_15_second_clamp(monkeypatch) -> None:
    monkeypatch.setenv("AI_BUILDER_TIMEOUT_SECONDS", "45")

    adapter = BuilderSpaceAdapter()
    readiness = adapter.readiness()

    assert adapter.timeout_seconds == 45
    assert readiness["timeout_seconds"] == 45
    assert readiness["configured_timeout_env"] == "45"
    assert readiness["default_timeout_seconds"] == 30
    assert readiness["max_timeout_seconds"] == 120
    assert readiness["timeout_was_clamped"] is False


def test_invalid_timeout_env_falls_back_to_default(monkeypatch) -> None:
    for value in ("", "not-a-number", "0", "-5"):
        monkeypatch.setenv("AI_BUILDER_TIMEOUT_SECONDS", value)
        adapter = BuilderSpaceAdapter()
        readiness = adapter.readiness()

        assert adapter.timeout_seconds == 30
        assert readiness["timeout_seconds"] == 30
        assert readiness["configured_timeout_env"] == value
        assert readiness["timeout_was_clamped"] is False


def test_timeout_env_above_max_is_clamped_and_reported(monkeypatch) -> None:
    monkeypatch.setenv("AI_BUILDER_TIMEOUT_SECONDS", "999999")

    adapter = BuilderSpaceAdapter()
    readiness = adapter.readiness()

    assert adapter.timeout_seconds == 120
    assert readiness["timeout_seconds"] == 120
    assert readiness["configured_timeout_env"] == "999999"
    assert readiness["default_timeout_seconds"] == 30
    assert readiness["max_timeout_seconds"] == 120
    assert readiness["timeout_was_clamped"] is True


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
