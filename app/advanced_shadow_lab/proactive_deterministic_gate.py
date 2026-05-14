from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_proactive_gate_policy import (
    DEFAULT_QUIET_HOURS,
    PERMISSION_POSTURE,
    permission_reasons,
)


def evaluate_proactive_deterministic_trigger_gate(
    *,
    trigger_type: str,
    turn: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    checks = {
        "quiet_hours_passed": not _inside_quiet_hours_context(context),
        "recent_send_cap_passed": _recent_send_cap_passed(context),
        "cooldown_passed": not _cooldown_active(turn=turn, context=context, trigger=trigger_type),
        "surface_passed": str(turn.get("surface") or "") == "chat",
        "permission_posture_passed": not permission_reasons(trigger=trigger_type, context=context),
        "onboarding_gate_passed": _trigger_ready(context, "onboarding_ready_by_trigger", trigger_type),
        "data_sufficiency_passed": _trigger_ready(context, "data_sufficiency_by_trigger", trigger_type),
    }
    suppression_reasons = _suppression_reasons(
        trigger=trigger_type,
        turn=turn,
        context=context,
        checks=checks,
    )
    return {
        "artifact_type": "advanced_product_lab_proactive_deterministic_trigger_gate",
        "artifact_schema_version": "1.0",
        "status": "pass" if not suppression_reasons else "blocked",
        "trigger_type": trigger_type,
        "permission_posture": PERMISSION_POSTURE.get(trigger_type, "user_expected"),
        "checks": checks,
        "suppression_reasons": suppression_reasons,
        "llm_contextual_send_skip_allowed": not suppression_reasons,
        "deterministic_gate_before_llm": True,
        "scheduler_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
    }


def _suppression_reasons(
    *,
    trigger: str,
    turn: Mapping[str, Any],
    context: Mapping[str, Any],
    checks: Mapping[str, bool],
) -> list[str]:
    reasons: list[str] = []
    if not checks["quiet_hours_passed"]:
        reasons.append("quiet_hours")
    if not checks["recent_send_cap_passed"]:
        reasons.append("recent_send_cap")
    if not checks["cooldown_passed"]:
        reasons.append("cooldown_active")
    if not checks["surface_passed"]:
        reasons.append("surface_not_chat")
    reasons.extend(permission_reasons(trigger=trigger, context=context))
    if not checks["onboarding_gate_passed"]:
        reasons.append("onboarding_gate_not_ready")
    if not checks["data_sufficiency_passed"]:
        reasons.append("data_sufficiency_missing")
    return reasons


def _inside_quiet_hours_context(context: Mapping[str, Any]) -> bool:
    local_time = str(context.get("local_time") or "")
    if not local_time:
        return False
    quiet_start = str(context.get("quiet_hours_start") or DEFAULT_QUIET_HOURS[0])
    quiet_end = str(context.get("quiet_hours_end") or DEFAULT_QUIET_HOURS[1])
    return _inside_quiet_hours(local_time, quiet_start, quiet_end)


def _recent_send_cap_passed(context: Mapping[str, Any]) -> bool:
    max_recent = context.get("max_recent_send_count")
    if not isinstance(max_recent, int):
        return True
    return int(context.get("recent_send_count") or 0) < max_recent


def _cooldown_active(
    *,
    turn: Mapping[str, Any],
    context: Mapping[str, Any],
    trigger: str,
) -> bool:
    last_sent = _trigger_value(context, "last_sent_minute_by_trigger", trigger, None)
    cooldown = _trigger_value(context, "cooldown_minutes_by_trigger", trigger, None)
    now = turn.get("lab_now_minute")
    if not all(isinstance(value, int) for value in (last_sent, cooldown, now)):
        return False
    if cooldown <= 0:
        return False
    return int(now) - int(last_sent) < int(cooldown)


def _trigger_ready(context: Mapping[str, Any], key: str, trigger: str) -> bool:
    return _trigger_value(context, key, trigger, True) is True


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


__all__ = ["evaluate_proactive_deterministic_trigger_gate"]
