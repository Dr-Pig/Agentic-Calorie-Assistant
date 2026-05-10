from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from app.runtime.application.proactive_no_send_nudge_candidate import (
    build_no_send_nudge_candidate,
)
from app.runtime.contracts.pending_meal_intent import PendingMealIntent
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_pending_meal_followup_shadow"
)

CONTROL_CLAIM_FLAGS = (
    "runtime_effect_allowed",
    "proactive_sent",
    "scheduler_enabled",
    "live_delivery_allowed",
    "scheduler_activation_allowed",
    "manager_context_injected",
    "recommendation_served",
    "intake_commit_requested",
    "pending_intent_mutated",
)

FALSE_FLAGS = {
    "runtime_effect_allowed": False,
    "proactive_sent": False,
    "scheduler_enabled": False,
    "live_delivery_allowed": False,
    "scheduler_activation_allowed": False,
    "manager_context_injected": False,
    "recommendation_served": False,
    "intake_commit_requested": False,
    "pending_intent_mutated": False,
    "user_facing_behavior_changed": False,
    "mutation_changed": False,
}


def build_pending_meal_followup_no_send_shadow(
    *,
    pending_meal_intent: PendingMealIntent,
    evaluation_time: datetime,
    control_context: Mapping[str, Any],
    wake_source: str = "manual_shadow_review",
    delivery_surface: str = "chat_open",
) -> dict[str, Any]:
    blockers = _pre_candidate_blockers(
        pending_meal_intent=pending_meal_intent,
        evaluation_time=evaluation_time,
        control_context=control_context,
    )
    source_review = _source_review(pending_meal_intent, active=not blockers)
    candidate = None
    if not blockers:
        candidate = build_no_send_nudge_candidate(
            trigger_type="pending_meal_followup",
            candidate_source=source_review,
            user_control_model=control_context,
            wake_source=wake_source,
        )
        blockers.extend(candidate.get("blockers") or [])

    return {
        "artifact_type": "proactive_pending_meal_followup_shadow",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/runtime",
        "consumer": "future_chat_first_pending_meal_followup_review",
        "retirement_trigger": "approved_proactive_pending_meal_runtime_activation",
        "pending_meal_intent_trace": pending_meal_intent.to_trace_payload(),
        "followup_source_review": source_review,
        "no_send_candidate": None if blockers and candidate is None else candidate,
        "simulation_input": None
        if blockers
        else _simulation_input(
            evaluation_time=evaluation_time,
            wake_source=wake_source,
            delivery_surface=delivery_surface,
        ),
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def _pre_candidate_blockers(
    *,
    pending_meal_intent: PendingMealIntent,
    evaluation_time: datetime,
    control_context: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if not pending_meal_intent.is_active_at(evaluation_time):
        blockers.append("pending_meal_intent.not_active")
    if pending_meal_intent.canonical_write_authorized is True:
        blockers.append("pending_meal_intent.canonical_write_authorized")
    blockers.extend(
        f"control_context.{flag}"
        for flag in CONTROL_CLAIM_FLAGS
        if control_context.get(flag) is True
    )
    return blockers


def _source_review(intent: PendingMealIntent, *, active: bool) -> dict[str, Any]:
    status = "active_pending_intent" if active else "inactive_pending_intent"
    return {
        "source_pending_intent_used": active,
        "status": status,
        "prompt_posture": "chat_first_followup_question_only",
        "pending_intent_status": intent.status,
        "source_surface": intent.source_surface,
        "runtime_effect_allowed": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "live_delivery_allowed": False,
        "scheduler_activation_allowed": False,
        "manager_context_injected": False,
        "recommendation_served": False,
        "intake_commit_requested": False,
        "pending_intent_mutated": False,
    }


def _simulation_input(
    *,
    evaluation_time: datetime,
    wake_source: str,
    delivery_surface: str,
) -> dict[str, Any]:
    return {
        "trigger_type": "pending_meal_followup",
        "now": evaluation_time,
        "data_sufficiency_status": "basic",
        "user_benefit_strength": "moderate",
        "minimum_evidence_ready": True,
        "minimum_quality_ready": True,
        "user_allows_proactive": True,
        "delivery_surface": delivery_surface,
        "wake_source": wake_source,
        "user_relevant_reason": "pending_intent_still_active",
        "copy_posture": "not_generated",
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_pending_meal_followup_no_send_shadow",
]
