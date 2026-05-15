from __future__ import annotations

from typing import Any

from sqlalchemy.exc import SQLAlchemyError


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _short_text(value: Any, *, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}..."


def _feedback_message_snapshot(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": message.get("message_id"),
        "role": message.get("role"),
        "content": _short_text(message.get("content")),
        "trace_id": message.get("trace_id"),
        "linked_meal_log_id": message.get("linked_meal_log_id"),
        "runtime_turn_status": message.get("runtime_turn_status"),
        "trace_chain_complete": message.get("trace_chain_complete"),
    }


def _find_feedback_target_message(
    messages: list[dict[str, Any]],
    *,
    request_id: str | None,
    trace_id: str | None,
    message_id: str | None,
) -> dict[str, Any] | None:
    target_trace_id = (trace_id or request_id or "").strip()
    target_message_id = (message_id or "").strip()
    if target_message_id:
        for message in reversed(messages):
            if str(message.get("message_id") or "") == target_message_id:
                return message
    if target_trace_id:
        for message in reversed(messages):
            if str(message.get("trace_id") or "") == target_trace_id:
                return message
    return next((message for message in reversed(messages) if message.get("trace_id")), None)


def _feedback_read_model_snapshot(debug_payload: dict[str, Any]) -> dict[str, Any]:
    model = _dict_or_empty(debug_payload.get("model"))
    today_summary = _dict_or_empty(model.get("today_summary"))
    same_truth = _dict_or_empty(model.get("same_truth"))
    meal_threads = model.get("meal_threads") if isinstance(model.get("meal_threads"), list) else []
    return {
        "state_posture": debug_payload.get("state_posture"),
        "local_date": debug_payload.get("local_date"),
        "today_summary": {
            "source_kind": today_summary.get("source_kind"),
            "budget_kcal": today_summary.get("budget_kcal"),
            "consumed_kcal": today_summary.get("consumed_kcal"),
            "remaining_kcal": today_summary.get("remaining_kcal"),
            "active_meal_count": today_summary.get("active_meal_count"),
        },
        "meal_thread_count": len(meal_threads),
        "same_truth_status": same_truth.get("status"),
        "same_truth_source": same_truth.get("source_truth"),
    }


def build_feedback_auto_context_unavailable(reason: str) -> dict[str, Any]:
    return {
        "context_status": reason,
        "auto_context_source": "chat_history_and_read_model",
    }


def build_feedback_auto_context_from_payloads(
    *,
    payload: dict[str, Any],
    chat_history_payload: dict[str, Any],
    debug_payload: dict[str, Any],
) -> dict[str, Any]:
    messages = (
        chat_history_payload.get("messages")
        if isinstance(chat_history_payload.get("messages"), list)
        else []
    )
    target = _find_feedback_target_message(
        messages,
        request_id=str(payload.get("request_id") or "") or None,
        trace_id=str(payload.get("trace_id") or "") or None,
        message_id=str(payload.get("message_id") or "") or None,
    )
    recent_messages = [_feedback_message_snapshot(message) for message in messages[-6:]]
    context_status = "auto_attached" if target is not None else "no_trace_context"
    return {
        "context_status": context_status,
        "auto_context_source": "chat_history_and_read_model",
        "request_id": target.get("trace_id") if target else None,
        "trace_id": target.get("trace_id") if target else None,
        "message_id": target.get("message_id") if target else None,
        "meal_id": payload.get("meal_id") or (target.get("linked_meal_log_id") if target else None),
        "recent_messages": recent_messages,
        "read_model_snapshot": _feedback_read_model_snapshot(debug_payload),
    }


def build_feedback_auto_context_from_backend(
    *,
    db: Any,
    payload: dict[str, Any],
    chat_history_builder: Any,
    debug_payload_builder: Any,
) -> dict[str, Any]:
    user_external_id = str(payload.get("user_external_id") or "")
    selected_date = str(payload.get("selected_date") or "")
    if not user_external_id or not selected_date:
        return build_feedback_auto_context_unavailable("missing_scope")

    try:
        chat_history = chat_history_builder(
            db,
            user_external_id=user_external_id,
            local_date=selected_date,
        )
        debug_payload = debug_payload_builder(
            db,
            user_external_id=user_external_id,
            local_date=selected_date,
        )
    except SQLAlchemyError:
        return build_feedback_auto_context_unavailable("auto_context_unavailable")

    return build_feedback_auto_context_from_payloads(
        payload=payload,
        chat_history_payload=chat_history,
        debug_payload=debug_payload,
    )
