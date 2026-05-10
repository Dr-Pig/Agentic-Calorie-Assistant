from __future__ import annotations

from typing import Any, Mapping


PERMISSION_POSTURE = {
    "recommendation_prompt": "app_open_only",
    "pending_intake_followup": "user_expected",
    "rescue_nudge": "later_requires_explicit_consent",
}
DEFAULT_QUIET_HOURS = ("22:00", "08:00")


def context_reasons(
    *,
    turn: Mapping[str, Any],
    context: Mapping[str, Any],
) -> list[str]:
    local_time = str(context.get("local_time") or "")
    quiet_start = str(context.get("quiet_hours_start") or DEFAULT_QUIET_HOURS[0])
    quiet_end = str(context.get("quiet_hours_end") or DEFAULT_QUIET_HOURS[1])
    reasons: list[str] = []
    if local_time and _inside_quiet_hours(local_time, quiet_start, quiet_end):
        reasons.append("quiet_hours")
    max_recent = context.get("max_recent_send_count")
    recent = int(context.get("recent_send_count") or 0)
    if isinstance(max_recent, int) and recent >= max_recent:
        reasons.append("recent_send_cap")
    if str(turn.get("surface") or "") != "chat":
        reasons.append("surface_not_chat")
    return reasons


def permission_reasons(*, trigger: str, context: Mapping[str, Any]) -> list[str]:
    posture = PERMISSION_POSTURE.get(trigger, "user_expected")
    surface = _trigger_value(context, "delivery_surface_by_trigger", trigger, "app_open")
    consent = _trigger_value(
        context,
        "explicit_consent_ready_by_trigger",
        trigger,
        True,
    )
    if posture == "app_open_only" and surface != "app_open":
        return ["permission_app_open_required"]
    if posture == "later_requires_explicit_consent" and consent is not True:
        return ["permission_explicit_consent_required"]
    return []


def review_status(reasons: list[str]) -> str:
    if not reasons:
        return "candidate_for_human_review"
    if any(reason.startswith("permission_") for reason in reasons):
        return "suppressed_permission"
    if any(reason.startswith(("dismissed_", "snoozed_", "control_")) for reason in reasons):
        return "suppressed_feedback"
    return "suppressed_context_or_data"


def reviewer_next_step(status: str) -> str:
    if status == "candidate_for_human_review":
        return "allow_lab_chat_review"
    return "omit_from_lab_chat_with_trace"


def _trigger_value(
    context: Mapping[str, Any],
    key: str,
    trigger: str,
    default: Any,
) -> Any:
    values = context.get(key)
    if not isinstance(values, Mapping):
        return default
    return values.get(trigger, default)


def _inside_quiet_hours(local_time: str, start: str, end: str) -> bool:
    current = _parse_hh_mm(local_time)
    start_min = _parse_hh_mm(start)
    end_min = _parse_hh_mm(end)
    if start_min == end_min:
        return False
    if start_min < end_min:
        return start_min <= current < end_min
    return current >= start_min or current < end_min


def _parse_hh_mm(value: str) -> int:
    hour_text, minute_text = value.split(":", 1)
    return int(hour_text) * 60 + int(minute_text)


__all__ = [
    "PERMISSION_POSTURE",
    "context_reasons",
    "permission_reasons",
    "review_status",
    "reviewer_next_step",
]
