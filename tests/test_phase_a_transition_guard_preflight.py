from __future__ import annotations

from types import SimpleNamespace
import inspect

import pytest

from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application import final_action_mutation_classifier as effect_policy
from app.intake.application.final_action_mutation_classifier import (
    classify_final_action_mutation,
    final_action_effect_class,
    final_action_has_persistence_effect,
)
from app.runtime.contracts.phase_a import TransitionGuardResult


def _transition_guard(verdict: str, *, reason: str = "test_guard") -> TransitionGuardResult:
    return TransitionGuardResult(
        verdict=verdict,
        reason=reason,
        blocked_mutation="meal_mutation" if verdict != "pass" else None,
        affected_object_type="meal_thread" if verdict != "pass" else "none",
        affected_object_id="77" if verdict != "pass" else None,
    )


def _resolved_state() -> SimpleNamespace:
    return SimpleNamespace(
        onboarding_ready=True,
        user_id=1,
        user_external_id="user-1",
        local_date="2026-04-29",
        active_body_plan_view=None,
        current_budget_view=None,
        conversation_state=None,
        injected_context={
            "ACTIVE_MEAL": None,
            "PENDING_FOLLOWUP": {
                "is_open": False,
                "meal_id": None,
                "meal_thread_id": None,
                "pending_question": None,
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": [],
            "TARGET_MEAL_REFERENCE": {
                "meal_thread_id": None,
                "meal_version_id": None,
                "meal_title": None,
                "target_resolution_source": "none",
                "correction_confidence": "low",
            },
            "SESSION_SUMMARY": {},
        },
    )


def test_transition_guard_preflight_blocks_answer_only_commit_effect() -> None:
    classification = classify_final_action_mutation(
        manager_payload={"final_action": "commit"},
        transition_guard_result=_transition_guard("answer_only"),
        persistence_effect_actions={"commit"},
    )

    assert classification.mutation_like is True
    assert classification.blocked is True
    assert classification.failure_family == "phase_a_transition_guard_blocked"
    assert classification.mutation_effect_class == "canonical_write"
    assert classification.trace_payload()["transition_guard_verdict"] == "answer_only"


def test_final_action_effect_policy_is_the_canonical_persistence_owner() -> None:
    assert final_action_effect_class("commit") == "canonical_write"
    assert final_action_effect_class("correction_applied") == "correction_persistence"
    assert final_action_effect_class("overshoot_note") == "ledger_mutation"
    assert final_action_effect_class("ask_followup") == "draft_pending_persistence"
    assert final_action_effect_class("request_clarification") == "none"
    assert final_action_has_persistence_effect("ask_followup") is True
    assert effect_policy.PERSISTENCE_EFFECT_ACTIONS == frozenset(
        {"commit", "correction_applied", "overshoot_note", "ask_followup"}
    )


def test_single_manager_prompt_names_commit_without_evidence_repair_tool() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "commit_without_evidence" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "manager_action='call_tools'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "estimate_nutrition" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_intake_persistence_consumes_effect_policy_instead_of_owning_action_set() -> None:
    from app.composition import intake_execution_persistence

    source = inspect.getsource(intake_execution_persistence)
    assert "COMMITTING_ACTIONS" not in source
    assert "final_action_has_persistence_effect" in source
    assert intake_execution_persistence.final_action_has_persistence_effect is final_action_has_persistence_effect


def test_transition_guard_preflight_classifies_ask_followup_by_effect_not_label() -> None:
    response_only = classify_final_action_mutation(
        manager_payload={"final_action": "ask_followup"},
        transition_guard_result=_transition_guard("clarify_required"),
        persistence_effect_actions=set(),
    )
    effectful = classify_final_action_mutation(
        manager_payload={"final_action": "ask_followup"},
        transition_guard_result=_transition_guard("clarify_required"),
        persistence_effect_actions={"ask_followup"},
    )

    assert response_only.mutation_like is False
    assert response_only.blocked is False
    assert response_only.mutation_effect_class == "none"
    assert effectful.mutation_like is True
    assert effectful.blocked is True
    assert effectful.mutation_effect_class == "draft_pending_persistence"


def test_transition_guard_preflight_allows_effectful_action_when_guard_passes() -> None:
    classification = classify_final_action_mutation(
        manager_payload={"final_action": "correction_applied"},
        transition_guard_result=_transition_guard("pass"),
        persistence_effect_actions={"correction_applied"},
    )

    assert classification.mutation_like is True
    assert classification.blocked is False
    assert classification.failure_family is None
    assert classification.mutation_effect_class == "correction_persistence"


def test_transition_guard_preflight_preserves_correction_target_unknown_reason() -> None:
    classification = classify_final_action_mutation(
        manager_payload={"final_action": "correction_applied"},
        transition_guard_result=TransitionGuardResult(
            verdict="clarify_required",
            reason="correction_target_unknown",
            blocked_mutation="correction",
            affected_object_type="meal_thread",
            affected_object_id=None,
        ),
        persistence_effect_actions={"correction_applied"},
    )

    trace = classification.trace_payload()
    assert classification.blocked is True
    assert trace["transition_guard_reason"] == "correction_target_unknown"
    assert trace["blocked_mutation"] == "correction"


class _SequenceProvider:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def readiness(self) -> dict[str, object]:
        return {"configured": True}

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        return self.responses.pop(0), {"source": "fake", "call_index": len(self.calls)}


def _manager_final_payload(final_action: str) -> dict[str, object]:
    return {
        "manager_action": "final",
        "intent": "log_meal",
        "final_action": final_action,
        "workflow_effect": final_action,
        "target_attachment": {"mode": "none"},
        "exactness": "unknown",
        "confidence": "medium",
        "evidence_posture": "none",
        "repair_ack": False,
        "answer_contract": {"reply_text": "ok"},
        "uncertainty_posture": "bounded",
        "evidence_honesty_posture": "none",
    }


@pytest.mark.asyncio
async def test_process_bundle2_intake_blocks_answer_only_commit_before_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="what is left today?",
        resolved_state=resolved_state,
    )
    provider = _SequenceProvider(
        [
            _manager_final_payload("commit"),
            _manager_final_payload("commit"),
        ]
    )
    persisted: list[object] = []

    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "resolve_v2_bundle1_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(
        module,
        "persist_bundle2_artifact",
        lambda *args, **kwargs: persisted.append((args, kwargs)) if kwargs["final_action"] != "no_commit" else None,
    )
    monkeypatch.setattr(
        module,
        "build_bundle2_response",
        lambda *_, **kwargs: {
            "manager_result": kwargs["manager_result"],
            "phase_a_trace": kwargs["phase_a_trace"],
            "state_mutation_summary": kwargs["state_mutation_summary"],
        },
    )

    result = await module.process_bundle2_intake(
        None,
        user_external_id="user-1",
        raw_user_input="what is left today?",
        local_date="2026-04-29",
        allow_search=False,
        provider=provider,
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal"),
        request_id="req-guard",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    manager_result = result["manager_result"]
    preflight = manager_result.guard_outcome["phase_a_transition_guard_preflight"]
    assert persisted == []
    assert manager_result.final_action == "no_commit"
    assert manager_result.request_failure_family == "phase_a_transition_guard_blocked"
    assert preflight["blocked"] is True
    assert preflight["manager_final_action"] == "commit"
    assert preflight["transition_guard_verdict"] == "answer_only"
    assert preflight["repair_attempted"] is True
    assert preflight["repair_result"] == "failed"


@pytest.mark.asyncio
async def test_process_bundle2_intake_records_successful_repair_after_guard_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="what is left today?",
        resolved_state=resolved_state,
    )
    provider = _SequenceProvider(
        [
            _manager_final_payload("commit"),
            _manager_final_payload("no_commit"),
        ]
    )

    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "resolve_v2_bundle1_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "persist_bundle2_artifact", lambda *_, **__: None)
    monkeypatch.setattr(
        module,
        "build_bundle2_response",
        lambda *_, **kwargs: {"manager_result": kwargs["manager_result"]},
    )

    result = await module.process_bundle2_intake(
        None,
        user_external_id="user-1",
        raw_user_input="what is left today?",
        local_date="2026-04-29",
        allow_search=False,
        provider=provider,
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal"),
        request_id="req-guard-repair",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    manager_result = result["manager_result"]
    preflight = manager_result.guard_outcome["phase_a_transition_guard_preflight"]
    assert manager_result.final_action == "no_commit"
    assert manager_result.request_failure_family is None
    assert manager_result.repair_round_used is True
    assert preflight["blocked"] is False
    assert preflight["repair_attempted"] is True
    assert preflight["repair_result"] == "passed_after_repair"


@pytest.mark.asyncio
async def test_process_bundle2_intake_repairs_commit_without_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="我吃了一顆茶葉蛋",
        resolved_state=resolved_state,
    )
    commit_payload = _manager_final_payload("commit")
    commit_payload["semantic_decision"] = {
        "semantic_authority": "manager_llm",
        "current_turn_intent": "log_meal",
        "target_attachment": {},
        "workflow_effect": "commit",
        "final_action_candidate": "commit",
        "estimation_posture": "requires_nutrition_estimate",
        "followup_posture": "closed",
        "mutation_intent_candidate": "canonical_write",
        "uncertainty_posture": "low",
        "source": "test",
    }
    provider = _SequenceProvider(
        [
            commit_payload,
            _manager_final_payload("no_commit"),
        ]
    )

    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "resolve_v2_bundle1_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "persist_bundle2_artifact", lambda *_, **__: None)
    monkeypatch.setattr(
        module,
        "build_bundle2_response",
        lambda *_, **kwargs: {"manager_result": kwargs["manager_result"]},
    )

    result = await module.process_bundle2_intake(
        None,
        user_external_id="user-1",
        raw_user_input="我吃了一顆茶葉蛋",
        local_date="2026-04-29",
        allow_search=False,
        provider=provider,
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal"),
        request_id="req-commit-without-evidence",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    manager_result = result["manager_result"]
    assert len(provider.calls) == 2
    assert provider.calls[1]["user_payload"]["guard_feedback"]["failure_family"] == "commit_without_evidence"
    assert provider.calls[1]["user_payload"]["constraints"]["guard_feedback_repair_request"] is True
    assert provider.calls[1]["user_payload"]["constraints"]["guard_feedback_failure_family"] == "commit_without_evidence"
    assert manager_result.repair_round_used is True
    assert manager_result.final_action == "no_commit"
