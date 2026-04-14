from __future__ import annotations

from app.application.rescue_overlay import RescueOverlayTargetDay
from app.application.rescue_proposal import (
    ALL_RESCUE_FAMILIES,
    RescueProposalInputs,
    build_rescue_proposal,
)


def _inputs(
    *,
    rescue_needed: bool = True,
    recovery_viability: str = "viable",
    rescue_horizon: int = 3,
    target_recovery_kcal: int = 450,
    safety_floor_kcal: int = 1500,
    target_days: list[RescueOverlayTargetDay] | None = None,
    activation_reference_hour_24: int | None = 9,
) -> RescueProposalInputs:
    return RescueProposalInputs(
        rescue_needed=rescue_needed,
        recovery_viability=recovery_viability,  # type: ignore[arg-type]
        rescue_horizon=rescue_horizon,
        target_recovery_kcal=target_recovery_kcal,
        target_days=target_days
        if target_days is not None
        else [
            RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-13", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-14", base_budget_kcal=1800),
        ],
        safety_floor_kcal=safety_floor_kcal,
        activation_reference_hour_24=activation_reference_hour_24,
    )


def test_build_rescue_proposal_returns_no_rescue_posture_when_not_needed() -> None:
    artifact = build_rescue_proposal(
        _inputs(
            rescue_needed=False,
            target_recovery_kcal=0,
            rescue_horizon=0,
            target_days=[],
        )
    )

    assert artifact.rescue_needed is False
    assert artifact.proposal_posture == "no_rescue"
    assert artifact.recommended_rescue_family == "no_rescue"
    assert artifact.allowed_rescue_families == ()
    assert artifact.blocked_rescue_families == ALL_RESCUE_FAMILIES
    assert artifact.option_payloads == ()


def test_build_rescue_proposal_prefers_next_meal_for_one_day_horizon() -> None:
    artifact = build_rescue_proposal(
        _inputs(
            rescue_horizon=1,
            target_recovery_kcal=240,
            target_days=[
                RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1800),
            ],
        )
    )

    assert artifact.proposal_posture == "proposal"
    assert artifact.recommended_rescue_family == "next_meal_protection"
    assert artifact.allowed_rescue_families == ("next_meal_protection", "same_day_soft_cap")
    assert artifact.top_option is not None
    assert artifact.top_option.option_family == "next_meal_protection"
    assert artifact.top_option.activation_mode == "immediate_next_meal"
    assert artifact.option_payloads[1].option_family == "same_day_soft_cap"
    assert artifact.option_payloads[1].activation_mode == "today_lunch"

    for option in artifact.option_payloads:
        for day in option.effect_payload.get("overlay_days", []):
            assert day["candidate_effective_budget_kcal"] >= day["safety_floor_kcal"]
            assert abs(day["proposed_rescue_overlay_kcal"]) <= day["max_daily_rescue_compression_kcal"]


def test_build_rescue_proposal_prefers_short_horizon_spread_when_viable() -> None:
    artifact = build_rescue_proposal(
        _inputs(
            rescue_horizon=3,
            target_recovery_kcal=450,
            target_days=[
                RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1800),
                RescueOverlayTargetDay(local_date="2026-04-13", base_budget_kcal=1800),
                RescueOverlayTargetDay(local_date="2026-04-14", base_budget_kcal=1800),
            ],
        )
    )

    assert artifact.proposal_posture == "proposal"
    assert artifact.recommended_rescue_family == "short_horizon_spread"
    assert artifact.top_option is not None
    assert artifact.top_option.option_family == "short_horizon_spread"
    assert artifact.top_option.activation_mode == "today_lunch"
    assert "short_horizon_spread" in artifact.allowed_rescue_families
    assert "same_day_soft_cap" in artifact.allowed_rescue_families

    spread_option = next(
        option for option in artifact.option_payloads if option.option_family == "short_horizon_spread"
    )
    overlay_days = spread_option.effect_payload["overlay_days"]
    assert len(overlay_days) == 3
    assert [day["proposed_rescue_overlay_kcal"] for day in overlay_days] == [-150, -150, -150]
    for day in overlay_days:
        assert day["candidate_effective_budget_kcal"] >= day["safety_floor_kcal"]


def test_build_rescue_proposal_blocks_same_day_soft_cap_after_11_and_shifts_spread_to_tomorrow() -> None:
    artifact = build_rescue_proposal(
        _inputs(
            rescue_horizon=3,
            target_recovery_kcal=450,
            activation_reference_hour_24=14,
            target_days=[
                RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1800),
                RescueOverlayTargetDay(local_date="2026-04-13", base_budget_kcal=1800),
                RescueOverlayTargetDay(local_date="2026-04-14", base_budget_kcal=1800),
            ],
        )
    )

    assert artifact.recommended_rescue_family == "short_horizon_spread"
    assert "same_day_soft_cap" not in artifact.allowed_rescue_families
    assert artifact.top_option is not None
    assert artifact.top_option.activation_mode == "tomorrow_0000"
    assert artifact.top_option.daily_kcal_adjustments == (-150, -150, -150)


def test_build_rescue_proposal_prefers_next_meal_for_strained_recovery() -> None:
    artifact = build_rescue_proposal(
        _inputs(
            recovery_viability="strained",
            rescue_horizon=1,
            target_recovery_kcal=300,
            target_days=[RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1800)],
        )
    )

    assert artifact.recommended_rescue_family == "next_meal_protection"
    assert artifact.top_option is not None
    assert artifact.top_option.option_family == "next_meal_protection"
    assert artifact.top_option.is_primary is True
    assert artifact.option_payloads[0].rank_order == 0
    assert artifact.option_payloads[0].daily_kcal_adjustments == (-270,)


def test_build_rescue_proposal_escalates_when_non_viable() -> None:
    artifact = build_rescue_proposal(
        _inputs(
            recovery_viability="non_viable",
            rescue_horizon=3,
            target_recovery_kcal=240,
            target_days=[
                RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1500),
                RescueOverlayTargetDay(local_date="2026-04-13", base_budget_kcal=1500),
            ],
        )
    )

    assert artifact.proposal_posture == "rescue_stop_and_escalate"
    assert artifact.recommended_rescue_family == "rescue_stop_and_escalate"
    assert artifact.allowed_rescue_families == ("rescue_stop_and_escalate",)
    assert artifact.top_option is not None
    assert artifact.top_option.effect_type == "escalation"
    assert artifact.top_option.effect_payload["overlay_days"] == []
    assert artifact.top_option.activation_mode == "immediate_next_meal"
