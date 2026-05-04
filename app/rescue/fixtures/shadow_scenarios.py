from __future__ import annotations

from datetime import date

from app.rescue.domain.shadow_context import RescueContextFixture
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.fixtures.shadow_scenarios"
)
LOCAL_DATE = date(2026, 5, 4)
TIMEZONE = "Asia/Taipei"


def _base_payload(*, user_id: str) -> dict[str, object]:
    return {
        "user_id": user_id,
        "local_date": LOCAL_DATE,
        "timezone": TIMEZONE,
        "current_budget": {
            "active": True,
            "daily_budget_kcal": 1800,
            "consumed_kcal": 1800,
            "remaining_kcal": 0,
            "day_part": "evening",
        },
        "active_body_plan": {
            "active": True,
            "daily_target_kcal": 1800,
            "safety_floor_kcal": 1400,
        },
        "recent_committed_meals": {
            "meal_count_today": 3,
            "logging_coverage": 0.9,
        },
        "deficit_summary": {
            "weekly_deficit_gap_kcal": 0,
            "weekly_deficit_posture": "on_track",
        },
        "overshoot_summary": {
            "today_overshoot_kcal": 0,
            "weekly_overshoot_kcal": 0,
            "recent_overshoot_days": 0,
        },
        "calibration_posture": {},
        "adherence_summary": {
            "logging_quality": "high",
            "adherence_score": 0.8,
        },
        "rescue_history_summary": {},
        "open_proposals": {},
        "proactive_status": {
            "suppressed": False,
            "quiet_hours_active": False,
            "proactive_send_allowed": False,
        },
    }


def _fixture(user_id: str, **overrides: object) -> RescueContextFixture:
    payload = _base_payload(user_id=user_id)
    for key, value in overrides.items():
        current_value = payload.get(key)
        if isinstance(current_value, dict) and isinstance(value, dict):
            payload[key] = {**current_value, **value}
        else:
            payload[key] = value
    return RescueContextFixture(**payload)


_RESCUE_SHADOW_SCENARIO_FIXTURES: tuple[tuple[str, RescueContextFixture], ...] = (
    (
        "small_overshoot_no_rescue_needed",
        _fixture(
            "user-rs6-small-overshoot",
            current_budget={
                "consumed_kcal": 1880,
                "remaining_kcal": -80,
            },
            deficit_summary={
                "weekly_deficit_gap_kcal": -250,
                "weekly_deficit_posture": "on_track",
            },
            overshoot_summary={
                "today_overshoot_kcal": 80,
                "weekly_overshoot_kcal": 0,
                "recent_overshoot_days": 0,
            },
        ),
    ),
    (
        "large_overshoot_candidate_rescue",
        _fixture(
            "user-rs6-large-overshoot",
            current_budget={
                "consumed_kcal": 2450,
                "remaining_kcal": -650,
            },
            deficit_summary={
                "weekly_deficit_gap_kcal": 700,
                "weekly_deficit_posture": "off_track",
            },
            overshoot_summary={
                "today_overshoot_kcal": 650,
                "weekly_overshoot_kcal": 0,
                "recent_overshoot_days": 0,
            },
        ),
    ),
    (
        "low_logging_quality_downgrades_confidence",
        _fixture(
            "user-rs6-low-logging",
            current_budget={
                "consumed_kcal": 2450,
                "remaining_kcal": -650,
            },
            recent_committed_meals={
                "meal_count_today": 1,
                "logging_coverage": 0.35,
            },
            deficit_summary={
                "weekly_deficit_gap_kcal": 700,
                "weekly_deficit_posture": "off_track",
            },
            overshoot_summary={
                "today_overshoot_kcal": 650,
                "weekly_overshoot_kcal": 0,
                "recent_overshoot_days": 0,
            },
            adherence_summary={
                "logging_quality": "low",
                "adherence_score": 0.42,
                "recent_low_adherence": True,
            },
        ),
    ),
    (
        "repeated_overshoot_pattern",
        _fixture(
            "user-rs6-repeated-overshoot",
            current_budget={
                "consumed_kcal": 1800,
                "remaining_kcal": 0,
            },
            deficit_summary={
                "weekly_deficit_gap_kcal": 300,
                "weekly_deficit_posture": "slipping",
            },
            overshoot_summary={
                "today_overshoot_kcal": 180,
                "weekly_overshoot_kcal": 420,
                "recent_overshoot_days": 4,
            },
            rescue_history_summary={
                "recent_rescue_count": 1,
                "history_quality": "available",
            },
        ),
    ),
    (
        "calibration_uncertain_no_overcorrect",
        _fixture(
            "user-rs6-calibration-uncertain",
            current_budget={
                "consumed_kcal": 2450,
                "remaining_kcal": -650,
            },
            deficit_summary={
                "weekly_deficit_gap_kcal": 700,
                "weekly_deficit_posture": "off_track",
            },
            overshoot_summary={
                "today_overshoot_kcal": 650,
                "weekly_overshoot_kcal": 0,
                "recent_overshoot_days": 0,
            },
            calibration_posture={
                "posture": "uncertain",
                "confidence": 0.2,
                "uncertain": True,
            },
        ),
    ),
    (
        "user_dislikes_strict_plans",
        _fixture(
            "user-rs6-strict-plan-resistant",
            current_budget={
                "consumed_kcal": 2450,
                "remaining_kcal": -650,
            },
            deficit_summary={
                "weekly_deficit_gap_kcal": 700,
                "weekly_deficit_posture": "off_track",
            },
            overshoot_summary={
                "today_overshoot_kcal": 650,
                "weekly_overshoot_kcal": 0,
                "recent_overshoot_days": 0,
            },
            adherence_summary={
                "logging_quality": "high",
                "adherence_score": 0.76,
                "user_strictness_tolerance": "low",
                "app_usage_style": "soft_first",
            },
            rescue_history_summary={
                "ignored_strict_plans": True,
                "history_quality": "available",
            },
        ),
    ),
    (
        "existing_open_proposal_blocks_duplicate",
        _fixture(
            "user-rs6-open-proposal",
            current_budget={
                "consumed_kcal": 2450,
                "remaining_kcal": -650,
            },
            overshoot_summary={
                "today_overshoot_kcal": 650,
                "weekly_overshoot_kcal": 0,
                "recent_overshoot_days": 0,
            },
            open_proposals={
                "has_open_rescue_like_proposal": True,
                "has_open_calibration_proposal": False,
            },
        ),
    ),
    (
        "no_active_budget_or_body_plan_blocks",
        _fixture(
            "user-rs6-no-active-plan",
            current_budget={
                "active": False,
                "consumed_kcal": 2450,
                "remaining_kcal": -650,
            },
            active_body_plan={
                "active": False,
            },
            overshoot_summary={
                "today_overshoot_kcal": 650,
                "weekly_overshoot_kcal": 0,
                "recent_overshoot_days": 0,
            },
        ),
    ),
)
RESCUE_SHADOW_SCENARIO_FIXTURES = tuple(
    (scenario_id, context.model_copy(deep=True))
    for scenario_id, context in _RESCUE_SHADOW_SCENARIO_FIXTURES
)


def rescue_shadow_scenario_ids() -> tuple[str, ...]:
    return tuple(
        scenario_id
        for scenario_id, _fixture_context in _RESCUE_SHADOW_SCENARIO_FIXTURES
    )


def rescue_shadow_scenario_fixture_pairs() -> tuple[tuple[str, RescueContextFixture], ...]:
    return tuple(
        (scenario_id, context.model_copy(deep=True))
        for scenario_id, context in _RESCUE_SHADOW_SCENARIO_FIXTURES
    )


__all__ = [
    "RESCUE_SHADOW_SCENARIO_FIXTURES",
    "SIDECAR_ACTIVATION_CONTRACT",
    "rescue_shadow_scenario_fixture_pairs",
    "rescue_shadow_scenario_ids",
]
