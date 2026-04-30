from __future__ import annotations

import json
from typing import Any

import httpx

from .builderspace_parsing import BuilderSpaceParseError
from ..runtime.agent.manager_branch_contract import (
    manager_pass1_decision_tool_arguments_schema_for_constraints,
    should_attempt_b1_common_commercial_meal_pass1_decision_transport,
    should_attempt_b1_pass1_structured_output_transport,
    should_attempt_b1_pass2_structured_output_transport,
    should_attempt_b1_profile_pass1_decision_transport,
)
from ..runtime.contracts.trace import MANAGER_LOOP_STAGE


DECISION_TRANSPORT_TOOL_NAME = "manager_call_tools_decision"


def response_format_request_for_stage(
    stage: str,
    *,
    constraints: dict[str, Any] | None = None,
    schema: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    constraint_snapshot = _constraint_snapshot(constraints)
    if stage == MANAGER_LOOP_STAGE and (
        should_attempt_b1_pass1_structured_output_transport(constraints)
        or should_attempt_b1_pass2_structured_output_transport(constraints)
    ):
        return (
            {
                "type": "json_schema",
                "json_schema": {
                    "name": _phase_b1_schema_name(constraints),
                    "strict": True,
                    "schema": schema,
                },
            },
            {
                "structured_output_transport_attempted": True,
                "structured_output_transport_mode": "json_schema",
                "structured_output_transport_accepted": None,
                "structured_output_transport_fallback": None,
                "fallback_reason": None,
                "structured_output_transport_constraint_snapshot": constraint_snapshot,
            },
        )
    return (
        {"type": "json_object"},
        {
            "structured_output_transport_attempted": False,
            "structured_output_transport_mode": "json_object",
            "structured_output_transport_accepted": False,
            "structured_output_transport_fallback": None,
            "fallback_reason": None,
            "structured_output_transport_constraint_snapshot": constraint_snapshot,
        },
    )


def _phase_b1_schema_name(constraints: dict[str, Any] | None) -> str:
    if should_attempt_b1_pass2_structured_output_transport(constraints):
        return "phase_b1_pass2_manager_contract"
    return "phase_b1_pass1_manager_contract"


def decision_transport_request_for_stage(
    stage: str,
    *,
    constraints: dict[str, Any] | None = None,
    manager_loop_schema: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    constraint_snapshot = _constraint_snapshot(constraints)
    meta = {
        "decision_transport_attempted": False,
        "decision_transport_mode": None,
        "decision_transport_accepted": False,
        "decision_transport_fallback": None,
        "decision_transport_fallback_reason": None,
        "decision_transport_contract_breach": False,
        "decision_transport_constraint_snapshot": constraint_snapshot,
    }
    if stage != MANAGER_LOOP_STAGE or not (
        should_attempt_b1_common_commercial_meal_pass1_decision_transport(constraints)
        or should_attempt_b1_profile_pass1_decision_transport(constraints)
    ):
        return None, meta
    schema = manager_pass1_decision_tool_arguments_schema_for_constraints(manager_loop_schema, constraints)
    meta["decision_transport_attempted"] = True
    meta["decision_transport_mode"] = "tool_call_decision_transport"
    return (
        {
            "mode": "tool_call_decision_transport",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": DECISION_TRANSPORT_TOOL_NAME,
                        "description": "Return the manager call-tools decision as structured arguments.",
                        "parameters": schema,
                    },
                }
            ],
            "tool_choice": {
                "type": "function",
                "function": {"name": DECISION_TRANSPORT_TOOL_NAME},
            },
        },
        meta,
    )


def is_structured_output_transport_rejection(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response is None or response.status_code not in {400, 404, 415, 422}:
        return False
    text = (response.text or "").lower()
    return any(marker in text for marker in ("response_format", "json_schema", "strict", "unsupported"))


def is_tool_call_transport_rejection(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response is None or response.status_code not in {400, 404, 415, 422}:
        return False
    text = (response.text or "").lower()
    return any(marker in text for marker in ("tool_choice", "tools", "function", "unsupported"))


def extract_tool_call_decision(data: dict[str, Any], *, tool_name: str) -> dict[str, Any]:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise BuilderSpaceParseError(
            "BuilderSpace returned no tool-call choices.",
            failure_family="tool_call_transport_contract_breach",
            failing_component="builderspace_adapter.extract_tool_call_decision",
            observed_value=choices,
        )
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise BuilderSpaceParseError(
            "BuilderSpace tool-call choice must be an object.",
            failure_family="tool_call_transport_contract_breach",
            failing_component="builderspace_adapter.extract_tool_call_decision",
            observed_value=first_choice,
        )
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise BuilderSpaceParseError(
            "BuilderSpace tool-call message must be an object.",
            failure_family="tool_call_transport_contract_breach",
            failing_component="builderspace_adapter.extract_tool_call_decision",
            observed_value=message,
        )
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list) or not tool_calls:
        raise BuilderSpaceParseError(
            "BuilderSpace did not return the synthetic decision tool call.",
            failure_family="tool_call_transport_contract_breach",
            failing_component="builderspace_adapter.extract_tool_call_decision",
            observed_value=message.get("content"),
        )
    if len(tool_calls) != 1:
        raise BuilderSpaceParseError(
            "BuilderSpace returned multiple synthetic decision tool calls.",
            failure_family="tool_call_transport_contract_breach",
            failing_component="builderspace_adapter.extract_tool_call_decision",
            observed_value=tool_calls,
        )
    tool_call = tool_calls[0]
    function = tool_call.get("function") if isinstance(tool_call, dict) else None
    if not isinstance(function, dict) or function.get("name") != tool_name:
        raise BuilderSpaceParseError(
            "BuilderSpace returned an unexpected synthetic decision tool call.",
            failure_family="tool_call_transport_contract_breach",
            failing_component="builderspace_adapter.extract_tool_call_decision",
            observed_value=tool_call,
        )
    arguments = function.get("arguments")
    if not isinstance(arguments, str):
        raise BuilderSpaceParseError(
            "BuilderSpace synthetic decision tool arguments must be a JSON string.",
            failure_family="tool_call_transport_contract_breach",
            failing_component="builderspace_adapter.extract_tool_call_decision",
            observed_value=arguments,
        )
    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise BuilderSpaceParseError(
            "BuilderSpace synthetic decision tool arguments were not valid JSON.",
            failure_family="tool_call_transport_contract_breach",
            failing_component="builderspace_adapter.extract_tool_call_decision",
            observed_value=arguments,
        ) from exc
    if not isinstance(parsed, dict):
        raise BuilderSpaceParseError(
            "BuilderSpace synthetic decision tool arguments must decode to an object.",
            failure_family="tool_call_transport_contract_breach",
            failing_component="builderspace_adapter.extract_tool_call_decision",
            observed_value=parsed,
        )
    return parsed


def _constraint_snapshot(constraints: dict[str, Any] | None) -> dict[str, str]:
    return {
        "phase_b1_manager_role": str((constraints or {}).get("phase_b1_manager_role") or ""),
        "phase_b1_pass1_mode": str((constraints or {}).get("phase_b1_pass1_mode") or ""),
        "phase_b1_case_family": str((constraints or {}).get("phase_b1_case_family") or ""),
        "phase_b1_provider_profile_id": str((constraints or {}).get("phase_b1_provider_profile_id") or ""),
        "phase_b1_provider_profile_transport_mode": str(
            (constraints or {}).get("phase_b1_provider_profile_transport_mode") or ""
        ),
    }
