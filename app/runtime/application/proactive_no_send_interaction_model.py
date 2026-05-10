from __future__ import annotations

from typing import Any, Literal, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_no_send_interaction_model"
)

Action = Literal["dismiss", "snooze", "undo"]
FALSE_FLAGS = {
    "runtime_effect_allowed": False,
    "proactive_sent": False,
    "scheduler_enabled": False,
    "live_delivery_allowed": False,
    "push_or_line_delivery_connected": False,
    "scheduler_activation_allowed": False,
    "manager_context_injected": False,
    "manager_context_packet_changed": False,
    "recommendation_served": False,
    "rescue_committed": False,
    "proposal_committed": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "meal_thread_mutated": False,
    "durable_memory_written": False,
    "durable_snooze_written": False,
    "mutation_changed": False,
    "user_facing_behavior_changed": False,
}
CLAIM_FLAGS = (
    "runtime_effect_allowed",
    "proactive_sent",
    "scheduler_enabled",
    "live_delivery_allowed",
    "scheduler_activation_allowed",
    "manager_context_injected",
    "manager_context_packet_changed",
    "recommendation_served",
    "rescue_committed",
    "proposal_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "mutation_changed",
)


def apply_no_send_candidate_interaction(
    *,
    no_send_candidate: Mapping[str, Any],
    action: Action,
    dismiss_reason: str | None = None,
    snooze_minutes: int | None = None,
    undo_token: str | None = None,
) -> dict[str, Any]:
    blockers = [
        *_candidate_blockers(no_send_candidate),
        *_action_blockers(
            no_send_candidate=no_send_candidate,
            action=action,
            dismiss_reason=dismiss_reason,
            snooze_minutes=snooze_minutes,
            undo_token=undo_token,
        ),
    ]
    return {
        "artifact_type": "proactive_no_send_interaction_model_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/runtime",
        "consumer": "future_proactive_user_control_activation_review",
        "retirement_trigger": "approved_proactive_scheduler_runtime_activation_plan",
        "action": action,
        "trigger_type": str(no_send_candidate.get("trigger_type") or ""),
        "dismiss_reason": dismiss_reason if action == "dismiss" else None,
        "blockers": blockers,
        "interaction_state": _blocked_state()
        if blockers
        else _interaction_state(
            no_send_candidate=no_send_candidate,
            action=action,
            snooze_minutes=snooze_minutes,
        ),
        "next_signal_required": str(no_send_candidate.get("next_signal_required") or ""),
        "non_claims": [
            "not_user_facing_interaction",
            "not_durable_suppression",
            "not_durable_snooze",
            "not_notification_delivery",
            "not_runtime_mutation",
        ],
        **dict(FALSE_FLAGS),
    }


def _candidate_blockers(candidate: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if candidate.get("artifact_type") != "proactive_no_send_nudge_candidate":
        blockers.append("no_send_candidate.unsupported_artifact_type")
    if candidate.get("status") != "pass":
        blockers.append("no_send_candidate.status_not_pass")
    for flag in CLAIM_FLAGS:
        if candidate.get(flag) is True:
            blockers.append(f"no_send_candidate.{flag}")
    return blockers


def _action_blockers(
    *,
    no_send_candidate: Mapping[str, Any],
    action: str,
    dismiss_reason: str | None,
    snooze_minutes: int | None,
    undo_token: str | None,
) -> list[str]:
    if action == "dismiss":
        return _dismiss_blockers(no_send_candidate, dismiss_reason)
    if action == "snooze":
        return _snooze_blockers(no_send_candidate, snooze_minutes)
    if action == "undo":
        return _undo_blockers(no_send_candidate, undo_token)
    return [f"unsupported_action:{action}"]


def _dismiss_blockers(
    candidate: Mapping[str, Any],
    dismiss_reason: str | None,
) -> list[str]:
    choices = {str(choice) for choice in candidate.get("dismiss_reason_choices") or []}
    reason = str(dismiss_reason or "")
    if reason in choices:
        return []
    return [f"dismiss_reason_not_allowed:{reason}"]


def _snooze_blockers(
    candidate: Mapping[str, Any],
    snooze_minutes: int | None,
) -> list[str]:
    minutes = snooze_minutes if isinstance(snooze_minutes, int) else 0
    max_minutes = _snooze_window_minutes(candidate)
    if minutes <= 0:
        return ["snooze_minutes_missing"]
    if minutes > max_minutes:
        return [f"snooze_minutes_exceed_candidate_window:{minutes}"]
    return []


def _undo_blockers(candidate: Mapping[str, Any], undo_token: str | None) -> list[str]:
    allowed = str(candidate.get("undo_scope") or "")
    token = str(undo_token or "")
    if token == allowed:
        return []
    return [f"undo_scope_not_allowed:{token}"]


def _interaction_state(
    *,
    no_send_candidate: Mapping[str, Any],
    action: str,
    snooze_minutes: int | None,
) -> dict[str, Any]:
    scope = str(no_send_candidate.get("undo_scope") or "")
    if action == "undo":
        return {
            "candidate_visible": True,
            "dismissed": False,
            "snoozed_until": None,
            "undo_available": False,
            "scope": scope,
        }
    return {
        "candidate_visible": False,
        "dismissed": action == "dismiss",
        "snoozed_until": f"duration:{snooze_minutes}m"
        if action == "snooze"
        else None,
        "undo_available": True,
        "scope": scope,
    }


def _blocked_state() -> dict[str, Any]:
    return {
        "candidate_visible": True,
        "dismissed": False,
        "snoozed_until": None,
        "undo_available": False,
        "scope": "current_no_send_candidate_only",
    }


def _snooze_window_minutes(candidate: Mapping[str, Any]) -> int:
    value = candidate.get("snooze_window")
    if not isinstance(value, Mapping):
        return 0
    minutes = value.get("minutes")
    return minutes if isinstance(minutes, int) else 0


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "apply_no_send_candidate_interaction",
]
