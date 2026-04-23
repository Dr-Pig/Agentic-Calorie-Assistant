from __future__ import annotations

from app.intake.application.workflow_routing import WorkflowRoutingStateHints, build_workflow_routing_decision


def test_workflow_routing_decision_routes_budget_query_to_general_chat() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="我今天還剩多少熱量？",
        state_hints=WorkflowRoutingStateHints(has_active_body_plan=True),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "answer_only"
    assert result.required_read_surfaces == ["CurrentBudgetView"]
    assert result.routing_confidence == "high"


def test_workflow_routing_decision_routes_explicit_meal_logging_to_intake() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="晚餐我吃牛肉麵",
        state_hints=WorkflowRoutingStateHints(),
    )

    assert result.target_workflow_family == "intake"
    assert result.disposition == "open_new_workflow"
    assert result.routing_confidence == "high"


def test_workflow_routing_decision_routes_recommendation_request() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="幫我推薦附近晚餐",
        state_hints=WorkflowRoutingStateHints(has_active_body_plan=True),
    )

    assert result.target_workflow_family == "recommendation"
    assert result.disposition == "answer_only"
    assert result.required_read_surfaces == ["CurrentBudgetView", "ActiveBodyPlanView"]


def test_workflow_routing_decision_routes_rescue_action_when_open_proposal_exists() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="好，就照這個方案",
        state_hints=WorkflowRoutingStateHints(has_open_rescue_proposal=True),
    )

    assert result.target_workflow_family == "rescue"
    assert result.disposition == "accept"


def test_workflow_routing_decision_routes_body_observation_create() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="我今天體重變成 58 公斤",
        state_hints=WorkflowRoutingStateHints(),
    )

    assert result.target_workflow_family == "body_observation"
    assert result.disposition == "create"


def test_workflow_routing_decision_routes_calibration_request() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="最近都沒變，幫我重新調整目標",
        state_hints=WorkflowRoutingStateHints(has_active_body_plan=True),
    )

    assert result.target_workflow_family == "calibration"
    assert result.disposition == "open_new_workflow"


def test_workflow_routing_decision_uses_pending_followup_for_intake_continue() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="大概半碗飯",
        state_hints=WorkflowRoutingStateHints(has_pending_intake_followup=True),
    )

    assert result.target_workflow_family == "intake"
    assert result.disposition == "continue"
    assert result.routing_confidence == "medium"


def test_workflow_routing_decision_keeps_ambiguous_turn_in_general_chat() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="先這樣吧",
        state_hints=WorkflowRoutingStateHints(),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "answer_only"
    assert result.routing_confidence == "low"
    assert result.ambiguity_posture == "allow_uncertain"
