from __future__ import annotations

from typing import Any

from ..application.stage_trace_runtime import append_stage_runtime_event
from ..schemas import PassExecutionEnvelope


def trace_with_request_id(trace: dict[str, Any], request_id: str) -> dict[str, Any]:
    return {"request_id": request_id, **(trace or {})}


def debug_step(request_id: str, **payload: Any) -> dict[str, Any]:
    return {"request_id": request_id, **payload}


async def run_text_stage(
    provider: Any,
    *,
    stage: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    max_tokens: int,
    attempt_index: int | None = None,
    trigger_reason: str | None = None,
    handoff_contract: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw, trace = await provider.complete_with_trace(
        system_prompt=system_prompt,
        user_payload=user_payload,
        stage=stage,
        max_tokens=max_tokens,
    )
    merged_trace = trace or {}
    if attempt_index is not None:
        merged_trace = {"attempt_index": attempt_index, **merged_trace}
    if trigger_reason:
        merged_trace = {"trigger_reason": trigger_reason, **merged_trace}
    if handoff_contract:
        merged_trace = {"handoff_contract": handoff_contract, **merged_trace}
    request_id = str(user_payload.get("request_id") or "").strip()
    if request_id:
        append_stage_runtime_event(
            request_id=request_id,
            stage=stage,
            provider=provider,
            merged_trace=merged_trace,
            trigger_reason=trigger_reason,
        )
    return raw or {}, merged_trace


def pass_envelope(
    *,
    status: str,
    payload: dict[str, Any] | None = None,
    fallback_used: bool = False,
    error: str | None = None,
) -> PassExecutionEnvelope:
    return PassExecutionEnvelope(
        status=status,  # type: ignore[arg-type]
        payload=payload or {},
        fallback_used=fallback_used,
        error=error,
    )
