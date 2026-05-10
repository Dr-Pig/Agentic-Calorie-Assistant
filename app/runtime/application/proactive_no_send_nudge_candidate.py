from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_no_send_nudge_candidate"
)

TRIGGER_SOURCE = {
    "recommendation_prompt": {
        "kind": "recommendation_prompt_review",
        "pass_status": "candidate_for_human_review",
        "source_used_field": "source_report_used",
    },
    "rescue_nudge": {
        "kind": "rescue_nudge_review",
        "pass_status": "context_available",
        "source_used_field": "source_projection_used",
    },
    "pending_meal_followup": {
        "kind": "pending_meal_followup_review",
        "pass_status": "active_pending_intent",
        "source_used_field": "source_pending_intent_used",
    },
}
SOURCE_CLAIM_FLAGS = (
    "runtime_effect_allowed",
    "proactive_sent",
    "scheduler_enabled",
    "live_delivery_allowed",
    "scheduler_activation_allowed",
    "recommendation_served",
    "rescue_committed",
    "proposal_committed",
    "manager_context_injected",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "intake_commit_requested",
    "pending_intent_mutated",
)
FALSE_FLAGS = {
    "runtime_effect_allowed": False,
    "sent": False,
    "proactive_sent": False,
    "scheduler_enabled": False,
    "live_delivery_allowed": False,
    "scheduler_activation_allowed": False,
    "runtime_connected": False,
    "manager_context_packet_changed": False,
    "manager_context_injected": False,
    "recommendation_served": False,
    "rescue_committed": False,
    "proposal_committed": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "meal_thread_mutated": False,
    "durable_memory_written": False,
    "intake_commit_requested": False,
    "pending_intent_mutated": False,
    "mutation_changed": False,
}
NON_CLAIMS = [
    "not_notification",
    "not_user_facing_delivery",
    "not_scheduler_activation",
    "not_durable_dismiss_or_snooze_state",
    "not_runtime_mutation",
]


def build_no_send_nudge_candidate(
    *,
    trigger_type: str,
    candidate_source: Mapping[str, Any],
    user_control_model: Mapping[str, Any],
    wake_source: str = "manual_shadow_review",
) -> dict[str, Any]:
    blockers = [
        *_source_blockers(trigger_type, candidate_source),
        *_control_blockers(user_control_model),
    ]
    source_config = TRIGGER_SOURCE.get(trigger_type, {})
    return {
        "artifact_type": "proactive_no_send_nudge_candidate",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/runtime",
        "consumer": "future_proactive_scheduler_activation_review",
        "retirement_trigger": "approved_proactive_scheduler_runtime_activation_plan",
        "trigger_type": trigger_type,
        "candidate_kind": source_config.get("kind", "unsupported"),
        "wake_source": wake_source,
        "candidate_source_used": not blockers,
        "dismiss_reason_choices": _dismiss_reason_choices(user_control_model),
        "snooze_window": _snooze_window(user_control_model),
        "undo_scope": str(user_control_model.get("undo_scope") or ""),
        "next_signal_required": str(user_control_model.get("next_signal_required") or ""),
        "primary_actions": [],
        "blockers": blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _source_blockers(
    trigger_type: str,
    candidate_source: Mapping[str, Any],
) -> list[str]:
    source_config = TRIGGER_SOURCE.get(trigger_type)
    if not source_config:
        return ["candidate_source.unsupported_trigger_type"]
    blockers: list[str] = []
    if candidate_source.get(source_config["source_used_field"]) is not True:
        blockers.append(f"candidate_source.{source_config['source_used_field']}_missing")
    if candidate_source.get("status") != source_config["pass_status"]:
        blockers.append(f"candidate_source.status_not_{source_config['pass_status']}")
    for flag in SOURCE_CLAIM_FLAGS:
        if candidate_source.get(flag) is True:
            blockers.append(f"candidate_source.{flag}")
    if trigger_type == "recommendation_prompt":
        blockers.extend(_recommendation_source_blockers(candidate_source))
    return blockers


def _recommendation_source_blockers(source: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if source.get("actual_candidates_included") is True:
        blockers.append("candidate_source.actual_candidates_included")
    if source.get("candidate_ids_exposed") is True:
        blockers.append("candidate_source.candidate_ids_exposed")
    return blockers


def _control_blockers(user_control_model: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not _dismiss_reason_choices(user_control_model):
        blockers.append("user_control_model.dismiss_reason_choices_missing")
    if not _snooze_window(user_control_model):
        blockers.append("user_control_model.snooze_window_missing")
    if not str(user_control_model.get("undo_scope") or "").strip():
        blockers.append("user_control_model.undo_scope_missing")
    if not str(user_control_model.get("next_signal_required") or "").strip():
        blockers.append("user_control_model.next_signal_required_missing")
    return blockers


def _dismiss_reason_choices(user_control_model: Mapping[str, Any]) -> list[str]:
    values = user_control_model.get("dismiss_reason_choices")
    return [str(value) for value in values] if isinstance(values, list) else []


def _snooze_window(user_control_model: Mapping[str, Any]) -> dict[str, Any]:
    value = user_control_model.get("snooze_window")
    if not isinstance(value, Mapping):
        return {}
    return dict(value) if value else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_no_send_nudge_candidate",
]
