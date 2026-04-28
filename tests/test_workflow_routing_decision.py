from __future__ import annotations

from app.intake.application.workflow_routing import WorkflowRoutingStateHints, build_workflow_routing_decision


def test_workflow_routing_decision_routes_budget_query_to_general_chat() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="??憭拚??拙?撠??",
        state_hints=WorkflowRoutingStateHints(has_active_body_plan=True),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "answer_only"
    assert result.required_read_surfaces in ([], ["CurrentBudgetView"])
    assert result.routing_confidence in ("high", "low")


def test_workflow_routing_decision_routes_explicit_meal_logging_to_intake() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="??????暻?",
        state_hints=WorkflowRoutingStateHints(),
    )

    assert result.target_workflow_family == "intake"
    assert result.disposition == "open_new_workflow"
    assert result.routing_confidence == "high"


def test_workflow_routing_decision_keeps_recommendation_request_out_of_wave1_mainline() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="撟急??刻????",
        state_hints=WorkflowRoutingStateHints(has_active_body_plan=True),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "answer_only"
    assert result.required_read_surfaces == []


def test_workflow_routing_decision_keeps_rescue_request_out_of_wave1_mainline() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="憟踝?撠梁?獢?",
        state_hints=WorkflowRoutingStateHints(has_open_rescue_proposal=True),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "answer_only"


def test_workflow_routing_decision_routes_body_observation_create() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="??憭拚?????58 ?祆",
        state_hints=WorkflowRoutingStateHints(),
    )

    assert result.target_workflow_family == "body_observation"
    assert result.disposition == "create"


def test_workflow_routing_decision_routes_calibration_request() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="?餈瘝?嚗鼠???啗矽?渡璅?",
        state_hints=WorkflowRoutingStateHints(has_active_body_plan=True),
    )

    assert result.target_workflow_family == "calibration"
    assert result.disposition == "open_new_workflow"


def test_workflow_routing_decision_uses_pending_followup_for_intake_continue() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="憭扳???憌?",
        state_hints=WorkflowRoutingStateHints(has_pending_intake_followup=True),
    )

    assert result.target_workflow_family == "intake"
    assert result.disposition == "continue"
    assert result.routing_confidence == "medium"


def test_workflow_routing_decision_keeps_ambiguous_turn_in_general_chat() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="?見??",
        state_hints=WorkflowRoutingStateHints(),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "answer_only"
    assert result.routing_confidence == "low"
    assert result.ambiguity_posture == "allow_uncertain"
