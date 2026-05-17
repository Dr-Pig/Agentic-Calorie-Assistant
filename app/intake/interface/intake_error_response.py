from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from ...logging import append_audit_event, now_iso, write_request_trace_artifact
from ...schemas import EstimateRequest
from ...shared.contracts.audit import AuditEvent


_TIMEOUT_ERROR_TYPES = {"TimeoutError", "TimeoutException", "ReadTimeout", "ConnectTimeout", "WriteTimeout"}
_USER_SAFE_TIMEOUT_MESSAGE = (
    "系統剛剛等模型回覆太久，這次沒有幫你記錄。"
    "你可以直接再送一次，或補一句「繼續剛剛那餐」。"
)
_USER_SAFE_GENERIC_MESSAGE = "系統剛剛處理失敗，這次沒有幫你記錄。請再送一次。"


def _provider_trace_from_exception(exc: Exception) -> dict[str, Any] | None:
    trace = getattr(exc, "trace", None)
    if not isinstance(trace, dict):
        return None
    return {
        "stage": trace.get("stage"),
        "provider": trace.get("provider"),
        "model": trace.get("model"),
        "failure_family": trace.get("failure_family") or trace.get("request_failure_family"),
        "failing_component": trace.get("failing_component"),
        "response_status": trace.get("response_status"),
        "timeout_seconds": trace.get("timeout_seconds"),
        "transport_attempts": trace.get("transport_attempts"),
        "parse_attempt_count": len(trace.get("parse_attempts") or []),
        "schema_name": trace.get("schema_name"),
        "schema_version": trace.get("schema_version"),
        "decision_transport_mode": trace.get("decision_transport_mode"),
        "structured_output_transport_mode": trace.get("structured_output_transport_mode"),
        "cache_metrics": trace.get("cache_metrics"),
    }


def _exception_family(exc: Exception, provider_trace: dict[str, Any] | None) -> str:
    trace_family = str((provider_trace or {}).get("failure_family") or "")
    error_type = type(exc).__name__
    error_text = str(exc)
    if trace_family == "provider_timeout":
        return "provider_timeout"
    if error_type in _TIMEOUT_ERROR_TYPES or any(token in error_text for token in _TIMEOUT_ERROR_TYPES):
        return "provider_timeout"
    if trace_family:
        return trace_family
    return "runtime_error"


def _user_safe_message(exception_family: str) -> str:
    if exception_family == "provider_timeout":
        return _USER_SAFE_TIMEOUT_MESSAGE
    return _USER_SAFE_GENERIC_MESSAGE


def build_estimate_error_response(
    *,
    request_id: str,
    request: EstimateRequest,
    source_page_version: str | None,
    exc: Exception,
) -> JSONResponse:
    provider_trace = _provider_trace_from_exception(exc)
    exception_family = _exception_family(exc, provider_trace)
    coach_message = _user_safe_message(exception_family)
    trace_path = write_request_trace_artifact(
        request_id,
        {
            "request_id": request_id,
            "timestamp": now_iso(),
            "request": {
                "user_id": getattr(request, "user_id", "anonymous"),
                "text": request.text,
                "allow_search": request.allow_search,
            },
            "source_page_version": source_page_version,
            "status": "error",
            "error": str(exc),
            "error_type": type(exc).__name__,
            "exception_family": exception_family,
            "provider_runtime": provider_trace,
            "coach_message": coach_message,
        },
    )
    append_audit_event(
        AuditEvent(
            request_id=request_id,
            timestamp=now_iso(),
            text=request.text,
            allow_search=request.allow_search,
            status="error",
            error=str(exc),
            source_page_version=source_page_version,
            trace_artifact_path=str(trace_path),
        )
    )
    return JSONResponse(
        status_code=500,
        content={
            "request_id": request_id,
            "error": "internal_server_error",
            "coach_message": coach_message,
            "payload": None,
        },
    )


__all__ = ["build_estimate_error_response"]
