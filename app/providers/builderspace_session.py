from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .builderspace_parsing import BuilderSpaceParseError, extract_finish_reason, extract_json_object, extract_text_content
from .builderspace_trace import build_failure_trace, build_success_trace, new_transport_attempt
from .builderspace_transport import (
    DECISION_TRANSPORT_TOOL_NAME,
    extract_tool_call_decision,
    is_structured_output_transport_rejection,
    is_tool_call_transport_rejection,
)

MAX_PARSE_RETRIES = 1


async def complete_builderspace_with_trace(
    *,
    base_url: str,
    token: str,
    timeout_seconds: int,
    transport_retry_count: int,
    transport_retry_backoff_seconds: float,
    model: str,
    stage: str,
    manager_temperature: float,
    base_request_payload: dict[str, Any],
    constraints: dict[str, Any],
    response_format: dict[str, Any],
    transport_meta: dict[str, Any],
    decision_transport_request: dict[str, Any] | None,
    decision_transport_meta: dict[str, Any],
    validate_manager_payload,
    build_error,
    async_client_factory,
) -> tuple[dict[str, Any], dict[str, Any]]:
    fallback_reason: str | None = None
    effective_response_format_type = response_format.get("type")
    transport_attempts: list[dict[str, Any]] = []
    parse_attempts: list[dict[str, Any]] = []
    last_error: Exception | None = None
    parse_retry_budget = MAX_PARSE_RETRIES
    response: httpx.Response | Any | None = None
    data: dict[str, Any] | None = None
    request_payload: dict[str, Any] = dict(base_request_payload)

    try:
        async with async_client_factory(timeout=timeout_seconds) as client:
            for attempt_index in range(1, transport_retry_count + 2):
                attempt_trace = new_transport_attempt(attempt_index, base_url, model, stage)
                if decision_transport_request is not None:
                    request_payload = dict(base_request_payload)
                    request_payload["tools"] = decision_transport_request["tools"]
                    request_payload["tool_choice"] = decision_transport_request["tool_choice"]
                    attempt_trace["decision_transport_mode"] = decision_transport_request["mode"]
                    try:
                        response = await _post_chat_completion(client, base_url, token, request_payload)
                        attempt_trace["http_status"] = response.status_code
                        response.raise_for_status()
                        data = response.json()
                        if not isinstance(data, dict):
                            raise BuilderSpaceParseError(
                                "BuilderSpace response JSON must be an object.",
                                failure_family="response_json_shape_error",
                                failing_component="builderspace_adapter.response_json",
                                observed_value=data,
                            )
                        parsed = extract_tool_call_decision(data, tool_name=DECISION_TRANSPORT_TOOL_NAME)
                        decision_transport_meta["decision_transport_accepted"] = True
                        decision_transport_meta["decision_transport_contract_breach"] = False
                        validate_manager_payload(stage, parsed, constraints=constraints)
                        attempt_trace["status"] = "success"
                        transport_attempts.append(attempt_trace)
                        return parsed, build_success_trace(
                            stage=stage,
                            provider="builderspace",
                            model=model,
                            request_payload=request_payload,
                            response_text=response.text,
                            parsed=parsed,
                            data=data,
                            transport_attempts=transport_attempts,
                            parse_attempts=parse_attempts,
                            transport_meta=transport_meta,
                            decision_transport_meta=decision_transport_meta,
                            finish_reason=extract_finish_reason(data),
                            response_status=response.status_code,
                            raw_content=None,
                            parse_meta=_empty_parse_meta(),
                            effective_response_format_type=None,
                        )
                    except httpx.HTTPStatusError as exc:
                        if is_tool_call_transport_rejection(exc):
                            decision_transport_meta["decision_transport_accepted"] = False
                            decision_transport_meta["decision_transport_fallback"] = "json_schema"
                            decision_transport_meta["decision_transport_fallback_reason"] = "provider_rejected_tool_call_transport"
                            decision_transport_request = None
                        else:
                            raise
                    except BuilderSpaceParseError:
                        decision_transport_meta["decision_transport_accepted"] = True
                        decision_transport_meta["decision_transport_contract_breach"] = True
                        raise
                request_payload, parsed, response, data, effective_response_format_type = await _run_structured_attempt(
                    client=client,
                    base_url=base_url,
                    token=token,
                    base_request_payload=base_request_payload,
                    response_format=response_format,
                    transport_meta=transport_meta,
                    attempt_trace=attempt_trace,
                    constraints=constraints,
                    stage=stage,
                    attempt_index=attempt_index,
                    parse_attempts=parse_attempts,
                    parse_retry_budget_ref={"value": parse_retry_budget},
                    validate_manager_payload=validate_manager_payload,
                )
                parse_retry_budget = _remaining_retry_budget(parse_attempts, MAX_PARSE_RETRIES)
                if parsed is None:
                    last_error = _last_parse_error(parse_attempts)
                    transport_attempts.append(attempt_trace)
                    if attempt_index < transport_retry_count + 1:
                        await asyncio.sleep(transport_retry_backoff_seconds * attempt_index)
                    continue
                attempt_trace["status"] = "success"
                transport_attempts.append(attempt_trace)
                raw_content = extract_text_content(data)
                parsed_object, parse_meta = extract_json_object(raw_content)
                return parsed_object, build_success_trace(
                    stage=stage,
                    provider="builderspace",
                    model=model,
                    request_payload=request_payload,
                    response_text=response.text,
                    parsed=parsed_object,
                    data=data,
                    transport_attempts=transport_attempts,
                    parse_attempts=parse_attempts,
                    transport_meta=transport_meta,
                    decision_transport_meta=decision_transport_meta,
                    finish_reason=extract_finish_reason(data),
                    response_status=response.status_code,
                    raw_content=raw_content,
                    parse_meta=parse_meta,
                    effective_response_format_type=effective_response_format_type,
                )
            raise last_error or RuntimeError("BuilderSpace transport failed without a captured exception.")
    except Exception as exc:
        raise build_error(
            exc=exc,
            request_payload=request_payload,
            transport_attempts=transport_attempts,
            parse_attempts=parse_attempts,
            response=response,
            data=data,
            transport_meta=transport_meta,
            decision_transport_meta=decision_transport_meta,
            fallback_reason=fallback_reason,
            effective_response_format_type=effective_response_format_type,
        ) from exc


async def _run_structured_attempt(
    *,
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    base_request_payload: dict[str, Any],
    response_format: dict[str, Any],
    transport_meta: dict[str, Any],
    attempt_trace: dict[str, Any],
    constraints: dict[str, Any],
    stage: str,
    attempt_index: int,
    parse_attempts: list[dict[str, Any]],
    parse_retry_budget_ref: dict[str, int],
    validate_manager_payload,
) -> tuple[dict[str, Any], dict[str, Any] | None, httpx.Response | Any, dict[str, Any], str | None]:
    response_format_attempts = [response_format]
    if transport_meta["structured_output_transport_attempted"]:
        response_format_attempts.append({"type": "json_object"})
    response: httpx.Response | Any | None = None
    data: dict[str, Any] | None = None
    request_payload = dict(base_request_payload)
    effective_type: str | None = None
    for format_index, current_response_format in enumerate(response_format_attempts, start=1):
        request_payload = dict(base_request_payload)
        request_payload["response_format"] = current_response_format
        attempt_trace["response_format_type"] = current_response_format.get("type")
        attempt_trace["response_format_attempt_index"] = format_index
        response = await _post_chat_completion(client, base_url, token, request_payload)
        attempt_trace["http_status"] = response.status_code
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if (
                current_response_format.get("type") == "json_schema"
                and is_structured_output_transport_rejection(exc)
                and format_index < len(response_format_attempts)
            ):
                transport_meta["structured_output_transport_accepted"] = False
                transport_meta["structured_output_transport_fallback"] = "json_object"
                transport_meta["fallback_reason"] = "provider_rejected_response_format"
                continue
            raise
        effective_type = current_response_format.get("type")
        transport_meta["structured_output_transport_accepted"] = current_response_format.get("type") == "json_schema"
        break
    data = _response_json_object(response, attempt_index=attempt_index, stage=stage)
    raw_content = extract_text_content(data)
    try:
        parsed, _ = extract_json_object(raw_content)
    except Exception as exc:
        parse_attempt = {
            "attempt_index": attempt_index,
            "stage": stage,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_content_excerpt": raw_content[:600],
            "failure_family": getattr(exc, "failure_family", "malformed_json"),
        }
        if isinstance(exc, BuilderSpaceParseError):
            parse_attempt["parse_recovery_used"] = exc.parse_recovery_used
            parse_attempt["parse_recovery_strategy"] = exc.parse_recovery_strategy
            parse_attempt["parse_recovery_ambiguous"] = exc.parse_recovery_ambiguous
            parse_attempt["raw_content_excerpt"] = exc.raw_content_excerpt or raw_content[:600]
        parse_attempts.append(parse_attempt)
        if parse_retry_budget_ref["value"] > 0:
            parse_retry_budget_ref["value"] -= 1
            return request_payload, None, response, data, effective_type
        raise
    if not parsed:
        exc = RuntimeError("empty parsed manager payload")
        parse_attempts.append(
            {
                "attempt_index": attempt_index,
                "stage": stage,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "failure_family": "empty_content",
            }
        )
        if parse_retry_budget_ref["value"] > 0:
            parse_retry_budget_ref["value"] -= 1
            return request_payload, None, response, data, effective_type
        raise exc
    try:
        validate_manager_payload(stage, parsed, constraints=constraints)
    except Exception as exc:
        if exc.__class__.__name__ == "ManagerPass1BranchContractError":
            raise
        parse_attempts.append(
            {
                "attempt_index": attempt_index,
                "stage": stage,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "failure_family": getattr(exc, "failure_family", "malformed_json"),
            }
        )
        if parse_retry_budget_ref["value"] > 0:
            parse_retry_budget_ref["value"] -= 1
            return request_payload, None, response, data, effective_type
        raise
    return request_payload, parsed, response, data, effective_type


def _response_json_object(response: httpx.Response | Any, *, attempt_index: int, stage: str) -> dict[str, Any]:
    try:
        data = response.json()
    except Exception as exc:
        error = BuilderSpaceParseError(
            "BuilderSpace response body is not a JSON object.",
            failure_family="response_json_shape_error",
            failing_component="builderspace_adapter.response_json",
            observed_value=response.text,
            parse_attempts=[{"attempt_index": attempt_index, "stage": stage, "parser": "response_json", "status": "failed", "failure_family": "response_json_shape_error"}],
        )
        setattr(error, "raw_response_excerpt", response.text)
        raise error from exc
    if not isinstance(data, dict):
        error = BuilderSpaceParseError(
            "BuilderSpace response JSON must be an object.",
            failure_family="response_json_shape_error",
            failing_component="builderspace_adapter.response_json",
            observed_value=data,
            parse_attempts=[{"attempt_index": attempt_index, "stage": stage, "parser": "response_json", "status": "failed", "failure_family": "response_json_shape_error"}],
        )
        setattr(error, "raw_response_excerpt", response.text)
        raise error
    return data


async def _post_chat_completion(client: httpx.AsyncClient, base_url: str, token: str, request_payload: dict[str, Any]):
    return await client.post(
        f"{base_url}/chat/completions",
        params={"debug": "true"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=request_payload,
    )


def _empty_parse_meta() -> dict[str, Any]:
    return {
        "parse_contract_status": None,
        "parse_recovery_used": False,
        "parse_recovery_strategy": None,
        "parse_recovery_ambiguous": False,
        "raw_content_excerpt": None,
        "parse_attempts": [],
    }


def _remaining_retry_budget(parse_attempts: list[dict[str, Any]], max_retries: int) -> int:
    return max(0, max_retries - len(parse_attempts))


def _last_parse_error(parse_attempts: list[dict[str, Any]]) -> Exception | None:
    if not parse_attempts:
        return None
    last = parse_attempts[-1]
    error = RuntimeError(str(last.get("error") or last.get("failure_family") or "parse failure"))
    setattr(error, "failure_family", last.get("failure_family"))
    setattr(error, "failing_component", "builderspace_adapter.extract_json_object")
    setattr(error, "raw_response_excerpt", last.get("raw_content_excerpt"))
    setattr(error, "raw_content_excerpt", last.get("raw_content_excerpt"))
    setattr(error, "parse_recovery_used", bool(last.get("parse_recovery_used")))
    setattr(error, "parse_recovery_strategy", last.get("parse_recovery_strategy"))
    setattr(error, "parse_recovery_ambiguous", bool(last.get("parse_recovery_ambiguous")))
    return error
