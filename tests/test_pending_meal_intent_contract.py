from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.runtime.contracts.pending_meal_intent import PendingMealIntent


def test_pending_meal_intent_is_short_term_contract_only() -> None:
    created_at = datetime(2026, 4, 30, 18, 0, tzinfo=timezone.utc)
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
