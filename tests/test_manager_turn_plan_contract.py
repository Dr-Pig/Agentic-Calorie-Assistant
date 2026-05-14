from __future__ import annotations

from app.shared.contracts.manager_turn_plan import (
    CapabilityRequest,
    FinalResponsePlan,
    ManagerTurnPlan,
    ToolCallCandidate,
    build_manager_turn_plan_contract,
)


def test_manager_turn_plan_contract_tracks_shared_capability_ids() -> None:
    artifact = build_manager_turn_plan_contract()

    assert artifact["artifact_type"] == "shared_manager_turn_plan_contract"
    assert artifact["status"] == "pass"
    assert artifact["allowed_capability_ids"] == [
        "intake",
        "query",
        "memory",
        "recommendation",
        "rescue",
        "proactive",
        "reusable_meal",
        "pending_meal_intent",
    ]
    assert artifact["turn_plan_outputs_structure_not_raw_transcript"] is True
    assert artifact["shared_capability_registry_required"] is True


def test_manager_turn_plan_accepts_multi_intent_shared_capability_shape() -> None:
    plan = ManagerTurnPlan(
        primary_workflow="intake_with_optional_rescue_and_recommendation",
        secondary_intents=["answer_budget", "remember_preference"],
        requested_capabilities=[
            CapabilityRequest(
                capability_id="pending_meal_intent", request_mode="optional", priority=0
            ),
            CapabilityRequest(capability_id="intake", request_mode="required", priority=1),
            CapabilityRequest(capability_id="rescue", request_mode="optional", priority=2),
            CapabilityRequest(
                capability_id="recommendation", request_mode="deferred_candidate", priority=3
            ),
        ],
        candidate_tool_calls=[
            ToolCallCandidate(tool_name="memory.search", capability_id="memory"),
            ToolCallCandidate(
                tool_name="rescue.run",
                capability_id="rescue",
                requires_prior_call_ids=["memory-search-1"],
            ),
        ],
        ordering_constraints=["intake_before_rescue", "rescue_before_recommendation"],
        mutation_posture="read_only",
        clarification_posture="optional",
        response_obligations=["show_budget_impact", "avoid_hidden_mutation_claims"],
        omission_candidates=["proactive"],
        scope_keys={"user_id": "u1", "workspace_id": "w1", "surface": "chat"},
    )

    assert plan.primary_workflow == "intake_with_optional_rescue_and_recommendation"
    assert [item.capability_id for item in plan.requested_capabilities] == [
        "pending_meal_intent",
        "intake",
        "rescue",
        "recommendation",
    ]
    assert plan.candidate_tool_calls[1].requires_prior_call_ids == ["memory-search-1"]


def test_final_response_plan_tracks_user_visible_capabilities_and_claim_boundaries() -> None:
    plan = FinalResponsePlan(
        response_mode="chat_first",
        user_visible_capabilities=["intake", "rescue"],
        source_tool_call_ids=["memory-search-1", "rescue-1"],
        action_affordances=["accept_rescue_plan", "dismiss_rescue_plan"],
        must_not_claim=["logged_when_not_committed", "scheduled_when_not_sent"],
    )

    assert plan.response_mode == "chat_first"
    assert plan.user_visible_capabilities == ["intake", "rescue"]
    assert "scheduled_when_not_sent" in plan.must_not_claim
