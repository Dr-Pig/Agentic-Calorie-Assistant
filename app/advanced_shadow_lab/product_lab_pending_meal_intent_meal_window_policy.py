from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from app.runtime.contracts.pending_meal_intent import (
    PendingMealIntent,
    PendingMealIntentMealWindowPosture,
    PendingMealIntentWindow,
    PendingMealIntentWindowSource,
)


DEFAULT_MEAL_WINDOWS: dict[PendingMealIntentWindow, tuple[str, str]] = {
    "lunch": ("11:00", "14:30"),
    "dinner": ("17:00", "22:00"),
    "late_night": ("22:00", "01:00"),
}
ALLOWED_OVERRIDE_STATUSES = {
    "confirmed": "confirmed_memory",
    "pattern_high_confidence": "pattern_memory",
}
DEFAULT_QUIET_HOURS = ("22:00", "08:00")


def build_meal_window_policy_trace(
    intent: PendingMealIntent,
    *,
    memory_context_pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    local_dt = _local_datetime(intent)
    target_window = _target_window(intent, local_dt)
    window_start, window_end = DEFAULT_MEAL_WINDOWS[target_window]
    window_source: PendingMealIntentWindowSource = "default"
    source_refs: list[str] = []
    blockers: list[str] = []

    override = _matching_override(memory_context_pack or {}, target_window)
    if override:
        status = str(override.get("status") or "")
        override_source = ALLOWED_OVERRIDE_STATUSES.get(status)
        if override_source:
            window_start = str(override.get("window_start") or window_start)
            window_end = str(override.get("window_end") or window_end)
            window_source = override_source
            source_refs = [str(override.get("source_ref") or "")]
        else:
            blockers.append(f"memory_override.status_not_allowed:{status}")

    followup_at_local = _followup_at_local(local_dt, window_start, window_end)
    followup_time = followup_at_local.strftime("%H:%M")
    return {
        "artifact_type": "advanced_product_lab_pending_meal_intent_meal_window_policy_trace",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "intent_id": intent.intent_id,
        "target_window": target_window,
        "window_start_local": window_start,
        "window_end_local": window_end,
        "window_source": window_source,
        "memory_override_applied": window_source != "default",
        "followup_timing": "meal_window_end",
        "followup_at_local": followup_at_local.isoformat(),
        "followup_time_local": followup_time,
        "followup_in_quiet_hours": _inside_quiet_hours(followup_time),
        "quiet_hours_policy": "chat_thread_message_only_no_push",
        "pending_intent_patch": {
            "candidate_metadata_patch": {
                "meal_window": target_window,
                "followup_at_local": followup_at_local.isoformat(),
            },
            "meal_window_posture": PendingMealIntentMealWindowPosture(
                target_window=target_window,
                window_source=window_source,
            ).model_dump(mode="json"),
        },
        "source_refs": [ref for ref in source_refs if ref],
        "blockers": blockers,
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
    }


def apply_meal_window_policy_to_intent(
    intent: PendingMealIntent,
    *,
    memory_context_pack: Mapping[str, Any] | None = None,
) -> PendingMealIntent:
    trace = build_meal_window_policy_trace(
        intent,
        memory_context_pack=memory_context_pack,
    )
    patch = trace["pending_intent_patch"]
    return intent.model_copy(
        update={
            "candidate_metadata": {
                **intent.candidate_metadata,
                **dict(patch["candidate_metadata_patch"]),
            },
            "meal_window_posture": PendingMealIntentMealWindowPosture.model_validate(
                patch["meal_window_posture"]
            ),
        }
    )


def _local_datetime(intent: PendingMealIntent) -> datetime:
    return intent.created_at.astimezone(ZoneInfo(intent.meal_window_posture.local_timezone))


def _target_window(
    intent: PendingMealIntent,
    local_dt: datetime,
) -> PendingMealIntentWindow:
    if intent.meal_window_posture.target_window != "unknown":
        return intent.meal_window_posture.target_window
    current_minute = _minute(local_dt.strftime("%H:%M"))
    for window, (start, end) in DEFAULT_MEAL_WINDOWS.items():
        if _inside_window(current_minute, _minute(start), _minute(end)):
            return window
    return _next_window(current_minute)


def _matching_override(
    memory_context_pack: Mapping[str, Any],
    target_window: str,
) -> Mapping[str, Any] | None:
    for override in memory_context_pack.get("meal_window_overrides") or []:
        if isinstance(override, Mapping) and override.get("target_window") == target_window:
            return override
    return None


def _followup_at_local(local_dt: datetime, start: str, end: str) -> datetime:
    start_minute = _minute(start)
    end_minute = _minute(end)
    candidate = local_dt.replace(
        hour=end_minute // 60,
        minute=end_minute % 60,
        second=0,
        microsecond=0,
    )
    if end_minute <= start_minute and _minute(local_dt.strftime("%H:%M")) >= start_minute:
        candidate += timedelta(days=1)
    return candidate


def _next_window(current_minute: int) -> PendingMealIntentWindow:
    for window, (start, _end) in DEFAULT_MEAL_WINDOWS.items():
        if current_minute < _minute(start):
            return window
    return "late_night"


def _inside_window(current: int, start: int, end: int) -> bool:
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _inside_quiet_hours(local_time: str) -> bool:
    current = _minute(local_time)
    start = _minute(DEFAULT_QUIET_HOURS[0])
    end = _minute(DEFAULT_QUIET_HOURS[1])
    return current >= start or current < end


def _minute(value: str) -> int:
    hour, minute = value.split(":", 1)
    return int(hour) * 60 + int(minute)


__all__ = [
    "DEFAULT_MEAL_WINDOWS",
    "apply_meal_window_policy_to_intent",
    "build_meal_window_policy_trace",
]
