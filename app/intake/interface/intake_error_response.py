from __future__ import annotations

from fastapi.responses import JSONResponse

from ...logging import append_audit_event, now_iso, write_request_trace_artifact
from ...schemas import EstimateRequest
from ...shared.contracts.audit import AuditEvent


def build_estimate_error_response(
    *,
    request_id: str,
    request: EstimateRequest,
    source_page_version: str | None,
    exc: Exception,
) -> JSONResponse:
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
            "coach_message": "處理這則訊息時發生錯誤，請稍後再試。",
            "payload": None,
        },
    )


__all__ = ["build_estimate_error_response"]
