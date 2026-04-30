from __future__ import annotations

from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.workflow_routing import WorkflowRoutingStateHints, build_workflow_routing_decision


class _ResolvedState:
    def __init__(self, *, pending_followup_open: bool = False, assistant_turns: tuple[str, ...] = ()) -> None:
        self.local_date = "2026-04-29"
        self.injected_context = {
            "ACTIVE_MEAL": None,
            "PENDING_FOLLOWUP": {
                "is_open": pending_followup_open,
                "meal_id": 10 if pending_followup_open else None,
                "meal_thread_id": 77 if pending_followup_open else None,
                "pending_question": "What portion was it?" if pending_followup_open else None,
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": [],
            "TARGET_MEAL_REFERENCE": {
                "meal_thread_id": 77 if pending_followup_open else None,
                "meal_version_id": 88 if pending_followup_open else None,
                "meal_title": "chicken rice" if pending_followup_open else None,
                "target_resolution_source": "pending_followup_state" if pending_followup_open else "none",
                "correction_confidence": "high" if pending_followup_open else "low",
            },
            "SESSION_SUMMARY": {
                "latest_assistant_turns": list(assistant_turns),
            },
        }
        self.conversation_state = None


def test_workflow_routing_decision_does_not_keyword_route_budget_query_to_general_chat() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="how many calories do I have remaining today?",
        state_hints=WorkflowRoutingStateHints(has_active_body_plan=True),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "defer"
    assert result.required_read_surfaces == []
    assert result.routing_confidence == "low"


def test_workflow_routing_decision_does_not_keyword_route_meal_logging_to_intake() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="log chicken rice",
        state_hints=WorkflowRoutingStateHints(),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "defer"
    assert result.routing_confidence == "low"


def test_workflow_routing_decision_keeps_recommendation_request_out_of_wave1_mainline() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="recommend dinner",
        state_hints=WorkflowRoutingStateHints(has_active_body_plan=True),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "defer"
    assert result.required_read_surfaces == []


def test_workflow_routing_decision_keeps_rescue_request_out_of_wave1_mainline() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="help me recover from overeating",
        state_hints=WorkflowRoutingStateHints(has_open_rescue_proposal=True),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "defer"


def test_workflow_routing_decision_does_not_keyword_route_body_observation_create() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="update my weight to 58 kg",
        state_hints=WorkflowRoutingStateHints(),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "defer"


def test_workflow_routing_decision_does_not_keyword_route_calibration_request() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="adjust my body plan",
        state_hints=WorkflowRoutingStateHints(has_active_body_plan=True),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "defer"


def test_workflow_routing_decision_does_not_use_state_hint_as_intake_semantic_owner() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="half bowl",
        state_hints=WorkflowRoutingStateHints(has_pending_intake_followup=True),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "defer"
    assert result.routing_confidence == "low"


def test_workflow_routing_decision_keeps_ambiguous_turn_in_general_chat_defer() -> None:
    result = build_workflow_routing_decision(
        raw_user_input="not sure",
        state_hints=WorkflowRoutingStateHints(),
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "defer"
    assert result.routing_confidence == "low"
    assert result.ambiguity_posture == "allow_uncertain"


def test_workflow_routing_decision_routes_explicit_ui_target_without_raw_text_keywords() -> None:
    from app.runtime.contracts.phase_a import InteractionEvent

    current_turn_context = build_current_turn_context_v1(
        raw_user_input="",
        interaction_event=InteractionEvent(
            source="ui",
            surface_mode="ui_anchored_action",
            event_type="tap_meal",
            raw_text=None,
            action_id="edit_meal",
            target_object_type="meal_thread",
            target_object_id="77",
        ),
        resolved_state=_ResolvedState(),
    )

    result = build_workflow_routing_decision(
        raw_user_input="",
        current_turn_context=current_turn_context,
    )

    assert result.target_workflow_family == "intake"
    assert result.disposition == "continue"
    assert result.routing_confidence == "high"


def test_workflow_routing_decision_exposes_phase_a_trace_surfaces_from_current_turn_context() -> None:
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="half bowl of rice",
        resolved_state=_ResolvedState(
            pending_followup_open=True,
            assistant_turns=("What portion was it?",),
        ),
    )

    result = build_workflow_routing_decision(
        raw_user_input="half bowl of rice",
        current_turn_context=current_turn_context,
    )

    assert result.target_workflow_family == "intake"
    assert result.disposition == "continue"
    assert result.attachment_decision is not None
    assert result.transition_guard_result is not None
    assert result.attachment_decision.disposition == "attach_existing_thread"
    assert result.transition_guard_result.verdict == "pass"
    assert set(result.phase_a_trace.keys()) == {
        "current_turn_context",
        "interaction_event",
        "attachment_decision",
        "transition_guard_result",
    }


def test_workflow_routing_decision_uses_structured_target_reference_to_route_correction_into_intake() -> None:
    resolved_state = _ResolvedState()
    resolved_state.injected_context["TARGET_MEAL_REFERENCE"] = {
        "meal_thread_id": 77,
        "meal_version_id": 88,
        "meal_title": "milk tea",
        "target_resolution_source": "manager_structured_target",
        "correction_confidence": "high",
    }
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="please update the selected item",
        resolved_state=resolved_state,
    )

    result = build_workflow_routing_decision(
        raw_user_input="please update the selected item",
        current_turn_context=current_turn_context,
        resolved_state=resolved_state,
    )

    assert result.target_workflow_family == "intake"
    assert result.disposition == "correct"
    assert result.attachment_decision is not None
    assert result.attachment_decision.target_object_id == "77"
    assert "history_expansion_activation" not in result.phase_a_trace
