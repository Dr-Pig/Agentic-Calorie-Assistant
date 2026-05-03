from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.composition.conversation_turn_trace import build_runtime_turn_trace, record_runtime_turn_messages
from app.models import Base
from app.shared.infra.models import MessageBuffer


def _state(*, pending_followup: dict[str, object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        user_external_id="trace-user",
        user_id=1,
        local_date="2026-04-29",
        onboarding_ready=True,
        active_meal=None,
        current_budget_view=None,
        active_body_plan_view=None,
        injected_context={
            "PENDING_FOLLOWUP": pending_followup
            if pending_followup is not None
            else {"is_open": False, "meal_id": None, "meal_thread_id": None, "pending_question": None}
        },
    )


def test_runtime_turn_trace_distinguishes_packet_trace_from_evidence_content() -> None:
    trace = build_runtime_turn_trace(
        request_id="turn-1",
        local_date="2026-04-29",
        raw_user_input="今天吃了多少？",
        assistant_message="今天已吃 480 kcal。",
        state_before=_state(),
        state_after=_state(),
        current_turn_context=None,
        result={
            "manager_decision": {"intent_type": "general_chat", "workflow_effect": "answer_only"},
            "intake_execution_manager": {
                "final": {"final_action": "answer_only", "workflow_effect": "answer_only"},
                "persistence_result": None,
            },
            "state_delta": {},
            "sidecar": {},
        },
    )

    assert trace["scope"] == "current_session_current_day"
    assert trace["long_term_memory"] is False
    assert trace["proactive"] is False
    assert trace["rescue_recommendation"] is False
    assert trace["trace_chain"]["evidence_packet_present"] is True
    assert trace["trace_chain"]["evidence_content_present"] is False
    assert trace["trace_chain"]["evidence_required"] is False
    assert trace["trace_chain"]["evidence_requirement_satisfied"] is True
    assert trace["trace_chain"]["final_mapping_present"] is True
    assert trace["trace_chain"]["state_before_present"] is True
    assert trace["trace_chain"]["state_after_present"] is True


def test_commit_trace_does_not_count_manager_rounds_as_evidence_content() -> None:
    trace = build_runtime_turn_trace(
        request_id="turn-commit-without-evidence",
        local_date="2026-04-29",
        raw_user_input="log lunch",
        assistant_message="logged",
        state_before=_state(),
        state_after=_state(),
        current_turn_context=None,
        result={
            "manager_decision": {"intent_type": "log_meal", "workflow_effect": "commit"},
            "intake_execution_manager": {
                "manager_rounds": [{"decision": {"semantic_decision": {"workflow_effect": "commit"}}}],
                "final": {"final_action": "commit", "workflow_effect": "commit"},
                "persistence_result": None,
            },
            "state_delta": {},
            "sidecar": {},
        },
    )

    assert trace["trace_chain"]["evidence_packet_present"] is True
    assert trace["trace_chain"]["evidence_content_present"] is False
    assert trace["trace_chain"]["evidence_required"] is True
    assert trace["trace_chain"]["evidence_requirement_satisfied"] is False


def test_commit_trace_accepts_canonical_persistence_as_evidence_content() -> None:
    trace = build_runtime_turn_trace(
        request_id="turn-commit-with-persistence",
        local_date="2026-04-29",
        raw_user_input="log lunch",
        assistant_message="logged",
        state_before=_state(),
        state_after=_state(),
        current_turn_context=None,
        result={
            "manager_decision": {"intent_type": "log_meal", "workflow_effect": "commit"},
            "intake_execution_manager": {
                "manager_rounds": [{"decision": {"semantic_decision": {"workflow_effect": "commit"}}}],
                "final": {"final_action": "commit", "workflow_effect": "commit"},
                "persistence_result": {"canonical_commit": {"meal_thread_id": 10, "meal_version_id": 20}},
            },
            "state_delta": {"canonical_commit": True},
            "sidecar": {},
        },
    )

    assert trace["trace_chain"]["evidence_content_present"] is True
    assert trace["trace_chain"]["evidence_required"] is True
    assert trace["trace_chain"]["evidence_requirement_satisfied"] is True


def test_runtime_turn_message_trace_links_pending_followup_to_chat_messages() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = session_local()
    try:
        result = record_runtime_turn_messages(
            db,
            user_external_id="trace-user",
            request_id="turn-followup",
            local_date="2026-04-29",
            raw_user_input="我吃了滷味",
            assistant_message="請列出滷味品項與大致份量。",
            state_before=_state(),
            state_after=_state(
                pending_followup={
                    "is_open": True,
                    "meal_id": 10,
                    "meal_thread_id": 77,
                    "pending_question": "請列出滷味品項與大致份量。",
                }
            ),
            current_turn_context=None,
            result={
                "manager_decision": {"intent_type": "log_meal", "workflow_effect": "draft_clarify_no_mutation"},
                "intake_execution_manager": {
                    "final": {"final_action": "ask_followup", "workflow_effect": "ask_followup"},
                    "persistence_result": {"persisted_log_id": 10},
                },
                "state_delta": {"draft_saved": True, "canonical_commit": False},
                "sidecar": {},
            },
        )
        messages = db.query(MessageBuffer).order_by(MessageBuffer.id.asc()).all()
    finally:
        db.close()
        engine.dispose()

    assert result["user_message_id"] is not None
    assert result["assistant_message_id"] is not None
    assert [message.role for message in messages] == ["user", "assistant"]
    runtime_trace = messages[1].trace_json["runtime_turn_trace"]
    assert runtime_trace["chat_linkage"]["user_message_id"] == result["user_message_id"]
    assert runtime_trace["chat_linkage"]["assistant_message_id"] == result["assistant_message_id"]
    assert runtime_trace["pending_followup_linkage"]["runtime_turn_id"] == "turn-followup"
    assert runtime_trace["pending_followup_linkage"]["pending_followup"]["meal_thread_id"] == 77
