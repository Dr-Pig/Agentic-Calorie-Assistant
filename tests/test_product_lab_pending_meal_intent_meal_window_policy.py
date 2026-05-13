from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.advanced_shadow_lab.product_lab_pending_meal_intent_meal_window_policy import (
    DEFAULT_MEAL_WINDOWS,
    apply_meal_window_policy_to_intent,
    build_meal_window_policy_trace,
)
from app.runtime.contracts.pending_meal_intent import PendingMealIntent


def test_meal_window_policy_uses_default_window_and_never_schedules_delivery() -> None:
    intent = _intent(datetime(2026, 5, 14, 10, 30, tzinfo=UTC))

    trace = build_meal_window_policy_trace(intent)

    assert DEFAULT_MEAL_WINDOWS["dinner"] == ("17:00", "22:00")
    assert trace["artifact_type"] == "advanced_product_lab_pending_meal_intent_meal_window_policy_trace"
    assert trace["status"] == "pass"
    assert trace["target_window"] == "dinner"
    assert trace["window_start_local"] == "17:00"
    assert trace["window_end_local"] == "22:00"
    assert trace["window_source"] == "default"
    assert trace["followup_timing"] == "meal_window_end"
    assert trace["quiet_hours_policy"] == "chat_thread_message_only_no_push"
    assert trace["scheduler_delivery_allowed"] is False
    assert trace["notification_delivery_allowed"] is False
    assert trace["canonical_product_mutation_allowed"] is False


def test_meal_window_policy_accepts_confirmed_memory_override_as_context_only() -> None:
    intent = _intent(datetime(2026, 5, 14, 10, 30, tzinfo=UTC))
    memory_context_pack = {
        "meal_window_overrides": [
            {
                "target_window": "dinner",
                "window_start": "18:30",
                "window_end": "21:30",
                "source_ref": "memory_record:confirmed_dinner_window",
                "status": "confirmed",
            }
        ]
    }

    trace = build_meal_window_policy_trace(
        intent,
        memory_context_pack=memory_context_pack,
    )
    updated = apply_meal_window_policy_to_intent(
        intent,
        memory_context_pack=memory_context_pack,
    )

    assert trace["target_window"] == "dinner"
    assert trace["window_start_local"] == "18:30"
    assert trace["window_end_local"] == "21:30"
    assert trace["window_source"] == "confirmed_memory"
    assert trace["memory_override_applied"] is True
    assert trace["source_refs"] == ["memory_record:confirmed_dinner_window"]
    assert trace["pending_intent_patch"]["meal_window_posture"]["window_source"] == (
        "confirmed_memory"
    )
    assert updated.meal_window_posture.target_window == "dinner"
    assert updated.meal_window_posture.window_source == "confirmed_memory"
    assert updated.candidate_metadata["meal_window"] == "dinner"
    assert updated.canonical_write_authorized is False


def test_meal_window_policy_rejects_low_confidence_override_and_handles_quiet_hours() -> None:
    intent = _intent(datetime(2026, 5, 14, 15, 30, tzinfo=UTC))
    memory_context_pack = {
        "meal_window_overrides": [
            {
                "target_window": "late_night",
                "window_start": "23:00",
                "window_end": "01:30",
                "source_ref": "memory_record:weak_late_night",
                "status": "candidate",
            }
        ]
    }

    trace = build_meal_window_policy_trace(
        intent,
        memory_context_pack=memory_context_pack,
    )

    assert trace["target_window"] == "late_night"
    assert trace["window_start_local"] == "22:00"
    assert trace["window_end_local"] == "01:00"
    assert trace["window_source"] == "default"
    assert trace["memory_override_applied"] is False
    assert "memory_override.status_not_allowed:candidate" in trace["blockers"]
    assert trace["followup_in_quiet_hours"] is True
    assert trace["quiet_hours_policy"] == "chat_thread_message_only_no_push"
    assert trace["scheduler_delivery_allowed"] is False


def _intent(created_at: datetime) -> PendingMealIntent:
    return PendingMealIntent(
        intent_id="pending-window-1",
        user_id="user-1",
        candidate_title="dinner candidate",
        source_surface="chat",
        created_at=created_at,
        expires_at=created_at + timedelta(hours=6),
    )
