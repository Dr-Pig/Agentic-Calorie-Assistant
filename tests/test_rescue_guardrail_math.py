from __future__ import annotations

from app.rescue.application.guardrail_math import build_rescue_guardrail_math_packet
from app.rescue.application.read_model_input_packet import (
    build_rescue_read_model_input_packet,
)


def _read_model_packet(
    *,
    consumed_kcal: int = 2250,
    effective_budget_kcal: int = 1800,
    target_base_budget_kcal: int = 1800,
    safety_floor_kcal: int = 1500,
    target_day_count: int = 2,
    calibration_adjustment_total_kcal: int = 0,
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
                    "local_date": f"2026-05-{14 + index}",
                    "base_budget_kcal": target_base_budget_kcal,
                    "calibration_adjustment_total_kcal": calibration_adjustment_total_kcal,
                }
                for index in range(target_day_count)
            ],
        },
        "open_proposals_view": {"open_rescue_proposal_count": 0},
    }
    return build_rescue_read_model_input_packet(event).model_dump()


def test_guardrail_math_uses_base_budget_denominator_and_standard_cap() -> None:
    packet = build_rescue_guardrail_math_packet(
        read_model_input_packet=_read_model_packet()
    )

    assert packet["status"] == "pass"
    assert packet["decision_mode"] == "deterministic"
    assert packet["overshoot_summary"] == {
        "meal_consumption_total_kcal": 2250,
        "effective_budget_kcal": 1800,
        "overshoot_kcal": 450,
    }
    assert packet["recommended_days"] == 2
    assert packet["daily_kcal_adjustment"] == -225
    assert packet["cap_mode"] == "standard_15_percent"
    assert packet["recovery_viability"] == "strained"
    assert packet["target_day_checks"][0]["max_daily_rescue_compression_kcal"] == 270
    assert packet["target_day_checks"][0]["cap_denominator"] == "base_budget_kcal"


def test_guardrail_math_blocks_below_safety_floor() -> None:
    packet = build_rescue_guardrail_math_packet(
        read_model_input_packet=_read_model_packet(
            consumed_kcal=2100,
            effective_budget_kcal=1800,
            target_base_budget_kcal=1600,
            safety_floor_kcal=1500,
        )
    )

    assert packet["status"] == "pass"
    assert packet["recovery_viability"] == "non_viable"
    assert packet["recommended_days"] is None
    assert packet["daily_kcal_adjustment"] is None
    assert "below_safety_floor" in packet["blockers"]
    assert packet["target_day_checks"][0]["candidate_effective_budget_kcal"] == 1450
    assert packet["target_day_checks"][0]["safety_floor_passed"] is False


def test_guardrail_math_does_not_use_effective_budget_as_cap_denominator() -> None:
    packet = build_rescue_guardrail_math_packet(
        read_model_input_packet=_read_model_packet(
            calibration_adjustment_total_kcal=400,
        )
    )

    check = packet["target_day_checks"][0]
    assert check["base_budget_kcal"] == 1800
    assert check["calibration_adjustment_total_kcal"] == 400
    assert check["candidate_effective_budget_kcal"] == 1975
    assert check["max_daily_rescue_compression_kcal"] == 270
    assert check["cap_denominator"] == "base_budget_kcal"


def test_guardrail_math_blocks_missing_read_model_packet() -> None:
    packet = build_rescue_guardrail_math_packet(
        read_model_input_packet={**_read_model_packet(), "status": "blocked"}
    )

    assert packet["status"] == "blocked"
    assert packet["recovery_viability"] == "blocked"
    assert packet["blockers"] == ["read_model_input_packet.status_blocked"]
    assert packet["runtime_effect_allowed"] is False
    assert packet["canonical_mutation_changed"] is False
    assert packet["production_scheduler_delivery_allowed"] is False
