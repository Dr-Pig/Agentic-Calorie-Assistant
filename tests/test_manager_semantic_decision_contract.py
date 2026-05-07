from __future__ import annotations

from app.runtime.agent.manager_fallback_policy import fallback_decision
from app.runtime.agent.manager_result_builder import fallback_result, result_from_payload
from app.runtime.contracts.phase_a import ManagerSemanticDecision


class _ReadyState:
    onboarding_ready = True


def test_manager_semantic_decision_schema_records_manager_authority() -> None:
    decision = ManagerSemanticDecision(
        semantic_authority="manager_llm",
        current_turn_intent="log_meal",
        target_attachment={"mode": "new_workflow"},
        workflow_effect="estimate_with_followup",
        final_action_candidate="commit",
        estimation_posture="estimable",
        followup_posture="refinement_not_commit_gate",
        followup_question="What size and sugar level was it?",
        followup_targets=["size", "sugar_level"],
        mutation_intent_candidate="canonical_write",
        uncertainty_posture="bounded_estimate",
        source="single_manager_loop",
    )

    dumped = decision.model_dump(mode="json")

    assert dumped["semantic_owner"] == "manager"
    assert dumped["semantic_authority"] == "manager_llm"
    assert dumped["current_turn_intent"] == "log_meal"
    assert dumped["followup_question"] == "What size and sugar level was it?"
    assert dumped["followup_targets"] == ["size", "sugar_level"]
    assert dumped["deterministic_role"] == "validate_gate_trace_only"


def test_result_from_payload_consumes_explicit_semantic_decision_without_rewriting() -> None:
    result = result_from_payload(
        {
            "intent": "log_meal",
            "intent_type": "log_meal",
            "workflow_effect": "commit",
            "final_action": "commit",
            "semantic_decision": {
                "semantic_authority": "manager_llm",
                "current_turn_intent": "answer_query",
                "target_attachment": {"mode": "none"},
                "workflow_effect": "answer_only",
                "final_action_candidate": "answer_only",
                "estimation_posture": "not_applicable",
                "followup_posture": "none",
                "mutation_intent_candidate": "no_mutation",
                "uncertainty_posture": "low",
                "source": "single_manager_loop",
            },
        },
        manager_rounds=[],
        tool_results=[],
    )

    assert result.semantic_decision["semantic_authority"] == "manager_llm"
    assert result.semantic_decision["current_turn_intent"] == "answer_query"
    assert result.semantic_decision["workflow_effect"] == "answer_only"


def test_result_from_payload_derives_missing_final_action_from_manager_semantic_candidate() -> None:
    result = result_from_payload(
        {
            "intent": "log_meal",
            "intent_type": "log_meal",
            "workflow_effect": "commit",
            "semantic_decision": {
                "semantic_authority": "manager_llm",
                "current_turn_intent": "log_meal",
                "target_attachment": {"mode": "new_meal"},
                "workflow_effect": "commit",
                "final_action_candidate": "commit",
                "estimation_posture": "tool_estimate",
                "followup_posture": "none",
                "mutation_intent_candidate": "canonical_write",
                "uncertainty_posture": "bounded",
                "source": "single_manager_loop",
            },
        },
        manager_rounds=[],
        tool_results=[],
    )

    assert result.final_action == "commit"
    assert result.trace["final_action_source"] == "semantic_decision.final_action_candidate"


def test_missing_semantic_decision_is_non_authoritative_not_derived_from_legacy_fields() -> None:
    result = result_from_payload(
        {
            "intent": "log_meal",
            "intent_type": "log_meal",
            "workflow_effect": "commit",
            "final_action": "commit",
        },
        manager_rounds=[],
        tool_results=[],
    )

    assert result.semantic_decision["semantic_authority"] == "missing"
    assert result.semantic_decision["current_turn_intent"] == "unknown"
    assert result.semantic_decision["workflow_effect"] == "none"
    assert result.semantic_decision["final_action_candidate"] == "no_commit"


def test_fallback_result_marks_semantics_as_degraded_not_authoritative() -> None:
    result = fallback_result(
        raw_user_input="我喝了一杯珍珠奶茶",
        onboarding_payload=None,
        resolved_state=_ReadyState(),
    )

    assert result.llm_used is False
    assert result.semantic_decision["semantic_authority"] == "degraded_fallback"
    assert result.semantic_decision["current_turn_intent"] == "unknown"
    assert result.semantic_decision["semantic_owner"] == "manager"
    assert result.intent_type == "manager_unavailable"
    assert result.final_action == "no_commit"
    assert result.workflow_effect == "safe_failure"


def test_fallback_decision_without_structured_payload_does_not_keyword_route_semantics() -> None:
    decision = fallback_decision(
        raw_user_input="actually change that meal to half sugar",
        onboarding_payload=None,
        onboarding_ready=True,
    )

    assert decision.intent_type == "manager_unavailable"
    assert decision.workflow_effect == "safe_failure"
    assert decision.tool_calls == ()


def test_fallback_decision_with_onboarding_payload_uses_public_read_tools() -> None:
    decision = fallback_decision(
        raw_user_input="",
        onboarding_payload={"onboarding_step": "profile"},
        onboarding_ready=False,
    )

    assert decision.intent_type == "complete_onboarding"
    assert decision.workflow_effect == "seed_active_body_plan_and_day_budget"
    assert decision.tool_calls == ("body.get_active_plan", "budget.get_today_summary")
