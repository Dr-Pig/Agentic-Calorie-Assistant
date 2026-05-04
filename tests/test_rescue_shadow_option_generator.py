from __future__ import annotations

import importlib
from datetime import date
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
    "app/composition/manager_context_runtime.py",
    "app/intake/application/manager_context_policy.py",
    "app/runtime/agent/manager_context_payload.py",
]


def _context_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "user_id": "user-rs4",
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


def _packet(**overrides: object):
    from app.rescue.application.shadow_option_generator import (
        generate_rescue_option_packet,
    )

    context = _context(**overrides)
    trigger = detect_rescue_trigger_candidate(context)
    viability = score_rescue_viability(context, trigger)
    return generate_rescue_option_packet(context, trigger, viability)


def test_small_overshoot_generates_only_informational_or_no_rescue_option() -> None:
    packet = _packet(
        overshoot_summary={"today_overshoot_kcal": 80},
        deficit_summary={
            "weekly_deficit_gap_kcal": -250,
            "weekly_deficit_posture": "on_track",
        },
    )

    option_types = {option.option_type for option in packet.option_candidates}
    assert option_types <= {"informational_only", "no_rescue_needed"}
    assert "bounded_spread_shadow_candidate" not in option_types
    assert packet.runtime_effect_allowed is False
    assert packet.proposal_authority is False
    assert all(option.user_confirmation_required_later is True for option in packet.option_candidates)
    assert all(option.runtime_effect_allowed is False for option in packet.option_candidates)
    assert all(
        option.live_equivalent_required_gate == "future_L3_4_proposal_accept_commit_gate"
        for option in packet.option_candidates
    )


def test_large_overshoot_off_track_generates_soft_spread_candidate_without_commit() -> None:
    packet = _packet(
        overshoot_summary={"today_overshoot_kcal": 650},
        deficit_summary={
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
    )

    spread = _single_option(packet, "bounded_spread_shadow_candidate")
    assert spread.affected_dates == (
        date(2026, 5, 5),
        date(2026, 5, 6),
        date(2026, 5, 7),
    )
    assert spread.suggested_adjustment_kcal_range[0] >= 75
    assert spread.suggested_adjustment_kcal_range[1] <= 270
    assert spread.user_confirmation_required_later is True
    assert spread.runtime_effect_allowed is False
    assert spread.live_equivalent_required_gate == "future_L3_4_proposal_accept_commit_gate"
    assert packet.selected_shadow_option_id_for_review == spread.option_id


def test_low_logging_quality_asks_user_before_any_adjustment_candidate() -> None:
    packet = _packet(
        overshoot_summary={"today_overshoot_kcal": 650},
        deficit_summary={
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
        recent_committed_meals={"logging_coverage": 0.35},
        adherence_summary={"logging_quality": "low"},
    )

    option_types = {option.option_type for option in packet.option_candidates}
    assert option_types == {"ask_user_context_first"}
    assert "low_logging_quality" in packet.reason_codes


def test_calibration_uncertain_avoids_overcorrection_and_asks_user() -> None:
    packet = _packet(
        overshoot_summary={"today_overshoot_kcal": 650},
        deficit_summary={
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
        calibration_posture={"uncertain": True, "confidence": 0.2},
    )

    option_types = {option.option_type for option in packet.option_candidates}
    assert option_types == {"ask_user_context_first"}
    assert "recent_calibration_uncertain" in packet.reason_codes
    assert "bounded_spread_shadow_candidate" not in option_types


def test_strict_plan_resistance_keeps_option_soft_and_user_confirmed() -> None:
    packet = _packet(
        overshoot_summary={"today_overshoot_kcal": 650},
        deficit_summary={
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
        adherence_summary={"app_usage_style": "soft_first"},
    )

    option_types = {option.option_type for option in packet.option_candidates}
    assert option_types == {"ask_user_context_first"}
    assert "bounded_spread_shadow_candidate" not in option_types
    assert all(option.user_confirmation_required_later is True for option in packet.option_candidates)


def test_soft_context_alone_cannot_create_adjustment_option_without_trigger() -> None:
    packet = _packet(
        overshoot_summary={"today_overshoot_kcal": 0},
        adherence_summary={"app_usage_style": "soft_first"},
    )

    option_types = {option.option_type for option in packet.option_candidates}
    assert option_types == {"no_rescue_needed"}
    assert packet.selected_shadow_option_id_for_review == packet.option_candidates[0].option_id


def test_spread_candidate_upper_bound_covers_overshoot_across_affected_dates() -> None:
    packet = _packet(
        overshoot_summary={"today_overshoot_kcal": 880},
        deficit_summary={
            "weekly_deficit_gap_kcal": 900,
            "weekly_deficit_posture": "off_track",
        },
    )
    spread = _single_option(packet, "bounded_spread_shadow_candidate")

    assert len(spread.affected_dates) == 4
    assert spread.suggested_adjustment_kcal_range[1] * len(spread.affected_dates) >= 880


def test_overshoot_beyond_soft_spread_capacity_asks_user_instead_of_undercovering() -> None:
    packet = _packet(
        current_budget={"daily_budget_kcal": 3000},
        active_body_plan={
            "daily_target_kcal": 3000,
            "safety_floor_kcal": 2300,
        },
        overshoot_summary={"today_overshoot_kcal": 2251},
        deficit_summary={
            "weekly_deficit_gap_kcal": 2300,
            "weekly_deficit_posture": "off_track",
        },
    )

    option_types = {option.option_type for option in packet.option_candidates}
    assert option_types == {"ask_user_context_first"}
    assert "soft_spread_capacity_exceeded" in packet.reason_codes
    assert packet.options_rejected[0].rejected_option_type == "bounded_spread_shadow_candidate"


def test_capacity_exceeded_overrides_strict_plan_soft_adjustment() -> None:
    packet = _packet(
        current_budget={"daily_budget_kcal": 3000},
        active_body_plan={
            "daily_target_kcal": 3000,
            "safety_floor_kcal": 2300,
        },
        overshoot_summary={"today_overshoot_kcal": 2251},
        deficit_summary={
            "weekly_deficit_gap_kcal": 2300,
            "weekly_deficit_posture": "off_track",
        },
        adherence_summary={"app_usage_style": "soft_first"},
    )

    option_types = {option.option_type for option in packet.option_candidates}
    assert option_types == {"ask_user_context_first"}
    assert "soft_spread_capacity_exceeded" in packet.reason_codes


def test_aggressive_within_capacity_asks_user_instead_of_no_rescue_needed() -> None:
    packet = _packet(
        current_budget={"daily_budget_kcal": 3000},
        active_body_plan={
            "daily_target_kcal": 3000,
            "safety_floor_kcal": 2850,
        },
        overshoot_summary={"today_overshoot_kcal": 1400},
        deficit_summary={
            "weekly_deficit_gap_kcal": 1400,
            "weekly_deficit_posture": "off_track",
        },
    )

    option_types = {option.option_type for option in packet.option_candidates}
    assert option_types == {"ask_user_context_first"}
    assert "rescue_risk_too_aggressive" in packet.reason_codes
    assert "viability_requires_user_context" in packet.reason_codes


def test_existing_open_proposal_blocks_duplicate_option_candidates() -> None:
    packet = _packet(
        overshoot_summary={"today_overshoot_kcal": 650},
        open_proposals={"has_open_rescue_like_proposal": True},
    )

    assert packet.option_candidates == ()
    assert packet.selected_shadow_option_id_for_review is None
    assert packet.options_rejected[0].reason_code == "existing_open_proposal"
    assert packet.runtime_effect_allowed is False


def test_no_active_plan_blocks_option_candidates() -> None:
    packet = _packet(
        current_budget={"active": False},
        overshoot_summary={"today_overshoot_kcal": 650},
    )

    assert packet.option_candidates == ()
    assert packet.selected_shadow_option_id_for_review is None
    assert packet.options_rejected[0].reason_code == "no_active_plan"


def test_option_contract_rejects_unknown_fields() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_options")

    with pytest.raises(ValidationError):
        module.RescueOptionCandidate(
            option_id="rs4-extra",
            option_type="informational_only",
            affected_dates=["2026-05-04"],
            suggested_adjustment_kcal_range=[0, 0],
            rationale="Informational shadow option only.",
            risk_if_wrong="low",
            live_equivalent_required_gate="future_L3_4_proposal_accept_commit_gate",
            unexpected_runtime_field="must_not_be_silently_accepted",
        )


def test_option_contract_rejects_inverted_adjustment_ranges() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_options")

    with pytest.raises(ValidationError):
        module.RescueOptionCandidate(
            option_id="rs4-inverted-range",
            option_type="informational_only",
            affected_dates=["2026-05-04"],
            suggested_adjustment_kcal_range=[220, 75],
            rationale="Invalid inverted range.",
            risk_if_wrong="low",
            live_equivalent_required_gate="future_L3_4_proposal_accept_commit_gate",
        )


def test_option_packet_requires_selected_option_to_exist() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_options")

    with pytest.raises(ValidationError):
        module.RescueOptionPacket(
            option_candidates=[],
            selected_shadow_option_id_for_review="missing",
        )


def test_option_packet_rejects_old_runtime_ambiguous_selected_option_field() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_options")

    with pytest.raises(ValidationError):
        module.RescueOptionPacket(
            option_candidates=[],
            selected_shadow_option_id="old-runtime-ambiguous-field",
        )


def test_option_packet_and_candidate_no_effect_flags_are_frozen() -> None:
    packet = _packet(
        overshoot_summary={"today_overshoot_kcal": 80},
        deficit_summary={
            "weekly_deficit_gap_kcal": -250,
            "weekly_deficit_posture": "on_track",
        },
    )
    option = packet.option_candidates[0]

    with pytest.raises(ValidationError):
        option.runtime_effect_allowed = True  # type: ignore[misc]

    with pytest.raises(ValidationError):
        packet.day_budget_mutated = True  # type: ignore[misc]


def test_active_runtime_entrypoints_do_not_import_shadow_option_generator() -> None:
    forbidden_tokens = [
        "app.rescue.domain.shadow_options",
        "app.rescue.application.shadow_option_generator",
        "shadow_options",
        "shadow_option_generator",
        "RescueOptionPacket",
        "generate_rescue_option_packet",
    ]

    for relative_path in ACTIVE_RUNTIME_ENTRYPOINTS:
        text = (ROOT / relative_path).read_text(encoding="utf-8-sig")
        for token in forbidden_tokens:
            assert token not in text, f"{relative_path} imports or references RS4 sidecar token {token!r}"


def _single_option(packet: object, option_type: str):
    matches = [
        option
        for option in packet.option_candidates  # type: ignore[attr-defined]
        if option.option_type == option_type
    ]
    assert len(matches) == 1
    return matches[0]
