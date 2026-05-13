from __future__ import annotations

from app.rescue.application.guardrail_math import build_rescue_guardrail_math_packet
from app.rescue.application.option_generation_node import (
    build_rescue_option_generation_result,
)
from app.rescue.application.read_model_input_packet import (
    build_rescue_read_model_input_packet,
)
from app.rescue.application.trigger_viability_assessment import (
    build_rescue_trigger_viability_assessment,
)


def _read_model_packet(
    *,
    consumed_kcal: int = 2250,
    effective_budget_kcal: int = 1800,
    target_base_budget_kcal: int = 1800,
    safety_floor_kcal: int = 1500,
) -> dict:
    event = {
        "artifact_type": "rescue_ingress_event",
        "scope_keys": {
            "user_id": "user-1",
            "workspace_id": "workspace-1",
            "project_id": "project-1",
            "surface": "advanced_lab",
            "run_id": "run-1",
        },
        "source_trace_ids": ["req-1"],
        "current_budget_view": {
            "local_date": "2026-05-13",
            "base_budget_kcal": 1800,
            "effective_budget_kcal": effective_budget_kcal,
            "meal_consumption_total_kcal": consumed_kcal,
            "remaining_kcal": effective_budget_kcal - consumed_kcal,
        },
        "recent_committed_meals_view": {"meal_count": 1, "meals": []},
        "active_body_plan_view": {
            "safety_floor_kcal": safety_floor_kcal,
            "target_days": [
                {
                    "local_date": "2026-05-14",
                    "base_budget_kcal": target_base_budget_kcal,
                    "calibration_adjustment_total_kcal": 0,
                },
                {
                    "local_date": "2026-05-15",
                    "base_budget_kcal": target_base_budget_kcal,
                    "calibration_adjustment_total_kcal": 0,
                },
            ],
        },
        "open_proposals_view": {"open_rescue_proposal_count": 0},
    }
    return build_rescue_read_model_input_packet(event).model_dump()


def _assessment(
    read_model: dict,
    *,
    explicit_rescue_request: bool = True,
) -> tuple[dict, dict]:
    math = build_rescue_guardrail_math_packet(read_model_input_packet=read_model)
    assessment = build_rescue_trigger_viability_assessment(
        read_model_input_packet=read_model,
        guardrail_math_packet=math,
        trigger_request={
            "trigger_source": "reactive_chat",
            "explicit_rescue_request": explicit_rescue_request,
        },
    )
    return math, assessment


def test_option_generation_outputs_one_short_horizon_spread_option() -> None:
    read_model = _read_model_packet()
    math, assessment = _assessment(read_model)

    result = build_rescue_option_generation_result(
        trigger_viability_assessment=assessment,
        guardrail_math_packet=math,
    )

    assert result["status"] == "pass"
    assert result["decision_mode"] == "deterministic"
    assert result["rescue_needed"] is True
    assert result["option_count"] == 1
    assert result["allowed_rescue_families"] == ["short_horizon_spread"]
    assert result["selected_option"] == {
        "rescue_family": "short_horizon_spread",
        "recommended_days": 2,
        "daily_kcal_adjustment": -225,
        "cap_mode": "standard_15_percent",
        "recovery_viability": "strained",
        "special_posture": "strained_standard_spread",
    }
    assert result["proposal_card"] is None
    assert result["ledger_entry_created"] is False


def test_option_generation_does_not_generate_when_trigger_not_allowed() -> None:
    read_model = _read_model_packet()
    math, assessment = _assessment(read_model, explicit_rescue_request=False)

    result = build_rescue_option_generation_result(
        trigger_viability_assessment=assessment,
        guardrail_math_packet=math,
    )

    assert result["status"] == "pass"
    assert result["rescue_needed"] is False
    assert result["option_count"] == 0
    assert result["selected_option"] is None
    assert result["blockers"] == ["reactive_trigger_missing_explicit_request"]
    assert result["proposal_shaping_allowed"] is False


def test_option_generation_stops_when_math_is_non_viable() -> None:
    read_model = _read_model_packet(
        consumed_kcal=2100,
        effective_budget_kcal=1800,
        target_base_budget_kcal=1600,
        safety_floor_kcal=1500,
    )
    math, assessment = _assessment(read_model)

    result = build_rescue_option_generation_result(
        trigger_viability_assessment=assessment,
        guardrail_math_packet=math,
    )

    assert result["status"] == "pass"
    assert result["rescue_needed"] is False
    assert result["recovery_viability"] == "non_viable"
    assert result["selected_option"] is None
    assert result["special_posture"] == "rescue_stop_and_escalate"
    assert "below_safety_floor" in result["blockers"]


def test_option_generation_keeps_v1_from_becoming_multi_family_menu() -> None:
    read_model = _read_model_packet()
    math, assessment = _assessment(read_model)

    result = build_rescue_option_generation_result(
        trigger_viability_assessment=assessment,
        guardrail_math_packet=math,
    )

    assert result["allowed_rescue_families"] == ["short_horizon_spread"]
    assert result["backup_options"] == []
    assert result["candidate_menu"] == []
    assert "no_multi_family_menu" in result["guardrail_notes"]
    assert "next_meal_protection" not in repr(result)
