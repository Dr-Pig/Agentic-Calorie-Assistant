from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.runtime.application.proactive_deterministic_gate import (
    evaluate_proactive_deterministic_gate,
)
from app.runtime.contracts.proactive_gate import ProactiveGateInput
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_no_send_shadow_evaluator"
)


DataSufficiencyStatus = Literal["missing", "basic", "higher"]
UserBenefitStrength = Literal["weak", "moderate", "strong"]
RiskLevel = Literal["low", "medium", "high"]
DeliverySurface = Literal["background", "app_open", "chat_open"]
FeedbackAdaptation = Literal["none", "lower_frequency", "suppress_once", "category_suppressed"]
WakeSource = Literal["scheduled_check", "state_threshold", "event_driven", "app_open", "manual_shadow_review"]


LEVEL_2_TRIGGERS = {
    "pre_meal_budget_awareness",
    "overshoot_risk",
    "calibration_insight",
    "recommendation_prompt",
}
LEVEL_2_REQUIRED = [
    "higher_data_sufficiency",
    "lower_frequency",
    "stronger_user_benefit",
    "explicit_suppression_reason_if_skipped",
]
LATER_ONLY_TRIGGERS = {
    "rescue_nudge",
    "location_based_food_push",
    "strict_multi_day_correction",
    "emotional_coaching_nudge",
    "memory_driven_intervention",
}
PERMISSION_POSTURE_BY_TRIGGER = {
    "weekly_insight": "user_expected",
    "meal_reminder": "user_expected",
    "low_frequency_weight_log_reminder": "user_opted_in",
    "weight_reminder": "user_opted_in",
    "missing_log_reminder_with_cooldown": "user_expected",
    "recommendation_prompt": "app_open_only",
    "pre_meal_budget_awareness": "no_push_allowed",
    "recommendation_nudge_meal_time": "no_push_allowed",
    "recommendation_nudge_nearby": "no_push_allowed",
    "swap_suggestion": "no_push_allowed",
    "overshoot_risk": "later_requires_explicit_consent",
    "calibration_insight": "later_requires_explicit_consent",
    "calibration_nudge": "later_requires_explicit_consent",
    "rescue_nudge": "later_requires_explicit_consent",
    "location_based_food_push": "later_requires_explicit_consent",
    "strict_multi_day_correction": "later_requires_explicit_consent",
    "emotional_coaching_nudge": "later_requires_explicit_consent",
    "memory_driven_intervention": "later_requires_explicit_consent",
}


class ProactiveNoSendShadowInput(BaseModel):
    trigger_type: str
    local_time: str | None = None
    data_sufficiency_status: DataSufficiencyStatus = "basic"
    user_benefit_strength: UserBenefitStrength = "moderate"
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    suppressed_trigger_types: list[str] = Field(default_factory=list)
    now: datetime | None = None
    cooldown_until: datetime | None = None
    recent_send_count: int = 0
    max_recent_send_count: int | None = None
    minimum_evidence_ready: bool = True
    minimum_quality_ready: bool = True
    user_allows_proactive: bool = True
    trigger_opt_in_ready: bool = False
    lower_frequency_ready: bool = False
    explicit_consent_ready: bool = False
    delivery_surface: DeliverySurface = "background"
    ignored_count: int = 0
    dismissed_count: int = 0
    accepted_count: int = 0
    explicit_trigger_opt_out: bool = False
    wake_source: WakeSource = "manual_shadow_review"
    user_relevant_reason: str | None = None
    confidence: float = 0.0
    annoyance_risk: RiskLevel = "medium"
    harm_if_wrong: RiskLevel = "low"


def build_proactive_no_send_simulation(
    inputs: list[ProactiveNoSendShadowInput],
) -> dict[str, Any]:
    trigger_evaluations = [_evaluate_trigger(item) for item in inputs]
    return {
        "artifact_type": "proactive_no_send_simulation",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "claim_scope": "no_send",
        "shadow_mode": True,
        "real_runtime_effect": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "manager_context_injected": False,
        "durable_memory_written": False,
        "recommendation_served": False,
        "rescue_committed": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "summary": _summary(trigger_evaluations),
        "trigger_evaluations": trigger_evaluations,
    }


def _evaluate_trigger(item: ProactiveNoSendShadowInput) -> dict[str, Any]:
    gate_result = evaluate_proactive_deterministic_gate(_to_gate_input(item))
    suppression_reasons = [gate_result.skip_reason] if gate_result.skip_reason else []
    level_2_gate = None
    if item.trigger_type in LEVEL_2_TRIGGERS:
        level_2_reasons = _level_2_suppression_reasons(item)
        suppression_reasons.extend(level_2_reasons)
        level_2_gate = {
            "required": LEVEL_2_REQUIRED,
            "passed": not level_2_reasons,
        }
    suppression_reasons.extend(_permission_suppression_reasons(item))
    suppression_reasons.extend(_interaction_feedback_suppression_reasons(item))
    suppression_reasons.extend(_reason_suppression_reasons(item))
    if _deferred_later_only(item) and "later_only_trigger_not_live_eligible" not in suppression_reasons:
        suppression_reasons.append("later_only_trigger_not_live_eligible")

    suppression_status = "not_suppressed" if gate_result.allowed and not suppression_reasons else "suppressed"
    if _deferred_later_only(item):
        suppression_status = "deferred_later_only"

    row: dict[str, Any] = {
        "trigger_type": item.trigger_type,
        "wake_source": item.wake_source,
        "ux_intent": _ux_intent(item.trigger_type),
        "user_benefit": _user_benefit(item.trigger_type),
        "why_now": _why_now(item),
        "data_sufficiency_status": item.data_sufficiency_status,
        "confidence": item.confidence,
        "annoyance_risk": item.annoyance_risk,
        "harm_if_wrong": item.harm_if_wrong,
        "suppression_status": suppression_status,
        "suppression_reasons": suppression_reasons,
        "cooldown_checked": True,
        "quiet_hours_checked": True,
        "user_agency_copy": "You can ignore this or change proactive settings any time.",
        "no_shame_copy": "This is informational only, with no judgment or blame.",
        "sent": False,
        "runtime_effect_allowed": False,
        "permission_posture": _permission_posture(item.trigger_type),
        "interrupt_cost": _interrupt_cost(item.delivery_surface),
        "interaction_feedback": _interaction_feedback(item),
        "user_callable_when_suppressed": True,
        "stay_silent_until_signal": _stay_silent_until_signal(item),
    }
    if level_2_gate is not None:
        row["level_2_gate"] = level_2_gate
    _add_trigger_boundaries(row, item.trigger_type)
    return row


def _to_gate_input(item: ProactiveNoSendShadowInput) -> ProactiveGateInput:
    return ProactiveGateInput(
        trigger_type=item.trigger_type,
        local_time=item.local_time,
        quiet_hours_start=item.quiet_hours_start,
        quiet_hours_end=item.quiet_hours_end,
        suppressed_trigger_types=item.suppressed_trigger_types,
        now=item.now,
        cooldown_until=item.cooldown_until,
        recent_send_count=item.recent_send_count,
        max_recent_send_count=item.max_recent_send_count,
        minimum_evidence_ready=item.minimum_evidence_ready,
        minimum_quality_ready=item.minimum_quality_ready,
        user_allows_proactive=item.user_allows_proactive,
    )


def _level_2_suppression_reasons(item: ProactiveNoSendShadowInput) -> list[str]:
    reasons: list[str] = []
    if item.data_sufficiency_status != "higher":
        reasons.append("level_2_higher_data_sufficiency_required")
    if not item.lower_frequency_ready:
        reasons.append("level_2_lower_frequency_required")
    if item.user_benefit_strength != "strong":
        reasons.append("level_2_stronger_user_benefit_required")
    return reasons


def _deferred_later_only(item: ProactiveNoSendShadowInput) -> bool:
    return item.trigger_type in LATER_ONLY_TRIGGERS or (
        item.trigger_type not in PERMISSION_POSTURE_BY_TRIGGER
        and item.harm_if_wrong == "high"
    )


def _permission_suppression_reasons(item: ProactiveNoSendShadowInput) -> list[str]:
    posture = _permission_posture(item.trigger_type)
    if posture == "user_opted_in" and not item.trigger_opt_in_ready:
        return ["permission_trigger_opt_in_required"]
    if posture == "app_open_only" and item.delivery_surface != "app_open":
        return ["permission_app_open_required"]
    if posture == "no_push_allowed" and item.delivery_surface == "background":
        return ["permission_no_push_allowed"]
    if posture == "later_requires_explicit_consent" and not item.explicit_consent_ready:
        return ["permission_explicit_consent_required"]
    return []


def _interaction_feedback_suppression_reasons(item: ProactiveNoSendShadowInput) -> list[str]:
    reasons: list[str] = []
    if item.explicit_trigger_opt_out:
        reasons.append("explicit_trigger_opt_out")
    if item.dismissed_count > 0:
        reasons.append("interaction_feedback_dismissed_recently")
    if item.ignored_count >= 2:
        reasons.append("interaction_feedback_lower_frequency_required")
    return reasons


def _reason_suppression_reasons(item: ProactiveNoSendShadowInput) -> list[str]:
    if item.wake_source == "manual_shadow_review":
        return []
    if not str(item.user_relevant_reason or "").strip():
        return ["missing_user_relevant_reason"]
    return []


def _interaction_feedback(item: ProactiveNoSendShadowInput) -> dict[str, Any]:
    return {
        "ignored_count": item.ignored_count,
        "dismissed_count": item.dismissed_count,
        "accepted_count": item.accepted_count,
        "explicit_trigger_opt_out": item.explicit_trigger_opt_out,
        "adaptation": _feedback_adaptation(item),
    }


def _feedback_adaptation(item: ProactiveNoSendShadowInput) -> FeedbackAdaptation:
    if item.explicit_trigger_opt_out:
        return "category_suppressed"
    if item.dismissed_count > 0:
        return "suppress_once"
    if item.ignored_count >= 2:
        return "lower_frequency"
    return "none"


def _stay_silent_until_signal(item: ProactiveNoSendShadowInput) -> str:
    if _feedback_adaptation(item) == "none":
        return "not_applicable"
    return "next_user_engagement_or_cooldown_window"


def _interrupt_cost(delivery_surface: DeliverySurface) -> RiskLevel:
    if delivery_surface == "background":
        return "high"
    if delivery_surface == "app_open":
        return "low"
    return "medium"


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    suppressed = {
        str(row["trigger_type"]): list(row["suppression_reasons"])
        for row in rows
        if row.get("suppression_status") == "suppressed"
    }
    deferred = [
        str(row["trigger_type"])
        for row in rows
        if row.get("suppression_status") == "deferred_later_only"
    ]
    reviewable = [
        str(row["trigger_type"])
        for row in rows
        if row.get("suppression_status") == "not_suppressed"
    ]
    suppressed_reasons = [
        str(reason)
        for row in rows
        if row.get("suppression_status") == "suppressed"
        for reason in list(row.get("suppression_reasons") or [])
    ]
    return {
        "trigger_count": len(rows),
        "candidate_for_human_review_trigger_types": reviewable,
        "suppressed_trigger_types": suppressed,
        "deferred_later_only_trigger_types": deferred,
        "suppressed_count": len(suppressed),
        "later_only_count": len(deferred),
        "permission_suppressed_count": sum(
            1 for reason in suppressed_reasons if reason.startswith("permission_")
        ),
        "interaction_feedback_suppressed_count": sum(
            1
            for reason in suppressed_reasons
            if reason.startswith("interaction_feedback_") or reason == "explicit_trigger_opt_out"
        ),
        "level_2_suppressed_count": sum(
            1 for reason in suppressed_reasons if reason.startswith("level_2_")
        ),
        "live_delivery_allowed": False,
        "scheduler_activation_allowed": False,
        "promotion_blockers": [
            "human_review_required_before_live_delivery",
            "live_scheduler_not_enabled",
            "no_send_shadow_only",
        ],
    }


def _permission_posture(trigger_type: str) -> str:
    return PERMISSION_POSTURE_BY_TRIGGER.get(trigger_type, "no_push_allowed")


def _add_trigger_boundaries(row: dict[str, Any], trigger_type: str) -> None:
    if trigger_type == "recommendation_prompt":
        row["recommendation_prompt_boundary"] = {
            "allowed": ["candidate_invitation_only"],
            "forbidden": [
                "output_actual_ranked_food_candidates",
                "query_live_menu_or_search",
                "create_intake_hint_packet",
                "serve_recommendation_result",
            ],
        }
        row["recommendation_served"] = False
        row["intake_hint_packet_created"] = False
    if trigger_type == "calibration_insight":
        row["allowed_output"] = ["offer_calibration_preview"]
        row["forbidden_output"] = [
            "tell_user_should_change_target",
            "output_specific_new_kcal_target",
            "mutate_body_plan",
        ]
        row["body_plan_mutated"] = False
    if trigger_type == "rescue_nudge":
        row["allowed_output"] = ["invite_future_rescue_review"]
        row["forbidden_output"] = [
            "output_specific_future_deficit",
            "create_rescue_proposal",
            "mutate_day_budget_ledger",
        ]
        row["rescue_committed"] = False


def _ux_intent(trigger_type: str) -> str:
    return f"shadow_evaluate_{trigger_type}_without_delivery"


def _user_benefit(trigger_type: str) -> str:
    return f"estimate_whether_{trigger_type}_could_help_without_sending"


def _why_now(item: ProactiveNoSendShadowInput) -> str:
    reason = str(item.user_relevant_reason or "").strip()
    if reason:
        return reason
    if item.wake_source == "manual_shadow_review":
        return f"manual_shadow_review_for_{item.trigger_type}"
    return "missing_user_relevant_reason"


__all__ = [
    "ProactiveNoSendShadowInput",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_proactive_no_send_simulation",
]
