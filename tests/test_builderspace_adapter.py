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


def _tool_call_envelope(*, tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(arguments),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "status": "ok",
        "usage": {"prompt_tokens": 10, "completion_tokens": 12},
    }


def _founder_live_constraints() -> dict[str, str]:
    return {
        "manager_contract_profile_id": "founder_live_contract",
        "manager_contract_provider_profile_id": "builderspace-grok-4-fast-founder-live-contract",
        "manager_contract_schema_name": "founder_live_manager_contract",
        "manager_contract_schema_version": "v1",
        "manager_contract_transport_policy": "synthetic_tool_transport",
    }


def _founder_live_commit_without_evidence_repair_constraints() -> dict[str, object]:
    return {
        **_founder_live_constraints(),
        "guard_feedback_repair_request": True,
        "guard_feedback_failure_family": "commit_without_evidence",
    }


def _founder_live_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "manager_action": "final",
        "intent": "log_meal",
        "intent_type": "log_meal",
        "tool_calls": [],
        "workflow_effect": "estimate_with_followup",
        "target_attachment": {"mode": "new_meal"},
        "final_action": "commit",
        "exactness": "estimated",
        "confidence": "medium",
        "evidence_posture": "bounded_estimate",
        "semantic_decision": {
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "target_attachment": {"mode": "new_meal"},
            "workflow_effect": "estimate_with_followup",
            "final_action_candidate": "logged_estimate",
            "estimation_posture": "estimable_with_optional_refinement",
            "followup_posture": "refinement_optional",
            "mutation_intent_candidate": "canonical_write",
            "uncertainty_posture": "bounded",
            "source": "live_manager_structured_output",
        },
        "answer_contract": {"reply_text": "Estimated and logged."},
    }
    payload.update(overrides)
    return payload


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


def test_founder_live_manager_contract_schema_uses_consumer_backed_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    constraints = {
        "manager_contract_profile_id": "founder_live_contract",
        "manager_contract_schema_name": "founder_live_manager_contract",
        "manager_contract_schema_version": "v1",
        "manager_contract_transport_policy": "synthetic_tool_transport",
    }

    schema = adapter._response_schema_for_stage("intake_manager_round", constraints=constraints)

    assert schema is not None
    assert schema["required"] == [
        "manager_action",
        "intent",
        "intent_type",
        "tool_calls",
        "workflow_effect",
        "target_attachment",
        "final_action",
        "exactness",
        "confidence",
        "evidence_posture",
        "semantic_decision",
        "answer_contract",
    ]
    assert "repair_ack" in schema["properties"]
    assert "repair_ack" not in schema["required"]
    assert schema["properties"]["intent_type"]["enum"] == [
        "complete_onboarding",
        "answer_remaining_budget",
        "onboarding_required",
        "manager_unavailable",
        "log_meal",
    ]
    assert schema["x-field-consumers"]["workflow_effect"] == "transition_guard_and_mutation_boundary"
    assert schema["x-field-consumers"]["answer_contract"] == "renderer_boundary"
    assert schema["x-field-consumers"]["tool_calls"] == "manager_loop_tool_router_when_calling_tools"
    assert schema["x-field-consumers"]["final_action"] == "final_mapping_and_renderer_boundary"


def test_founder_live_commit_without_evidence_repair_schema_requires_tool_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints=_founder_live_commit_without_evidence_repair_constraints(),
    )

    assert schema is not None
    assert schema["properties"]["manager_action"]["enum"] == ["call_tools"]
    assert "tool_calls" in schema["required"]
    assert "minItems" not in schema["properties"]["tool_calls"]
    assert schema["properties"]["tool_calls"]["items"]["properties"]["name"]["enum"] == [
        "resolve_correction_target",
        "estimate_nutrition",
        "compare_against_budget",
    ]
    assert schema["x-repair-contract"] == {
        "failure_family": "commit_without_evidence",
        "required_tool": "estimate_nutrition",
    }


def test_founder_live_manager_contract_payload_accepts_trace_repair_ack_outside_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    constraints = {
        "manager_contract_profile_id": "founder_live_contract",
        "manager_contract_schema_name": "founder_live_manager_contract",
        "manager_contract_schema_version": "v1",
        "manager_contract_transport_policy": "synthetic_tool_transport",
    }
    payload = {
        "manager_action": "final",
        "intent": "log_meal",
        "intent_type": "log_meal",
        "workflow_effect": "estimate_with_followup",
        "target_attachment": {"mode": "new_meal"},
        "tool_calls": [],
        "final_action": "commit",
        "exactness": "estimated",
        "confidence": "medium",
        "evidence_posture": "bounded_estimate",
        "semantic_decision": {
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "target_attachment": {"mode": "new_meal"},
            "workflow_effect": "estimate_with_followup",
            "final_action_candidate": "logged_estimate",
            "estimation_posture": "estimable_with_optional_refinement",
            "followup_posture": "refinement_optional",
            "mutation_intent_candidate": "canonical_write",
            "uncertainty_posture": "bounded",
            "source": "live_manager_structured_output",
        },
        "answer_contract": {"reply_text": "Estimated and logged."},
    }

    adapter._validate_manager_payload("intake_manager_round", payload, constraints=constraints)

    missing_semantic_decision = dict(payload)
    missing_semantic_decision.pop("semantic_decision")
    with pytest.raises(RuntimeError, match="semantic_decision"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            missing_semantic_decision,
            constraints=constraints,
        )

    unsupported_intent = dict(payload)
    unsupported_intent["intent_type"] = "user_initiated"
    with pytest.raises(RuntimeError, match="intent_type"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            unsupported_intent,
            constraints=constraints,
        )

    unsupported_final_action = dict(payload)
    unsupported_final_action["final_action"] = "begin_meal_logging"
    with pytest.raises(RuntimeError, match="final_action"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            unsupported_final_action,
            constraints=constraints,
        )

    contradictory_no_commit = dict(payload)
    contradictory_no_commit["final_action"] = "no_commit"
    with pytest.raises(RuntimeError, match="mutation intent"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            contradictory_no_commit,
            constraints=constraints,
        )

    mismatched_router_intent = dict(payload)
    mismatched_router_intent["intent_type"] = "complete_onboarding"
    mismatched_router_intent["semantic_decision"] = dict(payload["semantic_decision"])
    mismatched_router_intent["semantic_decision"]["current_turn_intent"] = "correct_meal"
    with pytest.raises(RuntimeError, match="intent_type mismatch"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            mismatched_router_intent,
            constraints=constraints,
        )

    missing_followup_question = dict(payload)
    missing_followup_question["semantic_decision"] = dict(payload["semantic_decision"])
    missing_followup_question["semantic_decision"]["followup_posture"] = "refinement_not_commit_gate"
    with pytest.raises(RuntimeError, match="followup question missing"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            missing_followup_question,
            constraints=constraints,
        )

    answer_contract_followup = dict(missing_followup_question)
    answer_contract_followup["answer_contract"] = {
        "reply_text": "Estimated and logged.",
        "followup_question": "What size and sugar level was it?",
    }
    adapter._validate_manager_payload(
        "intake_manager_round",
        answer_contract_followup,
        constraints=constraints,
    )

    answer_query_without_top_level_final_action = dict(payload)
    answer_query_without_top_level_final_action.pop("final_action", None)
    answer_query_without_top_level_final_action["workflow_effect"] = "answer_only"
    answer_query_without_top_level_final_action["semantic_decision"] = {
        **dict(payload["semantic_decision"]),
        "current_turn_intent": "answer_query",
        "workflow_effect": "answer_only",
        "final_action_candidate": "answer_only",
        "mutation_intent_candidate": "no_mutation",
        "followup_posture": "none",
    }
    with pytest.raises(RuntimeError, match="final_action"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            answer_query_without_top_level_final_action,
            constraints=constraints,
        )

    correction_as_new_commit = dict(payload)
    correction_as_new_commit["final_action"] = "commit"
    correction_as_new_commit["semantic_decision"] = {
        **dict(payload["semantic_decision"]),
        "current_turn_intent": "correct_meal",
        "workflow_effect": "canonical_write",
        "final_action_candidate": "commit",
        "mutation_intent_candidate": "canonical_write",
    }
    with pytest.raises(RuntimeError, match="correct_meal requires correction"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            correction_as_new_commit,
            constraints=constraints,
        )


def test_founder_live_commit_without_evidence_repair_payload_must_call_estimate_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    constraints = _founder_live_commit_without_evidence_repair_constraints()

    valid = _founder_live_payload(
        manager_action="call_tools",
        tool_calls=[{"name": "estimate_nutrition", "arguments": {}}],
    )
    adapter._validate_manager_payload("intake_manager_round", valid, constraints=constraints)

    final_payload = _founder_live_payload(
        manager_action="final",
        final_action="commit",
        tool_calls=[{"name": "estimate_nutrition", "arguments": {}}],
    )
    with pytest.raises(RuntimeError, match="manager_action"):
        adapter._validate_manager_payload("intake_manager_round", final_payload, constraints=constraints)

    missing_estimate = _founder_live_payload(
        manager_action="call_tools",
        tool_calls=[{"name": "compare_against_budget", "arguments": {}}],
    )
    with pytest.raises(RuntimeError, match="requires tool_calls to include 'estimate_nutrition'"):
        adapter._validate_manager_payload("intake_manager_round", missing_estimate, constraints=constraints)


def test_founder_live_initial_contract_rejects_final_commit_without_current_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    constraints = {
        **_founder_live_constraints(),
        "manager_contract_evidence_state": {
            "nutrition_evidence_present": False,
            "tool_result_names": [],
        },
    }

    final_without_evidence = _founder_live_payload(final_action="commit")

    with pytest.raises(RuntimeError, match="current-loop nutrition evidence"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            final_without_evidence,
            constraints=constraints,
        )

    call_tools_without_evidence = _founder_live_payload(
        manager_action="call_tools",
        tool_calls=[{"name": "estimate_nutrition", "arguments": {}}],
    )
    adapter._validate_manager_payload(
        "intake_manager_round",
        call_tools_without_evidence,
        constraints=constraints,
    )

    with_evidence_constraints = {
        **_founder_live_constraints(),
        "manager_contract_evidence_state": {
            "nutrition_evidence_present": True,
            "tool_result_names": ["estimate_nutrition"],
        },
    }
    adapter._validate_manager_payload(
        "intake_manager_round",
        final_without_evidence,
        constraints=with_evidence_constraints,
    )


def test_founder_live_contract_rejects_substitute_final_action_for_evidence_required_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    constraints = {
        **_founder_live_constraints(),
        "manager_contract_evidence_state": {
            "nutrition_evidence_present": False,
            "tool_result_names": [],
        },
    }

    substitute_followup = _founder_live_payload(
        final_action="ask_followup",
        workflow_effect="correction_applied",
        semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "correct_meal",
            "target_attachment": {"mode": "active_meal"},
            "workflow_effect": "correction_applied",
            "final_action_candidate": "correction_applied",
            "estimation_posture": "refinement_pending",
            "followup_posture": "refinement_not_commit_gate",
            "mutation_intent_candidate": "correction_write",
            "uncertainty_posture": "low",
            "source": "live_manager_structured_output",
        },
        answer_contract={"response_mode": "correction_update"},
    )

    with pytest.raises(RuntimeError, match="substituting another final_action"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            substitute_followup,
            constraints=constraints,
        )

    composition_unknown_followup = _founder_live_payload(
        final_action="ask_followup",
        workflow_effect="ask_followup",
        semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "target_attachment": {"mode": "none"},
            "workflow_effect": "ask_followup",
            "final_action_candidate": "ask_followup",
            "estimation_posture": "composition_unknown_basket",
            "followup_posture": "composition_clarification",
            "mutation_intent_candidate": "no_mutation",
            "uncertainty_posture": "composition_unknown",
            "source": "live_manager_structured_output",
        },
        answer_contract={
            "response_mode": "followup",
            "followup_question": "Which items or portions should I estimate?",
        },
    )
    adapter._validate_manager_payload(
        "intake_manager_round",
        composition_unknown_followup,
        constraints=constraints,
    )


def test_founder_live_contract_requires_tool_calls_for_call_tools_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    constraints = _founder_live_constraints()

    missing_tool_calls = _founder_live_payload(
        manager_action="call_tools",
        workflow_effect="pending_evidence",
        evidence_posture="evidence_pending",
        semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "target_attachment": {"mode": "new_meal"},
            "workflow_effect": "pending_evidence",
            "final_action_candidate": "commit",
            "estimation_posture": "pending_tool_call",
            "followup_posture": "none",
            "mutation_intent_candidate": "canonical_write",
            "uncertainty_posture": "bounded",
            "source": "live_manager_structured_output",
        },
    )
    with pytest.raises(RuntimeError, match="non-empty tool_calls"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            missing_tool_calls,
            constraints=constraints,
        )

    unsupported_tool = _founder_live_payload(
        manager_action="call_tools",
        workflow_effect="pending_evidence",
        evidence_posture="evidence_pending",
        tool_calls=[{"name": "web_search", "arguments": {}}],
        semantic_decision=missing_tool_calls["semantic_decision"],
    )
    with pytest.raises(RuntimeError, match="unsupported tool names"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            unsupported_tool,
            constraints=constraints,
        )

    valid_tool_call = _founder_live_payload(
        manager_action="call_tools",
        workflow_effect="pending_evidence",
        evidence_posture="evidence_pending",
        tool_calls=[{"name": "estimate_nutrition", "arguments": {}}],
        semantic_decision=missing_tool_calls["semantic_decision"],
    )
    adapter._validate_manager_payload(
        "intake_manager_round",
        valid_tool_call,
        constraints=constraints,
    )


def test_founder_live_schema_keeps_final_action_for_tool_candidates_and_validation_blocks_final_without_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    constraints_without_evidence = {
        **_founder_live_constraints(),
        "manager_contract_evidence_state": {
            "nutrition_evidence_present": False,
            "tool_result_names": [],
        },
    }
    schema_without_evidence = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints=constraints_without_evidence,
    )

    final_action_enum = schema_without_evidence["properties"]["final_action"]["enum"]
    assert "answer_only" in final_action_enum
    assert "ask_followup" in final_action_enum
    assert "commit" in final_action_enum
    assert "correction_applied" in final_action_enum
    assert "overshoot_note" in final_action_enum

    final_without_evidence = _founder_live_payload(final_action="commit")
    with pytest.raises(RuntimeError, match="current-loop nutrition evidence"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            final_without_evidence,
            constraints=constraints_without_evidence,
        )

    call_tools_without_evidence = _founder_live_payload(
        manager_action="call_tools",
        final_action="commit",
        workflow_effect="pending_evidence",
        evidence_posture="evidence_pending",
        tool_calls=[{"name": "estimate_nutrition", "arguments": {}}],
        semantic_decision={
            **dict(final_without_evidence["semantic_decision"]),
            "final_action_candidate": "commit",
            "estimation_posture": "pending_tool_call",
        },
    )
    adapter._validate_manager_payload(
        "intake_manager_round",
        call_tools_without_evidence,
        constraints=constraints_without_evidence,
    )

    constraints_with_evidence = {
        **_founder_live_constraints(),
        "manager_contract_evidence_state": {
            "nutrition_evidence_present": True,
            "tool_result_names": ["estimate_nutrition"],
        },
    }
    schema_with_evidence = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints=constraints_with_evidence,
    )

    final_action_enum = schema_with_evidence["properties"]["final_action"]["enum"]
    assert "commit" in final_action_enum
    assert "correction_applied" in final_action_enum
    assert schema_with_evidence["properties"]["tool_calls"]["items"]["properties"]["name"]["enum"] == [
        "resolve_correction_target",
        "estimate_nutrition",
        "compare_against_budget",
    ]


def test_founder_live_remove_item_can_finalize_with_target_evidence_without_nutrition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    constraints = {
        **_founder_live_constraints(),
        "manager_contract_evidence_state": {
            "nutrition_evidence_present": False,
            "target_evidence_present": True,
            "target_evidence_operation": "remove_item",
            "tool_result_names": ["resolve_correction_target"],
        },
    }
    target_attachment = {
        "mode": "target_committed_thread",
        "operation": "remove_item",
        "target_object_id": "meal-item-soup",
        "canonical_name": "soup",
    }
    remove_item_final = _founder_live_payload(
        final_action="correction_applied",
        workflow_effect="correction",
        target_attachment=target_attachment,
        evidence_posture="target_evidence_present",
        semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "correct_meal",
            "target_attachment": target_attachment,
            "workflow_effect": "correction",
            "operation": "remove_item",
            "final_action_candidate": "correction_applied",
            "estimation_posture": "target_resolved",
            "followup_posture": "none",
            "mutation_intent_candidate": "correction_write",
            "uncertainty_posture": "low",
            "source": "live_manager_structured_output",
        },
        answer_contract={"response_mode": "correction_update"},
    )

    adapter._validate_manager_payload(
        "intake_manager_round",
        remove_item_final,
        constraints=constraints,
    )


def test_founder_live_remove_item_schema_keeps_correction_action_with_target_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    constraints = {
        **_founder_live_constraints(),
        "manager_contract_evidence_state": {
            "nutrition_evidence_present": False,
            "target_evidence_present": True,
            "target_evidence_operation": "remove_item",
            "tool_result_names": ["resolve_correction_target"],
        },
    }

    schema = adapter._response_schema_for_stage("intake_manager_round", constraints=constraints)

    final_action_enum = schema["properties"]["final_action"]["enum"]
    assert "correction_applied" in final_action_enum
    assert "commit" in final_action_enum

    final_commit_without_evidence = _founder_live_payload(final_action="commit")
    with pytest.raises(RuntimeError, match="current-loop nutrition evidence"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            final_commit_without_evidence,
            constraints=constraints,
        )
    assert "overshoot_note" in final_action_enum


def test_founder_live_contract_does_not_count_failed_tool_result_as_evidence() -> None:
    from app.runtime.agent.founder_live_manager_contract import founder_live_manager_contract_constraints

    constraints = founder_live_manager_contract_constraints(
        "builderspace-grok-4-fast-founder-live-contract",
        tool_results=[
            {
                "tool_name": "estimate_nutrition",
                "evidence": {"nutrition_payload": None},
                "failure_family": "composition_unknown_estimate_blocked",
            }
        ],
    )

    assert constraints["manager_contract_evidence_state"] == {
        "tool_result_names": ["estimate_nutrition"],
        "nutrition_evidence_present": False,
        "target_evidence_present": False,
        "target_evidence_source": None,
    }


def test_founder_live_contract_blocks_composition_unknown_estimate_tool_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    payload = _founder_live_payload(
        manager_action="call_tools",
        workflow_effect="ask_followup",
        tool_calls=[{"name": "estimate_nutrition", "arguments": {}}],
        semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "target_attachment": {"mode": "none"},
            "workflow_effect": "ask_followup",
            "final_action_candidate": "ask_followup",
            "estimation_posture": "composition_unknown_basket",
            "followup_posture": "composition_clarification",
            "mutation_intent_candidate": "no_mutation",
            "uncertainty_posture": "composition_unknown",
            "source": "live_manager_structured_output",
        },
        answer_contract={"response_mode": "followup"},
    )

    with pytest.raises(RuntimeError, match="composition-unknown.*must not call estimate_nutrition"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            payload,
            constraints=_founder_live_constraints(),
        )


def test_founder_live_contract_requires_concrete_ask_followup_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    missing_final_action = _founder_live_payload(
        manager_action="final",
        workflow_effect="ask_followup",
        evidence_posture="evidence_missing",
        semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "target_attachment": {"mode": "draft_thread"},
            "workflow_effect": "ask_followup",
            "final_action_candidate": "ask_followup",
            "estimation_posture": "composition_unknown_basket",
            "followup_posture": "composition_clarification",
            "mutation_intent_candidate": "no_mutation",
            "uncertainty_posture": "composition_unknown",
            "source": "live_manager_structured_output",
        },
        answer_contract={"reply_text": "Please list the items."},
    )
    missing_final_action.pop("final_action", None)

    with pytest.raises(RuntimeError, match="final_action"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            missing_final_action,
            constraints=_founder_live_constraints(),
        )

    missing_question = _founder_live_payload(
        manager_action="final",
        final_action="ask_followup",
        workflow_effect="ask_followup",
        evidence_posture="evidence_missing",
        semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "target_attachment": {"mode": "draft_thread"},
            "workflow_effect": "ask_followup",
            "final_action_candidate": "ask_followup",
            "estimation_posture": "composition_unknown_basket",
            "followup_posture": "composition_clarification",
            "mutation_intent_candidate": "no_mutation",
            "uncertainty_posture": "composition_unknown",
            "source": "live_manager_structured_output",
        },
        answer_contract={"reply_text": "Please list the items."},
    )

    with pytest.raises(RuntimeError, match="ask_followup requires a concrete followup_question"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            missing_question,
            constraints=_founder_live_constraints(),
        )

    valid = dict(missing_question)
    valid["answer_contract"] = {
        "reply_text": "Please list the items.",
        "followup_question": "Which items or portions should I estimate?",
    }
    adapter._validate_manager_payload(
        "intake_manager_round",
        valid,
        constraints=_founder_live_constraints(),
    )


def test_founder_live_contract_policy_names_existing_query_only_and_followup_invariants() -> None:
    from app.runtime.agent.founder_live_manager_contract import (
        FOUNDER_LIVE_MANAGER_CONTRACT_EXAMPLES,
        FOUNDER_LIVE_MANAGER_CONTRACT_POLICY,
        founder_live_manager_tool_description,
    )

    policy = FOUNDER_LIVE_MANAGER_CONTRACT_POLICY

    assert policy["query_only_rule"]["semantic_intent"] == "answer_query"
    assert policy["query_only_rule"]["final_action"] == "answer_only"
    assert policy["query_only_rule"]["mutation_intent_candidate"] == "no_mutation"
    assert policy["correction_rule"]["final_action"] == "correction_applied"
    assert policy["composition_unknown_rule"]["mutation_intent_candidate"] == "no_mutation"
    assert policy["composition_unknown_rule"]["estimate_tool_allowed"] is False
    assert policy["composition_unknown_rule"]["required_manager_action"] == "final"
    assert policy["composition_unknown_rule"]["forbidden_tool"] == "estimate_nutrition"
    assert policy["listed_basket_followup_rule"]["semantic_intent"] == "log_meal"
    assert policy["listed_basket_followup_rule"]["required_tool_when_evidence_missing"] == "estimate_nutrition"
    assert policy["listed_basket_followup_rule"]["forbidden_substitute_final_actions"] == [
        "ask_followup",
        "no_commit",
        "answer_only",
    ]
    assert policy["followup_question_rule"]["fallback_postures_when_no_question"] == [
        "none",
        "refinement_optional",
        "closed",
    ]
    assert "precision_refinement" not in policy["followup_question_required_postures"]
    assert "refinement_not_commit_gate" in policy["followup_question_required_postures"]
    description = founder_live_manager_tool_description()
    assert "query-only" in description
    assert "answer_only" in description
    assert "correct_meal" in description
    assert "self-selected basket" in description
    assert "return final ask_followup directly" in description
    assert "manager_action call_tools is invalid for composition-unknown baskets" in description
    assert "do not call estimate_nutrition for composition-unknown baskets" in description
    assert "tool_calls=[] for composition-unknown ask_followup" in description
    assert "listed-item follow-up" in description
    assert "do not repeat the same composition clarification" in description
    assert "evidence_posture to requires_tool" in description
    assert "invalid evidence-required candidate pattern" in description
    assert "If you do not have a concrete follow-up question" in description
    assert "case_id" not in description
    assert FOUNDER_LIVE_MANAGER_CONTRACT_EXAMPLES[0]["invalid"]["manager_action"] == "final"
    assert FOUNDER_LIVE_MANAGER_CONTRACT_EXAMPLES[0]["valid"]["manager_action"] == "call_tools"
    composition_unknown = next(
        item for item in FOUNDER_LIVE_MANAGER_CONTRACT_EXAMPLES if item["name"] == "composition_unknown_exception"
    )
    assert composition_unknown["invalid"]["manager_action"] == "call_tools"
    assert composition_unknown["invalid"]["tool_calls"] == [{"name": "estimate_nutrition"}]
    assert "case_id" not in str(FOUNDER_LIVE_MANAGER_CONTRACT_EXAMPLES)


def test_founder_live_schema_guidance_names_composition_unknown_call_tools_as_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    schema = adapter._response_schema_for_stage("intake_manager_round", constraints=_founder_live_constraints())

    manager_action_description = schema["properties"]["manager_action"]["description"]
    tool_calls_description = schema["properties"]["tool_calls"]["description"]
    estimation_posture_description = schema["properties"]["semantic_decision"]["properties"]["estimation_posture"][
        "description"
    ]

    assert "manager_action=call_tools is invalid for composition-unknown" in manager_action_description
    assert "composition_unknown_basket is not pending_tool_call" in estimation_posture_description
    assert "Do not include estimate_nutrition for composition-unknown" in tool_calls_description


def test_founder_live_schema_constrains_call_tools_away_from_response_only_final_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    schema = adapter._response_schema_for_stage("intake_manager_round", constraints=_founder_live_constraints())

    assert schema["allOf"]
    call_tools_rule = next(
        item
        for item in schema["allOf"]
        if item["if"]["properties"]["manager_action"]["const"] == "call_tools"
    )
    assert call_tools_rule["then"]["properties"]["final_action"]["enum"] == [
        "commit",
        "correction_applied",
        "overshoot_note",
    ]
    assert call_tools_rule["then"]["properties"]["tool_calls"]["minItems"] == 1


def test_founder_live_contract_rejects_call_tools_with_response_only_final_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    payload = _founder_live_payload(
        manager_action="call_tools",
        final_action="ask_followup",
        workflow_effect="ask_followup",
        evidence_posture="composition_unknown",
        tool_calls=[{"name": "estimate_nutrition", "arguments": {}}],
        semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "target_attachment": {},
            "workflow_effect": "ask_followup",
            "final_action_candidate": "ask_followup",
            "estimation_posture": "composition_unknown_basket",
            "followup_posture": "refinement_not_commit_gate",
            "mutation_intent_candidate": "no_mutation",
            "uncertainty_posture": "high",
            "source": "live_manager_structured_output",
        },
        answer_contract={"followup_question": "Which items and portions should I estimate?"},
    )

    with pytest.raises(RuntimeError, match="call_tools cannot use response-only final_action"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            payload,
            constraints=_founder_live_constraints(),
        )


def test_founder_live_shared_contract_examples_are_provider_and_case_agnostic() -> None:
    from app.runtime.agent.founder_live_manager_contract import (
        FOUNDER_LIVE_MANAGER_CONTRACT_EXAMPLES,
        FOUNDER_LIVE_MANAGER_CONTRACT_POLICY_SUMMARY,
    )

    contract_text = json.dumps(
        {
            "summary": FOUNDER_LIVE_MANAGER_CONTRACT_POLICY_SUMMARY,
            "examples": FOUNDER_LIVE_MANAGER_CONTRACT_EXAMPLES,
        },
        ensure_ascii=False,
    ).lower()

    forbidden_markers = [
        "grok",
        "deepseek",
        "builderspace",
        "kimi",
        "minimax",
        "gemini",
        "gpt",
        "case_id",
        "b2-",
        "pearl",
        "milk tea",
        "tea egg",
        "luwei",
        "bento",
        "滷味",
        "珍奶",
        "茶葉蛋",
        "便當",
    ]
    for marker in forbidden_markers:
        assert marker not in contract_text


def test_founder_live_manager_contract_uses_synthetic_tool_transport_with_schema_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _configure_adapter(monkeypatch, _FakeResponse(payload=_json_envelope("{}"), text="{}"))
    constraints = {
        "manager_contract_profile_id": "founder_live_contract",
        "manager_contract_schema_name": "founder_live_manager_contract",
        "manager_contract_schema_version": "v1",
        "manager_contract_transport_policy": "synthetic_tool_transport",
    }

    transport_request, transport_meta = adapter._decision_transport_request_for_stage(
        "intake_manager_round",
        constraints=constraints,
    )
    response_format, response_meta = adapter._response_format_request_for_stage(
        "intake_manager_round",
        constraints=constraints,
    )

    assert transport_request is not None
    assert transport_request["mode"] == "synthetic_tool_transport"
    assert transport_request["tool_name"] == "manager_structured_decision"
    assert transport_request["tool_choice"]["function"]["name"] == "manager_structured_decision"
    assert transport_request["tools"][0]["function"]["strict"] is True
    assert "correct_meal -> log_meal" in transport_request["tools"][0]["function"]["description"]
    assert "estimate_nutrition" in transport_request["tools"][0]["function"]["description"]
    assert transport_request["tools"][0]["function"]["parameters"]["required"] == [
        "manager_action",
        "intent",
        "intent_type",
        "tool_calls",
        "workflow_effect",
        "target_attachment",
        "final_action",
        "exactness",
        "confidence",
        "evidence_posture",
        "semantic_decision",
        "answer_contract",
    ]
    assert transport_meta["decision_transport_mode"] == "synthetic_tool_transport"
    assert transport_meta["schema_name"] == "founder_live_manager_contract"
    assert transport_meta["schema_version"] == "v1"
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "founder_live_manager_contract"
    assert response_meta["schema_version"] == "v1"

    semantic_schema = transport_request["tools"][0]["function"]["parameters"]["properties"]["semantic_decision"]
    semantic_properties = semantic_schema["properties"]
    assert "not a final ask_followup" in semantic_properties["final_action_candidate"]["description"]
    assert "pending_tool_call or tool_pending" in semantic_properties["estimation_posture"]["description"]
    assert "concrete user-facing followup_question" in semantic_properties["followup_posture"]["description"]
    top_level_properties = transport_request["tools"][0]["function"]["parameters"]["properties"]
    assert "requires_tool" in top_level_properties["evidence_posture"]["description"]


@pytest.mark.asyncio
async def test_complete_with_trace_uses_founder_live_synthetic_tool_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posted_payloads: list[dict[str, object]] = []
    response = _FakeResponse(
        payload=_tool_call_envelope(
            tool_name="manager_structured_decision",
            arguments=_founder_live_payload(),
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
    adapter = BuilderSpaceAdapter(manager_model_override="grok-4-fast")

    parsed, trace = await adapter.complete_with_trace(
        system_prompt="Return structured manager payload.",
        user_payload={"constraints": _founder_live_constraints()},
        stage="intake_manager_round",
    )

    assert parsed["intent_type"] == "log_meal"
    assert posted_payloads[0]["json"]["tool_choice"]["function"]["name"] == "manager_structured_decision"
    assert posted_payloads[0]["json"]["parallel_tool_calls"] is False
    assert "response_format" not in posted_payloads[0]["json"]
    assert trace["decision_transport_mode"] == "synthetic_tool_transport"
    assert trace["schema_name"] == "founder_live_manager_contract"
    assert trace["schema_version"] == "v1"
    assert trace["repair_attempted"] is False
    assert trace["repair_result"] == "not_needed"
    assert trace["repair_attempt_count"] == 0


@pytest.mark.asyncio
async def test_complete_with_trace_repairs_founder_live_contract_shape_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posted_payloads: list[dict[str, object]] = []
    incomplete = _founder_live_payload()
    incomplete.pop("evidence_posture")
    first = _FakeResponse(
        payload=_tool_call_envelope(tool_name="manager_structured_decision", arguments=incomplete),
        text="first",
    )
    second = _FakeResponse(
        payload=_tool_call_envelope(
            tool_name="manager_structured_decision",
            arguments=_founder_live_payload(),
        ),
        text="second",
    )
    monkeypatch.setenv("AI_BUILDER_TOKEN", "test-token")
    monkeypatch.setenv("AI_BUILDER_BASE_URL", "https://example.test/backend/v1")
    monkeypatch.setenv("AI_BUILDER_TRANSPORT_RETRY_COUNT", "0")
    monkeypatch.setattr(
        builderspace_adapter_module.httpx,
        "AsyncClient",
        lambda **kwargs: _RecordingAsyncClient(responses=[first, second], recorder=posted_payloads, **kwargs),
    )
    adapter = BuilderSpaceAdapter(manager_model_override="grok-4-fast")

    parsed, trace = await adapter.complete_with_trace(
        system_prompt="Return structured manager payload.",
        user_payload={"constraints": _founder_live_constraints()},
        stage="intake_manager_round",
    )

    assert parsed["evidence_posture"] == "bounded_estimate"
    assert len(posted_payloads) == 2
    assert "CONTRACT_REPAIR" in posted_payloads[1]["json"]["messages"][-1]["content"]
    assert trace["repair_attempted"] is True
    assert trace["repair_result"] == "passed_after_repair"
    assert trace["repair_attempt_count"] == 1
    assert trace["transport_attempts"][0]["status"] == "parse_retry"
    assert trace["transport_attempts"][1]["status"] == "success"


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
