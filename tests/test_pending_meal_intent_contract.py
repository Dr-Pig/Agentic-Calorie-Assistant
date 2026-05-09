from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.runtime.contracts.pending_meal_intent import PendingMealIntent
from app.runtime.contracts.pending_meal_intent_replay_seeds import (
    pending_meal_intent_replay_seed_traces,
)


def test_pending_meal_intent_is_short_term_contract_only() -> None:
    created_at = datetime.now(timezone.utc) - timedelta(hours=1)
    intent = PendingMealIntent(
        intent_id="intent-1",
        user_id="user-1",
        candidate_title="Maybe eat chicken bento tonight",
        source_surface="chat",
        status="created",
        created_at=created_at,
        expires_at=created_at + timedelta(hours=6),
    )

    assert intent.is_active is True
    assert intent.canonical_write_authorized is False
    assert intent.to_trace_payload()["contract_scope"] == "pending_meal_intent_only"


@pytest.mark.parametrize("status", ["confirmed_eaten", "dismissed", "expired"])
def test_terminal_pending_meal_intent_statuses_are_not_active(status: str) -> None:
    created_at = datetime(2026, 4, 30, 18, 0, tzinfo=timezone.utc)
    intent = PendingMealIntent(
        intent_id=f"intent-{status}",
        user_id="user-1",
        candidate_title="Maybe eat noodles tonight",
        source_surface="recommendation_card",
        status=status,
        created_at=created_at,
        expires_at=created_at + timedelta(hours=6),
    )

    assert intent.is_active is False
    if status == "dismissed":
        assert intent.to_trace_payload()["dismissed_scope"] == "current_intent_instance_only"


def test_pending_meal_intent_rejects_canonical_write_authority() -> None:
    created_at = datetime(2026, 4, 30, 18, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError):
        PendingMealIntent(
            intent_id="intent-2",
            user_id="user-1",
            candidate_title="Maybe eat dumplings tonight",
            source_surface="chat",
            status="created",
            created_at=created_at,
            expires_at=created_at + timedelta(hours=6),
            canonical_write_authorized=True,
        )


def test_pending_meal_intent_requires_future_expiration_and_supports_time_check() -> None:
    created_at = datetime(2026, 4, 30, 18, 0, tzinfo=timezone.utc)
    intent = PendingMealIntent(
        intent_id="intent-3",
        user_id="user-1",
        candidate_title="Maybe eat chicken bento tonight",
        source_surface="chat",
        status="created",
        created_at=created_at,
        expires_at=created_at + timedelta(hours=2),
    )

    assert intent.is_active_at(created_at + timedelta(hours=1)) is True
    assert intent.is_active_at(created_at + timedelta(hours=3)) is False

    with pytest.raises(ValidationError):
        PendingMealIntent(
            intent_id="intent-4",
            user_id="user-1",
            candidate_title="Expired at creation",
            source_surface="chat",
            status="created",
            created_at=created_at,
            expires_at=created_at,
        )


def test_pending_meal_intent_is_active_property_respects_expiry() -> None:
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(hours=2)
    intent = PendingMealIntent(
        intent_id="intent-5",
        user_id="user-1",
        candidate_title="Maybe eat noodles tonight",
        source_surface="chat",
        status="created",
        created_at=created_at,
        expires_at=now + timedelta(hours=2),
    )

    intent = intent.model_copy(update={"expires_at": now - timedelta(minutes=1)})

    assert intent.is_active is False


def test_pending_meal_intent_replay_seeds_stay_contract_only() -> None:
    traces = pending_meal_intent_replay_seed_traces()

    assert [trace["status"] for trace in traces] == ["created", "dismissed"]
    for trace in traces:
        assert trace["contract_scope"] == "pending_meal_intent_only"
        assert trace["canonical_write_authorized"] is False
        assert trace["source_surface"] == "recommendation_card"

    assert traces[1]["dismissed_scope"] == "current_intent_instance_only"
