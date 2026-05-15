from __future__ import annotations

from typing import Any

from app.composition.dogfood_feedback_record import build_feedback_record_from_desktop_capture


def _operation_context(
    value: Any,
    *,
    submitted_endpoint: str,
    http_status: int,
    duration_ms: int,
    auto_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = dict(value) if isinstance(value, dict) else {}
    if not context.get("submitted_endpoint"):
        context["submitted_endpoint"] = submitted_endpoint
    if context.get("http_status") is None:
        context["http_status"] = http_status
    if context.get("duration_ms") is None:
        context["duration_ms"] = duration_ms
    auto_context_payload = dict(auto_context) if isinstance(auto_context, dict) else {}
    if auto_context_payload and not context.get("auto_context_status"):
        context["auto_context_status"] = auto_context_payload.get("context_status")
    return context


def _auto_or_payload(payload: dict[str, Any], auto_context: dict[str, Any], key: str) -> Any:
    return payload.get(key) or auto_context.get(key)


def build_feedback_record_from_route_payload(
    payload: dict[str, Any],
    *,
    submitted_endpoint: str,
    http_status: int = 200,
    duration_ms: int,
    auto_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    auto_context_payload = dict(auto_context) if isinstance(auto_context, dict) else {}
    return build_feedback_record_from_desktop_capture(
        category=str(payload.get("category") or ""),
        feedback_text=str(payload.get("feedback_text") or ""),
        page=str(payload.get("page") or ""),
        selected_date=str(payload.get("selected_date") or ""),
        user_external_id=str(payload.get("user_external_id") or ""),
        request_id=_auto_or_payload(payload, auto_context_payload, "request_id"),
        trace_id=_auto_or_payload(payload, auto_context_payload, "trace_id"),
        message_id=_auto_or_payload(payload, auto_context_payload, "message_id"),
        meal_id=_auto_or_payload(payload, auto_context_payload, "meal_id"),
        severity=str(payload.get("severity") or "medium"),
        ui_event=payload.get("ui_event") if isinstance(payload.get("ui_event"), dict) else {},
        operation_context=_operation_context(
            payload.get("operation_context"),
            submitted_endpoint=submitted_endpoint,
            http_status=http_status,
            duration_ms=duration_ms,
            auto_context=auto_context_payload,
        ),
        auto_context=auto_context_payload,
    )
