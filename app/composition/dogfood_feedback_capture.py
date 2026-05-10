from __future__ import annotations

from typing import Any

from app.composition.dogfood_review_queue import build_feedback_record_from_desktop_capture


def _operation_context(
    value: Any,
    *,
    submitted_endpoint: str,
    http_status: int,
    duration_ms: int,
) -> dict[str, Any]:
    context = dict(value) if isinstance(value, dict) else {}
    if not context.get("submitted_endpoint"):
        context["submitted_endpoint"] = submitted_endpoint
    if context.get("http_status") is None:
        context["http_status"] = http_status
    if context.get("duration_ms") is None:
        context["duration_ms"] = duration_ms
    return context


def build_feedback_record_from_route_payload(
    payload: dict[str, Any],
    *,
    submitted_endpoint: str,
    http_status: int = 200,
    duration_ms: int,
) -> dict[str, Any]:
    return build_feedback_record_from_desktop_capture(
        category=str(payload.get("category") or ""),
        feedback_text=str(payload.get("feedback_text") or ""),
        page=str(payload.get("page") or ""),
        selected_date=str(payload.get("selected_date") or ""),
        user_external_id=str(payload.get("user_external_id") or ""),
        trace_id=payload.get("trace_id"),
        message_id=payload.get("message_id"),
        meal_id=payload.get("meal_id"),
        severity=str(payload.get("severity") or "medium"),
        ui_event=payload.get("ui_event") if isinstance(payload.get("ui_event"), dict) else {},
        operation_context=_operation_context(
            payload.get("operation_context"),
            submitted_endpoint=submitted_endpoint,
            http_status=http_status,
            duration_ms=duration_ms,
        ),
    )
