from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Mapping

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
CopyPosture = Literal["not_generated", "invitation", "informational", "directive", "shaming", "fake_precision", "decision_or_mutation"]


LEVEL_2_TRIGGERS = {"pre_meal_budget_awareness", "overshoot_risk", "calibration_insight", "recommendation_prompt"}
LEVEL_2_REQUIRED = ["higher_data_sufficiency", "lower_frequency", "stronger_user_benefit", "explicit_suppression_reason_if_skipped"]
LATER_ONLY_TRIGGERS = {"rescue_nudge", "location_based_food_push", "strict_multi_day_correction", "emotional_coaching_nudge", "memory_driven_intervention"}
SAFE_COPY_POSTURES = {"invitation", "informational"}
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
    candidate_copy: str | None = None
    copy_posture: CopyPosture = "not_generated"
    copy_has_user_agency: bool = True
    copy_has_no_shame: bool = True
    copy_uncertainty_honest: bool = True
    copy_invitation_only: bool = True
    confidence: float = 0.0
    annoyance_risk: RiskLevel = "medium"
    harm_if_wrong: RiskLevel = "low"
    recommendation_prompt_review: dict[str, Any] | None = None
    rescue_nudge_review: dict[str, Any] | None = None


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
    suppression_reasons.extend(_recommendation_prompt_suppression_reasons(item))
    suppression_reasons.extend(_copy_suppression_reasons(item))
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
        "review_decision": _review_decision(
            suppression_status=suppression_status,
            suppression_reasons=suppression_reasons,
        ),
        "cooldown_checked": True,
        "quiet_hours_checked": True,
        "user_agency_copy": "You can ignore this or change proactive settings any time.",
        "no_shame_copy": "This is informational only, with no judgment or blame.",
        "sent": False,
        "runtime_effect_allowed": False,
        "permission_posture": _permission_posture(item.trigger_type),
        "interrupt_cost": _interrupt_cost(item.delivery_surface),
        "interaction_feedback": _interaction_feedback(item),
        "copy_review": _copy_review(item),
        "user_callable_when_suppressed": True,
        "stay_silent_until_signal": _stay_silent_until_signal(item),
        "proactive_sent": False,
    }
    if level_2_gate is not None:
        row["level_2_gate"] = level_2_gate
    if item.trigger_type == "recommendation_prompt":
        row["recommendation_prompt_review"] = _recommendation_prompt_review(item)
    if item.trigger_type == "rescue_nudge":
        row["rescue_nudge_review"] = _rescue_nudge_review(item)
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


def _recommendation_prompt_suppression_reasons(item: ProactiveNoSendShadowInput) -> list[str]:
    if item.trigger_type != "recommendation_prompt":
        return []
    review = _recommendation_prompt_review(item)
    if any(review.get(flag) is True for flag in ("actual_candidates_included", "candidate_ids_exposed", "runtime_effect_allowed", "recommendation_served", "proactive_sent", "scheduler_enabled", "live_delivery_allowed", "scheduler_activation_allowed", "manager_context_injected")):
        return ["recommendation_prompt_review_blocked"]
    status = str(review.get("status") or "")
    if status == "candidate_for_human_review":
        return []
    if status == "suppressed":
        return [str(reason) for reason in review.get("suppression_reasons") or []] or ["recommendation_prompt_review_suppressed"]
    if status == "blocked":
        return ["recommendation_prompt_review_blocked"]
    return ["recommendation_prompt_review_required"]


def _recommendation_prompt_review(item: ProactiveNoSendShadowInput) -> dict[str, Any]:
    review = item.recommendation_prompt_review
    if not isinstance(review, Mapping):
        return {}
    allowed = ("source_report_used", "status", "recommendation_pool_decision", "prompt_posture", "suppression_reasons", "blockers", "actual_candidates_included", "candidate_ids_exposed", "runtime_effect_allowed", "recommendation_served", "proactive_sent", "scheduler_enabled", "live_delivery_allowed", "scheduler_activation_allowed", "manager_context_injected", "review_decision")
    return {key: review[key] for key in allowed if key in review}


def _rescue_nudge_review(item: ProactiveNoSendShadowInput) -> dict[str, Any]:
    review = item.rescue_nudge_review
    if not isinstance(review, Mapping):
        return {}
    allowed = ("source_projection_used", "status", "prompt_posture", "suppression_reasons", "blockers", "rescue_history_context_available", "adherence_context_available", "suppression_context_count", "history_review_notes", "runtime_effect_allowed", "rescue_committed", "proposal_committed", "day_budget_mutated", "body_plan_mutated", "meal_thread_mutated", "durable_memory_written", "proactive_sent", "scheduler_enabled", "live_delivery_allowed", "scheduler_activation_allowed", "manager_context_injected", "recommendation_served", "review_decision")
    return {key: review[key] for key in allowed if key in review}


def _copy_suppression_reasons(item: ProactiveNoSendShadowInput) -> list[str]:
    if not _candidate_copy_provided(item):
        return []

    reasons: list[str] = []
    if item.copy_posture not in SAFE_COPY_POSTURES:
        reasons.append("copy_posture_not_safe")
    if not item.copy_has_user_agency:
        reasons.append("copy_user_agency_required")
    if not item.copy_has_no_shame:
        reasons.append("copy_no_shame_required")
    if not item.copy_uncertainty_honest:
        reasons.append("copy_uncertainty_honesty_required")
    if not item.copy_invitation_only:
        reasons.append("copy_invitation_boundary_required")
    return reasons


def _candidate_copy_provided(item: ProactiveNoSendShadowInput) -> bool:
    return bool(str(item.candidate_copy or "").strip())


def _copy_review(item: ProactiveNoSendShadowInput) -> dict[str, Any]:
    reasons = _copy_suppression_reasons(item)
    return {
        "candidate_copy_provided": _candidate_copy_provided(item),
        "posture": item.copy_posture,
        "passed": not reasons,
        "checks": {"user_agency": item.copy_has_user_agency, "no_shame": item.copy_has_no_shame, "uncertainty_honest": item.copy_uncertainty_honest, "invitation_only": item.copy_invitation_only},
        "deterministic_role": "validate_or_suppress_only",
        "llm_role": "write_or_judge_candidate_copy_before_shadow_input",
        "rewritten_by_evaluator": False,
    }


def _interaction_feedback(item: ProactiveNoSendShadowInput) -> dict[str, Any]:
    return {"ignored_count": item.ignored_count, "dismissed_count": item.dismissed_count, "accepted_count": item.accepted_count, "explicit_trigger_opt_out": item.explicit_trigger_opt_out, "adaptation": _feedback_adaptation(item)}


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
    review_decision_counts: dict[str, int] = {}
    for row in rows:
        review_decision = row.get("review_decision")
        if not isinstance(review_decision, dict):
            continue
        status = str(review_decision.get("status") or "unknown")
        review_decision_counts[status] = review_decision_counts.get(status, 0) + 1
    return {
        "trigger_count": len(rows),
        "candidate_for_human_review_trigger_types": reviewable,
        "suppressed_trigger_types": suppressed,
        "deferred_later_only_trigger_types": deferred,
        "review_decision_counts": review_decision_counts,
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
        "copy_suppressed_count": sum(
            1
            for row in rows
            if row.get("suppression_status") == "suppressed"
            and any(str(reason).startswith("copy_") for reason in list(row.get("suppression_reasons") or []))
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


def _review_decision(*, suppression_status: str, suppression_reasons: list[str]) -> dict[str, str]:
    if suppression_status == "deferred_later_only":
        return {
            "status": "deferred_later_only",
            "reviewer_next_step": "do_not_promote_later_only",
        }
    if any(reason.startswith("copy_") for reason in suppression_reasons):
        return {
            "status": "suppressed_copy_safety",
            "reviewer_next_step": "revise_candidate_copy_before_review",
        }
    if any(reason.startswith("permission_") for reason in suppression_reasons):
        return {
            "status": "suppressed_permission",
            "reviewer_next_step": "keep_silent_until_consent_or_safe_surface",
        }
    if any(
        reason.startswith("interaction_feedback_") or reason == "explicit_trigger_opt_out"
        for reason in suppression_reasons
    ):
        return {
            "status": "suppressed_feedback",
            "reviewer_next_step": "keep_silent_until_user_engagement_or_cooldown",
        }
    if suppression_status == "suppressed":
        return {
            "status": "suppressed_context_or_data",
            "reviewer_next_step": "collect_more_context_or_evidence",
        }
    return {
        "status": "candidate_for_human_review",
        "reviewer_next_step": "review_copy_context_and_permission_before_live_plan",
    }


def _add_trigger_boundaries(row: dict[str, Any], trigger_type: str) -> None:
    if trigger_type == "recommendation_prompt":
        row["recommendation_prompt_boundary"] = {
            "allowed": ["candidate_invitation_only"],
            "forbidden": ["output_actual_ranked_food_candidates", "query_live_menu_or_search", "create_intake_hint_packet", "serve_recommendation_result"],
        }
        row["recommendation_served"] = False
        row["intake_hint_packet_created"] = False
    if trigger_type == "calibration_insight":
        row["allowed_output"] = ["offer_calibration_preview"]
        row["forbidden_output"] = ["tell_user_should_change_target", "output_specific_new_kcal_target", "mutate_body_plan"]
        row["body_plan_mutated"] = False
    if trigger_type == "rescue_nudge":
        row["allowed_output"] = ["invite_future_rescue_review"]
        row["forbidden_output"] = ["output_specific_future_deficit", "create_rescue_proposal", "mutate_day_budget_ledger"]
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
