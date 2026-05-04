from __future__ import annotations

from app.rescue.domain.shadow_context import RescueContextFixture
from app.rescue.domain.shadow_trigger import RescueTriggerDetectionResult
from app.rescue.domain.shadow_viability import (
    RescueViabilityBand,
    RescueViabilityHarmIfWrong,
    RescueViabilityRecommendedAction,
    RescueViabilityScoreResult,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.shadow_viability_scorer"
)

STRICT_PLAN_RESISTANT_USAGE_STYLES = {
    "strict_plan_averse",
    "soft_first",
    "ignores_strict_plans",
    "low_friction_only",
}


def score_rescue_viability(
    context: RescueContextFixture,
    trigger: RescueTriggerDetectionResult,
) -> RescueViabilityScoreResult:
    reasons = list(trigger.trigger_reason_codes)

    if not (context.current_budget.active and context.active_body_plan.active):
        return _result(
            score=0.0,
            band="not_needed",
            reasons=[*reasons, "no_active_plan"],
            confidence=0.9,
            harm="low",
            action="discard",
        )

    if (
        context.open_proposals.has_open_rescue_like_proposal
        or context.open_proposals.has_open_calibration_proposal
    ):
        return _result(
            score=0.2,
            band="low",
            reasons=[*reasons, "existing_open_proposal"],
            confidence=0.8,
            harm="medium",
            action="keep_shadowing",
        )

    if _small_overshoot_with_healthy_weekly_deficit(context):
        return _result(
            score=0.0,
            band="not_needed",
            reasons=[*reasons, "weekly_deficit_still_ok"],
            confidence=0.85,
            harm="low",
            action="discard",
        )

    score = 0.0
    confidence = 0.75
    harm: RescueViabilityHarmIfWrong = "medium"

    today_overshoot = context.overshoot_summary.today_overshoot_kcal
    weekly_overshoot = context.overshoot_summary.weekly_overshoot_kcal
    weekly_gap = context.deficit_summary.weekly_deficit_gap_kcal
    recent_overshoot_days = context.overshoot_summary.recent_overshoot_days

    if today_overshoot >= 500:
        score += 0.45
        reasons.append("overshoot_large")
    elif today_overshoot > 0:
        score += 0.18 if today_overshoot > 100 else 0.05
        reasons.append("overshoot_small" if today_overshoot <= 100 else "overshoot_moderate")

    if weekly_gap >= 500 or context.deficit_summary.weekly_deficit_posture == "off_track":
        score += 0.2
    elif weekly_gap <= 0 or context.deficit_summary.weekly_deficit_posture in {"on_track", "ahead"}:
        score -= 0.1
        reasons.append("weekly_deficit_still_ok")

    if weekly_overshoot >= 700:
        score += 0.15

    if recent_overshoot_days >= 3:
        score += 0.15
        reasons.append("repeated_overshoot")

    if context.rescue_history_summary.recent_rescue_count > 0:
        score += min(context.rescue_history_summary.recent_rescue_count * 0.04, 0.12)
    if context.rescue_history_summary.history_quality == "sparse":
        confidence -= 0.05
        reasons.append("rescue_history_sparse")

    if context.adherence_summary.recent_low_adherence:
        score += 0.08

    low_logging_quality = _has_low_logging_quality(context)
    if low_logging_quality:
        score -= 0.1
        confidence -= 0.25
        reasons.append("low_logging_quality")

    calibration_uncertain = context.calibration_posture.uncertain or (
        context.calibration_posture.posture == "uncertain"
        and context.calibration_posture.confidence < 0.35
    )
    if calibration_uncertain:
        score -= 0.08
        confidence -= 0.15
        reasons.append("recent_calibration_uncertain")

    strictness_risk = _has_strict_plan_resistance(context)
    if strictness_risk:
        score -= 0.08
        confidence -= 0.1
        harm = "high"
        reasons.append("user_likely_dislikes_strict_plans")

    aggressive_risk = _risks_overly_aggressive_correction(context)
    if aggressive_risk:
        score -= 0.08
        harm = "high"
        reasons.append("rescue_risk_too_aggressive")

    if not trigger.should_generate_rescue_candidate:
        score = min(score, 0.2)

    score = _clamp(score)
    if calibration_uncertain or aggressive_risk:
        score = min(score, 0.59)

    band = _band_for_score(score)
    action = _action_for_result(
        band=band,
        confidence=_clamp(confidence),
        low_logging_quality=low_logging_quality,
        calibration_uncertain=calibration_uncertain,
        strictness_risk=strictness_risk,
        aggressive_risk=aggressive_risk,
    )

    return _result(
        score=score,
        band=band,
        reasons=reasons,
        confidence=confidence,
        harm=harm,
        action=action,
    )


def _small_overshoot_with_healthy_weekly_deficit(context: RescueContextFixture) -> bool:
    return (
        0 < context.overshoot_summary.today_overshoot_kcal <= 100
        and context.overshoot_summary.weekly_overshoot_kcal == 0
        and context.deficit_summary.weekly_deficit_gap_kcal <= 0
        and context.deficit_summary.weekly_deficit_posture in {"on_track", "ahead"}
    )


def _has_low_logging_quality(context: RescueContextFixture) -> bool:
    return (
        context.recent_committed_meals.logging_coverage < 0.6
        or context.adherence_summary.logging_quality in {"low", "unknown"}
    )


def _has_strict_plan_resistance(context: RescueContextFixture) -> bool:
    return (
        context.adherence_summary.user_strictness_tolerance == "low"
        or context.adherence_summary.app_usage_style in STRICT_PLAN_RESISTANT_USAGE_STYLES
        or context.rescue_history_summary.ignored_strict_plans
    )


def _risks_overly_aggressive_correction(context: RescueContextFixture) -> bool:
    daily_budget = context.current_budget.daily_budget_kcal
    max_five_day_recovery = daily_budget * 0.15 * 5
    if context.overshoot_summary.today_overshoot_kcal > max_five_day_recovery:
        return True
    target = context.active_body_plan.daily_target_kcal
    floor = context.active_body_plan.safety_floor_kcal
    return target - floor < 250


def _band_for_score(score: float) -> RescueViabilityBand:
    if score <= 0.0:
        return "not_needed"
    if score < 0.35:
        return "low"
    if score < 0.7:
        return "medium"
    return "high"


def _action_for_result(
    *,
    band: RescueViabilityBand,
    confidence: float,
    low_logging_quality: bool,
    calibration_uncertain: bool,
    strictness_risk: bool,
    aggressive_risk: bool,
) -> RescueViabilityRecommendedAction:
    if band == "not_needed":
        return "discard"
    if calibration_uncertain:
        return "ask_user"
    if strictness_risk or aggressive_risk:
        return "ask_user"
    if low_logging_quality:
        return "ask_user" if band in {"medium", "high"} else "keep_shadowing"
    if band in {"medium", "high"} and confidence >= 0.7:
        return "promote_later"
    return "keep_shadowing"


def _result(
    *,
    score: float,
    band: RescueViabilityBand,
    reasons: list[str],
    confidence: float,
    harm: RescueViabilityHarmIfWrong,
    action: RescueViabilityRecommendedAction,
) -> RescueViabilityScoreResult:
    return RescueViabilityScoreResult(
        rescue_viability_score=round(_clamp(score), 3),
        viability_band=band,
        reason_codes=_unique(reasons),
        confidence=round(_clamp(confidence), 3),
        harm_if_wrong=harm,
        recommended_action=action,
    )


def _clamp(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "score_rescue_viability",
]
