import json
from json import JSONDecodeError

import pytest

import app.providers.builderspace_adapter as builderspace_adapter_module
from app.providers.builderspace_adapter import BuilderSpaceAdapter, BuilderSpaceResponseError
from app.runtime.agent.manager_branch_contract import (
    B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
    B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
    B1_COMMON_FOOD_ITEM_CASE_FAMILY,
    B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
    B1_LISTED_INGREDIENT_CASE_FAMILY,
    ManagerPass1BranchContractError,
)
from app.schemas import ComponentEstimate


class _FakeResponse:
    def __init__(self, *, payload: object = None, text: str = "", status_code: int = 200, json_error: Exception | None = None) -> None:
        self._payload = payload
        self._json_error = json_error
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = builderspace_adapter_module.httpx.Request("POST", "https://example.test/backend/v1/chat/completions")
            response = builderspace_adapter_module.httpx.Response(self.status_code, request=request, text=self.text)
            raise builderspace_adapter_module.httpx.HTTPStatusError("fake http error", request=request, response=response)
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


class _RecordingAsyncClient:
    def __init__(self, *, responses: list[_FakeResponse], recorder: list[dict[str, object]], **_: object) -> None:
        self._responses = list(responses)
        self._recorder = recorder

    async def __aenter__(self) -> "_RecordingAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, *args: object, **kwargs: object) -> _FakeResponse:
        self._recorder.append(dict(kwargs))
        if not self._responses:
            raise AssertionError("No fake responses remaining.")
        return self._responses.pop(0)


class _RecordingAsyncClientWithFailures:
    def __init__(self, *, outcomes: list[object], recorder: list[dict[str, object]], **_: object) -> None:
        self._outcomes = list(outcomes)
        self._recorder = recorder

    async def __aenter__(self) -> "_RecordingAsyncClientWithFailures":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, *args: object, **kwargs: object) -> _FakeResponse:
        self._recorder.append(dict(kwargs))
        if not self._outcomes:
            raise AssertionError("No fake outcomes remaining.")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


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


def _http_error_response(status_code: int, payload: object) -> _FakeResponse:
    return _FakeResponse(payload=payload, text=json.dumps(payload), status_code=status_code)


class _JsonObjectOnlyBuilderSpaceAdapter(BuilderSpaceAdapter):
    def _response_format_request_for_stage(
        self,
        stage: str,
        constraints: dict[str, object] | None = None,
    ) -> tuple[dict[str, object], dict[str, object]]:
        return (
            {"type": "json_object"},
            {
                "structured_output_transport_attempted": False,
                "structured_output_transport_mode": "json_object",
                "structured_output_transport_accepted": False,
                "structured_output_transport_fallback": None,
                "fallback_reason": None,
                "structured_output_transport_constraint_snapshot": {
                    "phase_b1_manager_role": str((constraints or {}).get("phase_b1_manager_role") or ""),
                    "phase_b1_pass1_mode": str((constraints or {}).get("phase_b1_pass1_mode") or ""),
                    "phase_b1_case_family": str((constraints or {}).get("phase_b1_case_family") or ""),
                },
            },
        )


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
    payload = _json_envelope(
        "{\"manager_action\":\"final\",\"intent\":\"log_meal\",\"workflow_effect\":\"none\",\"target_attachment\":{},\"exactness\":\"unknown\",\"confidence\":\"unknown\",\"evidence_posture\":\"unknown\",\"repair_ack\":false}"
    )
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
    payload = _json_envelope(
        "```json\n{\"manager_action\":\"final\",\"intent\":\"log_meal\",\"workflow_effect\":\"none\",\"target_attachment\":{},\"exactness\":\"unknown\",\"confidence\":\"unknown\",\"evidence_posture\":\"unknown\",\"repair_ack\":false}\n```"
    )
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
    payload = _json_envelope(
        "Here is the result:\n{\"manager_action\":\"final\",\"intent\":\"log_meal\",\"workflow_effect\":\"none\",\"target_attachment\":{},\"exactness\":\"unknown\",\"confidence\":\"unknown\",\"evidence_posture\":\"unknown\",\"repair_ack\":false}\nThanks."
    )
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
async def test_complete_with_trace_long_synthesis_prose_plus_single_fenced_json_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _json_envelope(
        "Now I have comprehensive evidence. Let me synthesize the final answer.\n\n"
        "- item one\n"
        "- item two\n\n"
        "```json\n"
        "{\"manager_action\":\"final\",\"intent\":\"estimate_calories\",\"workflow_effect\":\"complete\","
        "\"target_attachment\":\"food_log\",\"exactness\":\"approximate\",\"confidence\":\"medium\","
        "\"evidence_posture\":\"packetized_generic_db\",\"repair_ack\":false,\"answer_contract\":{\"items\":[]}}\n"
        "```\n"
        "Finalized."
    )
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=json.dumps(payload)))

    parsed, trace = await adapter.complete_with_trace(
        system_prompt="Return JSON.",
        user_payload={"foo": "bar"},
        stage="intake_manager_round",
    )

    assert parsed["manager_action"] == "final"
    assert parsed["intent"] == "estimate_calories"
    assert trace["parse_contract_status"] == "fenced_json_recovered"
    assert trace["parse_recovery_used"] is True
    assert trace["parse_recovery_strategy"] == "fenced_json"
    assert trace["parse_recovery_ambiguous"] is False


@pytest.mark.asyncio
async def test_complete_with_trace_recovered_json_validation_failure_preserves_contract_attribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _json_envelope(
        "Now I have comprehensive evidence. Let me synthesize the final answer.\n\n"
        "```json\n"
        "{\"manager_action\":\"final\",\"intent\":\"estimate_calories\",\"workflow_effect\":\"complete\","
        "\"target_attachment\":\"food_log\",\"answer_contract\":{\"items\":[]}}\n"
        "```\n"
        "Finalized."
    )
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=json.dumps(payload)))

    with pytest.raises(BuilderSpaceResponseError) as exc_info:
        await adapter.complete_with_trace(
            system_prompt="Return JSON.",
            user_payload={"foo": "bar"},
            stage="intake_manager_round",
        )

    trace = exc_info.value.trace
    assert trace["failure_family"] == "manager_output_contract_violation"
    assert trace["failing_component"] == "builderspace_runtime_contract.validate_manager_payload"
    assert trace["parse_contract_status"] == "fenced_json_recovered"
    assert trace["parse_recovery_used"] is True
    assert trace["parse_recovery_strategy"] == "fenced_json"
    assert trace["parse_recovery_ambiguous"] is False
    assert trace["parsed_object"]["manager_action"] == "final"


@pytest.mark.asyncio
async def test_complete_with_trace_open_fenced_json_marker_plus_single_object_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _json_envelope(
        "Now I have comprehensive evidence.\n\n"
        "```json\n"
        "{\"manager_action\":\"final\",\"intent\":\"estimate_calories\",\"workflow_effect\":\"complete\","
        "\"target_attachment\":\"food_log\",\"exactness\":\"approximate\",\"confidence\":\"medium\","
        "\"evidence_posture\":\"packetized_generic_db\",\"repair_ack\":false,\"answer_contract\":{\"items\":[]}}\n"
        "\nAdditional closing commentary is missing."
    )
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=payload, text=json.dumps(payload)))

    parsed, trace = await adapter.complete_with_trace(
        system_prompt="Return JSON.",
        user_payload={"foo": "bar"},
        stage="intake_manager_round",
    )

    assert parsed["manager_action"] == "final"
    assert trace["parse_contract_status"] == "open_fenced_json_recovered"
    assert trace["parse_recovery_used"] is True
    assert trace["parse_recovery_strategy"] == "open_fenced_json_marker"
    assert trace["parse_recovery_ambiguous"] is False


@pytest.mark.asyncio
async def test_complete_with_trace_multiple_fenced_json_blocks_is_ambiguous_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _json_envelope(
        "```json\n{\"manager_action\":\"final\",\"intent\":\"one\",\"workflow_effect\":\"complete\",\"target_attachment\":{},"
        "\"exactness\":\"unknown\",\"confidence\":\"unknown\",\"evidence_posture\":\"unknown\",\"repair_ack\":false}\n```\n"
        "```json\n{\"manager_action\":\"final\",\"intent\":\"two\",\"workflow_effect\":\"complete\",\"target_attachment\":{},"
        "\"exactness\":\"unknown\",\"confidence\":\"unknown\",\"evidence_posture\":\"unknown\",\"repair_ack\":false}\n```"
    )
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
    assert trace["parse_recovery_strategy"] == "fenced_json"


@pytest.mark.asyncio
async def test_complete_with_trace_parse_failure_preserves_incomplete_details(monkeypatch: pytest.MonkeyPatch) -> None:
    raw_payload = _json_envelope("Now I have comprehensive evidence but no JSON.")
    raw_payload["incomplete_details"] = {"reason": "max_output_tokens"}
    raw_payload["choices"][0]["finish_reason"] = "length"
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=raw_payload, text=json.dumps(raw_payload)))

    with pytest.raises(BuilderSpaceResponseError) as exc_info:
        await adapter.complete_with_trace(
            system_prompt="Return JSON.",
            user_payload={"foo": "bar"},
            stage="intake_manager_round",
        )

    trace = exc_info.value.trace
    assert trace["failure_family"] == "non_json_model_output"
    assert trace["incomplete_details"] == {"reason": "max_output_tokens"}
    assert trace["status"] == "ok"
    assert trace["finish_reason"] == "length"


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


def test_builderspace_response_format_uses_json_schema_for_b1_common_food_item(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))

    response_format, transport_meta = adapter._response_format_request_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
        },
    )

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["required"] == [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]
    assert transport_meta["structured_output_transport_attempted"] is True
    assert transport_meta["structured_output_transport_mode"] == "json_schema"
    assert transport_meta["structured_output_transport_constraint_snapshot"]["phase_b1_case_family"] == "common_food_item"


def test_builderspace_response_format_uses_json_schema_for_b1_common_commercial_drink(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))

    response_format, transport_meta = adapter._response_format_request_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
        },
    )

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["required"] == [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]
    assert transport_meta["structured_output_transport_attempted"] is True
    assert transport_meta["structured_output_transport_mode"] == "json_schema"
    assert transport_meta["structured_output_transport_constraint_snapshot"]["phase_b1_case_family"] == "common_commercial_drink"


def test_builderspace_response_schema_forced_composition_unknown_is_tool_call_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "forced_tool_request_smoke",
            "phase_b1_case_family": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
        },
    )

    assert schema is not None
    assert schema["properties"]["manager_action"]["enum"] == ["call_tools"]
    assert schema["properties"]["tool_calls"]["minItems"] == 1
    assert schema["properties"]["tool_calls"]["items"]["properties"]["name"]["enum"] == [
        "lookup_generic_food",
        "retrieve_web_food_evidence",
        "load_taiwan_food_semantics_skill",
    ]
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]


def test_builderspace_response_format_uses_json_schema_for_b1_pass2_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))

    response_format, transport_meta = adapter._response_format_request_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "forced_tool_request_smoke",
            "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
        },
    )

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["required"] == [
        "manager_action",
        "response_mode",
        "intent",
        "workflow_effect",
        "target_attachment",
        "exactness",
        "confidence",
        "evidence_posture",
        "repair_ack",
        "operations",
        "answer_contract",
    ]
    assert transport_meta["structured_output_transport_attempted"] is True
    assert transport_meta["structured_output_transport_mode"] == "json_schema"
    assert transport_meta["structured_output_transport_constraint_snapshot"]["phase_b1_manager_role"] == "pass_2_synthesis"


def test_builderspace_decision_transport_request_for_b1_common_commercial_meal(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))

    transport_request, transport_meta = adapter._decision_transport_request_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        },
    )

    assert transport_request is not None
    assert transport_request["mode"] == "tool_call_decision_transport"
    assert transport_request["tool_choice"]["type"] == "function"
    assert transport_request["tool_choice"]["function"]["name"] == "manager_call_tools_decision"
    assert transport_request["tools"][0]["type"] == "function"
    assert transport_request["tools"][0]["function"]["name"] == "manager_call_tools_decision"
    schema = transport_request["tools"][0]["function"]["parameters"]
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]
    assert schema["properties"]["manager_action"]["enum"] == ["call_tools"]
    assert transport_meta["decision_transport_attempted"] is True
    assert transport_meta["decision_transport_mode"] == "tool_call_decision_transport"
    assert transport_meta["decision_transport_constraint_snapshot"]["phase_b1_case_family"] == "common_commercial_meal"


def test_builderspace_decision_transport_request_honors_b1_profile_transport_mode_for_pass1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))

    transport_request, transport_meta = adapter._decision_transport_request_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "forced_tool_request_smoke",
            "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            "phase_b1_provider_profile_id": "builderspace-grok-4-fast-b1-pass1-tool-choice",
            "phase_b1_provider_profile_transport_mode": "tool_call_decision_transport",
        },
    )

    assert transport_request is not None
    assert transport_request["mode"] == "tool_call_decision_transport"
    assert transport_request["tool_choice"]["function"]["name"] == "manager_call_tools_decision"
    assert transport_meta["decision_transport_attempted"] is True
    assert transport_meta["decision_transport_mode"] == "tool_call_decision_transport"
    assert transport_meta["decision_transport_constraint_snapshot"]["phase_b1_provider_profile_id"] == (
        "builderspace-grok-4-fast-b1-pass1-tool-choice"
    )
    assert transport_meta["decision_transport_constraint_snapshot"]["phase_b1_provider_profile_transport_mode"] == (
        "tool_call_decision_transport"
    )


def test_builderspace_decision_transport_profile_mode_does_not_apply_to_pass2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))

    transport_request, transport_meta = adapter._decision_transport_request_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "forced_tool_request_smoke",
            "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            "phase_b1_provider_profile_id": "builderspace-grok-4-fast-b1-pass1-tool-choice",
            "phase_b1_provider_profile_transport_mode": "tool_call_decision_transport",
        },
    )

    assert transport_request is None
    assert transport_meta["decision_transport_attempted"] is False


@pytest.mark.asyncio
async def test_complete_with_trace_falls_back_from_json_schema_to_json_object_for_b1_common_food_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posted_payloads: list[dict[str, object]] = []
    first = _http_error_response(
        400,
        {"error": {"message": "unsupported response_format json_schema"}},
    )
    second = _FakeResponse(
        payload=_json_envelope(
            "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"茶葉蛋\"}}]}"
        ),
        text="ok",
    )
    monkeypatch.setenv("AI_BUILDER_TOKEN", "test-token")
    monkeypatch.setenv("AI_BUILDER_BASE_URL", "https://example.test/backend/v1")
    monkeypatch.setattr(
        builderspace_adapter_module.httpx,
        "AsyncClient",
        lambda **kwargs: _RecordingAsyncClient(responses=[first, second], recorder=posted_payloads, **kwargs),
    )
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    parsed, trace = await adapter.complete_with_trace(
        system_prompt="Return JSON.",
        user_payload={
            "constraints": {
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            }
        },
        stage="intake_manager_round",
    )

    assert parsed["manager_action"] == "call_tools"
    assert posted_payloads[0]["json"]["response_format"]["type"] == "json_schema"
    assert posted_payloads[1]["json"]["response_format"]["type"] == "json_object"
    assert trace["structured_output_transport_attempted"] is True
    assert trace["structured_output_transport_mode"] == "json_schema"
    assert trace["structured_output_transport_accepted"] is False
    assert trace["structured_output_transport_fallback"] == "json_object"
    assert trace["fallback_reason"] == "provider_rejected_response_format"
    assert trace["structured_output_transport_constraint_snapshot"]["phase_b1_case_family"] == "common_food_item"


@pytest.mark.asyncio
async def test_complete_with_trace_uses_adapter_transport_override(monkeypatch: pytest.MonkeyPatch) -> None:
    posted_payloads: list[dict[str, object]] = []
    response = _FakeResponse(
        payload=_json_envelope(
            "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"tea egg\"}}]}"
        ),
        text="ok",
    )
    monkeypatch.setenv("AI_BUILDER_TOKEN", "test-token")
    monkeypatch.setenv("AI_BUILDER_BASE_URL", "https://example.test/backend/v1")
    monkeypatch.setattr(
        builderspace_adapter_module.httpx,
        "AsyncClient",
        lambda **kwargs: _RecordingAsyncClient(responses=[response], recorder=posted_payloads, **kwargs),
    )
    adapter = _JsonObjectOnlyBuilderSpaceAdapter(manager_model_override="deepseek")

    _, trace = await adapter.complete_with_trace(
        system_prompt="Return JSON.",
        user_payload={
            "constraints": {
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "forced_tool_request_smoke",
                "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            }
        },
        stage="intake_manager_round",
    )

    assert posted_payloads[0]["json"]["response_format"]["type"] == "json_object"
    assert trace["structured_output_transport_mode"] == "json_object"


@pytest.mark.asyncio
async def test_complete_with_trace_preserves_json_schema_http_error_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posted_payloads: list[dict[str, object]] = []
    response = _http_error_response(
        400,
        {
            "error": {
                "message": "provider rejected structured contract: nested enum not accepted",
            }
        },
    )
    monkeypatch.setenv("AI_BUILDER_TOKEN", "test-token")
    monkeypatch.setenv("AI_BUILDER_BASE_URL", "https://example.test/backend/v1")
    monkeypatch.setattr(
        builderspace_adapter_module.httpx,
        "AsyncClient",
        lambda **kwargs: _RecordingAsyncClient(responses=[response], recorder=posted_payloads, **kwargs),
    )
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    with pytest.raises(BuilderSpaceResponseError) as exc_info:
        await adapter.complete_with_trace(
            system_prompt="Return JSON.",
            user_payload={
                "constraints": {
                    "phase_b1_manager_role": "pass_1_tool_request",
                    "phase_b1_pass1_mode": "forced_tool_request_smoke",
                    "phase_b1_case_family": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
                }
            },
            stage="intake_manager_round",
        )

    trace = exc_info.value.trace
    assert posted_payloads[0]["json"]["response_format"]["type"] == "json_schema"
    assert trace["response_status"] == 400
    assert trace["failure_family"] == "schema_transport_rejected"
    assert trace["request_failure_family"] == "schema_transport_rejected"
    assert trace["structured_output_transport_attempted"] is True
    assert trace["structured_output_transport_mode"] == "json_schema"
    assert trace["effective_response_format_type"] == "json_schema"
    assert "nested enum not accepted" in trace["raw_response_excerpt"]
    assert "nested enum not accepted" in trace["transport_attempts"][0]["response_body_excerpt"]


@pytest.mark.asyncio
async def test_complete_with_trace_b1_common_commercial_meal_tool_call_transport_contract_breach(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posted_payloads: list[dict[str, object]] = []
    response = _FakeResponse(
        payload=_json_envelope(
            "I have gathered evidence and would like to explain it before deciding."
        ),
        text="ok",
    )
    monkeypatch.setenv("AI_BUILDER_TOKEN", "test-token")
    monkeypatch.setenv("AI_BUILDER_BASE_URL", "https://example.test/backend/v1")
    monkeypatch.setattr(
        builderspace_adapter_module.httpx,
        "AsyncClient",
        lambda **kwargs: _RecordingAsyncClient(responses=[response], recorder=posted_payloads, **kwargs),
    )
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    with pytest.raises(BuilderSpaceResponseError) as exc_info:
        await adapter.complete_with_trace(
            system_prompt="Return JSON.",
            user_payload={
                "constraints": {
                    "phase_b1_manager_role": "pass_1_tool_request",
                    "phase_b1_pass1_mode": "natural_tool_selection_probe",
                    "phase_b1_case_family": B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
                }
            },
            stage="intake_manager_round",
        )

    trace = exc_info.value.trace
    assert posted_payloads[0]["json"]["tool_choice"]["function"]["name"] == "manager_call_tools_decision"
    assert "tools" in posted_payloads[0]["json"]
    assert "response_format" not in posted_payloads[0]["json"]
    assert trace["decision_transport_attempted"] is True
    assert trace["decision_transport_mode"] == "tool_call_decision_transport"
    assert trace["decision_transport_accepted"] is True
    assert trace["decision_transport_contract_breach"] is True
    assert trace["decision_transport_fallback"] is None
    assert trace["decision_transport_fallback_reason"] is None
    assert trace["failure_family"] == "tool_call_transport_contract_breach"
    assert trace["failing_component"] == "builderspace_adapter.extract_tool_call_decision"


@pytest.mark.asyncio
async def test_complete_with_trace_retries_connect_error_and_preserves_attempt_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posted_payloads: list[dict[str, object]] = []
    request = builderspace_adapter_module.httpx.Request("POST", "https://example.test/backend/v1/chat/completions")
    connect_error = builderspace_adapter_module.httpx.ConnectError("All connection attempts failed", request=request)
    response = _FakeResponse(
        payload=_json_envelope(
            "{\"manager_action\":\"final\",\"intent\":\"log_meal\",\"workflow_effect\":\"none\",\"target_attachment\":{},\"exactness\":\"unknown\",\"confidence\":\"unknown\",\"evidence_posture\":\"unknown\",\"repair_ack\":false}"
        ),
        text="ok",
    )
    monkeypatch.setenv("AI_BUILDER_TOKEN", "test-token")
    monkeypatch.setenv("AI_BUILDER_BASE_URL", "https://example.test/backend/v1")
    monkeypatch.setenv("AI_BUILDER_TRANSPORT_RETRY_COUNT", "1")
    monkeypatch.setattr(
        builderspace_adapter_module.httpx,
        "AsyncClient",
        lambda **kwargs: _RecordingAsyncClientWithFailures(
            outcomes=[connect_error, response],
            recorder=posted_payloads,
            **kwargs,
        ),
    )
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    parsed, trace = await adapter.complete_with_trace(
        system_prompt="Return JSON.",
        user_payload={"foo": "bar"},
        stage="intake_manager_round",
    )

    assert parsed["manager_action"] == "final"
    assert len(posted_payloads) == 2
    assert trace["transport_attempts"][0]["error_type"] == "ConnectError"
    assert trace["transport_attempts"][0]["status"] == "error"
    assert trace["transport_attempts"][1]["status"] == "success"


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


def test_response_schema_narrows_for_b1_listed_ingredient_tool_call_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
        },
    )

    assert schema is not None
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]
    assert schema["properties"]["manager_action"]["enum"] == ["call_tools"]


def test_validate_manager_payload_accepts_b1_listed_ingredient_tool_call_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "call_tools",
            "interaction_family": "food_logging",
            "response_mode": "intake_result",
            "operations": [],
            "answer_contract": {},
            "tool_calls": [
                {"name": "lookup_generic_food", "arguments": {"food_name": "豆干"}},
                {"name": "lookup_generic_food", "arguments": {"food_name": "海帶"}},
            ],
        },
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
        },
    )


def test_validate_manager_payload_rejects_b1_listed_ingredient_final_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))

    with pytest.raises(ManagerPass1BranchContractError, match="tool-call branch"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "final",
                "interaction_family": "food_logging",
                "response_mode": "clarification",
                "final_action": "request_clarification",
                "operations": [],
                "answer_contract": {},
                "tool_calls": [],
            },
            constraints={
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
            },
        )


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
    assert "interaction_family" in schema["properties"]
    assert "response_mode" in schema["properties"]
    assert "target_attachment" in schema["properties"]
    assert "exactness" in schema["properties"]
    assert "confidence" in schema["properties"]
    assert "evidence_posture" in schema["properties"]
    assert "repair_ack" in schema["properties"]
    assert "operations" in schema["properties"]
    assert "thoughts" not in schema["properties"]


def test_manager_stages_use_manager_model_and_schema() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    assert adapter._model_for_stage("intake_manager_round") == "deepseek"
    assert adapter._response_schema_for_stage("intake_manager_round") is not None


def test_builderspace_schema_narrows_for_b1_clarification_branch() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
        },
    )

    assert schema is not None
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "final_action",
        "operations",
        "answer_contract",
    ]
    assert schema["properties"]["manager_action"]["enum"] == ["final"]
    assert schema["properties"]["response_mode"]["enum"] == ["clarification"]
    assert schema["properties"]["final_action"]["enum"] == ["request_clarification"]


def test_builderspace_schema_narrows_for_b1_clarification_pass2_branch() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
        },
    )

    assert schema is not None
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "intent",
        "workflow_effect",
        "target_attachment",
        "final_action",
        "exactness",
        "confidence",
        "evidence_posture",
        "repair_ack",
        "operations",
        "answer_contract",
    ]
    assert schema["properties"]["response_mode"]["enum"] == ["clarification"]
    assert schema["properties"]["final_action"]["enum"] == ["request_clarification"]
    assert schema["properties"]["workflow_effect"]["enum"] == ["pause_for_clarification", "none"]
    assert schema["properties"]["uncertainty_posture"]["enum"] == ["composition_unknown_basket", "none"]


def test_builderspace_validate_manager_payload_rejects_b1_mixed_branch_contract() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    with pytest.raises(ManagerPass1BranchContractError, match="conflicting fields"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "call_tools",
                "interaction_family": "food_logging",
                "response_mode": "intake_result",
                "final_action": "request_clarification",
                "operations": [],
                "answer_contract": {},
                "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": "滷味"}}],
            },
            constraints={
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
            },
        )


def test_builderspace_response_schema_narrows_for_b1_listed_ingredient_pass2_branch() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
        },
    )

    assert schema is not None
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "intent",
        "workflow_effect",
        "target_attachment",
        "exactness",
        "confidence",
        "evidence_posture",
        "repair_ack",
        "item_results",
        "operations",
        "answer_contract",
    ]
    assert schema["properties"]["manager_action"]["enum"] == ["final"]
    assert "tool_calls" not in schema["properties"]
    assert schema["properties"]["item_results"]["type"] == "array"


def test_builderspace_validate_manager_payload_accepts_b1_listed_ingredient_pass2_branch() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "final",
            "interaction_family": "food_logging",
            "response_mode": "intake_result",
            "intent": "estimate_calories",
            "workflow_effect": "complete",
            "target_attachment": {"kind": "food_logging_estimate"},
            "exactness": "approximate",
            "confidence": "medium",
            "evidence_posture": "packetized_generic_db",
            "repair_ack": False,
            "item_results": [
                {
                    "food_name": "豆干",
                    "kcal_range": [70, 90],
                    "likely_kcal": 80,
                    "uncertainty": "medium",
                    "evidence_used": ["generic_food_db:豆干"],
                }
            ],
            "operations": [],
            "answer_contract": {},
        },
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
        },
    )


@pytest.mark.parametrize(
    ("case_family", "expected_required"),
    (
        (
            B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            [
                "manager_action",
                "response_mode",
                "intent",
                "workflow_effect",
                "target_attachment",
                "exactness",
                "confidence",
                "evidence_posture",
                "repair_ack",
                "operations",
                "answer_contract",
            ],
        ),
        (
            B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
            [
                "manager_action",
                "response_mode",
                "intent",
                "workflow_effect",
                "target_attachment",
                "exactness",
                "confidence",
                "evidence_posture",
                "repair_ack",
                "operations",
                "answer_contract",
            ],
        ),
        (
            B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
            [
                "manager_action",
                "response_mode",
                "intent",
                "workflow_effect",
                "target_attachment",
                "exactness",
                "confidence",
                "evidence_posture",
                "repair_ack",
                "item_results",
                "operations",
                "answer_contract",
            ],
        ),
    ),
)
def test_builderspace_response_schema_narrows_for_b1_generic_pass2_branch(
    case_family: str,
    expected_required: list[str],
) -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": case_family,
        },
    )

    assert schema is not None
    assert schema["required"] == expected_required
    assert schema["properties"]["manager_action"]["enum"] == ["final"]
    assert schema["properties"]["item_results"]["type"] == "array"
    assert schema["properties"]["evidence_used"]["type"] == "array"


def test_builderspace_validate_manager_payload_accepts_b1_generic_common_food_pass2_without_broad_wrapper_fields() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "final",
            "interaction_family": "food_logging",
            "response_mode": "intake_result",
            "intent": "log_food_item",
            "workflow_effect": "item_logged",
            "target_attachment": "茶葉蛋",
            "exactness": "approximate",
            "confidence": "medium",
            "evidence_posture": "packetized_generic_db",
            "repair_ack": False,
            "operations": [],
            "answer_contract": {
                "item_results": [
                    {
                        "item_name": "茶葉蛋",
                        "kcal_range": [70, 90],
                        "likely_kcal": 80,
                    }
                ]
            },
        },
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
        },
    )


def test_builderspace_validate_manager_payload_accepts_b1_generic_common_drink_pass2_with_top_level_item_results() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "final",
            "interaction_family": "nutrition_info_query",
            "response_mode": "info_answer",
            "intent": "query_food_calories",
            "workflow_effect": "complete",
            "target_attachment": "food_item",
            "exactness": "approximate",
            "confidence": "medium",
            "evidence_posture": "packetized_generic_db",
            "repair_ack": False,
            "item_results": [
                {
                    "food_name": "珍珠奶茶",
                    "kcal_range": [350, 450],
                    "likely_kcal": 400,
                    "uncertainty": "medium",
                    "evidence_used": ["generic_food_db:珍珠奶茶"],
                }
            ],
            "evidence_used": ["generic_food_db:珍珠奶茶"],
            "operations": [],
            "answer_contract": {},
        },
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
        },
    )


def test_builderspace_validate_manager_payload_accepts_b1_common_commercial_meal_pass2_with_top_level_item_results() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "final",
            "interaction_family": "food_logging",
            "response_mode": "intake_result",
            "intent": "estimate_calories",
            "workflow_effect": "complete",
            "target_attachment": "generic_taiwanese_bento",
            "exactness": "approximate",
            "confidence": "medium",
            "evidence_posture": "packetized_generic_db",
            "repair_ack": False,
            "item_results": [
                {
                    "food_name": "taiwanese_bento",
                    "kcal_range": [550, 960],
                    "likely_kcal": 750,
                    "uncertainty": "medium",
                    "evidence_used": ["generic_food_db:taiwanese_bento"],
                }
            ],
            "evidence_used": ["generic_food_db:taiwanese_bento"],
            "operations": [],
            "answer_contract": {},
        },
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        },
    )


def test_builderspace_validate_manager_payload_rejects_b1_common_commercial_meal_pass2_bridge_only_item_results() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    with pytest.raises(RuntimeError, match="item_results"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "final",
                "interaction_family": "food_logging",
                "response_mode": "intake_result",
                "intent": "estimate_calories",
                "workflow_effect": "complete",
                "target_attachment": "generic_taiwanese_bento",
                "exactness": "approximate",
                "confidence": "medium",
                "evidence_posture": "packetized_generic_db",
                "repair_ack": False,
                "answer_contract": {
                    "item_results": [
                        {
                            "item_name": "taiwanese_bento",
                            "item_quantity": 1,
                            "item_unit": "serving",
                        }
                    ],
                    "kcal_range": [550, 960],
                    "likely_kcal": 750,
                    "uncertainty": "medium",
                    "evidence_used": ["generic_food_db:taiwanese_bento"],
                },
                "operations": [],
            },
            constraints={
                "phase_b1_manager_role": "pass_2_synthesis",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
            },
        )


def test_builderspace_validate_manager_payload_rejects_pass1_item_results_even_for_listed_ingredient_case() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    with pytest.raises(RuntimeError, match="unknown fields"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "call_tools",
                "interaction_family": "food_logging",
                "response_mode": "intake_result",
                "operations": [],
                "answer_contract": {},
                "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": "豆干"}}],
                "item_results": [],
            },
            constraints={
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
            },
        )


@pytest.mark.parametrize(
    "case_family",
    (
        B1_COMMON_FOOD_ITEM_CASE_FAMILY,
        B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
        B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
    ),
)
def test_builderspace_response_schema_narrows_for_b1_generic_pass1_tool_call_branch(case_family: str) -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": case_family,
        },
    )

    assert schema is not None
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]
    assert schema["properties"]["manager_action"]["enum"] == ["call_tools"]


@pytest.mark.parametrize(
    ("case_family", "food_name"),
    (
        (B1_COMMON_FOOD_ITEM_CASE_FAMILY, "茶葉蛋"),
        (B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY, "珍珠奶茶"),
        (B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY, "便當"),
    ),
)
def test_builderspace_validate_manager_payload_accepts_b1_generic_pass1_tool_call_branch(
    case_family: str,
    food_name: str,
) -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "call_tools",
            "interaction_family": "food_logging",
            "response_mode": "intake_result",
            "operations": [],
            "answer_contract": {},
            "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": food_name}}],
        },
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": case_family,
        },
    )


def test_builderspace_validate_manager_payload_rejects_b1_generic_pass1_empty_tool_calls() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    with pytest.raises(ManagerPass1BranchContractError, match="tool-call branch"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "call_tools",
                "interaction_family": "food_logging",
                "response_mode": "intake_result",
                "operations": [],
                "answer_contract": {},
                "tool_calls": [],
            },
            constraints={
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            },
        )


def test_builderspace_validate_manager_payload_rejects_b1_generic_pass1_final_truth_fields() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")

    with pytest.raises(RuntimeError, match="unknown fields"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "call_tools",
                "interaction_family": "food_logging",
                "response_mode": "intake_result",
                "operations": [],
                "answer_contract": {},
                "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": "茶葉蛋"}}],
                "item_results": [],
            },
            constraints={
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            },
        )


def test_readiness_exposes_manager_model_stage_mapping() -> None:
    adapter = BuilderSpaceAdapter(manager_model_override="deepseek")
    readiness = adapter.readiness()

    assert readiness["manager_model"] == "deepseek"
    assert readiness["stage_models"]["intake_manager_round"] == "deepseek"
    assert set(readiness["stage_models"].keys()) == {
        "intake_manager_round",
    }
