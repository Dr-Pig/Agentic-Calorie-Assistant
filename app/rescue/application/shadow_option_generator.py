from __future__ import annotations

from math import ceil
from datetime import timedelta

from app.rescue.domain.shadow_context import RescueContextFixture
from app.rescue.domain.shadow_options import (
    RescueOptionCandidate,
    RescueOptionPacket,
    RescueOptionRejection,
    RescueOptionRiskIfWrong,
    RescueOptionType,
)
from app.rescue.domain.shadow_trigger import RescueTriggerDetectionResult
from app.rescue.domain.shadow_viability import RescueViabilityScoreResult
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.shadow_option_generator"
)

STRICT_PLAN_RESISTANT_USAGE_STYLES = {
    "strict_plan_averse",
    "soft_first",
    "ignores_strict_plans",
    "low_friction_only",
}
MAX_SOFT_SPREAD_DAYS = 7
MAX_SOFT_DAILY_ADJUSTMENT_KCAL = 220


def generate_rescue_option_packet(
    context: RescueContextFixture,
    trigger: RescueTriggerDetectionResult,
    viability: RescueViabilityScoreResult,
) -> RescueOptionPacket:
    reason_codes = _unique(
        [*trigger.trigger_reason_codes, *viability.reason_codes]
    )

    if not (context.current_budget.active and context.active_body_plan.active):
        return _packet(
            reason_codes=[*reason_codes, "no_active_plan"],
            rejected=[
                _rejection(
                    reason_code="no_active_plan",
                    rationale=(
                        "A rescue option cannot be shadowed without an active "
                        "budget and body plan."
                    ),
                )
            ],
        )

    if _has_existing_open_proposal(context):
        return _packet(
            reason_codes=[*reason_codes, "existing_open_proposal"],
            rejected=[
                _rejection(
                    reason_code="existing_open_proposal",
                    rationale=(
                        "An existing rescue-like or calibration proposal is "
                        "already open."
                    ),
                )
            ],
        )

    if _should_not_generate_any_rescue_option(context, trigger, viability):
        if _small_overshoot_with_healthy_weekly_deficit(context):
            option = _informational_option(context)
            return _packet(
                candidates=[option],
                selected_option_id=option.option_id,
                reason_codes=[*reason_codes, "weekly_deficit_still_ok"],
            )
        option = _no_rescue_needed_option(context)
        return _packet(
            candidates=[option],
            selected_option_id=option.option_id,
            reason_codes=[*reason_codes, "no_rescue_needed"],
        )

    if _has_low_logging_quality(context):
        option = _ask_user_option(
            context,
            rationale=(
                "Logging coverage is too low to safely shadow an adjustment "
                "candidate."
            ),
            risk_if_wrong="medium",
        )
        return _packet(
            candidates=[option],
            selected_option_id=option.option_id,
            reason_codes=[
                *reason_codes,
                "low_logging_quality",
                "confidence_downgraded_for_logging_quality",
            ],
            rejected=[
                _rejection(
                    reason_code="low_logging_quality",
                    rationale="Adjustment candidates require better logging confidence.",
                    rejected_option_type="multi_day_spread_candidate",
                )
            ],
        )

    if _is_calibration_uncertain(context, viability):
        option = _ask_user_option(
            context,
            rationale=(
                "Recent calibration uncertainty makes automatic rescue math "
                "too likely to overcorrect."
            ),
            risk_if_wrong="high",
        )
        return _packet(
            candidates=[option],
            selected_option_id=option.option_id,
            reason_codes=[
                *reason_codes,
                "recent_calibration_uncertain",
                "overcorrection_avoided",
            ],
            rejected=[
                _rejection(
                    reason_code="recent_calibration_uncertain",
                    rationale="Calibration uncertainty blocks adjustment candidates.",
                    rejected_option_type="multi_day_spread_candidate",
                )
            ],
        )

    if _exceeds_soft_spread_capacity(context):
        option = _ask_user_option(
            context,
            rationale=(
                "The overshoot is too large for a bounded soft spread candidate "
                "without risking overcorrection."
            ),
            risk_if_wrong="high",
        )
        return _packet(
            candidates=[option],
            selected_option_id=option.option_id,
            reason_codes=[
                *reason_codes,
                "rescue_risk_too_aggressive",
                "soft_spread_capacity_exceeded",
            ],
            rejected=[
                _rejection(
                    reason_code="soft_spread_capacity_exceeded",
                    rationale="The bounded soft spread cap cannot cover this overshoot.",
                    rejected_option_type="multi_day_spread_candidate",
                )
            ],
        )

    if _viability_requires_user_context(viability):
        option = _ask_user_option(
            context,
            rationale=(
                "The rescue signal is present, but viability risk requires user "
                "context before any adjustment candidate."
            ),
            risk_if_wrong=viability.harm_if_wrong,
        )
        return _packet(
            candidates=[option],
            selected_option_id=option.option_id,
            reason_codes=[*reason_codes, "viability_requires_user_context"],
            rejected=[
                _rejection(
                    reason_code="viability_requires_user_context",
                    rationale="Viability scoring asked for user context before adjustment.",
                    rejected_option_type="multi_day_spread_candidate",
                )
            ],
        )

    if _has_strict_plan_resistance(context, viability):
        option = _next_day_soft_option(context)
        return _packet(
            candidates=[option],
            selected_option_id=option.option_id,
            reason_codes=[
                *reason_codes,
                "user_likely_dislikes_strict_plans",
                "strict_plan_resistance_softened",
            ],
            rejected=[
                _rejection(
                    reason_code="user_likely_dislikes_strict_plans",
                    rationale="Strict multi-day spread candidates are too forceful.",
                    rejected_option_type="multi_day_spread_candidate",
                )
            ],
        )

    if _is_repeated_overshoot_strategy_candidate(trigger):
        option = _ask_user_option(
            context,
            rationale=(
                "Repeated overshoot signals warrant a shadow strategy review "
                "before any adjustment candidate."
            ),
            risk_if_wrong=viability.harm_if_wrong,
        )
        return _packet(
            candidates=[option],
            selected_option_id=option.option_id,
            reason_codes=[*reason_codes, "repeated_overshoot_strategy_review"],
        )

    if _should_generate_spread_candidate(context, trigger, viability):
        option = _multi_day_spread_option(context)
        return _packet(
            candidates=[option],
            selected_option_id=option.option_id,
            reason_codes=[*reason_codes, "shadow_multi_day_spread_candidate"],
        )

    option = _no_rescue_needed_option(context)
    return _packet(
        candidates=[option],
        selected_option_id=option.option_id,
        reason_codes=[*reason_codes, "no_rescue_needed"],
    )


def _packet(
    *,
    candidates: list[RescueOptionCandidate] | None = None,
    rejected: list[RescueOptionRejection] | None = None,
    selected_option_id: str | None = None,
    reason_codes: list[str] | None = None,
) -> RescueOptionPacket:
    return RescueOptionPacket(
        option_candidates=candidates or [],
        options_rejected=rejected or [],
        selected_shadow_option_id=selected_option_id,
        reason_codes=_unique(reason_codes or []),
    )


def _informational_option(context: RescueContextFixture) -> RescueOptionCandidate:
    return RescueOptionCandidate(
        option_id=_option_id(context, "informational"),
        option_type="informational_only",
        affected_dates=[context.local_date],
        suggested_adjustment_kcal_range=(0, 0),
        rationale="Small overshoot with weekly deficit still on track.",
        risk_if_wrong="low",
    )


def _no_rescue_needed_option(context: RescueContextFixture) -> RescueOptionCandidate:
    return RescueOptionCandidate(
        option_id=_option_id(context, "no-rescue"),
        option_type="no_rescue_needed",
        affected_dates=[context.local_date],
        suggested_adjustment_kcal_range=(0, 0),
        rationale="No rescue adjustment is warranted by the shadow inputs.",
        risk_if_wrong="low",
    )


def _ask_user_option(
    context: RescueContextFixture,
    *,
    rationale: str,
    risk_if_wrong: RescueOptionRiskIfWrong,
) -> RescueOptionCandidate:
    return RescueOptionCandidate(
        option_id=_option_id(context, "ask-user-context"),
        option_type="ask_user_context_first",
        affected_dates=[context.local_date],
        suggested_adjustment_kcal_range=(0, 0),
        rationale=rationale,
        risk_if_wrong=risk_if_wrong,
    )


def _next_day_soft_option(context: RescueContextFixture) -> RescueOptionCandidate:
    return RescueOptionCandidate(
        option_id=_option_id(context, "next-day-soft"),
        option_type="next_day_soft_adjustment",
        affected_dates=[context.local_date + timedelta(days=1)],
        suggested_adjustment_kcal_range=(75, 150),
        rationale=(
            "User plan-resistance signals call for only a soft next-day shadow "
            "candidate."
        ),
        risk_if_wrong="medium",
    )


def _multi_day_spread_option(context: RescueContextFixture) -> RescueOptionCandidate:
    affected_dates = _spread_dates(context)
    lower, upper = _spread_adjustment_range(
        context.overshoot_summary.today_overshoot_kcal,
        day_count=len(affected_dates),
    )
    return RescueOptionCandidate(
        option_id=_option_id(context, "multi-day-spread"),
        option_type="multi_day_spread_candidate",
        affected_dates=affected_dates,
        suggested_adjustment_kcal_range=(lower, upper),
        rationale=(
            "Large overshoot and weekly off-track posture can be shadowed as a "
            "modest three-day spread."
        ),
        risk_if_wrong="medium",
    )


def _rejection(
    *,
    reason_code: str,
    rationale: str,
    rejected_option_type: RescueOptionType | None = None,
) -> RescueOptionRejection:
    return RescueOptionRejection(
        reason_code=reason_code,
        rationale=rationale,
        rejected_option_type=rejected_option_type,
    )


def _has_existing_open_proposal(context: RescueContextFixture) -> bool:
    return (
        context.open_proposals.has_open_rescue_like_proposal
        or context.open_proposals.has_open_calibration_proposal
    )


def _has_low_logging_quality(context: RescueContextFixture) -> bool:
    return (
        context.recent_committed_meals.logging_coverage < 0.6
        or context.adherence_summary.logging_quality in {"low", "unknown"}
    )


def _is_calibration_uncertain(
    context: RescueContextFixture,
    viability: RescueViabilityScoreResult,
) -> bool:
    return (
        context.calibration_posture.uncertain
        or (
            context.calibration_posture.posture == "uncertain"
            and context.calibration_posture.confidence < 0.35
        )
        or "recent_calibration_uncertain" in viability.reason_codes
    )


def _has_strict_plan_resistance(
    context: RescueContextFixture,
    viability: RescueViabilityScoreResult,
) -> bool:
    return (
        context.adherence_summary.user_strictness_tolerance == "low"
        or context.adherence_summary.app_usage_style in STRICT_PLAN_RESISTANT_USAGE_STYLES
        or context.rescue_history_summary.ignored_strict_plans
        or "user_likely_dislikes_strict_plans" in viability.reason_codes
    )


def _viability_requires_user_context(viability: RescueViabilityScoreResult) -> bool:
    return (
        viability.recommended_action == "ask_user"
        or "rescue_risk_too_aggressive" in viability.reason_codes
    )


def _small_overshoot_with_healthy_weekly_deficit(context: RescueContextFixture) -> bool:
    return (
        0 < context.overshoot_summary.today_overshoot_kcal <= 100
        and context.overshoot_summary.weekly_overshoot_kcal == 0
        and context.deficit_summary.weekly_deficit_gap_kcal <= 0
        and context.deficit_summary.weekly_deficit_posture in {"on_track", "ahead"}
    )


def _should_not_generate_any_rescue_option(
    context: RescueContextFixture,
    trigger: RescueTriggerDetectionResult,
    viability: RescueViabilityScoreResult,
) -> bool:
    return (
        not trigger.should_generate_rescue_candidate
        or trigger.trigger_candidate == "no_rescue_needed"
        or viability.viability_band == "not_needed"
        or viability.recommended_action == "discard"
        or context.overshoot_summary.today_overshoot_kcal <= 0
    )


def _should_generate_spread_candidate(
    context: RescueContextFixture,
    trigger: RescueTriggerDetectionResult,
    viability: RescueViabilityScoreResult,
) -> bool:
    return (
        trigger.should_generate_rescue_candidate
        and context.overshoot_summary.today_overshoot_kcal >= 500
        and (
            context.deficit_summary.weekly_deficit_gap_kcal >= 500
            or context.deficit_summary.weekly_deficit_posture == "off_track"
        )
        and viability.recommended_action == "promote_later"
        and viability.confidence >= 0.7
        and not _exceeds_soft_spread_capacity(context)
    )


def _is_repeated_overshoot_strategy_candidate(
    trigger: RescueTriggerDetectionResult,
) -> bool:
    return (
        trigger.trigger_candidate == "repeated_overshoot_pattern"
        or "repeated_overshoot" in trigger.trigger_reason_codes
    )


def _exceeds_soft_spread_capacity(context: RescueContextFixture) -> bool:
    return (
        context.overshoot_summary.today_overshoot_kcal
        > MAX_SOFT_SPREAD_DAYS * MAX_SOFT_DAILY_ADJUSTMENT_KCAL
    )


def _spread_dates(context: RescueContextFixture) -> tuple:
    day_count = min(
        max(
            ceil(
                context.overshoot_summary.today_overshoot_kcal
                / MAX_SOFT_DAILY_ADJUSTMENT_KCAL
            ),
            3,
        ),
        MAX_SOFT_SPREAD_DAYS,
    )
    return tuple(context.local_date + timedelta(days=offset) for offset in range(1, day_count + 1))


def _spread_adjustment_range(
    today_overshoot_kcal: int,
    *,
    day_count: int,
) -> tuple[int, int]:
    upper = min(
        MAX_SOFT_DAILY_ADJUSTMENT_KCAL,
        max(75, ceil(today_overshoot_kcal / max(day_count, 1))),
    )
    lower = max(75, ceil(upper * 0.6))
    return lower, upper


def _option_id(context: RescueContextFixture, suffix: str) -> str:
    return f"rs4-{context.user_id}-{context.local_date.isoformat()}-{suffix}"


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "generate_rescue_option_packet",
]
