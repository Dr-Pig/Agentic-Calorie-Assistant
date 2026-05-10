from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.runtime.application.proactive_no_send_shadow_evaluator import (
    ProactiveNoSendShadowInput,
    build_proactive_no_send_simulation,
)
from app.runtime.contracts.pending_meal_intent import PendingMealIntent


def test_active_pending_meal_intent_becomes_controlled_no_send_followup() -> None:
    from app.runtime.application.proactive_pending_meal_followup_shadow import (
        build_pending_meal_followup_no_send_shadow,
    )

    now = datetime(2026, 5, 10, 19, 0, tzinfo=UTC)
    artifact = build_pending_meal_followup_no_send_shadow(
        pending_meal_intent=_intent(now),
        evaluation_time=now,
        control_context=_controls(),
    )

    assert artifact["artifact_type"] == "proactive_pending_meal_followup_shadow"
    assert artifact["status"] == "pass"
    assert artifact["pending_meal_intent_trace"]["contract_scope"] == (
        "pending_meal_intent_only"
    )
    assert artifact["followup_source_review"] == {
        "source_pending_intent_used": True,
        "status": "active_pending_intent",
        "prompt_posture": "chat_first_followup_question_only",
        "pending_intent_status": "created",
        "source_surface": "chat",
        "runtime_effect_allowed": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "live_delivery_allowed": False,
        "scheduler_activation_allowed": False,
        "manager_context_injected": False,
        "recommendation_served": False,
        "intake_commit_requested": False,
        "pending_intent_mutated": False,
    }
    candidate = artifact["no_send_candidate"]
    assert candidate["trigger_type"] == "pending_meal_followup"
    assert candidate["candidate_kind"] == "pending_meal_followup_review"
    assert candidate["status"] == "pass"
    assert candidate["dismiss_reason_choices"] == [
        "already_logged",
        "did_not_eat_it",
        "too_frequent",
    ]
    assert candidate["snooze_window"] == {"kind": "duration", "minutes": 120}
    assert candidate["next_signal_required"] == "pending_intent_still_active"
    assert artifact["simulation_input"]["trigger_type"] == "pending_meal_followup"
    assert artifact["proactive_sent"] is False
    assert artifact["scheduler_enabled"] is False
    assert artifact["intake_commit_requested"] is False
    assert artifact["pending_intent_mutated"] is False
    assert artifact["user_facing_behavior_changed"] is False


def test_pending_meal_followup_suppresses_terminal_or_expired_intents() -> None:
    from app.runtime.application.proactive_pending_meal_followup_shadow import (
        build_pending_meal_followup_no_send_shadow,
    )

    now = datetime(2026, 5, 10, 19, 0, tzinfo=UTC)
    dismissed = build_pending_meal_followup_no_send_shadow(
        pending_meal_intent=_intent(now, status="dismissed"),
        evaluation_time=now,
        control_context=_controls(),
    )
    expired = build_pending_meal_followup_no_send_shadow(
        pending_meal_intent=_intent(now, expires_at=now - timedelta(minutes=1)),
        evaluation_time=now,
        control_context=_controls(),
    )

    assert dismissed["status"] == "blocked"
    assert "pending_meal_intent.not_active" in dismissed["blockers"]
    assert expired["status"] == "blocked"
    assert "pending_meal_intent.not_active" in expired["blockers"]
    assert dismissed["no_send_candidate"] is None
    assert expired["no_send_candidate"] is None
    assert dismissed["proactive_sent"] is False
    assert expired["pending_intent_mutated"] is False


def test_pending_meal_followup_blocks_claim_drift_without_intake_commit() -> None:
    from app.runtime.application.proactive_pending_meal_followup_shadow import (
        build_pending_meal_followup_no_send_shadow,
    )

    now = datetime(2026, 5, 10, 19, 0, tzinfo=UTC)
    artifact = build_pending_meal_followup_no_send_shadow(
        pending_meal_intent=_intent(now),
        evaluation_time=now,
        control_context={**_controls(), "proactive_sent": True},
    )

    assert artifact["status"] == "blocked"
    assert "control_context.proactive_sent" in artifact["blockers"]
    assert artifact["no_send_candidate"] is None
    assert artifact["proactive_sent"] is False
    assert artifact["intake_commit_requested"] is False
    assert artifact["pending_intent_mutated"] is False


def test_pending_meal_followup_can_feed_existing_no_send_simulation() -> None:
    from app.runtime.application.proactive_pending_meal_followup_shadow import (
        build_pending_meal_followup_no_send_shadow,
    )

    now = datetime(2026, 5, 10, 19, 0, tzinfo=UTC)
    artifact = build_pending_meal_followup_no_send_shadow(
        pending_meal_intent=_intent(now),
        evaluation_time=now,
        control_context=_controls(),
    )
    simulation = build_proactive_no_send_simulation(
        [ProactiveNoSendShadowInput(**artifact["simulation_input"])]
    )

    assert simulation["artifact_type"] == "proactive_no_send_simulation"
    assert simulation["summary"]["candidate_for_human_review_trigger_types"] == [
        "pending_meal_followup"
    ]
    assert simulation["trigger_evaluations"][0]["permission_posture"] == "user_expected"
    assert simulation["proactive_sent"] is False
    assert simulation["scheduler_enabled"] is False


def _intent(
    now: datetime,
    *,
    status: str = "created",
    expires_at: datetime | None = None,
) -> PendingMealIntent:
    return PendingMealIntent(
        intent_id="pending-meal-golden-1-action-1",
        user_id="user-1",
        candidate_title="FamilyMart chicken bento",
        source_surface="chat",
        status=status,
        created_at=now - timedelta(minutes=30),
        expires_at=expires_at or now + timedelta(hours=5),
        candidate_metadata={
            "candidate_id": "golden-1",
            "source_refs": ["memory_candidate:golden-1"],
        },
    )


def _controls() -> dict[str, object]:
    return {
        "dismiss_reason_choices": [
            "already_logged",
            "did_not_eat_it",
            "too_frequent",
        ],
        "snooze_window": {"kind": "duration", "minutes": 120},
        "undo_scope": "current_no_send_candidate_only",
        "next_signal_required": "pending_intent_still_active",
        "permission_posture": "user_expected",
        "cooldown": {"passed": True},
        "suppression": {"suppressed": False},
        "runtime_effect_allowed": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "live_delivery_allowed": False,
        "scheduler_activation_allowed": False,
        "manager_context_injected": False,
        "recommendation_served": False,
        "intake_commit_requested": False,
        "pending_intent_mutated": False,
    }
