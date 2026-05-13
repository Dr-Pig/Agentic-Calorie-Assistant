from __future__ import annotations

from app.rescue.application.guardrail_math import build_rescue_guardrail_math_packet
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
    open_proposal_count: int = 0,
    cooldown_active: bool = False,
    suppressed_trigger_types: list[str] | None = None,
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
            "safety_floor_kcal": 1500,
            "target_days": [
                {
                    "local_date": "2026-05-14",
                    "base_budget_kcal": 1800,
                    "calibration_adjustment_total_kcal": 0,
                },
                {
                    "local_date": "2026-05-15",
                    "base_budget_kcal": 1800,
                    "calibration_adjustment_total_kcal": 0,
                },
            ],
        },
        "open_proposals_view": {
            "open_rescue_proposal_count": open_proposal_count,
            "active_proposal_ids": ["proposal-1"] if open_proposal_count else [],
        },
    }
    return build_rescue_read_model_input_packet(
        event,
        proactive_status_view={
            "budget_alert_cooldown_active": cooldown_active,
            "suppressed_trigger_types": suppressed_trigger_types or [],
        },
    ).model_dump()


def _math_packet(read_model_packet: dict) -> dict:
    return build_rescue_guardrail_math_packet(
        read_model_input_packet=read_model_packet
    )


def test_trigger_viability_allows_explicit_reactive_rescue_request() -> None:
    read_model = _read_model_packet()
    assessment = build_rescue_trigger_viability_assessment(
        read_model_input_packet=read_model,
        guardrail_math_packet=_math_packet(read_model),
        trigger_request={
            "trigger_source": "reactive_chat",
            "explicit_rescue_request": True,
            "message_event_id": "msg-1",
        },
    )

    assert assessment["status"] == "pass"
    assert assessment["triggered"] is True
    assert assessment["trigger_type"] == "reactive_same_day_overshoot"
    assert assessment["trigger_object_ref"] == {
        "source_type": "CurrentBudgetView",
        "local_date": "2026-05-13",
    }
    assert assessment["overshoot_summary"]["overshoot_kcal"] == 450
    assert assessment["recovery_viability"] == "strained"
    assert assessment["proactive_eligibility"]["eligible"] is True
    assert assessment["option_generated"] is False
    assert assessment["proposal_committed"] is False


def test_trigger_viability_rejects_current_intake_event_as_trigger_source() -> None:
    read_model = _read_model_packet()
    assessment = build_rescue_trigger_viability_assessment(
        read_model_input_packet=read_model,
        guardrail_math_packet=_math_packet(read_model),
        trigger_request={
            "trigger_source": "current_intake_event_context",
            "explicit_rescue_request": True,
        },
    )

    assert assessment["status"] == "blocked"
    assert assessment["triggered"] is False
    assert assessment["blockers"] == [
        "unsupported_trigger_source:current_intake_event_context"
    ]
    assert "current_intake_event_context" in assessment["forbidden_input_sources"]
    assert assessment["runtime_effect_allowed"] is False


def test_trigger_viability_requires_explicit_reactive_request() -> None:
    read_model = _read_model_packet()
    assessment = build_rescue_trigger_viability_assessment(
        read_model_input_packet=read_model,
        guardrail_math_packet=_math_packet(read_model),
        trigger_request={
            "trigger_source": "reactive_chat",
            "explicit_rescue_request": False,
        },
    )

    assert assessment["status"] == "pass"
    assert assessment["triggered"] is False
    assert assessment["trigger_type"] == "none"
    assert assessment["blockers"] == ["reactive_trigger_missing_explicit_request"]
    assert assessment["recovery_viability"] == "not_assessed"


def test_trigger_viability_blocks_proactive_when_suppressed_or_open_proposal() -> None:
    read_model = _read_model_packet(
        open_proposal_count=1,
        cooldown_active=True,
        suppressed_trigger_types=["budget_alert_check"],
    )
    assessment = build_rescue_trigger_viability_assessment(
        read_model_input_packet=read_model,
        guardrail_math_packet=_math_packet(read_model),
        trigger_request={"trigger_source": "proactive_budget_alert"},
    )

    assert assessment["status"] == "pass"
    assert assessment["triggered"] is False
    assert assessment["proactive_eligibility"] == {
        "eligible": False,
        "reasons": [
            "open_rescue_proposal",
            "budget_alert_cooldown_active",
            "suppressed_trigger_type:budget_alert_check",
        ],
    }
    assert assessment["blockers"] == [
        "open_rescue_proposal",
        "budget_alert_cooldown_active",
        "suppressed_trigger_type:budget_alert_check",
    ]
