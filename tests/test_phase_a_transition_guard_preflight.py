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


def test_overshoot_note_with_manager_canonical_write_is_not_blocked_by_answer_only_preflight() -> None:
    classification = classify_final_action_mutation(
        manager_payload={
            "final_action": "overshoot_note",
            "semantic_decision": {
                "semantic_authority": "manager_llm",
                "current_turn_intent": "log_meal",
                "final_action_candidate": "overshoot_note",
                "mutation_intent_candidate": "canonical_write",
            },
        },
        transition_guard_result=_transition_guard("answer_only"),
        persistence_effect_actions={"overshoot_note"},
    )

    assert classification.mutation_like is True
    assert classification.blocked is False
    assert classification.mutation_effect_class == "ledger_mutation"
    assert classification.transition_guard_verdict == "pass"
    assert classification.transition_guard_reason == "manager_semantic_decision_authorized_mutation"


def test_single_manager_prompt_names_commit_without_evidence_repair_tool() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "commit_without_evidence" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "manager_action='call_tools'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "estimate_nutrition" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_single_manager_prompt_separates_pending_draft_answer_from_optional_refinement() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "blocking pending follow-up answer for an unresolved draft" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "use current_turn_intent='log_meal'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "final_action='commit'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "Optional refinement of an already committed item" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "correct_meal/correction_applied" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_single_manager_prompt_routes_body_observation_from_non_body_scope() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "When manager_loop_scope is not 'body_observation'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "workflow_effect='route_to_body_observation'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "final_action='no_commit'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "Do not use final_action='commit' for body observations outside body_observation scope" in (
        SINGLE_MANAGER_SYSTEM_PROMPT
    )


def test_single_manager_prompt_uses_context_for_correction_and_named_removal() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "apply the user's removal or portion change to the existing item candidates" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "keep unchanged prior components from ACTIVE_MEAL or RECENT_COMMITTED_MEALS_SUMMARY" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "call estimate_nutrition for the updated component list" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "If the user names a meal slot such as 早餐/breakfast" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "select that matching meal_thread_id from RECENT_COMMITTED_MEALS_SUMMARY" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "target_display_name, display_name, or meal_title contains that slot" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "target_display_name alone is not a valid target" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "include the concrete meal_thread_id and meal_version_id" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "use operation='update_meal_components'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "do not use operation='correct_item'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "do not expose meal_thread_id" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_single_manager_prompt_keeps_chain_menu_set_meals_on_manager_owned_exact_lookup() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT
    from app.runtime.agent.founder_live_manager_tool_description import (
        founder_live_manager_tool_description,
    )

    tool_description = founder_live_manager_tool_description()

    assert "named brand or chain menu set meal" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "include base_dish or product identity" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "retrieval_goal='exact_brand_lookup'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "do not downgrade it to a composition-unknown basket" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "named brand or chain menu set meal" in tool_description
    assert "exact_brand_lookup" in tool_description


def test_single_manager_prompt_keeps_listed_brand_combos_on_component_lookup() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT
    from app.runtime.agent.founder_live_manager_tool_description import (
        founder_live_manager_tool_description,
    )

    tool_description = founder_live_manager_tool_description()

    assert "brand combo with user-listed components" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "listed-items rule has priority over exact brand lookup" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "listed_item_lookup" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "component list the user already supplied" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "brand combo with user-listed components" in tool_description
    assert "do not repeat the component-list question" in tool_description


def test_single_manager_prompt_forbids_exact_lookup_when_listed_items_are_present() -> None:
    from app.runtime.agent.manager_branch_shapes import manager_semantic_decision_schema
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT
    from app.runtime.agent.founder_live_manager_tool_description import (
        founder_live_manager_tool_description,
    )

    tool_description = founder_live_manager_tool_description()
    listed_items_description = manager_semantic_decision_schema()["properties"]["listed_items"]["description"]
    retrieval_goal_description = manager_semantic_decision_schema()["properties"]["retrieval_goal"]["description"]

    assert "If semantic_decision.listed_items is non-empty" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "retrieval_goal='listed_item_lookup'" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "never exact_brand_lookup with non-empty listed_items" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "If semantic_decision.listed_items is non-empty" in tool_description
    assert "never exact_brand_lookup with non-empty listed_items" in tool_description
    assert "non-empty listed_items" in listed_items_description
    assert "never exact_brand_lookup" in retrieval_goal_description
    assert "combo plus concrete items" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "put the main item and named side/drink items in semantic_decision.listed_items" in (
        SINGLE_MANAGER_SYSTEM_PROMPT
    )
    assert "combo plus concrete items" in tool_description


def test_single_manager_prompt_explains_rejected_web_evidence_before_followup() -> None:
    from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT

    assert "wrong-context or rejected Web evidence" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "explain that the source was not used" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "wrong_context_source_rejected=true" in SINGLE_MANAGER_SYSTEM_PROMPT
    assert "source was not adopted" in SINGLE_MANAGER_SYSTEM_PROMPT


def test_pending_followup_attach_guard_requests_repair_for_unresolved_draft_correction() -> None:
    from app.composition.pending_followup_attach_guard import (
        pending_followup_attach_repair_outcome,
    )

    outcome = pending_followup_attach_repair_outcome(
        manager_payload={
            "final_action": "correction_applied",
            "workflow_effect": "correction_applied",
            "semantic_decision": {
                "current_turn_intent": "correct_meal",
                "mutation_intent_candidate": "correction_write",
                "target_attachment": {
                    "operation": "attach_to_pending_followup",
                    "target_resolution_source": "pending_followup_state",
                },
            },
        },
        correction_target={
            "meal_thread_id": None,
            "meal_version_id": None,
            "target_resolution_source": "pending_followup_state",
        },
    )

    assert outcome == {
        "ok": False,
        "repair_request": True,
        "failure_family": "pending_followup_attach_requires_commit",
        "repair_instruction": (
            "A blocking pending follow-up answer for an unresolved draft completes a new meal log: "
            "use current_turn_intent='log_meal', final_action='commit', "
            "workflow_effect='commit', and mutation_intent_candidate='canonical_write'. "
            "Use correct_meal/correction_applied only for optional refinement of an already committed target."
        ),
    }


def test_pending_followup_attach_guard_requires_explicit_target_for_write() -> None:
    from app.composition.pending_followup_attach_guard import (
        pending_followup_attach_repair_outcome,
    )

    outcome = pending_followup_attach_repair_outcome(
        manager_payload={
            "final_action": "commit",
            "workflow_effect": "commit",
            "target_attachment": {},
            "semantic_decision": {
                "current_turn_intent": "log_meal",
                "mutation_intent_candidate": "canonical_write",
                "target_attachment": {},
            },
        },
        correction_target={
            "target_resolution_source": "pending_followup_state",
            "source_meal_id": "draft-1",
        },
    )

    assert outcome is not None
    assert outcome["failure_family"] == "pending_followup_commit_requires_explicit_target"
    assert outcome["repair_request"] is True
    assert "target_attachment={}" in outcome["repair_instruction"]


def test_pending_followup_attach_guard_allows_manager_explicit_new_meal_choice() -> None:
    from app.composition.pending_followup_attach_guard import (
        pending_followup_attach_repair_outcome,
    )

    outcome = pending_followup_attach_repair_outcome(
        manager_payload={
            "final_action": "commit",
            "workflow_effect": "commit",
            "target_attachment": {"mode": "new_meal"},
            "semantic_decision": {
                "current_turn_intent": "log_meal",
                "mutation_intent_candidate": "canonical_write",
                "target_attachment": {"mode": "new_meal"},
            },
        },
        correction_target={},
        pending_followup={"is_open": True, "source_meal_id": "draft-1"},
    )

    assert outcome is None


def test_pending_followup_attach_guard_allows_manager_pending_attach_choice() -> None:
    from app.composition.pending_followup_attach_guard import (
        pending_followup_attach_repair_outcome,
    )

    outcome = pending_followup_attach_repair_outcome(
        manager_payload={
            "final_action": "commit",
            "workflow_effect": "commit",
            "target_attachment": {
                "operation": "attach_to_pending_followup",
                "target_resolution_source": "pending_followup_state",
                "source_meal_id": "draft-1",
            },
            "semantic_decision": {
                "current_turn_intent": "log_meal",
                "mutation_intent_candidate": "canonical_write",
                "target_attachment": {
                    "operation": "attach_to_pending_followup",
                    "target_resolution_source": "pending_followup_state",
                    "source_meal_id": "draft-1",
                },
            },
        },
        correction_target={},
        pending_followup={"is_open": True, "source_meal_id": "draft-1"},
    )

    assert outcome is None


def test_pending_followup_attach_guard_does_not_block_resolved_committed_refinement() -> None:
    from app.composition.pending_followup_attach_guard import (
        pending_followup_attach_repair_outcome,
    )

    outcome = pending_followup_attach_repair_outcome(
        manager_payload={
            "final_action": "correction_applied",
            "workflow_effect": "correction_applied",
            "semantic_decision": {
                "current_turn_intent": "correct_meal",
                "mutation_intent_candidate": "correction_write",
                "target_attachment": {
                    "operation": "attach_to_pending_followup",
                    "target_resolution_source": "pending_followup_state",
                },
            },
        },
        correction_target={
            "meal_thread_id": 10,
            "meal_version_id": 20,
            "operation": "update_meal_components",
            "target_resolution_source": "pending_followup_state",
        },
    )

    assert outcome is None


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
async def test_process_intake_execution_turn_blocks_answer_only_commit_before_persistence(
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
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(
        module,
        "persist_intake_execution_artifact",
        lambda *args, **kwargs: persisted.append((args, kwargs)) if kwargs["final_action"] != "no_commit" else None,
    )
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {
            "manager_result": kwargs["manager_result"],
            "phase_a_trace": kwargs["phase_a_trace"],
            "state_mutation_summary": kwargs["state_mutation_summary"],
        },
    )

    result = await module.process_intake_execution_turn(
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
async def test_process_intake_execution_turn_records_successful_repair_after_guard_block(
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
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", lambda *_, **__: None)
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {"manager_result": kwargs["manager_result"]},
    )

    result = await module.process_intake_execution_turn(
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
async def test_process_intake_execution_turn_repairs_commit_without_evidence(
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
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", lambda *_, **__: None)
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {"manager_result": kwargs["manager_result"]},
    )

    result = await module.process_intake_execution_turn(
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
