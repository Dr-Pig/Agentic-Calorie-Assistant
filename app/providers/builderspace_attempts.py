from __future__ import annotations

from typing import Any

import httpx

from .builderspace_parsing import BuilderSpaceParseError, extract_json_object, extract_text_content
from .builderspace_prompt_cache import apply_prompt_cache_key
from .builderspace_transport import is_structured_output_transport_rejection


async def run_structured_attempt(
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
    model: str,
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
        request_payload = apply_prompt_cache_key(request_payload, model=model, stage=stage)
        attempt_trace["response_format_type"] = current_response_format.get("type")
        attempt_trace["response_format_attempt_index"] = format_index
        response = await post_chat_completion(client, base_url, token, request_payload)
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
    data = response_json_object(response, attempt_index=attempt_index, stage=stage)
    raw_content = extract_text_content(data)
    try:
        parsed, parse_meta = extract_json_object(raw_content)
    except Exception as exc:
        parse_attempt = {
            "attempt_index": attempt_index,
            "stage": stage,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_content_excerpt": raw_content[:600],
            "failure_family": getattr(exc, "failure_family", "malformed_json"),
            "failing_component": getattr(exc, "failing_component", "builderspace_adapter.extract_json_object"),
        }
        if isinstance(exc, BuilderSpaceParseError):
            parse_attempt["parse_recovery_used"] = exc.parse_recovery_used
            parse_attempt["parse_recovery_strategy"] = exc.parse_recovery_strategy
            parse_attempt["parse_recovery_ambiguous"] = exc.parse_recovery_ambiguous
            parse_attempt["parse_contract_status"] = exc.parse_contract_status
            parse_attempt["observed_value"] = exc.observed_value
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
        failure_family = getattr(exc, "failure_family", "manager_output_contract_violation")
        failing_component = getattr(exc, "failing_component", "builderspace_runtime_contract.validate_manager_payload")
        parse_attempts.append(
            {
                "attempt_index": attempt_index,
                "stage": stage,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "failure_family": failure_family,
                "failing_component": failing_component,
                "parse_contract_status": parse_meta.get("parse_contract_status"),
                "parse_recovery_used": parse_meta.get("parse_recovery_used"),
                "parse_recovery_strategy": parse_meta.get("parse_recovery_strategy"),
                "parse_recovery_ambiguous": parse_meta.get("parse_recovery_ambiguous"),
                "raw_content_excerpt": parse_meta.get("raw_content_excerpt") or raw_content[:600],
                "observed_value": parsed,
            }
        )
        if parse_retry_budget_ref["value"] > 0:
            parse_retry_budget_ref["value"] -= 1
            return request_payload, None, response, data, effective_type
        raise manager_payload_contract_error(
            exc=exc,
            parsed=parsed,
            raw_content=raw_content,
            parse_meta=parse_meta,
            parse_attempt=parse_attempts[-1],
        ) from exc
    return request_payload, parsed, response, data, effective_type


def response_json_object(response: httpx.Response | Any, *, attempt_index: int, stage: str) -> dict[str, Any]:
    try:
        data = response.json()
    except Exception as exc:
        error = BuilderSpaceParseError(
            "BuilderSpace response body is not a JSON object.",
            failure_family="response_json_shape_error",
            failing_component="builderspace_adapter.response_json",
            observed_value=response.text,
            parse_attempts=[
                {"attempt_index": attempt_index, "stage": stage, "parser": "response_json", "status": "failed", "failure_family": "response_json_shape_error"}
            ],
        )
        setattr(error, "raw_response_excerpt", response.text)
        raise error from exc
    if not isinstance(data, dict):
        error = BuilderSpaceParseError(
            "BuilderSpace response JSON must be an object.",
            failure_family="response_json_shape_error",
            failing_component="builderspace_adapter.response_json",
            observed_value=data,
            parse_attempts=[
                {"attempt_index": attempt_index, "stage": stage, "parser": "response_json", "status": "failed", "failure_family": "response_json_shape_error"}
            ],
        )
        setattr(error, "raw_response_excerpt", response.text)
        raise error
    return data


async def post_chat_completion(client: httpx.AsyncClient, base_url: str, token: str, request_payload: dict[str, Any]):
    return await client.post(
        f"{base_url}/chat/completions",
        params={"debug": "true"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=request_payload,
    )


def empty_parse_meta() -> dict[str, Any]:
    return {
        "parse_contract_status": None,
        "parse_recovery_used": False,
        "parse_recovery_strategy": None,
        "parse_recovery_ambiguous": False,
        "raw_content_excerpt": None,
        "parse_attempts": [],
    }


def remaining_retry_budget(parse_attempts: list[dict[str, Any]], max_retries: int) -> int:
    return max(0, max_retries - len(parse_attempts))


def last_parse_error(parse_attempts: list[dict[str, Any]]) -> Exception | None:
    if not parse_attempts:
        return None
    last = parse_attempts[-1]
    return BuilderSpaceParseError(
        str(last.get("error") or last.get("failure_family") or "parse failure"),
        failure_family=str(last.get("failure_family") or "malformed_json"),
        failing_component=str(last.get("failing_component") or "builderspace_adapter.extract_json_object"),
        observed_value=last.get("observed_value"),
        raw_content=last.get("raw_content_excerpt"),
        parse_attempts=[last],
        parse_contract_status=last.get("parse_contract_status"),
        parse_recovery_used=bool(last.get("parse_recovery_used")),
        parse_recovery_strategy=last.get("parse_recovery_strategy"),
        parse_recovery_ambiguous=bool(last.get("parse_recovery_ambiguous")),
    )


def manager_payload_contract_error(
    *,
    exc: Exception,
    parsed: dict[str, Any],
    raw_content: str,
    parse_meta: dict[str, Any],
    parse_attempt: dict[str, Any],
) -> BuilderSpaceParseError:
    return BuilderSpaceParseError(
        str(exc),
        failure_family=str(parse_attempt.get("failure_family") or "manager_output_contract_violation"),
        failing_component=str(parse_attempt.get("failing_component") or "builderspace_runtime_contract.validate_manager_payload"),
        observed_value=parsed,
        raw_content=raw_content,
        parse_attempts=[parse_attempt],
        parse_contract_status=parse_meta.get("parse_contract_status"),
        parse_recovery_used=bool(parse_meta.get("parse_recovery_used")),
        parse_recovery_strategy=parse_meta.get("parse_recovery_strategy"),
        parse_recovery_ambiguous=bool(parse_meta.get("parse_recovery_ambiguous")),
    )


__all__ = [
    "empty_parse_meta",
    "last_parse_error",
    "post_chat_completion",
    "remaining_retry_budget",
    "response_json_object",
    "run_structured_attempt",
]
