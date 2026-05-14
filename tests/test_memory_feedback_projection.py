from __future__ import annotations


def _scope() -> dict[str, str]:
    return {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
    }


def _event(
    *,
    target_type: str,
    target_id: str,
    action: str,
    source_turn_id: str = "turn-1",
    **overrides: object,
) -> dict[str, object]:
    event: dict[str, object] = {
        "target_type": target_type,
        "target_id": target_id,
        "action": action,
        "source_turn_id": source_turn_id,
        "scope_keys": _scope(),
    }
    event.update(overrides)
    return event


def _target(
    target_type: str,
    target_id: str,
    *,
    trigger_type: str = "recommendation_prompt",
) -> dict[str, object]:
    return {
        "target_type": target_type,
        "target_id": target_id,
        "scope_keys": _scope(),
        "source_turn_ids": ["turn-1"],
        "source_refs": [f"{target_type}:{target_id}:source"],
        "candidate_type": "negative_preference",
        "trigger_type": trigger_type,
        "next_signal_required": "new_app_open_with_qualified_pool",
    }


def test_memory_confirm_projects_to_validator_input_without_promotion() -> None:
    from app.memory.application.memory_feedback_projection import (
        project_feedback_event_to_shadow_controls,
    )

    artifact = project_feedback_event_to_shadow_controls(
        feedback_event=_event(
            target_type="memory_candidate",
            target_id="memory-candidate-spicy",
            action="confirm",
        ),
        targets=[_target("memory_candidate", "memory-candidate-spicy")],
    )

    projection = artifact["consumer_projections"][0]
    assert artifact["status"] == "pass"
    assert projection["projection_type"] == "memory_confirmation_validator_input"
    assert projection["may_satisfy_memory_confirmation_gate"] is True
    assert projection["validator_required"] is True
    assert artifact["confirmed_memory_promoted"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["proactive_delivery_enabled"] is False
    assert artifact["scheduler_delivery_allowed"] is False


def test_proactive_dismiss_projects_to_control_event_with_next_signal() -> None:
    from app.memory.application.memory_feedback_projection import (
        project_feedback_event_to_shadow_controls,
    )

    artifact = project_feedback_event_to_shadow_controls(
        feedback_event=_event(
            target_type="proactive_candidate",
            target_id="proactive-evening-meal",
            action="dismiss",
            reason="too_frequent",
        ),
        targets=[_target("proactive_candidate", "proactive-evening-meal")],
    )

    projection = artifact["consumer_projections"][0]
    assert projection["projection_type"] == "user_control_suppression"
    assert projection["dismiss_reason"] == "too_frequent"
    assert projection["next_signal_required"] == "new_app_open_with_qualified_pool"
    assert projection["auto_promotes_memory"] is False
    assert artifact["user_control_event_projected"] is True


def test_snooze_reopen_and_legacy_undo_project_without_mutating_target_truth() -> None:
    from app.memory.application.memory_feedback_projection import (
        project_feedback_event_to_shadow_controls,
    )

    snooze = project_feedback_event_to_shadow_controls(
        feedback_event=_event(
            target_type="recommendation_offer",
            target_id="offer-1",
            action="snooze",
            snooze_until="2026-05-13T12:00:00Z",
        ),
        targets=[_target("recommendation_offer", "offer-1")],
    )
    undo = project_feedback_event_to_shadow_controls(
        feedback_event=_event(
            target_type="recommendation_offer",
            target_id="offer-1",
            action="undo",
        ),
        targets=[_target("recommendation_offer", "offer-1")],
    )
    reopen = project_feedback_event_to_shadow_controls(
        feedback_event=_event(
            target_type="recommendation_offer",
            target_id="offer-1",
            action="reopen",
        ),
        targets=[_target("recommendation_offer", "offer-1")],
    )

    assert snooze["consumer_projections"][0]["projection_type"] == "user_control_snooze"
    assert snooze["consumer_projections"][0]["snooze_until"] == "2026-05-13T12:00:00Z"
    assert undo["consumer_projections"][0]["projection_type"] == "user_control_undo"
    assert reopen["consumer_projections"][0]["projection_type"] == "user_control_reopen_modify"
    assert snooze["recommendation_offer_mutated"] is False
    assert undo["recommendation_offer_mutated"] is False
    assert reopen["recommendation_offer_mutated"] is False


def test_opt_out_creates_separate_pending_validated_projections() -> None:
    from app.memory.application.memory_feedback_projection import (
        project_feedback_event_to_shadow_controls,
    )

    artifact = project_feedback_event_to_shadow_controls(
        feedback_event=_event(
            target_type="proactive_candidate",
            target_id="proactive-evening-meal",
            action="opt_out",
            reason="no_meal_reminders",
        ),
        targets=[_target("proactive_candidate", "proactive-evening-meal")],
    )

    projection_types = {
        projection["projection_type"] for projection in artifact["consumer_projections"]
    }
    assert projection_types == {
        "proactive_suppression_candidate",
        "app_use_memory_candidate",
    }
    assert all(
        projection["validator_required"] is True
        for projection in artifact["consumer_projections"]
    )
    assert artifact["durable_product_memory_written"] is False
    assert artifact["confirm_enables_proactive_delivery"] is False


def test_projection_blocks_unknown_target_and_source_scope_mismatch() -> None:
    from app.memory.application.memory_feedback_projection import (
        project_feedback_event_to_shadow_controls,
    )

    unknown = project_feedback_event_to_shadow_controls(
        feedback_event=_event(
            target_type="memory_candidate",
            target_id="missing",
            action="confirm",
        ),
        targets=[_target("memory_candidate", "other")],
    )
    bad_source = project_feedback_event_to_shadow_controls(
        feedback_event=_event(
            target_type="memory_candidate",
            target_id="memory-candidate-spicy",
            action="confirm",
            source_turn_id="turn-cross-scope",
        ),
        targets=[_target("memory_candidate", "memory-candidate-spicy")],
    )

    assert unknown["status"] == "blocked"
    assert "target.not_found:memory_candidate.missing" in unknown["blockers"]
    assert bad_source["status"] == "blocked"
    assert "target.source_turn_mismatch:turn-cross-scope" in bad_source["blockers"]
    assert bad_source["consumer_projections"] == []
