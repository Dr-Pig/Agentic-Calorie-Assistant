from __future__ import annotations

from app.rescue.application.degraded_modes import build_rescue_degraded_mode_result
from app.rescue.application.read_model_input_packet import (
    build_rescue_read_model_input_packet,
)


def _read_model_packet(
    *,
    budget_available: bool = True,
    body_plan_available: bool = True,
    open_proposals_available: bool = True,
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
        "current_budget_view": {}
        if not budget_available
        else {
            "local_date": "2026-05-13",
            "base_budget_kcal": 1800,
            "effective_budget_kcal": 1800,
            "meal_consumption_total_kcal": 2250,
            "remaining_kcal": -450,
        },
        "recent_committed_meals_view": {"meal_count": 1, "meals": []},
        "active_body_plan_view": {}
        if not body_plan_available
        else {
            "safety_floor_kcal": 1500,
            "target_days": [
                {
                    "local_date": "2026-05-14",
                    "base_budget_kcal": 1800,
                    "calibration_adjustment_total_kcal": 0,
                }
            ],
        },
        "open_proposals_view": {}
        if not open_proposals_available
        else {"open_rescue_proposal_count": 0},
    }
    return build_rescue_read_model_input_packet(event).model_dump()


def test_degraded_modes_block_when_current_budget_view_unavailable() -> None:
    result = build_rescue_degraded_mode_result(
        read_model_input_packet=_read_model_packet(budget_available=False),
        onboarding_status={"body_plan_complete": True},
        provider_status={"proposal_shaping_available": True},
    )

    assert result["status"] == "blocked"
    assert result["degraded_mode"] == "required_view_unavailable"
    assert result["rescue_skipped"] == "budget_view_unavailable"
    assert result["rescue_flow_allowed"] is False
    assert result["runtime_effect_allowed"] is False


def test_degraded_modes_route_to_onboarding_when_body_plan_missing() -> None:
    result = build_rescue_degraded_mode_result(
        read_model_input_packet=_read_model_packet(body_plan_available=False),
        onboarding_status={"body_plan_complete": False},
        provider_status={"proposal_shaping_available": True},
    )

    assert result["status"] == "blocked"
    assert result["degraded_mode"] == "onboarding_missing"
    assert result["recommended_next_step"] == "route_to_onboarding"
    assert result["rescue_flow_allowed"] is False
    assert result["proactive_budget_alert_allowed"] is False


def test_degraded_modes_allow_conservative_body_plan_fallback_when_onboarded() -> None:
    result = build_rescue_degraded_mode_result(
        read_model_input_packet=_read_model_packet(body_plan_available=False),
        onboarding_status={"body_plan_complete": True},
        provider_status={"proposal_shaping_available": True},
    )

    assert result["status"] == "pass"
    assert result["degraded_mode"] == "conservative_body_plan_fallback"
    assert result["rescue_flow_allowed"] is True
    assert result["safety_floor_source"] == "conservative_fallback"
    assert result["conservative_safety_floor_kcal"] == 1500


def test_degraded_modes_use_logging_first_when_llm_provider_unavailable() -> None:
    result = build_rescue_degraded_mode_result(
        read_model_input_packet=_read_model_packet(),
        onboarding_status={"body_plan_complete": True},
        provider_status={"proposal_shaping_available": False},
    )

    assert result["status"] == "pass"
    assert result["degraded_mode"] == "provider_unavailable_logging_first"
    assert result["rescue_flow_allowed"] is True
    assert result["proposal_shaping_allowed"] is False
    assert result["response_template_allowed"] is True
    assert result["provider_recomputed_math"] is False


def test_degraded_modes_mark_open_proposals_view_missing_as_duplicate_risk() -> None:
    result = build_rescue_degraded_mode_result(
        read_model_input_packet=_read_model_packet(open_proposals_available=False),
        onboarding_status={"body_plan_complete": True},
        provider_status={"proposal_shaping_available": True},
    )

    assert result["status"] == "pass"
    assert result["degraded_mode"] == "open_proposals_view_unavailable"
    assert result["rescue_flow_allowed"] is True
    assert result["trace_notes"] == ["open_proposal_duplicate_risk"]
