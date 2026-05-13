from __future__ import annotations

from app.rescue.application.guardrail_math import build_rescue_guardrail_math_packet
from app.rescue.application.option_generation_node import (
    build_rescue_option_generation_result,
)
from app.rescue.application.reactive_message_flow import (
    build_reactive_rescue_independent_message_flow,
)
from app.rescue.application.read_model_input_packet import (
    build_rescue_read_model_input_packet,
)
from app.rescue.application.trigger_viability_assessment import (
    build_rescue_trigger_viability_assessment,
)


def _reactive_chain(*, explicit_request: bool = True) -> tuple[dict, dict]:
    read_model = build_rescue_read_model_input_packet(
        {
            "artifact_type": "rescue_ingress_event",
            "scope_keys": {
                "user_id": "user-1",
                "workspace_id": "workspace-1",
                "project_id": "project-1",
                "surface": "advanced_lab",
                "run_id": "run-1",
            },
            "current_budget_view": {
                "local_date": "2026-05-13",
                "base_budget_kcal": 1800,
                "effective_budget_kcal": 1800,
                "meal_consumption_total_kcal": 2250,
                "remaining_kcal": -450,
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
            "open_proposals_view": {"open_rescue_proposal_count": 0},
        }
    ).model_dump()
    math = build_rescue_guardrail_math_packet(read_model_input_packet=read_model)
    assessment = build_rescue_trigger_viability_assessment(
        read_model_input_packet=read_model,
        guardrail_math_packet=math,
        trigger_request={
            "trigger_source": "reactive_chat",
            "explicit_rescue_request": explicit_request,
            "message_event_id": "msg-1",
        },
    )
    option = build_rescue_option_generation_result(
        trigger_viability_assessment=assessment,
        guardrail_math_packet=math,
    )
    return assessment, option


def test_reactive_flow_creates_independent_rescue_message_envelope() -> None:
    assessment, option = _reactive_chain()

    flow = build_reactive_rescue_independent_message_flow(
        trigger_viability_assessment=assessment,
        option_generation_result=option,
        source_turn={
            "message_event_id": "msg-1",
            "surface": "chat",
            "current_intake_reply_id": "intake-reply-1",
        },
    )

    assert flow["status"] == "pass"
    assert flow["rescue_message_created"] is True
    assert flow["independent_message"]["message_kind"] == "independent_rescue_message"
    assert flow["independent_message"]["source_message_event_id"] == "msg-1"
    assert flow["independent_message"]["rendering_state"] == "pending_proposal_shaping"
    assert flow["independent_message"]["contains_formal_proposal"] is False
    assert flow["message_independent"] is True


def test_reactive_flow_keeps_intake_reply_free_of_formal_proposal_and_ledger() -> None:
    assessment, option = _reactive_chain()

    flow = build_reactive_rescue_independent_message_flow(
        trigger_viability_assessment=assessment,
        option_generation_result=option,
        source_turn={
            "message_event_id": "msg-1",
            "surface": "chat",
            "current_intake_reply_id": "intake-reply-1",
        },
    )

    assert flow["intake_reply_effects"] == {
        "overshoot_awareness_allowed": True,
        "formal_rescue_proposal_created": False,
        "ledger_overlay_created": False,
        "rescue_card_attached": False,
    }
    assert flow["canonical_mutation_changed"] is False
    assert flow["ledger_entry_created"] is False


def test_reactive_flow_does_not_create_message_without_explicit_request() -> None:
    assessment, option = _reactive_chain(explicit_request=False)

    flow = build_reactive_rescue_independent_message_flow(
        trigger_viability_assessment=assessment,
        option_generation_result=option,
        source_turn={"message_event_id": "msg-1", "surface": "chat"},
    )

    assert flow["status"] == "pass"
    assert flow["rescue_message_created"] is False
    assert flow["independent_message"] is None
    assert flow["blockers"] == ["reactive_trigger_missing_explicit_request"]


def test_reactive_flow_rejects_non_reactive_trigger_source() -> None:
    assessment, option = _reactive_chain()
    assessment = {**assessment, "trigger_type": "proactive_same_day_overshoot"}

    flow = build_reactive_rescue_independent_message_flow(
        trigger_viability_assessment=assessment,
        option_generation_result=option,
        source_turn={"message_event_id": "msg-1", "surface": "chat"},
    )

    assert flow["status"] == "blocked"
    assert flow["rescue_message_created"] is False
    assert flow["blockers"] == ["trigger_viability_assessment.not_reactive_trigger"]
