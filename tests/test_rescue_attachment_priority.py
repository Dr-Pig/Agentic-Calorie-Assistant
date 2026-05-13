from __future__ import annotations

import pytest


def _packet(semantic: str, *, open_objects: list[dict] | None = None) -> dict:
    return {
        "artifact_type": "manager_rescue_attachment_packet",
        "status": "pass",
        "manager_semantics": {
            "semantic": semantic,
            "source": "manager_runtime_structured_output",
        },
        "open_objects": open_objects
        if open_objects is not None
        else [
            {
                "object_type": "rescue_proposal",
                "object_id": "rescue-proposal-1",
                "status": "open",
            },
            {
                "object_type": "intake_followup",
                "object_id": "meal-thread-1",
                "status": "open",
            },
        ],
        "raw_utterance": "kept for audit only",
    }


def _artifact(semantic: str, *, open_objects: list[dict] | None = None) -> dict:
    from app.rescue.application.rescue_attachment_priority import (
        build_rescue_attachment_priority_contract,
    )

    return build_rescue_attachment_priority_contract(
        manager_attachment_packet=_packet(semantic, open_objects=open_objects),
    )


@pytest.mark.parametrize(
    ("semantic", "target_action", "next_contract"),
    [
        ("explicit_accept", "accept_rescue_plan", "accept_rescue_plan_lab_contract"),
        ("explicit_dismiss", "dismiss_rescue_plan", "dismiss_rescue_plan_lab_contract"),
    ],
)
def test_explicit_accept_and_dismiss_attach_to_rescue_action_contract(
    semantic: str,
    target_action: str,
    next_contract: str,
) -> None:
    artifact = _artifact(semantic)

    assert artifact["status"] == "pass"
    decision = artifact["attachment_decision"]
    assert decision["disposition"] == "attach_rescue_proposal_action"
    assert decision["target_object_id"] == "rescue-proposal-1"
    assert decision["target_action"] == target_action
    assert decision["next_contract"] == next_contract
    assert decision["mutation_allowed_in_lab"] is True
    assert decision["rescue_proposal_state_mutation_allowed"] is True


@pytest.mark.parametrize("semantic", ["explicit_adjust", "explain_request"])
def test_adjust_and_explain_attach_as_non_mutating_rescue_negotiation(
    semantic: str,
) -> None:
    artifact = _artifact(semantic)

    assert artifact["status"] == "pass"
    decision = artifact["attachment_decision"]
    assert decision["disposition"] == "attach_rescue_proposal_negotiation"
    assert decision["target_object_id"] == "rescue-proposal-1"
    assert decision["target_action"] == "negotiate_rescue_plan"
    assert decision["mutation_allowed_in_lab"] is False
    assert decision["rescue_proposal_state_mutation_allowed"] is False


@pytest.mark.parametrize(
    "semantic",
    ["complaint_or_hardness_feedback", "feasibility_question", "hesitation"],
)
def test_complaint_feasibility_and_hesitation_are_answer_only_not_dismiss(
    semantic: str,
) -> None:
    artifact = _artifact(semantic)

    assert artifact["status"] == "pass"
    decision = artifact["attachment_decision"]
    assert decision["disposition"] == "answer_only"
    assert decision["target_object_id"] is None
    assert decision["target_action"] == "answer_without_state_change"
    assert decision["mutation_allowed_in_lab"] is False
    assert decision["rescue_proposal_state_mutation_allowed"] is False


def test_followup_answer_attaches_to_intake_before_open_rescue_proposal() -> None:
    artifact = _artifact("followup_answer")

    assert artifact["status"] == "pass"
    decision = artifact["attachment_decision"]
    assert decision["disposition"] == "attach_intake_followup"
    assert decision["target_object_type"] == "intake_followup"
    assert decision["target_object_id"] == "meal-thread-1"
    assert decision["rescue_proposal_state_mutation_allowed"] is False


@pytest.mark.parametrize(
    ("semantic", "disposition"),
    [("ambiguous", "answer_only"), ("topic_reset", "start_new_workflow_or_defer")],
)
def test_ambiguous_and_topic_reset_do_not_attach_any_open_object(
    semantic: str,
    disposition: str,
) -> None:
    artifact = _artifact(semantic)

    assert artifact["status"] == "pass"
    decision = artifact["attachment_decision"]
    assert decision["disposition"] == disposition
    assert decision["target_object_id"] is None
    assert decision["mutation_allowed_in_lab"] is False


def test_attachment_priority_requires_manager_semantics_not_raw_keyword_oracle() -> None:
    from app.rescue.application.rescue_attachment_priority import (
        build_rescue_attachment_priority_contract,
    )

    packet = _packet("explicit_dismiss")
    packet.pop("manager_semantics")
    artifact = build_rescue_attachment_priority_contract(
        manager_attachment_packet=packet,
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "manager_attachment_packet.manager_semantics_missing",
    ]
    assert artifact["raw_utterance_used_for_semantic_classification"] is False


def test_explicit_rescue_actions_require_open_rescue_proposal() -> None:
    artifact = _artifact(
        "explicit_accept",
        open_objects=[
            {
                "object_type": "intake_followup",
                "object_id": "meal-thread-1",
                "status": "open",
            }
        ],
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["open_objects.rescue_proposal_missing"]
