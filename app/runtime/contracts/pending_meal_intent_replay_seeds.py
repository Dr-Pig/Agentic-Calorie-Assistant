from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.runtime.contracts.pending_meal_intent import PendingMealIntent


def pending_meal_intent_replay_seed_traces() -> list[dict[str, Any]]:
    created_at = datetime(2026, 5, 5, 10, 0, tzinfo=UTC)
    return [
        PendingMealIntent(
            intent_id="pending-meal-recommendation-001",
            user_id="short-term-context-runtime-replay-user",
            candidate_title="low-calorie chicken bento candidate",
            source_surface="recommendation_card",
            status="created",
            created_at=created_at,
            expires_at=created_at + timedelta(hours=6),
        ).to_trace_payload(),
        PendingMealIntent(
            intent_id="pending-meal-recommendation-001",
            user_id="short-term-context-runtime-replay-user",
            candidate_title="low-calorie chicken bento candidate",
            source_surface="recommendation_card",
            status="dismissed",
            created_at=created_at,
            expires_at=created_at + timedelta(hours=6),
        ).to_trace_payload(),
    ]


__all__ = ["pending_meal_intent_replay_seed_traces"]
