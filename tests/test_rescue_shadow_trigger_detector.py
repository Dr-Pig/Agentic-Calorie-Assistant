from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rescue.application.shadow_trigger_detector import detect_rescue_trigger_candidate
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
        "user_id": "user-rs2",
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


def test_today_small_overshoot_with_healthy_weekly_deficit_is_informational() -> None:
    result = detect_rescue_trigger_candidate(
        _context(
            overshoot_summary={"today_overshoot_kcal": 80},
            deficit_summary={
                "weekly_deficit_gap_kcal": -250,
                "weekly_deficit_posture": "on_track",
            },
        )
    )

    assert result.trigger_candidate == "no_rescue_needed"
    assert result.trigger_strength in {"none", "low"}
    assert result.should_generate_rescue_candidate is False
    assert result.why_no_rescue_candidate == "informational_only"
    assert "overshoot_small" in result.trigger_reason_codes


def test_large_today_overshoot_with_weekly_deficit_gap_generates_high_candidate() -> None:
    result = detect_rescue_trigger_candidate(
        _context(
            overshoot_summary={"today_overshoot_kcal": 600},
            deficit_summary={
                "weekly_deficit_gap_kcal": 550,
                "weekly_deficit_posture": "off_track",
            },
        )
    )

    assert result.trigger_candidate == "today_overshoot"
    assert result.trigger_strength == "high"
    assert result.should_generate_rescue_candidate is True
    assert result.why_no_rescue_candidate is None
    assert "overshoot_large" in result.trigger_reason_codes
    assert "weekly_deficit_off_track" in result.trigger_reason_codes


def test_weekly_overshoot_without_large_today_overshoot_generates_candidate() -> None:
    result = detect_rescue_trigger_candidate(
        _context(
            overshoot_summary={
                "today_overshoot_kcal": 120,
                "weekly_overshoot_kcal": 760,
            },
        )
    )

    assert result.trigger_candidate == "weekly_overshoot"
    assert result.trigger_strength in {"medium", "high"}
    assert result.should_generate_rescue_candidate is True
    assert "weekly_overshoot" in result.trigger_reason_codes


def test_weekly_deficit_gap_without_weekly_overshoot_is_reason_only() -> None:
    result = detect_rescue_trigger_candidate(
        _context(
            overshoot_summary={
                "today_overshoot_kcal": 0,
                "weekly_overshoot_kcal": 0,
            },
            deficit_summary={"weekly_deficit_gap_kcal": 650},
        )
    )

    assert result.trigger_candidate == "no_rescue_needed"
    assert result.trigger_strength == "low"
    assert result.should_generate_rescue_candidate is False
    assert result.why_no_rescue_candidate == "no_trigger"
    assert "weekly_deficit_off_track" in result.trigger_reason_codes
    assert "weekly_overshoot" not in result.trigger_reason_codes


def test_repeated_overshoot_days_generates_repeated_pattern_candidate() -> None:
    result = detect_rescue_trigger_candidate(
        _context(
            overshoot_summary={
                "today_overshoot_kcal": 140,
                "recent_overshoot_days": 3,
            },
        )
    )

    assert result.trigger_candidate == "repeated_overshoot_pattern"
    assert result.trigger_strength == "medium"
    assert result.should_generate_rescue_candidate is True
    assert "repeated_overshoot" in result.trigger_reason_codes


def test_low_logging_quality_downgrades_strength_and_records_reason() -> None:
    result = detect_rescue_trigger_candidate(
        _context(
            overshoot_summary={"today_overshoot_kcal": 600},
            recent_committed_meals={"logging_coverage": 0.4},
            adherence_summary={"logging_quality": "low"},
        )
    )

    assert result.trigger_candidate == "today_overshoot"
    assert result.trigger_strength == "medium"
    assert result.should_generate_rescue_candidate is True
    assert "low_logging_quality" in result.trigger_reason_codes


def test_no_active_budget_or_body_plan_blocks_candidate_generation() -> None:
    result = detect_rescue_trigger_candidate(
        _context(
            current_budget={"active": False},
            active_body_plan={"active": True},
            overshoot_summary={"today_overshoot_kcal": 600},
        )
    )

    assert result.trigger_candidate == "today_overshoot"
    assert result.should_generate_rescue_candidate is False
    assert result.why_no_rescue_candidate == "no_active_budget_or_body_plan"


def test_existing_open_rescue_or_calibration_proposal_blocks_duplicate_candidate() -> None:
    result = detect_rescue_trigger_candidate(
        _context(
            overshoot_summary={"today_overshoot_kcal": 600},
            open_proposals={"has_open_calibration_proposal": True},
        )
    )

    assert result.trigger_candidate == "today_overshoot"
    assert result.should_generate_rescue_candidate is False
    assert result.why_no_rescue_candidate == "open_proposal_exists"


def test_remaining_budget_too_low_before_evening_generates_day_part_candidate() -> None:
    result = detect_rescue_trigger_candidate(
        _context(
            current_budget={"remaining_kcal": 90, "day_part": "afternoon"},
            overshoot_summary={"today_overshoot_kcal": 0},
        )
    )

    assert result.trigger_candidate == "budget_remaining_too_low_for_day_part"
    assert result.trigger_strength == "medium"
    assert result.should_generate_rescue_candidate is True
    assert "budget_remaining_too_low_for_day_part" in result.trigger_reason_codes


def test_optional_calibration_and_low_adherence_reasons_are_recorded() -> None:
    result = detect_rescue_trigger_candidate(
        _context(
            overshoot_summary={"today_overshoot_kcal": 600},
            calibration_posture={"recently_accepted": True},
            adherence_summary={"recent_low_adherence": True},
        )
    )

    assert result.trigger_candidate == "today_overshoot"
    assert "accepted_calibration_recently" in result.trigger_reason_codes
    assert "low_adherence_recently" in result.trigger_reason_codes


def test_shadow_trigger_contract_rejects_unknown_fields() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_trigger")

    with pytest.raises(ValidationError):
        module.RescueTriggerDetectionResult(
            trigger_candidate="no_rescue_needed",
            trigger_reason_codes=[],
            trigger_strength="none",
            should_generate_rescue_candidate=False,
            why_no_rescue_candidate="no_trigger",
            unexpected_runtime_field="must_not_be_silently_accepted",
        )


def test_active_runtime_entrypoints_do_not_import_shadow_trigger_detector() -> None:
    forbidden_tokens = [
        "app.rescue.domain.shadow_trigger",
        "app.rescue.application.shadow_trigger_detector",
        "shadow_trigger",
        "shadow_trigger_detector",
        "RescueTriggerDetectionResult",
        "detect_rescue_trigger_candidate",
    ]

    for relative_path in ACTIVE_RUNTIME_ENTRYPOINTS:
        text = (ROOT / relative_path).read_text(encoding="utf-8-sig")
        for token in forbidden_tokens:
            assert token not in text, f"{relative_path} imports or references RS2 sidecar token {token!r}"
