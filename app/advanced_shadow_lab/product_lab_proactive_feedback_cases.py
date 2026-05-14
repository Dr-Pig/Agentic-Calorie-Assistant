from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.memory_feedback_projection import (
    project_feedback_event_to_shadow_controls,
)


SCOPE_KEYS = {
    "user_id": "founder-self-use",
    "workspace_id": "advanced-product-lab",
    "project_id": "agentic-calorie-assistant",
    "surface": "manager_runtime_lab",
}


def build_proactive_feedback_case_reports() -> list[dict[str, Any]]:
    return [
        _case_report("proactive_dismiss_reason_next_signal", "dismiss"),
        _case_report("proactive_snooze_window", "snooze"),
        _case_report("proactive_reopen_or_modify", "reopen"),
        _case_report("proactive_opt_out_dual_projection", "opt_out"),
    ]


def _case_report(case_id: str, action: str) -> dict[str, Any]:
    projection = project_feedback_event_to_shadow_controls(
        feedback_event=_event(action),
        targets=[_target()],
    )
    projections = [
        item for item in projection.get("consumer_projections", []) if isinstance(item, Mapping)
    ]
    first = projections[0] if projections else {}
    return {
        "case_id": case_id,
        "action": action,
        "status": "pass" if _projection_passes(action, projection) else "blocked",
        "projection_status": str(projection.get("status") or ""),
        "projection_type": str(first.get("projection_type") or ""),
        "projection_count": len(projections),
        "dismiss_reason": str(first.get("dismiss_reason") or ""),
        "next_signal_required": str(first.get("next_signal_required") or ""),
        "snooze_until": str(first.get("snooze_until") or ""),
        "proactive_delivery_enabled": projection.get("proactive_delivery_enabled")
        is True,
        "scheduler_delivery_allowed": projection.get("scheduler_delivery_allowed") is True,
        "durable_product_memory_written": projection.get(
            "durable_product_memory_written"
        )
        is True,
        "blockers": list(projection.get("blockers") or []),
    }


def _event(action: str) -> dict[str, Any]:
    event = {
        "target_type": "proactive_candidate",
        "target_id": "proactive-evening-meal",
        "action": action,
        "reason": "too_frequent",
        "source_turn_id": "turn-proactive-feedback-1",
        "scope_keys": dict(SCOPE_KEYS),
    }
    if action == "snooze":
        event["snooze_until"] = "2026-05-13T12:00:00Z"
    return event


def _target() -> dict[str, Any]:
    return {
        "target_type": "proactive_candidate",
        "target_id": "proactive-evening-meal",
        "scope_keys": dict(SCOPE_KEYS),
        "source_turn_ids": ["turn-proactive-feedback-1"],
        "source_refs": ["proactive:evening-meal:source"],
        "candidate_type": "proactive_nudge",
        "trigger_type": "evening_meal_check",
        "next_signal_required": "new_app_open_with_qualified_pool",
    }


def _projection_passes(action: str, projection: Mapping[str, Any]) -> bool:
    reports = projection.get("consumer_projections")
    projections = [item for item in reports or [] if isinstance(item, Mapping)]
    if projection.get("status") != "pass":
        return False
    if projection.get("proactive_delivery_enabled") is True:
        return False
    if action == "opt_out":
        return {item.get("projection_type") for item in projections} == {
            "proactive_suppression_candidate",
            "app_use_memory_candidate",
        }
    expected = {
        "dismiss": "user_control_suppression",
        "snooze": "user_control_snooze",
        "reopen": "user_control_reopen_modify",
    }[action]
    return bool(projections) and projections[0].get("projection_type") == expected


__all__ = ["build_proactive_feedback_case_reports"]
