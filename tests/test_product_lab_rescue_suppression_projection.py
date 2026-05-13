from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.advanced_shadow_lab.product_lab_rescue_suppression_projection import (
    build_rescue_suppression_feedback_projection,
)


def test_explicit_rescue_opt_out_creates_validated_category_suppression_projection() -> None:
    artifact = build_rescue_suppression_feedback_projection(
        feedback_event=_event("opt_out", reason="don't remind me about rescue"),
        rescue_nudge_target=_target(),
        now=datetime(2026, 5, 14, 12, 0, tzinfo=UTC),
    )

    assert artifact["status"] == "pass"
    assert artifact["action"] == "opt_out"
    assert artifact["trigger_type"] == "rescue_nudge"
    assert artifact["suppression_projection"]["projection_type"] == (
        "explicit_rescue_nudge_opt_out"
    )
    assert artifact["suppression_projection"]["suppression_status"] == "active_until_reenabled"
    assert artifact["suppression_projection"]["user_callable_rescue_remains"] is True
    assert artifact["app_use_memory_candidate"]["status"] == "pending_review"
    assert artifact["confirmed_memory_promoted"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["scheduler_delivery_allowed"] is False
    assert artifact["rescue_plan_mutated"] is False


def test_rescue_dismiss_and_snooze_are_control_only_not_memory_or_opt_out() -> None:
    dismiss = build_rescue_suppression_feedback_projection(
        feedback_event=_event("dismiss", reason="not today"),
        rescue_nudge_target=_target(),
        now=datetime(2026, 5, 14, 12, 0, tzinfo=UTC),
    )
    snooze_until = "2026-05-14T18:00:00+00:00"
    snooze = build_rescue_suppression_feedback_projection(
        feedback_event=_event("snooze", snooze_until=snooze_until),
        rescue_nudge_target=_target(),
        now=datetime(2026, 5, 14, 12, 0, tzinfo=UTC),
    )

    assert dismiss["suppression_projection"]["projection_type"] == "current_candidate_control"
    assert dismiss["suppression_projection"]["next_signal_required"] == (
        "material_budget_change_or_user_reopens_rescue"
    )
    assert dismiss["app_use_memory_candidate"] is None
    assert dismiss["confirmed_memory_promoted"] is False

    assert snooze["suppression_projection"]["projection_type"] == "cooldown_snooze_control"
    assert snooze["suppression_projection"]["snooze_until"] == snooze_until
    assert snooze["app_use_memory_candidate"] is None
    assert snooze["durable_product_memory_written"] is False


def test_three_rescue_dismiss_or_ignore_signals_in_14_days_only_create_pending_review() -> None:
    now = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    artifact = build_rescue_suppression_feedback_projection(
        feedback_event=_event("dismiss", reason="again"),
        rescue_nudge_target=_target(),
        recent_control_signals=[
            _signal("dismiss", now - timedelta(days=13)),
            _signal("ignore", now - timedelta(days=7)),
        ],
        now=now,
    )

    assert artifact["repeated_control_projection"] == {
        "projection_type": "rescue_nudge_repeated_dismiss_pending_review",
        "status": "pending_review",
        "signal_count": 3,
        "window_days": 14,
        "confirmed_suppression": False,
        "chat_first_confirmation_required": True,
    }
    assert artifact["suppression_projection"]["projection_type"] == "current_candidate_control"
    assert artifact["confirmed_memory_promoted"] is False
    assert artifact["proactive_delivery_enabled"] is False


def test_rescue_suppression_projection_blocks_scope_source_and_wrong_trigger() -> None:
    scope_mismatch = build_rescue_suppression_feedback_projection(
        feedback_event=_event("opt_out", scope_keys=_scope(user_id="other-user")),
        rescue_nudge_target=_target(),
        now=datetime(2026, 5, 14, 12, 0, tzinfo=UTC),
    )
    wrong_trigger = build_rescue_suppression_feedback_projection(
        feedback_event=_event("opt_out"),
        rescue_nudge_target=_target(trigger_type="recommendation_prompt"),
        now=datetime(2026, 5, 14, 12, 0, tzinfo=UTC),
    )

    assert scope_mismatch["status"] == "blocked"
    assert "target.scope_mismatch" in scope_mismatch["blockers"]
    assert scope_mismatch["suppression_projection"] is None
    assert wrong_trigger["status"] == "blocked"
    assert "rescue_nudge_target.trigger_type_not_rescue_nudge" in wrong_trigger["blockers"]


def _scope(**overrides: str) -> dict[str, str]:
    scope = {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-product-lab",
        "surface": "chat",
    }
    scope.update(overrides)
    return scope


def _event(action: str, **overrides: object) -> dict[str, object]:
    event = {
        "target_type": "proactive_candidate",
        "target_id": "rescue_nudge",
        "action": action,
        "reason": "not today",
        "source_turn_id": "turn-rescue-nudge-1",
        "scope_keys": _scope(),
    }
    event.update(overrides)
    return event


def _target(**overrides: object) -> dict[str, object]:
    target = {
        "target_type": "proactive_candidate",
        "target_id": "rescue_nudge",
        "trigger_type": "rescue_nudge",
        "scope_keys": _scope(),
        "source_turn_ids": ["turn-rescue-nudge-1"],
        "source_refs": ["proactive_candidate:rescue_nudge"],
        "next_signal_required": "material_budget_change_or_user_reopens_rescue",
    }
    target.update(overrides)
    return target


def _signal(action: str, occurred_at: datetime) -> dict[str, str]:
    return {"action": action, "occurred_at": occurred_at.isoformat()}
