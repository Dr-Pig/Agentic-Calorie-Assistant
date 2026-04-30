from __future__ import annotations

from app.intake.application.commit_boundary_preflight import run_commit_boundary_preflight
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


def test_attachment_resolver_does_not_import_manager_keyword_fallbacks() -> None:
    from pathlib import Path

    source = Path("app/intake/application/attachment_resolver.py").read_text(encoding="utf-8")

    assert "manager_fallback_policy" not in source
    assert "looks_like_budget_query" not in source
    assert "looks_like_correction" not in source
    assert "_INTAKE_TOKENS" not in source
    assert "_looks_like_intake_request" not in source
