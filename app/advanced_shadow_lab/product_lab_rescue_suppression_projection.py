from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import NON_MUTATION_FLAGS
from app.memory.application.memory_feedback_projection import (
    project_feedback_event_to_shadow_controls,
)


RESCUE_TRIGGER = "rescue_nudge"
REPEATED_WINDOW_DAYS = 14
REPEATED_SIGNAL_THRESHOLD = 3


def build_rescue_suppression_feedback_projection(
    *,
    feedback_event: Mapping[str, Any],
    rescue_nudge_target: Mapping[str, Any],
    recent_control_signals: list[Mapping[str, Any]] | None = None,
    now: datetime,
) -> dict[str, Any]:
    source_projection = project_feedback_event_to_shadow_controls(
        feedback_event=feedback_event,
        targets=[rescue_nudge_target],
    )
    blockers = [
        *[str(item) for item in source_projection.get("blockers") or []],
        *_target_blockers(rescue_nudge_target),
    ]
    action = str(feedback_event.get("action") or "")
    suppression_projection = (
        None
        if blockers
        else _suppression_projection(feedback_event, rescue_nudge_target)
    )
    return {
        "artifact_type": "advanced_product_lab_rescue_suppression_feedback_projection",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "action": action,
        "trigger_type": str(rescue_nudge_target.get("trigger_type") or ""),
        "source_projection_artifact_type": source_projection.get("artifact_type"),
        "suppression_projection": suppression_projection,
        "app_use_memory_candidate": _app_use_memory_candidate(
            feedback_event,
            rescue_nudge_target,
            suppression_projection,
        ),
        "repeated_control_projection": _repeated_control_projection(
            feedback_event=feedback_event,
            recent_control_signals=recent_control_signals or [],
            now=now,
        ),
        "blockers": blockers,
        "confirmed_memory_promoted": False,
        "proactive_delivery_enabled": False,
        "rescue_plan_mutated": False,
        **dict(NON_MUTATION_FLAGS),
    }


def _target_blockers(target: Mapping[str, Any]) -> list[str]:
    if str(target.get("trigger_type") or "") != RESCUE_TRIGGER:
        return ["rescue_nudge_target.trigger_type_not_rescue_nudge"]
    return []


def _suppression_projection(
    event: Mapping[str, Any],
    target: Mapping[str, Any],
) -> dict[str, Any] | None:
    action = str(event.get("action") or "")
    if action == "opt_out":
        return {
            "projection_type": "explicit_rescue_nudge_opt_out",
            "suppression_status": "active_until_reenabled",
            "user_callable_rescue_remains": True,
            "source_refs": _source_refs(target),
        }
    if action == "dismiss":
        return {
            "projection_type": "current_candidate_control",
            "dismiss_reason": str(event.get("reason") or ""),
            "next_signal_required": str(target.get("next_signal_required") or ""),
            "confirmed_suppression": False,
        }
    if action == "snooze":
        return {
            "projection_type": "cooldown_snooze_control",
            "snooze_until": str(event.get("snooze_until") or ""),
            "confirmed_suppression": False,
        }
    if action == "undo":
        return {
            "projection_type": "undo_rescue_nudge_control",
            "confirmed_suppression": False,
        }
    return None


def _app_use_memory_candidate(
    event: Mapping[str, Any],
    target: Mapping[str, Any],
    suppression_projection: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not suppression_projection or event.get("action") != "opt_out":
        return None
    return {
        "candidate_type": "app_use_suppression",
        "status": "pending_review",
        "record_type": "suppression_rule",
        "family": "proactive_control",
        "trigger_type": RESCUE_TRIGGER,
        "summary": "User explicitly opted out of proactive rescue nudges.",
        "scope_keys": dict(_mapping(event.get("scope_keys"))),
        "source_refs": _source_refs(target),
        "confirmed_memory_promoted": False,
        "validator_required": True,
    }


def _repeated_control_projection(
    *,
    feedback_event: Mapping[str, Any],
    recent_control_signals: list[Mapping[str, Any]],
    now: datetime,
) -> dict[str, Any] | None:
    signals = list(recent_control_signals)
    if feedback_event.get("action") == "dismiss":
        signals.append({"action": "dismiss", "occurred_at": now.isoformat()})
    count = sum(1 for signal in signals if _counts_for_repeated_review(signal, now))
    if count < REPEATED_SIGNAL_THRESHOLD:
        return None
    return {
        "projection_type": "rescue_nudge_repeated_dismiss_pending_review",
        "status": "pending_review",
        "signal_count": count,
        "window_days": REPEATED_WINDOW_DAYS,
        "confirmed_suppression": False,
        "chat_first_confirmation_required": True,
    }


def _counts_for_repeated_review(signal: Mapping[str, Any], now: datetime) -> bool:
    if str(signal.get("action") or "") not in {"dismiss", "ignore"}:
        return False
    occurred_at = _parse_datetime(signal.get("occurred_at"))
    if occurred_at is None:
        return False
    age = now - occurred_at
    return timedelta(0) <= age <= timedelta(days=REPEATED_WINDOW_DAYS)


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _source_refs(target: Mapping[str, Any]) -> list[str]:
    return [str(ref) for ref in target.get("source_refs") or [] if str(ref)]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_rescue_suppression_feedback_projection"]
