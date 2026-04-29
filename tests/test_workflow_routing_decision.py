from __future__ import annotations

from app.intake.application.workflow_routing import WorkflowRoutingStateHints, build_workflow_routing_decision
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1


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


def test_workflow_routing_decision_uses_history_activation_to_route_correction_into_intake() -> None:
    resolved_state = _ResolvedState()
    resolved_state.conversation_state = type(
        "ConversationState",
        (),
        {
            "retrieved_meal_records": [
                {
                    "chunk_id": "meal:500",
                    "source_type": "meal_record",
                    "source_id": 500,
                    "content": "milk tea bubble tea half sugar",
                    "timestamp": "2026-04-29T09:00:00Z",
                    "linked_meal_id": 500,
                    "score": 9.0,
                    "matched_terms": ["milk", "tea"],
                    "metadata": {
                        "title": "milk tea",
                        "meal_thread_id": 77,
                        "meal_version_id": 88,
                        "local_date": "2026-04-29",
                        "relative_time_label": "today",
                    },
                }
            ],
            "historical_meal_chunks": [],
            "transcript_chunks": [],
        },
    )()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="actually change that milk tea to half sugar",
        resolved_state=resolved_state,
    )

    result = build_workflow_routing_decision(
        raw_user_input="actually change that milk tea to half sugar",
        current_turn_context=current_turn_context,
        resolved_state=resolved_state,
    )

    assert result.target_workflow_family == "intake"
    assert result.disposition == "correct"
    assert result.attachment_decision is not None
    assert result.attachment_decision.target_object_id == "77"
    assert result.phase_a_trace["history_expansion_activation"]["triggered"] is True
    assert result.phase_a_trace["history_expansion_activation"]["resolution_gain"] is True
