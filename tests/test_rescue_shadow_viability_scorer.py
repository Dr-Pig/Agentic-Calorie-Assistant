from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rescue.application.shadow_trigger_detector import detect_rescue_trigger_candidate
from app.rescue.application.shadow_viability_scorer import score_rescue_viability
from app.rescue.domain.shadow_context import RescueContextFixture


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_RUNTIME_ENTRYPOINTS = [
    "app/routes.py",
    "app/schemas.py",
    "app/models.py",
    "app/composition/intake_routes.py",
    "app/composition/v2_routes.py",
    "app/composition/intake_turn_orchestrator.py",
    "app/composition/intake_execution_orchestrator.py",
    "app/runtime/application/manager_service.py",
    "app/composition/intake_manager_tool_batch.py",
    "app/runtime/interface/provider_runtime.py",
]


def _context_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "user_id": "user-rs3",
        "local_date": "2026-05-04",
        "timezone": "Asia/Taipei",
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
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(payload.get(key), dict):
            payload[key] = {**payload[key], **value}  # type: ignore[index]
        else:
            payload[key] = value
    return payload


def _context(**overrides: object) -> RescueContextFixture:
    return RescueContextFixture(**_context_payload(**overrides))


def _score(**overrides: object):
    context = _context(**overrides)
    trigger = detect_rescue_trigger_candidate(context)
    return score_rescue_viability(context, trigger)


def test_small_overshoot_without_rescue_trigger_is_not_needed_discard() -> None:
    result = _score(
        overshoot_summary={"today_overshoot_kcal": 80},
        deficit_summary={
            "weekly_deficit_gap_kcal": -250,
            "weekly_deficit_posture": "on_track",
        },
    )

    assert result.viability_band == "not_needed"
    assert result.recommended_action == "discard"
    assert result.rescue_viability_score == 0.0
    assert "overshoot_small" in result.reason_codes
    assert "weekly_deficit_still_ok" in result.reason_codes


def test_large_overshoot_off_track_weekly_deficit_and_good_logging_promotes_later() -> None:
    result = _score(
        overshoot_summary={"today_overshoot_kcal": 650},
        deficit_summary={
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
    )

    assert result.viability_band == "medium"
    assert result.recommended_action == "promote_later"
    assert "overshoot_large" in result.reason_codes
    assert result.confidence >= 0.7


def test_low_logging_quality_lowers_confidence_and_softens_action() -> None:
    result = _score(
        overshoot_summary={"today_overshoot_kcal": 650},
        deficit_summary={
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
        recent_committed_meals={"logging_coverage": 0.35},
        adherence_summary={"logging_quality": "low"},
    )

    assert "low_logging_quality" in result.reason_codes
    assert result.confidence < 0.6
    assert result.viability_band == "medium"
    assert result.recommended_action == "ask_user"


def test_no_active_plan_trigger_returns_not_needed_discard() -> None:
    result = _score(
        current_budget={"active": False},
        overshoot_summary={"today_overshoot_kcal": 650},
    )

    assert result.viability_band == "not_needed"
    assert result.recommended_action == "discard"
    assert "no_active_plan" in result.reason_codes


def test_open_proposal_trigger_returns_low_keep_shadowing() -> None:
    result = _score(
        overshoot_summary={"today_overshoot_kcal": 650},
        open_proposals={"has_open_rescue_like_proposal": True},
    )

    assert result.viability_band == "low"
    assert result.recommended_action == "keep_shadowing"
    assert "existing_open_proposal" in result.reason_codes


def test_repeated_overshoot_increases_score_and_records_reason() -> None:
    single = _score(overshoot_summary={"today_overshoot_kcal": 180})
    repeated = _score(
        overshoot_summary={
            "today_overshoot_kcal": 180,
            "recent_overshoot_days": 3,
        },
    )

    assert repeated.rescue_viability_score > single.rescue_viability_score
    assert "repeated_overshoot" in repeated.reason_codes


def test_calibration_uncertain_prevents_high_band_and_promote_later() -> None:
    result = _score(
        overshoot_summary={"today_overshoot_kcal": 650},
        deficit_summary={
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
        calibration_posture={"uncertain": True, "confidence": 0.2},
    )

    assert "recent_calibration_uncertain" in result.reason_codes
    assert result.viability_band == "medium"
    assert result.recommended_action == "ask_user"


def test_low_strictness_tolerance_or_ignored_strict_plans_softens_action() -> None:
    result = _score(
        overshoot_summary={"today_overshoot_kcal": 650},
        deficit_summary={
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
        adherence_summary={"user_strictness_tolerance": "low"},
        rescue_history_summary={"ignored_strict_plans": True},
    )

    assert "user_likely_dislikes_strict_plans" in result.reason_codes
    assert result.viability_band == "medium"
    assert result.recommended_action == "ask_user"
    assert result.harm_if_wrong == "high"


def test_app_usage_style_strict_plan_resistance_softens_action() -> None:
    result = _score(
        overshoot_summary={"today_overshoot_kcal": 650},
        deficit_summary={
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
        adherence_summary={"app_usage_style": "soft_first"},
    )

    assert "user_likely_dislikes_strict_plans" in result.reason_codes
    assert result.viability_band == "medium"
    assert result.recommended_action == "ask_user"
    assert result.harm_if_wrong == "high"


def test_extreme_overshoot_recovery_pressure_prevents_high_and_promote_later() -> None:
    result = _score(
        current_budget={"daily_budget_kcal": 1800},
        active_body_plan={
            "daily_target_kcal": 1800,
            "safety_floor_kcal": 1700,
        },
        overshoot_summary={
            "today_overshoot_kcal": 1600,
            "weekly_overshoot_kcal": 1200,
        },
        deficit_summary={
            "weekly_deficit_gap_kcal": 900,
            "weekly_deficit_posture": "off_track",
        },
    )

    assert "rescue_risk_too_aggressive" in result.reason_codes
    assert result.viability_band == "medium"
    assert result.recommended_action == "ask_user"
    assert result.harm_if_wrong == "high"


def test_viability_result_declares_shadow_non_authority_flags() -> None:
    result = _score(
        overshoot_summary={"today_overshoot_kcal": 650},
        deficit_summary={
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
    )

    assert result.shadow_review_only is True
    assert result.runtime_effect_allowed is False
    assert result.proposal_authority is False


def test_active_runtime_entrypoints_do_not_import_shadow_viability_scorer() -> None:
    forbidden_tokens = [
        "app.rescue.domain.shadow_viability",
        "app.rescue.application.shadow_viability_scorer",
        "shadow_viability",
        "shadow_viability_scorer",
        "RescueViabilityScoreResult",
        "score_rescue_viability",
    ]

    for relative_path in ACTIVE_RUNTIME_ENTRYPOINTS:
        text = (ROOT / relative_path).read_text(encoding="utf-8-sig")
        for token in forbidden_tokens:
            assert token not in text, f"{relative_path} imports or references RS3 sidecar token {token!r}"


def test_viability_result_rejects_unknown_fields() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_viability")

    with pytest.raises(ValidationError):
        module.RescueViabilityScoreResult(
            rescue_viability_score=0.2,
            viability_band="low",
            reason_codes=[],
            confidence=0.5,
            harm_if_wrong="low",
            recommended_action="keep_shadowing",
            unexpected_runtime_field="must_not_be_silently_accepted",
        )
