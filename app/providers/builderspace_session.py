from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import time
from typing import Any

import httpx

from .builderspace_attempts import (
    empty_parse_meta,
    last_parse_error,
    manager_payload_contract_error,
    post_chat_completion,
    remaining_retry_budget,
    run_structured_attempt,
)
from .builderspace_parsing import BuilderSpaceParseError, extract_finish_reason, extract_json_object, extract_text_content
from .builderspace_prompt_cache import apply_prompt_cache_key
from .builderspace_trace import build_success_trace, new_transport_attempt
from .builderspace_transport import (
    DECISION_TRANSPORT_TOOL_NAME,
    extract_tool_call_decision,
    is_tool_call_transport_rejection,
)

MAX_PARSE_RETRIES = 1
RETRYABLE_TRANSPORT_ERROR_TYPES = (
    httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout,
    httpx.WriteTimeout, httpx.PoolTimeout,
)
RETRYABLE_HTTP_STATUS_CODES = {429, 500, 503}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
    active_base_request_payload: dict[str, Any] = dict(base_request_payload)
    transport_meta.setdefault("repair_attempted", False)
    transport_meta.setdefault("repair_result", "not_needed")
    transport_meta.setdefault("repair_attempt_count", 0)
    max_attempt_count = transport_retry_count + MAX_PARSE_RETRIES + 1

    try:
        async with async_client_factory(timeout=timeout_seconds) as client:
            for attempt_index in range(1, max_attempt_count + 1):
                attempt_trace = new_transport_attempt(attempt_index, base_url, model, stage)
                _start_attempt_timer(attempt_trace)
                try:
                    if decision_transport_request is not None:
                        request_payload = dict(active_base_request_payload)
                        request_payload["tools"] = decision_transport_request["tools"]
                        request_payload["tool_choice"] = decision_transport_request["tool_choice"]
                        request_payload["parallel_tool_calls"] = False
                        request_payload = apply_prompt_cache_key(request_payload, model=model, stage=stage)
                        attempt_trace["decision_transport_mode"] = decision_transport_request["mode"]
                        try:
                            response = await post_chat_completion(client, base_url, token, request_payload)
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
                            parsed = extract_tool_call_decision(
                                data,
                                tool_name=str(decision_transport_request.get("tool_name") or DECISION_TRANSPORT_TOOL_NAME),
                            )
                            decision_transport_meta["decision_transport_accepted"] = True
                            decision_transport_meta["decision_transport_contract_breach"] = False
                            try:
                                validate_manager_payload(stage, parsed, constraints=constraints)
                            except Exception as exc:
                                if exc.__class__.__name__ == "ManagerPass1BranchContractError":
                                    raise
                                decision_transport_meta["decision_transport_contract_breach"] = True
                                parse_attempt = _manager_contract_parse_attempt(
                                    attempt_index=attempt_index,
                                    stage=stage,
                                    exc=exc,
                                    parsed=parsed,
                                )
                                parse_attempts.append(parse_attempt)
                                if parse_retry_budget > 0:
                                    parse_retry_budget -= 1
                                    active_base_request_payload = _with_contract_repair_message(
                                        active_base_request_payload,
                                        parse_attempt=parse_attempt,
                                    )
                                    _mark_repair_requested(transport_meta)
                                    _mark_attempt_completed(attempt_trace, status="parse_retry")
                                    transport_attempts.append(attempt_trace)
                                    if attempt_index < max_attempt_count:
                                        await asyncio.sleep(transport_retry_backoff_seconds * attempt_index)
                                    continue
                                raise manager_payload_contract_error(
                                    exc=exc,
                                    parsed=parsed,
                                    raw_content="",
                                    parse_meta=empty_parse_meta(),
                                    parse_attempt=parse_attempt,
                                ) from exc
                            _mark_repair_success_if_needed(transport_meta)
                            _mark_attempt_completed(attempt_trace, status="success")
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
                                parse_meta=empty_parse_meta(),
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
                    request_payload, parsed, response, data, effective_response_format_type = await run_structured_attempt(
                        client=client,
                        base_url=base_url,
                        token=token,
                        base_request_payload=active_base_request_payload,
                        response_format=response_format,
                        transport_meta=transport_meta,
                        attempt_trace=attempt_trace,
                        constraints=constraints,
                        stage=stage,
                        attempt_index=attempt_index,
                        parse_attempts=parse_attempts,
                        parse_retry_budget_ref={"value": parse_retry_budget},
                        validate_manager_payload=validate_manager_payload,
                        model=model,
                    )
                    parse_retry_budget = remaining_retry_budget(parse_attempts, MAX_PARSE_RETRIES)
                    if parsed is None:
                        last_error = last_parse_error(parse_attempts)
                        if parse_attempts:
                            active_base_request_payload = _with_contract_repair_message(
                                active_base_request_payload,
                                parse_attempt=parse_attempts[-1],
                            )
                            _mark_repair_requested(transport_meta)
                        _mark_attempt_completed(attempt_trace, status="parse_retry")
                        transport_attempts.append(attempt_trace)
                        if attempt_index < max_attempt_count:
                            await asyncio.sleep(transport_retry_backoff_seconds * attempt_index)
                        continue
                    _mark_attempt_completed(attempt_trace, status="success")
                    _mark_repair_success_if_needed(transport_meta)
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
                except Exception as exc:
                    last_error = exc
                    _record_attempt_failure(attempt_trace, exc=exc, response=response)
                    transport_attempts.append(attempt_trace)
                    if _should_retry_transport_error(exc) and attempt_index < transport_retry_count + 1:
                        await asyncio.sleep(transport_retry_backoff_seconds * attempt_index)
                        continue
                    raise
            raise last_error or RuntimeError("BuilderSpace transport failed without a captured exception.")
    except Exception as exc:
        if response is None and isinstance(exc, httpx.HTTPStatusError):
            response = exc.response
        _mark_repair_failure_if_needed(transport_meta)
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


def _record_attempt_failure(
    attempt_trace: dict[str, Any],
    *,
    exc: Exception,
    response: httpx.Response | Any | None,
) -> None:
    attempt_trace["status"] = "error"
    attempt_trace["ended_at_utc"] = _utc_now_iso()
    _finish_attempt_timer(attempt_trace)
    attempt_trace["error_type"] = type(exc).__name__
    attempt_trace["error"] = str(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        attempt_trace["http_status"] = exc.response.status_code
        attempt_trace["response_body_excerpt"] = (exc.response.text or "")[:1200]
        attempt_trace["response_body_truncated"] = len(exc.response.text or "") > 1200
    elif response is not None:
        attempt_trace["http_status"] = getattr(response, "status_code", None)


def _mark_attempt_completed(attempt_trace: dict[str, Any], *, status: str) -> None:
    attempt_trace["status"] = status
    attempt_trace["ended_at_utc"] = _utc_now_iso()
    _finish_attempt_timer(attempt_trace)


def _start_attempt_timer(attempt_trace: dict[str, Any]) -> None:
    attempt_trace["_started_monotonic_s"] = time.perf_counter()


def _finish_attempt_timer(attempt_trace: dict[str, Any]) -> None:
    started = attempt_trace.pop("_started_monotonic_s", None)
    if isinstance(started, (int, float)):
        attempt_trace["duration_ms"] = max(0, int(round((time.perf_counter() - started) * 1000)))


def _manager_contract_parse_attempt(
    *,
    attempt_index: int,
    stage: str,
    exc: Exception,
    parsed: dict[str, Any],
) -> dict[str, Any]:
    return {
        "attempt_index": attempt_index,
        "stage": stage,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "failure_family": getattr(exc, "failure_family", "manager_output_contract_violation"),
        "failing_component": getattr(
            exc,
            "failing_component",
            "builderspace_runtime_contract.validate_manager_payload",
        ),
        "observed_value": parsed,
    }


def _with_contract_repair_message(
    base_request_payload: dict[str, Any],
    *,
    parse_attempt: dict[str, Any],
) -> dict[str, Any]:
    repaired = dict(base_request_payload)
    messages = list(repaired.get("messages") or [])
    messages.append(
        {
            "role": "user",
            "content": (
                "CONTRACT_REPAIR: Return the same manager decision using the required structured schema. "
                "Do not change user intent, workflow_effect, target_attachment, exactness, confidence, "
                "or evidence_posture. Fix only the contract shape. "
                f"Previous validation error: {parse_attempt.get('error')}"
            ),
        }
    )
    repaired["messages"] = messages
    return repaired


def _mark_repair_requested(transport_meta: dict[str, Any]) -> None:
    transport_meta["repair_attempted"] = True
    transport_meta["repair_result"] = "requested"
    transport_meta["repair_attempt_count"] = int(transport_meta.get("repair_attempt_count") or 0) + 1


def _mark_repair_success_if_needed(transport_meta: dict[str, Any]) -> None:
    if transport_meta.get("repair_attempted"):
        transport_meta["repair_result"] = "passed_after_repair"


def _mark_repair_failure_if_needed(transport_meta: dict[str, Any]) -> None:
    if transport_meta.get("repair_attempted") and transport_meta.get("repair_result") == "requested":
        transport_meta["repair_result"] = "failed"


def _should_retry_transport_error(exc: Exception) -> bool:
    if isinstance(exc, RETRYABLE_TRANSPORT_ERROR_TYPES):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_HTTP_STATUS_CODES
    return False
