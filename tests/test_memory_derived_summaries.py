from datetime import datetime, timezone

from app.memory.application.derived_summaries import (
    build_golden_order_summary,
    build_preference_profile_summary,
    build_suppression_summary,
)
from app.memory.domain.summaries import CommittedMealEvent, InteractionPreferenceEvent


def test_preference_profile_summary_is_read_only_derived_state() -> None:
    events = [
        CommittedMealEvent(
            event_id="m1",
            occurred_at=datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc),
            item_names=["chicken bento"],
            store_name="Corner Bento",
            cuisine_family="taiwanese",
        ),
        CommittedMealEvent(
            event_id="m2",
            occurred_at=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
            item_names=["chicken bento"],
            store_name="Corner Bento",
            cuisine_family="taiwanese",
        ),
    ]

    summary = build_preference_profile_summary(events)

    assert summary.source_kind == "derived_read_model"
    assert summary.is_durable_memory_truth is False
    assert summary.top_items[0].label == "chicken bento"
    assert summary.top_stores[0].label == "Corner Bento"


def test_golden_order_summary_requires_repeated_committed_pattern() -> None:
    events = [
        CommittedMealEvent(
            event_id=f"m{i}",
            occurred_at=datetime(2026, 4, 20 + i, 18, 0, tzinfo=timezone.utc),
            item_names=["salad chicken", "sweet potato"],
            store_name="FamilyMart",
        )
        for i in range(3)
    ]

    summary = build_golden_order_summary(events, minimum_count=3)

    assert summary.source_kind == "derived_read_model"
    assert summary.is_durable_memory_truth is False
    assert len(summary.orders) == 1
    assert summary.orders[0].store_name == "FamilyMart"
    assert summary.orders[0].item_names == ["salad chicken", "sweet potato"]


def test_suppression_summary_ignores_current_instance_dismissals_without_writing_memory() -> None:
    events = [
        InteractionPreferenceEvent(
            event_id="i1",
            occurred_at=datetime(2026, 4, 28, 8, 0, tzinfo=timezone.utc),
            trigger_type="meal_reminder",
            action="dismissed",
        ),
        InteractionPreferenceEvent(
            event_id="i2",
            occurred_at=datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc),
            trigger_type="meal_reminder",
            action="ignored",
        ),
    ]

    summary = build_suppression_summary(events)

    assert summary.source_kind == "derived_read_model"
    assert summary.is_durable_memory_truth is False
    assert summary.suppression_signals[0].trigger_type == "meal_reminder"
    assert summary.suppression_signals[0].count == 1
    assert summary.suppression_signals[0].actions == ["ignored"]
