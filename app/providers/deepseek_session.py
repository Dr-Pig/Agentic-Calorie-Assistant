from __future__ import annotations

import asyncio
from typing import Any

from .deepseek_parsing import extract_json_object, extract_text_content


async def complete_deepseek_with_trace(
    *,
    base_url: str,
    token: str,
    timeout_seconds: int,
    transport_retry_count: int,
    transport_retry_backoff_seconds: float,
    model: str,
    stage: str,
    temperature: float,
    request_payload: dict[str, Any],
    transport_meta: dict[str, Any],
    validate_manager_payload,
    build_error,
    async_client_factory,
) -> tuple[dict[str, Any], dict[str, Any]]:
    transport_attempts: list[dict[str, Any]] = []
    parse_attempts: list[dict[str, Any]] = []
    last_error: Exception | None = None
    parse_retry_budget = 1
    try:
        async with async_client_factory(timeout=timeout_seconds) as client:
            for attempt_index in range(1, transport_retry_count + 2):
                attempt_trace = {
                    "attempt_index": attempt_index,
                    "model": model,
                    "stage": stage,
                    "endpoint": f"{base_url}/chat/completions",
                }
                try:
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                        json=request_payload,
                    )
                    attempt_trace["http_status"] = response.status_code
                    response.raise_for_status()
                    data = response.json()
                    raw_content = extract_text_content(data)
                    try:
                        parsed = extract_json_object(raw_content)
                    except Exception as exc:
                        parse_attempts.append(
                            {"attempt_index": attempt_index, "stage": stage, "error_type": type(exc).__name__, "error": str(exc), "raw_content_excerpt": raw_content[:600], "failure_family": "malformed_json"}
                        )
                        last_error = exc
                        if parse_retry_budget > 0:
                            parse_retry_budget -= 1
                            continue
                        raise
                    if not parsed:
                        exc = RuntimeError("empty parsed manager payload")
                        parse_attempts.append(
                            {"attempt_index": attempt_index, "stage": stage, "error_type": type(exc).__name__, "error": str(exc), "failure_family": "empty_content"}
                        )
                        last_error = exc
                        if parse_retry_budget > 0:
                            parse_retry_budget -= 1
                            continue
                        raise exc
                    try:
                        validate_manager_payload(stage, parsed, constraints=dict((request_payload.get("messages") or [{}])[-1] and {}))
                    except Exception as exc:
                        if exc.__class__.__name__ == "ManagerPass1BranchContractError":
                            raise
                        parse_attempts.append(
                            {"attempt_index": attempt_index, "stage": stage, "error_type": type(exc).__name__, "error": str(exc), "failure_family": getattr(exc, "failure_family", "malformed_json")}
                        )
                        last_error = exc
                        if parse_retry_budget > 0:
                            parse_retry_budget -= 1
                            continue
                        raise
                    attempt_trace["status"] = "success"
                    transport_attempts.append(attempt_trace)
                    return parsed, {
                        "stage": stage,
                        "provider": "deepseek",
                        "model": model,
                        "request_payload": request_payload,
                        "raw_content": raw_content,
                        "parsed_object": parsed,
                        "usage": data.get("usage"),
                        "transport_attempts": transport_attempts,
                        "parse_attempts": parse_attempts,
                        "finish_reason": (data.get("choices") or [{}])[0].get("finish_reason"),
                        "request_failure_family": None,
                        "structured_output_transport_attempted": transport_meta["structured_output_transport_attempted"],
                        "structured_output_transport_mode": transport_meta["structured_output_transport_mode"],
                        "structured_output_transport_accepted": transport_meta["structured_output_transport_accepted"],
                        "structured_output_transport_fallback": transport_meta["structured_output_transport_fallback"],
                        "fallback_reason": transport_meta["fallback_reason"],
                        "structured_output_transport_constraint_snapshot": transport_meta["structured_output_transport_constraint_snapshot"],
                        "effective_response_format_type": request_payload["response_format"].get("type"),
                    }
                except Exception as exc:
                    last_error = exc
                    attempt_trace["error_type"] = type(exc).__name__
                    attempt_trace["error"] = str(exc)
                    transport_attempts.append(attempt_trace)
                    if attempt_index < transport_retry_count + 1:
                        await asyncio.sleep(transport_retry_backoff_seconds * attempt_index)
            raise last_error or RuntimeError("DeepSeek transport failed without a captured exception.")
    except Exception as exc:
        raise build_error(exc=exc, request_payload=request_payload, transport_attempts=transport_attempts, parse_attempts=parse_attempts, transport_meta=transport_meta) from exc
