from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.composition.commit_boundary_preflight import run_commit_boundary_preflight
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.final_action_mutation_classifier import classify_final_action_mutation
from app.shared.contracts.intake_results import EstimatePayload
from app.runtime.contracts.phase_a import TransitionGuardResult


def _payload(
    *,
    estimated_kcal: int,
    action_taken: str = "direct_answer",
    route_target: str = "direct_answer",
    canonical_write_allowed: bool = True,
    followup_question: str | None = None,
) -> EstimatePayload:
    return EstimatePayload(
        request_id="req-preflight",
        meal_title="milk tea",
        estimated_kcal=estimated_kcal,
        action_taken=action_taken,
        route_target=route_target,
        follow_up_needed=bool(followup_question),
        followup_question=followup_question,
        trace_contract={
            "canonical_write_decision": {"can_write_canonical": canonical_write_allowed},
            "followup_question": followup_question,
            "unresolved_info": [followup_question] if followup_question else [],
        },
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


def test_commit_boundary_preflight_allows_canonical_write_commit() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(estimated_kcal=420),
        manager_final_action="commit",
        active_body_plan_present=True,
    )

    assert result.blocked is False
    assert result.mutation_effect_class == "canonical_write"
    assert result.projected_commit_intent == "commit"
    assert result.canonical_write_allowed is True


def test_commit_boundary_preflight_blocks_canonical_write_when_projection_is_draft() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(
            estimated_kcal=420,
            action_taken="answer_with_uncertainty",
            route_target="clarify_user_private",
            canonical_write_allowed=False,
            followup_question="What size was it?",
        ),
        manager_final_action="commit",
        active_body_plan_present=True,
    )

    assert result.blocked is True
    assert result.failure_family == "phase_a_commit_boundary_blocked"
    assert result.mutation_effect_class == "canonical_write"
    assert result.projected_commit_intent == "draft"
    assert result.canonical_write_allowed is False


def test_commit_boundary_preflight_allows_manager_authorized_estimate_with_followup() -> None:
    payload = _payload(
        estimated_kcal=420,
        action_taken="answer_with_uncertainty",
        route_target="clarify_user_private",
        canonical_write_allowed=False,
        followup_question="What size was it?",
    )

    result = run_commit_boundary_preflight(
        payload=payload,
        manager_final_action="commit",
        active_body_plan_present=True,
        manager_semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "workflow_effect": "estimate_with_followup",
            "final_action_candidate": "commit",
            "mutation_intent_candidate": "canonical_write",
        },
    )

    assert result.blocked is False
    assert result.projected_commit_intent == "commit"
    assert result.predicted_meal_status == "completed_meal"
    assert result.canonical_write_allowed is True
    assert payload.trace_contract["canonical_write_decision"]["source"] == "manager_semantic_decision"


def test_commit_boundary_preflight_blocks_manager_authorized_shadow_stub_commit() -> None:
    payload = _payload(
        estimated_kcal=400,
        action_taken="direct_answer",
        route_target="direct_answer",
        canonical_write_allowed=True,
    )
    payload.trace_contract["shadow_stub"] = True

    result = run_commit_boundary_preflight(
        payload=payload,
        manager_final_action="commit",
        active_body_plan_present=True,
        manager_semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "workflow_effect": "commit",
            "final_action_candidate": "commit",
            "mutation_intent_candidate": "canonical_write",
        },
    )

    decision = payload.trace_contract["canonical_write_decision"]
    assert result.blocked is True
    assert result.failure_family == "nutrition_evidence_not_commit_eligible"
    assert result.projected_commit_intent == "no_mutation"
    assert result.canonical_write_allowed is False
    assert decision["can_write_canonical"] is False
    assert decision["source"] == "commit_evidence_policy"
    assert "shadow_stub_estimate" in decision["blockers"]


def test_manager_semantic_decision_can_supersede_pre_manager_answer_only_guard() -> None:
    result = classify_final_action_mutation(
        manager_payload={
            "final_action": "commit",
            "semantic_decision": {
                "semantic_authority": "manager_llm",
                "current_turn_intent": "log_meal",
                "workflow_effect": "estimate_with_followup",
                "final_action_candidate": "commit",
                "mutation_intent_candidate": "canonical_write",
            },
        },
        transition_guard_result=TransitionGuardResult(
            verdict="answer_only",
            reason="pre_manager_no_intake_signal",
            blocked_mutation="meal_mutation",
        ),
    )

    assert result.blocked is False
    assert result.transition_guard_verdict == "pass"
    assert result.transition_guard_reason == "manager_semantic_decision_authorized_mutation"


def test_commit_boundary_preflight_allows_draft_pending_persistence_for_projected_draft() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(
            estimated_kcal=420,
            action_taken="answer_with_uncertainty",
            route_target="clarify_user_private",
            canonical_write_allowed=False,
            followup_question="What size was it?",
        ),
        manager_final_action="ask_followup",
        active_body_plan_present=True,
    )

    assert result.blocked is False
    assert result.mutation_effect_class == "draft_pending_persistence"
    assert result.projected_commit_intent == "draft"
    assert result.ledger_mutation_allowed is False


def test_commit_boundary_preflight_blocks_draft_pending_persistence_for_projected_commit() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(estimated_kcal=420),
        manager_final_action="ask_followup",
        active_body_plan_present=True,
    )

    assert result.blocked is True
    assert result.failure_family == "phase_a_commit_boundary_blocked"
    assert result.mutation_effect_class == "draft_pending_persistence"
    assert result.projected_commit_intent == "commit"


def test_commit_boundary_preflight_checks_ledger_mutation_separately_from_canonical_write() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(estimated_kcal=420, canonical_write_allowed=False),
        manager_final_action="overshoot_note",
        active_body_plan_present=True,
    )

    assert result.blocked is True
    assert result.mutation_effect_class == "ledger_mutation"
    assert result.ledger_mutation_allowed is False


def test_commit_boundary_preflight_allows_ledger_mutation_when_projection_allows_it() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(estimated_kcal=420),
        manager_final_action="overshoot_note",
        active_body_plan_present=True,
    )

    assert result.blocked is False
    assert result.mutation_effect_class == "ledger_mutation"
    assert result.ledger_mutation_allowed is True


def test_commit_boundary_preflight_bypasses_non_persistence_effect() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(estimated_kcal=420),
        manager_final_action="no_commit",
        active_body_plan_present=True,
    )

    trace = result.trace_payload()
    assert result.blocked is False
    assert result.bypassed is True
    assert trace["bypass_reason"] == "non_persistence_effect"


def test_commit_boundary_preflight_blocks_unresolved_correction_when_target_evidence_exists() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(estimated_kcal=420),
        manager_final_action="correction_applied",
        active_body_plan_present=True,
        correction_target={"target_resolution_source": "history_expansion", "meal_thread_id": None},
    )

    assert result.blocked is True
    assert result.mutation_effect_class == "correction_persistence"
    assert result.correction_target_resolved is False


def test_commit_boundary_preflight_allows_correction_with_resolved_target() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(estimated_kcal=420),
        manager_final_action="correction_applied",
        active_body_plan_present=True,
        correction_target={"target_resolution_source": "history_expansion", "meal_thread_id": 77, "meal_item_id": 8801},
    )

    assert result.blocked is False
    assert result.mutation_effect_class == "correction_persistence"
    assert result.correction_target_resolved is True


def test_commit_boundary_preflight_blocks_correction_with_thread_but_missing_item_target() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(estimated_kcal=420),
        manager_final_action="correction_applied",
        active_body_plan_present=True,
        correction_target={"target_resolution_source": "history_expansion", "meal_thread_id": 77},
    )

    assert result.blocked is True
    assert result.correction_target_resolved is False
    assert result.trace_payload()["correction_target_validation"]["failure_family"] == "correction_item_target_missing"


def test_commit_boundary_preflight_allows_manager_owned_thread_level_correction() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(estimated_kcal=300),
        manager_final_action="correction_applied",
        active_body_plan_present=True,
        correction_target={
            "target_resolution_source": "manager_target_proposal_validated",
            "meal_thread_id": 77,
            "operation": "correct_active_meal",
            "correction_operation": "correct_active_meal",
        },
        manager_semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "correct_meal",
            "workflow_effect": "correction_applied",
            "final_action_candidate": "correction_applied",
            "mutation_intent_candidate": "correction_write",
        },
    )

    assert result.blocked is False
    assert result.mutation_effect_class == "correction_persistence"
    assert result.correction_target_resolved is True
    assert result.trace_payload()["correction_target_validation"]["truth_owner"] == "meal_thread_id"


def test_commit_boundary_preflight_traces_canonical_name_mismatch_without_using_name_as_authority() -> None:
    result = run_commit_boundary_preflight(
        payload=_payload(estimated_kcal=420),
        manager_final_action="correction_applied",
        active_body_plan_present=True,
        correction_target={
            "target_resolution_source": "history_expansion",
            "meal_thread_id": 77,
            "meal_item_id": 8801,
            "canonical_name": "pearl milk tea",
            "observed_canonical_name": "chicken rice",
        },
    )

    assert result.blocked is True
    assert result.correction_target_resolved is False
    trace = result.trace_payload()["correction_target_validation"]
    assert trace["failure_family"] == "correction_canonical_name_mismatch"
    assert trace["truth_owner"] == "meal_item_id"


class _Provider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def readiness(self) -> dict[str, object]:
        return {"configured": True}

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        if len(self.calls) == 1:
            return {"manager_action": "call_tools", "tool_calls": [{"name": "estimate_nutrition"}]}, {"source": "fake"}
        return (
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "commit",
                "workflow_effect": "commit",
                "target_attachment": {"mode": "new_meal"},
                "exactness": "anchored",
                "confidence": "medium",
                "evidence_posture": "generic_with_uncertainty",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "generic_with_uncertainty",
                "semantic_decision": {
                    "semantic_authority": "manager_llm",
                    "current_turn_intent": "log_meal",
                    "target_attachment": {"mode": "new_workflow"},
                    "workflow_effect": "commit",
                    "final_action_candidate": "commit",
                    "estimation_posture": "estimable",
                    "followup_posture": "none",
                    "mutation_intent_candidate": "canonical_write",
                    "uncertainty_posture": "bounded_estimate",
                    "source": "test_provider",
                },
            },
            {"source": "fake"},
        )


class _RepairingProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def readiness(self) -> dict[str, object]:
        return {"configured": True}

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        if len(self.calls) == 1:
            return {"manager_action": "call_tools", "tool_calls": [{"name": "estimate_nutrition"}]}, {"source": "fake"}
        if len(self.calls) == 2:
            return (
                {
                    "manager_action": "final",
                    "intent": "log_meal",
                    "final_action": "commit",
                    "workflow_effect": "commit",
                    "target_attachment": {"mode": "new_meal"},
                    "exactness": "estimated",
                    "confidence": "medium",
                    "evidence_posture": "tool_estimated",
                    "repair_ack": False,
                    "answer_contract": {"reply_text": "logged"},
                    "uncertainty_posture": "bounded",
                    "evidence_honesty_posture": "tool_estimated",
                    "semantic_decision": {
                        "semantic_authority": "manager_llm",
                        "current_turn_intent": "log_meal",
                        "target_attachment": {"mode": "new_workflow"},
                        "workflow_effect": "commit",
                        "final_action_candidate": "commit",
                        "estimation_posture": "estimable",
                        "followup_posture": "none",
                        "mutation_intent_candidate": "canonical_write",
                        "uncertainty_posture": "bounded_estimate",
                        "source": "test_provider",
                    },
                },
                {"source": "fake"},
            )
        return (
            {
                "manager_action": "final",
                "intent": "log_meal",
                "intent_type": "log_meal",
                "final_action": "ask_followup",
                "workflow_effect": "ask_followup",
                "target_attachment": {"mode": "new_workflow"},
                "exactness": "unknown",
                "confidence": "low",
                "evidence_posture": "composition_unknown",
                "repair_ack": True,
                "answer_contract": {
                    "reply_text": "I need the combo contents first.",
                    "followup_question": "What did the combo include?",
                },
                "uncertainty_posture": "composition_unknown_basket",
                "evidence_honesty_posture": "needs_user_details",
                "semantic_decision": {
                    "semantic_authority": "manager_llm",
                    "current_turn_intent": "log_meal",
                    "target_attachment": {"mode": "new_workflow"},
                    "workflow_effect": "ask_followup",
                    "final_action_candidate": "ask_followup",
                    "estimation_posture": "composition_unknown_basket",
                    "followup_posture": "refinement_not_commit_gate",
                    "mutation_intent_candidate": "no_mutation",
                    "uncertainty_posture": "composition_unknown_basket",
                    "followup_question": "What did the combo include?",
                    "source": "test_provider_repair",
                },
            },
            {"source": "fake"},
        )


class _FirstPassAskProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def readiness(self) -> dict[str, object]:
        return {"configured": True}

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        return (
            {
                "manager_action": "final",
                "intent": "log_meal",
                "intent_type": "log_meal",
                "final_action": "ask_followup",
                "workflow_effect": "ask_followup",
                "target_attachment": {"mode": "new_workflow"},
                "exactness": "unknown",
                "confidence": "low",
                "evidence_posture": "composition_unknown",
                "repair_ack": False,
                "answer_contract": {
                    "reply_text": "I need the combo contents first.",
                    "followup_question": "What did the combo include?",
                },
                "uncertainty_posture": "composition_unknown_basket",
                "evidence_honesty_posture": "needs_user_details",
                "semantic_decision": {
                    "semantic_authority": "manager_llm",
                    "current_turn_intent": "log_meal",
                    "target_attachment": {"mode": "new_workflow"},
                    "workflow_effect": "ask_followup",
                    "final_action_candidate": "ask_followup",
                    "estimation_posture": "composition_unknown_basket",
                    "followup_posture": "refinement_not_commit_gate",
                    "mutation_intent_candidate": "no_mutation",
                    "uncertainty_posture": "composition_unknown_basket",
                    "followup_question": "What did the combo include?",
                    "source": "test_provider_first_pass_ask",
                },
            },
            {"source": "fake"},
        )


@pytest.mark.asyncio
async def test_process_intake_execution_turn_blocks_commit_boundary_contradiction_before_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="I ate milk tea meal",
        resolved_state=resolved_state,
    )
    nutrition_artifact = SimpleNamespace(
        payload=_payload(
            estimated_kcal=420,
            action_taken="answer_with_uncertainty",
            route_target="clarify_user_private",
            canonical_write_allowed=False,
            followup_question="What size was it?",
        )
    )
    nutrition_artifact.payload.trace_contract["blocking_slots"] = ["item_identity"]
    persisted: list[object] = []

    async def _fake_execute_manager_tool_calls(**kwargs: object) -> list[dict[str, object]]:
        kwargs["tool_state"]["nutrition_artifact"] = nutrition_artifact
        return [{"tool_name": "estimate_nutrition", "failure_family": None}]

    monkeypatch.setattr(module, "execute_manager_tool_calls", _fake_execute_manager_tool_calls)
    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", lambda *args, **kwargs: persisted.append((args, kwargs)))
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {
            "persistence_result": kwargs["persistence_result"],
            "phase_a_trace": kwargs["phase_a_trace"],
            "state_mutation_summary": kwargs["state_mutation_summary"],
        },
    )

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="I ate milk tea meal",
        local_date="2026-04-29",
        allow_search=False,
        provider=_Provider(),
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal", tool_calls=(), llm_used=False),
        request_id="req-commit-boundary",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    preflight = result["phase_a_trace"]["phase_a_commit_boundary_preflight"]
    assert persisted == []
    assert result["persistence_result"] is None
    assert preflight["blocked"] is True
    assert preflight["failure_family"] == "phase_a_commit_boundary_blocked"
    assert preflight["mutation_effect_class"] == "canonical_write"
    assert result["state_mutation_summary"]["canonical_commit"] is False


@pytest.mark.asyncio
async def test_process_intake_execution_turn_blocks_shadow_stub_commit_before_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    resolved_state = _resolved_state()
    resolved_state.current_budget_view = SimpleNamespace(
        budget_kcal=1312,
        consumed_kcal=0,
        remaining_kcal=1312,
    )
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="I ate a breakfast shop combo",
        resolved_state=resolved_state,
    )
    nutrition_artifact = SimpleNamespace(
        payload=_payload(estimated_kcal=400),
    )
    nutrition_artifact.payload.trace_contract["shadow_stub"] = True
    persisted: list[object] = []

    async def _fake_execute_manager_tool_calls(**kwargs: object) -> list[dict[str, object]]:
        kwargs["tool_state"]["nutrition_artifact"] = nutrition_artifact
        kwargs["tool_state"]["budget_summary"] = {
            "budget_kcal": 1312,
            "consumed_kcal_before": 0,
            "predicted_consumed_kcal_after": 400,
            "predicted_remaining_kcal_after": 912,
            "overshoot_detected": False,
            "overshoot_kcal": 0,
        }
        return [{"tool_name": "estimate_nutrition", "failure_family": None}]

    monkeypatch.setattr(module, "execute_manager_tool_calls", _fake_execute_manager_tool_calls)
    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", lambda *args, **kwargs: persisted.append((args, kwargs)))
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {
            "persistence_result": kwargs["persistence_result"],
            "phase_a_trace": kwargs["phase_a_trace"],
            "state_mutation_summary": kwargs["state_mutation_summary"],
            "budget_summary": kwargs["budget_summary"],
        },
    )

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="I ate a breakfast shop combo",
        local_date="2026-04-29",
        allow_search=False,
        provider=_Provider(),
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal", tool_calls=(), llm_used=False),
        request_id="req-shadow-stub-block",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    preflight = result["phase_a_trace"]["phase_a_commit_boundary_preflight"]
    assert persisted == []
    assert result["persistence_result"] is None
    assert preflight["blocked"] is True
    assert preflight["failure_family"] == "nutrition_evidence_not_commit_eligible"
    assert result["budget_summary"]["predicted_consumed_kcal_after"] == 0
    assert result["budget_summary"]["predicted_remaining_kcal_after"] == 1312
    assert result["state_mutation_summary"]["canonical_commit"] is False


@pytest.mark.asyncio
async def test_process_intake_execution_turn_repairs_shadow_stub_commit_to_manager_followup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    provider = _RepairingProvider()
    resolved_state = _resolved_state()
    resolved_state.current_budget_view = SimpleNamespace(
        budget_kcal=1312,
        consumed_kcal=0,
        remaining_kcal=1312,
    )
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="I ate a breakfast shop combo",
        resolved_state=resolved_state,
    )
    nutrition_artifact = SimpleNamespace(
        payload=_payload(estimated_kcal=400),
    )
    nutrition_artifact.payload.trace_contract["shadow_stub"] = True
    persisted: list[object] = []

    async def _fake_execute_manager_tool_calls(**kwargs: object) -> list[dict[str, object]]:
        kwargs["tool_state"]["nutrition_artifact"] = nutrition_artifact
        return [{"tool_name": "estimate_nutrition", "failure_family": None}]

    monkeypatch.setattr(module, "execute_manager_tool_calls", _fake_execute_manager_tool_calls)
    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", lambda *args, **kwargs: persisted.append((args, kwargs)))
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {
            "manager_result": kwargs["manager_result"],
            "persistence_result": kwargs["persistence_result"],
            "phase_a_trace": kwargs["phase_a_trace"],
            "nutrition_payload": getattr(kwargs["nutrition_artifact"], "payload", None),
        },
    )

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="I ate a breakfast shop combo",
        local_date="2026-04-29",
        allow_search=False,
        provider=provider,
        state_before=resolved_state,
        manager_decision=SimpleNamespace(intent_type="log_meal", tool_calls=(), llm_used=False),
        request_id="req-shadow-stub-repair",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    manager_result = result["manager_result"]
    payload = result["nutrition_payload"]
    assert len(provider.calls) == 3
    assert provider.calls[2]["user_payload"]["guard_feedback"]["failure_family"] == "nutrition_evidence_not_commit_eligible"
    assert manager_result.final_action == "ask_followup"
    assert manager_result.workflow_effect == "ask_followup"
    assert manager_result.repair_round_used is True
    assert persisted
    assert getattr(payload, "estimated_kcal", None) == 0
    assert payload.trace_contract["manager_ask_followup_draft_contract"]["raw_text_semantic_inference"] is False


@pytest.mark.asyncio
async def test_entry_handoff_shadow_stub_does_not_supply_initial_guard_feedback_before_intake_provider_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_orchestrator as module

    provider = _FirstPassAskProvider()
    resolved_state = _resolved_state()
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="I ate a breakfast shop combo",
        resolved_state=resolved_state,
    )
    nutrition_artifact = SimpleNamespace(payload=_payload(estimated_kcal=400))
    nutrition_artifact.payload.trace_contract["shadow_stub"] = True
    persisted: list[object] = []

    async def _fake_execute_manager_tool_calls(**kwargs: object) -> list[dict[str, object]]:
        kwargs["tool_state"]["nutrition_artifact"] = nutrition_artifact
        return [{"tool_name": "estimate_nutrition", "failure_family": None}]

    monkeypatch.setattr(module, "execute_manager_tool_calls", _fake_execute_manager_tool_calls)
    monkeypatch.setattr(module, "resolve_correction_target_tool", lambda **_: {})
    monkeypatch.setattr(module, "append_trace_event_tool", lambda **_: None)
    monkeypatch.setattr(module, "resolve_intake_state", lambda *_, **__: resolved_state)
    monkeypatch.setattr(module, "persist_intake_execution_artifact", lambda *args, **kwargs: persisted.append((args, kwargs)))
    monkeypatch.setattr(
        module,
        "build_intake_execution_response",
        lambda *_, **kwargs: {
            "manager_result": kwargs["manager_result"],
            "nutrition_payload": getattr(kwargs["nutrition_artifact"], "payload", None),
        },
    )
    entry_manager_decision = SimpleNamespace(
        workflow_effect="route_to_intake",
        intent_type="log_meal",
        target_attachment={},
        semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "target_attachment": {},
            "workflow_effect": "route_to_intake",
            "final_action_candidate": "commit",
            "estimation_posture": "pending_tool_call",
            "mutation_intent_candidate": "canonical_write",
            "uncertainty_posture": "medium",
            "source": "entry_manager_test",
        },
    )

    result = await module.process_intake_execution_turn(
        None,
        user_external_id="user-1",
        raw_user_input="I ate a breakfast shop combo",
        local_date="2026-04-29",
        allow_search=False,
        provider=provider,
        state_before=resolved_state,
        manager_decision=entry_manager_decision,
        request_id="req-entry-shadow-stub-initial-repair",
        stage_timings=[],
        current_turn_context=current_turn_context,
        phase_a_trace={},
    )

    manager_result = result["manager_result"]
    payload = result["nutrition_payload"]
    assert len(provider.calls) == 1
    assert provider.calls[0]["user_payload"]["guard_feedback"] is None
    assert manager_result.final_action == "ask_followup"
    assert manager_result.repair_round_used is False
    assert persisted
    assert getattr(payload, "estimated_kcal", None) == 0
    assert payload.trace_contract["manager_ask_followup_draft_contract"]["raw_text_semantic_inference"] is False
