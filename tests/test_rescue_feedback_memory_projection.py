from __future__ import annotations


def _scope() -> dict[str, str]:
    return {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-product-lab",
        "surface": "rescue_lab",
    }


def _event(action: str, **overrides: object) -> dict:
    event = {
        "target_type": "rescue_plan",
        "target_id": "rescue-proposal-1",
        "action": action,
        "reason": "felt workable",
        "source_turn_id": "turn-rescue-1",
        "scope_keys": _scope(),
    }
    event.update(overrides)
    return event


def _target(feedback_kind: str, **overrides: object) -> dict:
    target = {
        "target_type": "rescue_plan",
        "target_id": "rescue-proposal-1",
        "feedback_kind": feedback_kind,
        "scope_keys": _scope(),
        "source_turn_ids": ["turn-rescue-1"],
        "source_refs": ["rescue_plan:rescue-proposal-1", "message:turn-rescue-1"],
        "summary": "short horizon spread rescue",
    }
    target.update(overrides)
    return target


def _projection(action: str, feedback_kind: str, **event_overrides: object) -> dict:
    from app.rescue.application.feedback_memory_projection import (
        build_rescue_feedback_memory_projection,
    )

    return build_rescue_feedback_memory_projection(
        feedback_event=_event(action, **event_overrides),
        rescue_feedback_target=_target(feedback_kind),
    )


def test_accept_feedback_projects_reviewed_rescue_memory_candidate_without_promotion() -> None:
    artifact = _projection("confirm", "accept")

    assert artifact["status"] == "pass"
    assert artifact["lab_enabled"] is True
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["candidate_count"] == 1
    candidate = artifact["reviewed_memory_candidates"][0]
    assert candidate["candidate_type"] == "rescue_shadow"
    assert candidate["payload"]["rescue_memory_subtype"] == "accepted_rescue_pattern"
    assert candidate["payload"]["promotion_allowed_now"] is False
    assert candidate["human_review_required"] is True
    assert artifact["confirmed_memory_promoted"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["rescue_plan_mutated"] is False


def test_dismiss_feedback_is_instance_feedback_not_permanent_opt_out() -> None:
    artifact = _projection("dismiss", "dismiss", reason="too strict today")
    candidate = artifact["reviewed_memory_candidates"][0]

    assert artifact["status"] == "pass"
    assert candidate["payload"]["rescue_memory_subtype"] == "dismissed_rescue_instance"
    assert candidate["payload"]["not_permanent_rescue_opt_out"] is True
    assert candidate["reason_codes"] == [
        "dismiss_is_instance_feedback_not_permanent_opt_out"
    ]
    assert artifact["proactive_delivery_enabled"] is False
    assert artifact["auto_promotes_memory"] is False


def test_complaint_correction_and_outcome_feedback_create_review_candidates() -> None:
    cases = [
        ("correct", "complaint", "rescue_hardness_feedback"),
        ("correct", "correction", "rescue_correction_signal"),
        ("confirm", "outcome", "rescue_outcome_signal"),
    ]

    for action, kind, expected_subtype in cases:
        artifact = _projection(action, kind)
        candidate = artifact["reviewed_memory_candidates"][0]
        assert artifact["status"] == "pass"
        assert candidate["payload"]["rescue_memory_subtype"] == expected_subtype
        assert candidate["review_status"] == "pending"
        assert candidate["memory_truth_claimed"] is False


def test_projection_blocks_scope_or_source_mismatch_before_candidate_creation() -> None:
    from app.rescue.application.feedback_memory_projection import (
        build_rescue_feedback_memory_projection,
    )

    artifact = build_rescue_feedback_memory_projection(
        feedback_event=_event("confirm", source_turn_id="other-turn"),
        rescue_feedback_target=_target("accept"),
    )

    assert artifact["status"] == "blocked"
    assert "target.source_turn_mismatch:other-turn" in artifact["blockers"]
    assert artifact["reviewed_memory_candidates"] == []


def test_projection_blocks_non_rescue_target_and_unknown_feedback_kind() -> None:
    from app.rescue.application.feedback_memory_projection import (
        build_rescue_feedback_memory_projection,
    )

    artifact = build_rescue_feedback_memory_projection(
        feedback_event=_event("confirm", target_type="recommendation_offer"),
        rescue_feedback_target=_target("unknown"),
    )

    assert artifact["status"] == "blocked"
    assert "feedback_event.target_type_not_rescue_plan" in artifact["blockers"]
    assert "rescue_feedback_target.feedback_kind_unsupported" in artifact["blockers"]
    assert artifact["durable_product_memory_written"] is False
