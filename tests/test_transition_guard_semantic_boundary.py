from __future__ import annotations

from app.composition.commit_boundary_preflight import run_commit_boundary_preflight
from app.composition.intake_manager_tool_batch import validate_manager_target_proposal
from app.intake.application.transition_guard import resolve_transition_guard
from app.runtime.contracts.phase_a import AttachmentDecision, CurrentTurnContextV1, InteractionEvent
from app.shared.contracts.intake_results import EstimatePayload


def test_transition_guard_does_not_infer_correction_from_user_text() -> None:
    context = CurrentTurnContextV1(
        user_utterance="actually change that meal to half sugar",
        current_interaction_event=InteractionEvent(source="chat", event_type="user_message"),
    )
    attachment = AttachmentDecision(
        disposition="answer_only",
        reason="no_attachment_signal",
        allowed_transition_class="none",
    )

    result = resolve_transition_guard(context, attachment)

    assert result.verdict == "answer_only"
    assert result.reason == "no_state_mutation_allowed"


def test_commit_boundary_blocks_correction_without_resolved_target() -> None:
    payload = EstimatePayload(
        request_id="req-correction",
        meal_title="milk tea",
        estimated_kcal=420,
        action_taken="direct_answer",
        route_target="direct_answer",
        trace_contract={
            "canonical_write_decision": {"can_write_canonical": True},
        },
    )

    result = run_commit_boundary_preflight(
        payload=payload,
        manager_final_action="correction_applied",
        active_body_plan_present=True,
        correction_target=None,
    )

    assert result.blocked is True
    assert result.mutation_effect_class == "correction_persistence"
    assert result.correction_target_resolved is False


def test_manager_target_validator_accepts_manager_owned_thread_level_correction() -> None:
    resolved = validate_manager_target_proposal(
        correction_target={
            "meal_thread_id": 77,
            "meal_version_id": 88,
            "target_resolution_source": "active_meal_view",
            "item_candidates": [
                {"meal_item_id": 1, "canonical_name": "teppan noodles"},
                {"meal_item_id": 2, "canonical_name": "egg"},
            ],
        },
        proposal={
            "meal_thread_id": 77,
            "operation": "correct_active_meal",
            "target_proposal_source": "manager_result.semantic_decision.target_attachment",
        },
    )

    assert resolved["meal_thread_id"] == 77
    assert resolved["meal_version_id"] == 88
    assert resolved["operation"] == "correct_active_meal"
    assert resolved["manager_target_proposal_validation"]["status"] == "accepted"
    assert resolved["manager_target_proposal_validation"]["truth_owner"] == "deterministic_target_validator"


def test_manager_target_validator_accepts_manager_selected_recent_thread_candidate() -> None:
    resolved = validate_manager_target_proposal(
        correction_target={
            "meal_thread_id": 22,
            "meal_version_id": 33,
            "target_resolution_source": "active_meal_view",
            "thread_candidates": [
                {"meal_thread_id": 11, "meal_version_id": 12, "meal_title": "breakfast teppan set"},
                {"meal_thread_id": 22, "meal_version_id": 33, "meal_title": "lunch chicken rice"},
            ],
        },
        proposal={
            "meal_thread_id": 11,
            "operation": "remove_meal",
            "target_proposal_source": "manager_result.semantic_decision.target_attachment",
        },
    )

    assert resolved["meal_thread_id"] == 11
    assert resolved["meal_version_id"] == 12
    assert resolved["operation"] == "remove_meal"
    assert resolved["target_resolution_source"] == "manager_target_proposal_validated"
    assert resolved["manager_target_proposal_validation"]["status"] == "accepted"


def test_manager_target_validator_rejects_whole_meal_removal_without_manager_selected_thread_id() -> None:
    resolved = validate_manager_target_proposal(
        correction_target={
            "meal_thread_id": 22,
            "meal_version_id": 33,
            "target_resolution_source": "active_meal_view",
            "thread_candidates": [
                {"meal_thread_id": 11, "meal_version_id": 12, "meal_title": "breakfast teppan set"},
                {"meal_thread_id": 22, "meal_version_id": 33, "meal_title": "lunch chicken rice"},
            ],
        },
        proposal={
            "meal_title": "breakfast",
            "operation": "remove_meal",
            "target_proposal_source": "manager_result.semantic_decision.target_attachment",
        },
    )

    assert resolved["manager_target_proposal_validation"]["status"] == "rejected"
    assert resolved["manager_target_proposal_validation"]["failure_family"] == "manager_thread_target_proposal_not_found"


def test_manager_target_validator_does_not_treat_thread_id_as_remove_item_target() -> None:
    resolved = validate_manager_target_proposal(
        correction_target={
            "meal_thread_id": 77,
            "meal_version_id": 88,
            "target_resolution_source": "active_meal_view",
            "item_candidates": [{"meal_item_id": 1, "canonical_name": "teppan noodles"}],
        },
        proposal={
            "meal_thread_id": 77,
            "operation": "remove_item",
            "target_proposal_source": "manager_result.semantic_decision.target_attachment",
        },
    )

    assert resolved["manager_target_proposal_validation"]["status"] == "rejected"
    assert resolved["manager_target_proposal_validation"]["failure_family"] == "manager_target_proposal_not_found"


def test_attachment_resolver_does_not_import_manager_keyword_fallbacks() -> None:
    from pathlib import Path

    source = Path("app/intake/application/attachment_resolver.py").read_text(encoding="utf-8")

    assert "manager_fallback_policy" not in source
    assert "looks_like_budget_query" not in source
    assert "looks_like_correction" not in source
    assert "_INTAKE_TOKENS" not in source
    assert "_looks_like_intake_request" not in source
