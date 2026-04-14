from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Sequence

from .rescue_overlay import (
    RescueOverlayDayAssessment,
    RescueOverlayTargetDay,
    ShortHorizonRescuePlan,
    assess_rescue_overlay_day,
    build_short_horizon_rescue_plan,
    max_daily_rescue_compression,
)

RescueProposalFamily = Literal[
    "same_day_soft_cap",
    "short_horizon_spread",
    "next_meal_protection",
    "logging_first_rescue",
    "rescue_stop_and_escalate",
    "no_rescue",
]

RescueProposalPosture = Literal["no_rescue", "proposal", "rescue_stop_and_escalate"]
RecoveryViability = Literal["viable", "strained", "non_viable"]
OptionEffectType = Literal["rescue_overlay", "logging", "escalation"]
ActivationMode = Literal["immediate_next_meal", "today_lunch", "tomorrow_0000"]

ALL_RESCUE_FAMILIES: tuple[RescueProposalFamily, ...] = (
    "same_day_soft_cap",
    "short_horizon_spread",
    "next_meal_protection",
    "logging_first_rescue",
    "rescue_stop_and_escalate",
)

RescueProposalTargetDay = RescueOverlayTargetDay


@dataclass(frozen=True)
class RescueProposalInputs:
    rescue_needed: bool
    recovery_viability: RecoveryViability
    rescue_horizon: int
    target_recovery_kcal: int
    target_days: Sequence[RescueProposalTargetDay]
    safety_floor_kcal: int
    activation_reference_hour_24: int | None = None


@dataclass(frozen=True)
class RescueProposalOption:
    proposal_option_id: str
    option_family: RescueProposalFamily
    option_label: str
    option_summary: str
    horizon_days: int | None
    daily_kcal_adjustments: tuple[int, ...]
    activation_mode: ActivationMode
    effect_type: OptionEffectType
    effect_payload: dict[str, object]
    expected_effect_summary: str
    guardrail_summary: str
    confidence: Literal["low", "medium", "high"] = "medium"
    rank_order: int = 0
    is_primary: bool = False

    @property
    def rescue_option_id(self) -> str:
        return self.proposal_option_id


@dataclass(frozen=True)
class RescueProposalArtifact:
    rescue_needed: bool
    recovery_viability: RecoveryViability
    rescue_horizon: int
    allowed_rescue_families: tuple[RescueProposalFamily, ...]
    blocked_rescue_families: tuple[RescueProposalFamily, ...]
    recommended_rescue_family: RescueProposalFamily
    proposal_posture: RescueProposalPosture
    safety_floor_kcal: int
    target_recovery_kcal: int
    option_payloads: tuple[RescueProposalOption, ...]
    top_option: RescueProposalOption | None = None


def _filter_blocked(allowed: tuple[RescueProposalFamily, ...]) -> tuple[RescueProposalFamily, ...]:
    allowed_set = set(allowed)
    return tuple(family for family in ALL_RESCUE_FAMILIES if family not in allowed_set)


def _normalize_non_negative(value: int) -> int:
    return max(0, int(value))


def _normalize_hour(value: int | None) -> int | None:
    if value is None:
        return None
    hour = int(value)
    if hour < 0:
        return 0
    if hour > 23:
        return 23
    return hour


def _after_rescue_cutoff(hour_24: int | None) -> bool:
    return hour_24 is not None and hour_24 >= 11


def _activation_mode_for_family(
    family: RescueProposalFamily,
    *,
    activation_reference_hour_24: int | None,
) -> ActivationMode:
    if family == "next_meal_protection":
        return "immediate_next_meal"
    if _after_rescue_cutoff(activation_reference_hour_24):
        return "tomorrow_0000"
    return "today_lunch"


def _day_payload(day: RescueOverlayDayAssessment) -> dict[str, object]:
    return asdict(day)


def _build_single_day_option(
    *,
    family: RescueProposalFamily,
    option_label: str,
    option_summary: str,
    day: RescueProposalTargetDay,
    target_recovery_kcal: int,
    safety_floor_kcal: int,
    activation_scope: str,
    activation_mode: ActivationMode,
    rank_order: int,
    is_primary: bool,
) -> RescueProposalOption | None:
    max_compression = max_daily_rescue_compression(day.base_budget_kcal)
    floor_headroom = max(
        0,
        day.base_budget_kcal + day.calibration_adjustment_kcal - safety_floor_kcal,
    )
    proposed_recovery = min(_normalize_non_negative(target_recovery_kcal), max_compression, floor_headroom)
    if proposed_recovery <= 0:
        return None

    assessment = assess_rescue_overlay_day(
        local_date=day.local_date,
        base_budget_kcal=day.base_budget_kcal,
        calibration_adjustment_kcal=day.calibration_adjustment_kcal,
        proposed_rescue_overlay_kcal=-proposed_recovery,
        safety_floor_kcal=safety_floor_kcal,
    )
    if assessment.viability == "non_viable":
        return None

    effect_payload = {
        "activation_scope": activation_scope,
        "activation_mode": activation_mode,
        "target_recovery_kcal": _normalize_non_negative(target_recovery_kcal),
        "scheduled_recovery_kcal": proposed_recovery,
        "safety_floor_kcal": safety_floor_kcal,
        "recovery_viability": assessment.viability,
        "overlay_days": [_day_payload(assessment)],
    }
    guardrail_summary = (
        f"{assessment.local_date}: |delta|={abs(assessment.proposed_rescue_overlay_kcal)} "
        f"<= cap={assessment.max_daily_rescue_compression_kcal}; "
        f"candidate={assessment.candidate_effective_budget_kcal} >= floor={assessment.safety_floor_kcal}"
    )
    expected_effect_summary = (
        f"{activation_scope} applies {-proposed_recovery} kcal on {assessment.local_date}"
    )
    confidence: Literal["low", "medium", "high"] = "high" if assessment.viability == "viable" else "medium"
    return RescueProposalOption(
        proposal_option_id=f"{family}:{assessment.local_date}",
        option_family=family,
        option_label=option_label,
        option_summary=option_summary,
        horizon_days=1,
        daily_kcal_adjustments=(assessment.proposed_rescue_overlay_kcal,),
        activation_mode=activation_mode,
        effect_type="rescue_overlay",
        effect_payload=effect_payload,
        expected_effect_summary=expected_effect_summary,
        guardrail_summary=guardrail_summary,
        confidence=confidence,
        rank_order=rank_order,
        is_primary=is_primary,
    )


def _build_short_horizon_option(
    *,
    family: RescueProposalFamily,
    option_label: str,
    option_summary: str,
    target_days: Sequence[RescueProposalTargetDay],
    target_recovery_kcal: int,
    safety_floor_kcal: int,
    activation_mode: ActivationMode,
    rank_order: int,
    is_primary: bool,
) -> RescueProposalOption | None:
    if len(target_days) < 2:
        return None

    plan: ShortHorizonRescuePlan = build_short_horizon_rescue_plan(
        overshoot_kcal=_normalize_non_negative(target_recovery_kcal),
        target_days=target_days,
        safety_floor_kcal=safety_floor_kcal,
    )
    if plan.viability == "non_viable" or plan.scheduled_recovery_kcal <= 0:
        return None

    effect_payload = {
        "activation_scope": "multi_day",
        "activation_mode": activation_mode,
        "target_recovery_kcal": plan.target_recovery_kcal,
        "scheduled_recovery_kcal": plan.scheduled_recovery_kcal,
        "unallocated_recovery_kcal": plan.unallocated_recovery_kcal,
        "safety_floor_kcal": plan.safety_floor_kcal,
        "recovery_viability": plan.viability,
        "overlay_days": [_day_payload(day) for day in plan.overlay_days],
    }
    guardrail_summary = "; ".join(
        (
            f"{day.local_date}: |delta|={abs(day.proposed_rescue_overlay_kcal)} <= cap={day.max_daily_rescue_compression_kcal}, "
            f"candidate={day.candidate_effective_budget_kcal} >= floor={day.safety_floor_kcal}"
        )
        for day in plan.overlay_days
    )
    expected_effect_summary = (
        f"multi-day spread schedules {plan.scheduled_recovery_kcal} kcal across {len(plan.overlay_days)} days"
    )
    confidence: Literal["low", "medium", "high"] = "high" if plan.viability == "viable" else "medium"
    return RescueProposalOption(
        proposal_option_id=f"{family}:{len(plan.overlay_days)}d",
        option_family=family,
        option_label=option_label,
        option_summary=option_summary,
        horizon_days=len(plan.overlay_days),
        daily_kcal_adjustments=tuple(day.proposed_rescue_overlay_kcal for day in plan.overlay_days),
        activation_mode=activation_mode,
        effect_type="rescue_overlay",
        effect_payload=effect_payload,
        expected_effect_summary=expected_effect_summary,
        guardrail_summary=guardrail_summary,
        confidence=confidence,
        rank_order=rank_order,
        is_primary=is_primary,
    )


def _build_logging_first_option(
    *,
    target_recovery_kcal: int,
    safety_floor_kcal: int,
    rank_order: int,
    is_primary: bool,
) -> RescueProposalOption:
    return RescueProposalOption(
        proposal_option_id="logging_first_rescue",
        option_family="logging_first_rescue",
        option_label="logging_first_rescue",
        option_summary="hold rescue shaping until the overshoot record is complete",
        horizon_days=None,
        daily_kcal_adjustments=tuple(),
        activation_mode="immediate_next_meal",
        effect_type="logging",
        effect_payload={
            "requires_logging": True,
            "target_recovery_kcal": _normalize_non_negative(target_recovery_kcal),
            "safety_floor_kcal": safety_floor_kcal,
            "overlay_days": [],
        },
        expected_effect_summary="no budget overlay is applied until logging is clarified",
        guardrail_summary="no kcal delta is emitted",
        confidence="medium",
        rank_order=rank_order,
        is_primary=is_primary,
    )


def _build_escalation_option(
    *,
    target_recovery_kcal: int,
    safety_floor_kcal: int,
    rank_order: int,
    is_primary: bool,
) -> RescueProposalOption:
    return RescueProposalOption(
        proposal_option_id="rescue_stop_and_escalate",
        option_family="rescue_stop_and_escalate",
        option_label="rescue_stop_and_escalate",
        option_summary="stop short-horizon recovery and escalate to calibration or plan reset",
        horizon_days=None,
        daily_kcal_adjustments=tuple(),
        activation_mode="immediate_next_meal",
        effect_type="escalation",
        effect_payload={
            "target_recovery_kcal": _normalize_non_negative(target_recovery_kcal),
            "safety_floor_kcal": safety_floor_kcal,
            "overlay_days": [],
            "escalation_target": "calibration_or_plan_reset",
        },
        expected_effect_summary="no rescue overlay is applied",
        guardrail_summary="recovery viability is non_viable",
        confidence="high",
        rank_order=rank_order,
        is_primary=is_primary,
    )


def build_rescue_proposal(inputs: RescueProposalInputs) -> RescueProposalArtifact:
    safety_floor_kcal = _normalize_non_negative(inputs.safety_floor_kcal)
    rescue_horizon = _normalize_non_negative(inputs.rescue_horizon)
    target_recovery_kcal = _normalize_non_negative(inputs.target_recovery_kcal)
    activation_reference_hour_24 = _normalize_hour(inputs.activation_reference_hour_24)

    if not inputs.rescue_needed or target_recovery_kcal == 0:
        return RescueProposalArtifact(
            rescue_needed=False,
            recovery_viability=inputs.recovery_viability,
            rescue_horizon=rescue_horizon,
            allowed_rescue_families=tuple(),
            blocked_rescue_families=ALL_RESCUE_FAMILIES,
            recommended_rescue_family="no_rescue",
            proposal_posture="no_rescue",
            safety_floor_kcal=safety_floor_kcal,
            target_recovery_kcal=target_recovery_kcal,
            option_payloads=tuple(),
            top_option=None,
        )

    if inputs.recovery_viability == "non_viable":
        option = _build_escalation_option(
            target_recovery_kcal=target_recovery_kcal,
            safety_floor_kcal=safety_floor_kcal,
            rank_order=0,
            is_primary=True,
        )
        return RescueProposalArtifact(
            rescue_needed=True,
            recovery_viability=inputs.recovery_viability,
            rescue_horizon=rescue_horizon,
            allowed_rescue_families=("rescue_stop_and_escalate",),
            blocked_rescue_families=_filter_blocked(("rescue_stop_and_escalate",)),
            recommended_rescue_family="rescue_stop_and_escalate",
            proposal_posture="rescue_stop_and_escalate",
            safety_floor_kcal=safety_floor_kcal,
            target_recovery_kcal=target_recovery_kcal,
            option_payloads=(option,),
            top_option=option,
        )

    target_days = tuple(inputs.target_days)
    option_payloads: list[RescueProposalOption] = []
    allowed_families: list[RescueProposalFamily] = []

    if not target_days:
        logging_option = _build_logging_first_option(
            target_recovery_kcal=target_recovery_kcal,
            safety_floor_kcal=safety_floor_kcal,
            rank_order=0,
            is_primary=True,
        )
        option_payloads.append(logging_option)
        allowed_families.append("logging_first_rescue")
        return RescueProposalArtifact(
            rescue_needed=True,
            recovery_viability=inputs.recovery_viability,
            rescue_horizon=rescue_horizon,
            allowed_rescue_families=tuple(allowed_families),
            blocked_rescue_families=_filter_blocked(tuple(allowed_families)),
            recommended_rescue_family="logging_first_rescue",
            proposal_posture="proposal",
            safety_floor_kcal=safety_floor_kcal,
            target_recovery_kcal=target_recovery_kcal,
            option_payloads=tuple(option_payloads),
            top_option=logging_option,
        )

    next_meal_option = None
    if rescue_horizon <= 1:
        next_meal_activation_mode = _activation_mode_for_family(
            "next_meal_protection",
            activation_reference_hour_24=activation_reference_hour_24,
        )
        next_meal_option = _build_single_day_option(
            family="next_meal_protection",
            option_label="next_meal_protection",
            option_summary="protect the next meal with a safe one-day correction",
            day=target_days[0],
            target_recovery_kcal=target_recovery_kcal,
            safety_floor_kcal=safety_floor_kcal,
            activation_scope="next_meal",
            activation_mode=next_meal_activation_mode,
            rank_order=0,
            is_primary=True,
        )
        if next_meal_option is not None:
            option_payloads.append(next_meal_option)
            allowed_families.append("next_meal_protection")

    same_day_option = None
    same_day_activation_mode = _activation_mode_for_family(
        "same_day_soft_cap",
        activation_reference_hour_24=activation_reference_hour_24,
    )
    if same_day_activation_mode == "today_lunch":
        same_day_option = _build_single_day_option(
            family="same_day_soft_cap",
            option_label="same_day_soft_cap",
            option_summary="apply a safe same-day intake cap without dropping below the floor",
            day=target_days[0],
            target_recovery_kcal=target_recovery_kcal,
            safety_floor_kcal=safety_floor_kcal,
            activation_scope="same_day",
            activation_mode=same_day_activation_mode,
            rank_order=1 if next_meal_option is not None else 0,
            is_primary=next_meal_option is None,
        )
    if same_day_option is not None:
        option_payloads.append(same_day_option)
        allowed_families.append("same_day_soft_cap")

    spread_activation_mode = _activation_mode_for_family(
        "short_horizon_spread",
        activation_reference_hour_24=activation_reference_hour_24,
    )
    spread_option = _build_short_horizon_option(
        family="short_horizon_spread",
        option_label="short_horizon_spread",
        option_summary="spread the short-term recovery across the available horizon",
        target_days=target_days,
        target_recovery_kcal=target_recovery_kcal,
        safety_floor_kcal=safety_floor_kcal,
        activation_mode=spread_activation_mode,
        rank_order=2 if option_payloads else 0,
        is_primary=not option_payloads,
    )
    if spread_option is not None:
        option_payloads.append(spread_option)
        allowed_families.append("short_horizon_spread")

    if not option_payloads:
        logging_option = _build_logging_first_option(
            target_recovery_kcal=target_recovery_kcal,
            safety_floor_kcal=safety_floor_kcal,
            rank_order=0,
            is_primary=True,
        )
        option_payloads.append(logging_option)
        allowed_families.append("logging_first_rescue")

    if inputs.recovery_viability == "strained":
        preferred_families: tuple[RescueProposalFamily, ...] = (
            "next_meal_protection",
            "short_horizon_spread",
            "same_day_soft_cap",
            "logging_first_rescue",
        )
    elif rescue_horizon <= 1:
        preferred_families: tuple[RescueProposalFamily, ...] = (
            "next_meal_protection",
            "same_day_soft_cap",
            "short_horizon_spread",
            "logging_first_rescue",
        )
    else:
        preferred_families = (
            "short_horizon_spread",
            "same_day_soft_cap",
            "next_meal_protection",
            "logging_first_rescue",
        )

    sorted_options = tuple(
        sorted(
            option_payloads,
            key=lambda option: (
                preferred_families.index(option.option_family)
                if option.option_family in preferred_families
                else len(preferred_families),
                option.rank_order,
                option.option_family,
            ),
        )
    )
    top_option = sorted_options[0]
    recommended_rescue_family = top_option.option_family
    proposal_posture: RescueProposalPosture = "proposal"

    normalized_options: list[RescueProposalOption] = []
    for index, option in enumerate(sorted_options):
        normalized_options.append(
            RescueProposalOption(
                proposal_option_id=option.proposal_option_id,
                option_family=option.option_family,
                option_label=option.option_label,
                option_summary=option.option_summary,
                horizon_days=option.horizon_days,
                daily_kcal_adjustments=option.daily_kcal_adjustments,
                activation_mode=option.activation_mode,
                effect_type=option.effect_type,
                effect_payload=option.effect_payload,
                expected_effect_summary=option.expected_effect_summary,
                guardrail_summary=option.guardrail_summary,
                confidence=option.confidence,
                rank_order=index,
                is_primary=index == 0,
            )
        )

    return RescueProposalArtifact(
        rescue_needed=True,
        recovery_viability=inputs.recovery_viability,
        rescue_horizon=rescue_horizon,
        allowed_rescue_families=tuple(dict.fromkeys(allowed_families)),
        blocked_rescue_families=_filter_blocked(tuple(dict.fromkeys(allowed_families))),
        recommended_rescue_family=recommended_rescue_family,
        proposal_posture=proposal_posture,
        safety_floor_kcal=safety_floor_kcal,
        target_recovery_kcal=target_recovery_kcal,
        option_payloads=tuple(normalized_options),
        top_option=normalized_options[0],
    )


def build_rescue_proposal_artifact(inputs: RescueProposalInputs) -> RescueProposalArtifact:
    return build_rescue_proposal(inputs)
