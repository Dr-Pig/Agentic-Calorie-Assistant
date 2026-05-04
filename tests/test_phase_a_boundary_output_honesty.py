from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.composition.current_budget_answer import RemainingBudgetAnswerContract
from app.runtime.contracts.phase_a import CurrentTurnContextV1, InteractionEvent
from app.intake.application.boundary_output_honesty import (
    enforce_budget_output_honesty,
    enforce_intake_output_honesty,
)
from app.composition.general_chat_service import GeneralChatPassResult
from app.shared.contracts.common import EstimateRequest


def test_intake_output_honesty_normalizes_blocked_commit_structured_surfaces() -> None:
    phase_a_trace = {
        "phase_a_commit_boundary_preflight": {
            "checked": True,
            "blocked": True,
            "failure_family": "phase_a_commit_boundary_blocked",
            "mutation_effect_class": "canonical_write",
        },
        "boundary_projection": {
            "commit_boundary_decision": {
                "intent": "draft",
                "canonical_write_allowed": False,
                "ledger_mutation_allowed": False,
            }
        },
    }
    state_delta = {
        "meal_logged": True,
        "canonical_commit": True,
        "ledger_updated": True,
        "draft_saved": False,
        "new_meal_version_created": True,
        "old_version_superseded": True,
    }
    sidecar = {"state_mutation_summary": dict(state_delta)}

    result = enforce_intake_output_honesty(
        assistant_message="Logged. milk tea 420 kcal.",
        state_delta=state_delta,
        sidecar=sidecar,
        phase_a_trace=phase_a_trace,
        manager_final_action="no_commit",
        persistence_result=None,
    )

    assert result.state_delta["meal_logged"] is False
    assert result.state_delta["canonical_commit"] is False
    assert result.state_delta["ledger_updated"] is False
    assert result.state_delta["new_meal_version_created"] is False
    assert result.state_delta["old_version_superseded"] is False
    assert result.sidecar["state_mutation_summary"]["canonical_commit"] is False
    assert result.assistant_message == "I could not safely complete that turn, so nothing was committed."
    trace = result.phase_a_trace["phase_a_output_honesty"]
    assert trace["checked"] is True
    assert trace["normalized"] is True
    assert "structured_state_delta_no_commit" in trace["reasons"]
    assert trace["text_check_used"] is True


def test_budget_output_honesty_removes_concrete_remaining_when_degraded() -> None:
    answer = RemainingBudgetAnswerContract(
        status="onboarding_required",
        user_id=1,
        local_date="2026-04-29",
        daily_target_kcal=0,
        consumed_kcal=600,
        remaining_kcal=500,
        meal_count=2,
    )

    result = enforce_budget_output_honesty(
        reply_text="You have remaining 500 kcal today.",
        remaining_budget=answer,
        active_body_plan_present=False,
        phase_a_trace={},
    )

    assert "500" not in result.reply_text
    assert result.reply_text == "Onboarding is required before I can answer remaining budget."
    trace = result.phase_a_trace["phase_a_output_honesty"]
    assert trace["checked"] is True
    assert trace["normalized"] is True
    assert "degraded_budget_concrete_remaining_removed" in trace["reasons"]


def test_budget_output_honesty_keeps_ready_budget_answer_unchanged() -> None:
    answer = RemainingBudgetAnswerContract(
        status="ready",
        user_id=1,
        local_date="2026-04-29",
        daily_target_kcal=1800,
        consumed_kcal=600,
        remaining_kcal=1200,
        meal_count=2,
    )

    result = enforce_budget_output_honesty(
        reply_text="You have remaining 1200 kcal today.",
        remaining_budget=answer,
        active_body_plan_present=True,
        phase_a_trace={},
    )

    assert result.reply_text == "You have remaining 1200 kcal today."
    trace = result.phase_a_trace["phase_a_output_honesty"]
    assert trace["checked"] is True
    assert trace["normalized"] is False
    assert trace["reasons"] == []


def test_intake_execution_response_applies_output_honesty_to_structured_surfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.composition import intake_execution_response as module

    class _View:
        user_id = 1
        onboarding_ready = True
        injected_context: dict[str, object] = {}

        def __init__(self) -> None:
            self.active_body_plan_view = self
            self.current_budget_view = self

        def model_dump(self, *, mode: str = "json") -> dict[str, object]:
            return {
                "body_plan_id": 1,
                "budget_kcal": 1800,
                "remaining_kcal": 900,
                "show_macro": False,
            }

    monkeypatch.setattr(
        module,
        "build_remaining_budget_answer_contract",
        lambda *_, **__: RemainingBudgetAnswerContract(
            status="ready",
            user_id=1,
            local_date="2026-04-29",
            daily_target_kcal=1800,
            consumed_kcal=900,
            remaining_kcal=900,
            meal_count=1,
        ),
    )
    monkeypatch.setattr(module, "render_intake_reply", lambda **_: "Logged. milk tea 420 kcal.")
    monkeypatch.setattr(module, "write_intake_execution_trace_artifact", lambda **_: None)
    monkeypatch.setattr(module, "build_trace_refs", lambda **_: {"request_id": "req-output-honesty"})

    result = module.build_intake_execution_response(
        None,
        request_id="req-output-honesty",
        user_external_id="user-1",
        raw_user_input="milk tea",
        local_date="2026-04-29",
        allow_search=False,
        state_before=_View(),
        state_after=_View(),
        manager_decision=SimpleNamespace(
            intent_type="log_meal",
            workflow_effect="commit",
            response_summary="",
            pending_followup=None,
            tool_calls=[],
            llm_used=False,
            trace={},
        ),
        manager_result=SimpleNamespace(
            final_action="no_commit",
            workflow_effect="safe_failure",
            manager_rounds=[],
            tool_calls=[],
            tool_results=[],
        ),
        nutrition_artifact=None,
        persistence_result=None,
        budget_summary=None,
        tool_outputs={},
        state_mutation_summary={
            "meal_logged": True,
            "canonical_commit": True,
            "ledger_updated": True,
            "draft_saved": False,
            "new_meal_version_created": True,
            "old_version_superseded": True,
        },
        stage_timings=[],
        phase_a_trace={
            "phase_a_commit_boundary_preflight": {
                "checked": True,
                "blocked": True,
                "failure_family": "phase_a_commit_boundary_blocked",
            }
        },
    )

    assert result["assistant_message"] == "I could not safely complete that turn, so nothing was committed."
    assert result["state_delta"]["canonical_commit"] is False
    assert result["state_delta"]["ledger_updated"] is False
    assert result["sidecar"]["state_mutation_summary"]["meal_logged"] is False


@pytest.mark.asyncio
async def test_general_chat_route_applies_degraded_budget_output_honesty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_routes as module

    answer = RemainingBudgetAnswerContract(
        status="onboarding_required",
        user_id=1,
        local_date="2026-04-29",
        daily_target_kcal=0,
        consumed_kcal=600,
        remaining_kcal=500,
        meal_count=2,
    )
    captured_trace: dict[str, object] = {}
    captured_record: dict[str, object] = {}

    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(
        module,
        "build_current_turn_context_v1",
        lambda **_: CurrentTurnContextV1(
            user_utterance="how many calories can I still eat?",
            current_interaction_event=InteractionEvent(
                source="chat",
                event_type="user_message",
                raw_text="how many calories can I still eat?",
            ),
        ),
    )
    monkeypatch.setattr(
        module,
        "build_workflow_routing_decision",
        lambda **_: SimpleNamespace(
            target_workflow_family="general_chat",
            disposition="answer_only",
            required_read_surfaces=["CurrentBudgetView", "ActiveBodyPlanView"],
            phase_a_trace={},
        ),
    )
    monkeypatch.setattr(
        module,
        "build_general_chat_response_pass",
        lambda *_, **__: GeneralChatPassResult(
            target_workflow_family="general_chat",
            disposition="answer_only",
            workflow_effect="answer_budget_summary_without_state_mutation",
            required_read_surfaces=["CurrentBudgetView", "ActiveBodyPlanView"],
            reply_text="You have remaining 500 kcal today.",
            asked_follow_up=False,
            ui_hints={"mode": "general_chat_onboarding_required"},
            remaining_budget_contract=answer,
            active_body_plan_present=False,
        ),
    )

    def _capture_trace(**kwargs: object) -> None:
        captured_trace.update(kwargs)

    monkeypatch.setattr(module, "write_general_chat_request_trace_artifact", _capture_trace)
    monkeypatch.setattr(module, "record_runtime_turn_messages", lambda *_, **kwargs: captured_record.update(kwargs))

    result = await module.estimate(
        EstimateRequest(
            text="how many calories can I still eat?",
            user_id="user-1",
            local_date="2026-04-29",
            allow_search=False,
        ),
        SimpleNamespace(headers={}),
        db=None,
    )

    assert result["coach_message"] == "Onboarding is required before I can answer remaining budget."
    phase_a_trace = captured_trace["phase_a_trace"]
    assert isinstance(phase_a_trace, dict)
    assert captured_trace["local_date"] == "2026-04-29"
    assert phase_a_trace["phase_a_output_honesty"]["normalized"] is True
    assert "500" not in captured_trace["assistant_message"]
    assert captured_record["manager_context_packet_v1"] is not None
    assert captured_record["manager_context_packet_v1"]["metadata"]["context_policy_version"]
