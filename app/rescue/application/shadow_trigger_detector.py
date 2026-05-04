from __future__ import annotations

from app.rescue.domain.shadow_context import RescueContextFixture
from app.rescue.domain.shadow_trigger import (
    RescueTriggerCandidate,
    RescueTriggerDetectionResult,
    RescueTriggerStrength,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.shadow_trigger_detector"
)

_STRENGTH_RANK: dict[RescueTriggerStrength, int] = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
}


def detect_rescue_trigger_candidate(
    context: RescueContextFixture,
) -> RescueTriggerDetectionResult:
    reasons: list[str] = []
    candidate: RescueTriggerCandidate = "no_rescue_needed"
    strength: RescueTriggerStrength = "none"

    today_overshoot = context.overshoot_summary.today_overshoot_kcal
    weekly_overshoot = context.overshoot_summary.weekly_overshoot_kcal
    weekly_gap = context.deficit_summary.weekly_deficit_gap_kcal
    recent_overshoot_days = context.overshoot_summary.recent_overshoot_days

    if today_overshoot >= 500:
        candidate = "today_overshoot"
        strength = "high"
        reasons.append("overshoot_large")
    elif today_overshoot > 0:
        reasons.append("overshoot_small" if today_overshoot <= 100 else "overshoot_moderate")
        strength = "low"

    weekly_off_track = weekly_gap >= 500
    if weekly_overshoot >= 700 or weekly_off_track:
        if weekly_overshoot >= 700:
            reasons.append("weekly_overshoot")
        if weekly_gap >= 500:
            reasons.append("weekly_deficit_off_track")
        if candidate == "no_rescue_needed" and weekly_overshoot >= 700:
            candidate = "weekly_overshoot"
            strength = "high" if weekly_overshoot >= 1000 else "medium"
        elif candidate == "today_overshoot":
            strength = _max_strength(strength, "high" if weekly_overshoot >= 1000 else "medium")
        elif weekly_off_track:
            strength = _max_strength(strength, "low")

    if recent_overshoot_days >= 3:
        reasons.append("repeated_overshoot")
        if candidate == "no_rescue_needed":
            candidate = "repeated_overshoot_pattern"
            strength = "medium"

    if _remaining_too_low_before_evening(context):
        reasons.append("budget_remaining_too_low_for_day_part")
        if candidate == "no_rescue_needed":
            candidate = "budget_remaining_too_low_for_day_part"
            strength = "medium"

    if context.calibration_posture.recently_accepted:
        reasons.append("accepted_calibration_recently")
        if candidate == "no_rescue_needed":
            candidate = "accepted_calibration_recently"
            strength = "low"

    if context.adherence_summary.recent_low_adherence:
        reasons.append("low_adherence_recently")
        if candidate == "no_rescue_needed":
            candidate = "low_adherence_recently"
            strength = "low"

    low_logging_quality = _has_low_logging_quality(context)
    if low_logging_quality:
        reasons.append("low_logging_quality")
        strength = _min_strength(strength, "medium")

    if _small_overshoot_with_healthy_weekly_deficit(context):
        return RescueTriggerDetectionResult(
            trigger_candidate="no_rescue_needed",
            trigger_reason_codes=_unique(reasons),
            trigger_strength=_min_strength(strength, "low"),
            should_generate_rescue_candidate=False,
            why_no_rescue_candidate="informational_only",
        )

    should_generate = candidate != "no_rescue_needed" and strength != "none"
    why_no_rescue = None

    if not (context.current_budget.active and context.active_body_plan.active):
        should_generate = False
        why_no_rescue = "no_active_budget_or_body_plan"
    elif (
        context.open_proposals.has_open_rescue_like_proposal
        or context.open_proposals.has_open_calibration_proposal
    ):
        should_generate = False
        why_no_rescue = "open_proposal_exists"
    elif not should_generate:
        why_no_rescue = "no_trigger"
    elif low_logging_quality and not _is_large_or_repeated_context(context):
        should_generate = False
        why_no_rescue = "informational_only"

    return RescueTriggerDetectionResult(
        trigger_candidate=candidate,
        trigger_reason_codes=_unique(reasons),
        trigger_strength=strength,
        should_generate_rescue_candidate=should_generate,
        why_no_rescue_candidate=why_no_rescue,
    )


def _small_overshoot_with_healthy_weekly_deficit(context: RescueContextFixture) -> bool:
    return (
        0 < context.overshoot_summary.today_overshoot_kcal <= 100
        and context.overshoot_summary.weekly_overshoot_kcal == 0
        and context.deficit_summary.weekly_deficit_gap_kcal <= 0
        and context.deficit_summary.weekly_deficit_posture in {"on_track", "ahead"}
    )


def _remaining_too_low_before_evening(context: RescueContextFixture) -> bool:
    day_part = context.current_budget.day_part.lower()
    return context.current_budget.remaining_kcal <= 100 and day_part not in {
        "evening",
        "night",
        "unknown",
    }


def _has_low_logging_quality(context: RescueContextFixture) -> bool:
    return (
        context.recent_committed_meals.logging_coverage < 0.6
        or context.adherence_summary.logging_quality in {"low", "unknown"}
    )


def _is_large_or_repeated_context(context: RescueContextFixture) -> bool:
    return (
        context.overshoot_summary.today_overshoot_kcal >= 500
        or context.overshoot_summary.weekly_overshoot_kcal >= 700
        or context.deficit_summary.weekly_deficit_gap_kcal >= 500
        or context.overshoot_summary.recent_overshoot_days >= 3
    )


def _max_strength(
    left: RescueTriggerStrength,
    right: RescueTriggerStrength,
) -> RescueTriggerStrength:
    return left if _STRENGTH_RANK[left] >= _STRENGTH_RANK[right] else right


def _min_strength(
    left: RescueTriggerStrength,
    right: RescueTriggerStrength,
) -> RescueTriggerStrength:
    return left if _STRENGTH_RANK[left] <= _STRENGTH_RANK[right] else right


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "detect_rescue_trigger_candidate",
]
