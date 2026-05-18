from __future__ import annotations

import pytest

from app.providers.builderspace_runtime_contract import manager_loop_schema, validate_manager_payload
from app.runtime.agent.manager_branch_shapes import manager_semantic_decision_schema
from app.runtime.agent.manager_result_builder import result_from_payload
from app.runtime.contracts.phase_a import ManagerSemanticDecision
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE


def _active_workflow_resolution(**overrides: object) -> dict[str, object]:
    resolution: dict[str, object] = {
        "current_turn_relation": "answers_optional_slot",
        "slot_updates": [
            {
                "slot_id": "sugar_level",
                "slot_kind": "sugar_level",
                "required_for_commit": False,
                "current_value": "half sugar",
                "source": "current_turn",
                "resolution_condition": "user answered the optional sugar-level slot",
                "asked_question": "What size and sugar level was it?",
            }
        ],
        "still_missing_slots": [],
        "attach_target": {
            "operation": "attach_to_pending_followup",
            "meal_thread_id": "meal-thread-1",
        },
        "final_action": "correction_applied",
        "resolution_basis": ["current_turn", "pending_followup", "target_candidates"],
        "selection_owner": "manager",
        "deterministic_role": "validate_only",
    }
    resolution.update(overrides)
    return resolution


def _manager_payload(*, active_workflow_resolution: dict[str, object] | None = None) -> dict[str, object]:
    semantic_decision: dict[str, object] = {
        "semantic_authority": "manager_llm",
        "current_turn_intent": "log_meal",
        "target_attachment": {"mode": "new_meal"},
        "workflow_effect": "commit",
        "final_action_candidate": "commit",
        "estimation_posture": "estimable",
        "followup_posture": "none",
        "mutation_intent_candidate": "canonical_write",
        "uncertainty_posture": "bounded",
        "source": "single_manager_loop",
    }
    if active_workflow_resolution is not None:
        semantic_decision["active_workflow_resolution"] = active_workflow_resolution
    return {
        "manager_action": "final",
        "intent": "log_meal",
        "workflow_effect": "commit",
        "target_attachment": {"mode": "new_meal"},
        "exactness": "estimated",
        "confidence": "medium",
        "evidence_posture": "bounded_estimate",
        "repair_ack": False,
        "semantic_decision": semantic_decision,
    }


def test_semantic_decision_schema_requires_manager_active_workflow_resolution() -> None:
    schema = manager_semantic_decision_schema()

    active_schema = schema["properties"]["active_workflow_resolution"]

    assert "active_workflow_resolution" in schema["required"]
    assert active_schema["properties"]["current_turn_relation"]["enum"] == [
        "answers_required_slot",
        "answers_optional_slot",
        "basis_inquiry",
        "correction",
        "removal",
        "unrelated_new_log",
        "ambiguous",
        "none",
    ]
    assert "slot_updates" in active_schema["required"]
    assert "still_missing_slots" in active_schema["required"]
    assert active_schema["properties"]["selection_owner"]["enum"] == ["manager"]
    assert active_schema["properties"]["deterministic_role"]["enum"] == ["validate_only"]
    assert "raw text" in active_schema["description"]


def test_manager_loop_schema_exposes_active_workflow_resolution_to_provider() -> None:
    semantic_schema = manager_loop_schema(None)["properties"]["semantic_decision"]

    assert "active_workflow_resolution" in semantic_schema["properties"]
    assert "active_workflow_resolution" in semantic_schema["required"]


def test_runtime_validation_blocks_missing_active_workflow_resolution() -> None:
    with pytest.raises(RuntimeError, match="active_workflow_resolution missing"):
        validate_manager_payload(MANAGER_LOOP_STAGE, _manager_payload())


def test_runtime_validation_blocks_invalid_active_workflow_resolution_shape() -> None:
    resolution = _active_workflow_resolution(current_turn_relation="keyword_router_decided")

    with pytest.raises(RuntimeError, match="current_turn_relation invalid"):
        validate_manager_payload(
            MANAGER_LOOP_STAGE,
            _manager_payload(active_workflow_resolution=resolution),
        )


def test_runtime_validation_accepts_manager_owned_active_workflow_resolution_shape() -> None:
    validate_manager_payload(
        MANAGER_LOOP_STAGE,
        _manager_payload(active_workflow_resolution=_active_workflow_resolution()),
    )


def test_manager_semantic_decision_model_preserves_active_workflow_resolution() -> None:
    decision = ManagerSemanticDecision(
        semantic_authority="manager_llm",
        current_turn_intent="correct_meal",
        target_attachment={"operation": "attach_to_pending_followup"},
        active_workflow_resolution=_active_workflow_resolution(),
        workflow_effect="correction",
        final_action_candidate="correction_applied",
        estimation_posture="pending_tool_call",
        followup_posture="none",
        mutation_intent_candidate="correction_write",
        uncertainty_posture="bounded",
        source="active_workflow_context",
    )

    dumped = decision.model_dump(mode="json")

    assert dumped["active_workflow_resolution"]["current_turn_relation"] == "answers_optional_slot"
    assert dumped["active_workflow_resolution"]["selection_owner"] == "manager"
    assert dumped["active_workflow_resolution"]["deterministic_role"] == "validate_only"


def test_result_from_payload_preserves_active_workflow_resolution_without_rewriting() -> None:
    result = result_from_payload(
        {
            "intent": "correct meal",
            "intent_type": "correct_meal",
            "workflow_effect": "correction",
            "final_action": "correction_applied",
            "semantic_decision": {
                "semantic_authority": "manager_llm",
                "current_turn_intent": "correct_meal",
                "target_attachment": {"operation": "attach_to_pending_followup"},
                "active_workflow_resolution": _active_workflow_resolution(),
                "workflow_effect": "correction",
                "final_action_candidate": "correction_applied",
                "estimation_posture": "pending_tool_call",
                "followup_posture": "none",
                "mutation_intent_candidate": "correction_write",
                "uncertainty_posture": "bounded",
                "source": "active_workflow_context",
            },
        },
        manager_rounds=[],
        tool_results=[],
    )

    active_resolution = result.semantic_decision["active_workflow_resolution"]

    assert active_resolution["attach_target"]["meal_thread_id"] == "meal-thread-1"
    assert active_resolution["slot_updates"][0]["slot_id"] == "sugar_level"
    assert result.trace["semantic_decision"]["active_workflow_resolution"] == active_resolution
