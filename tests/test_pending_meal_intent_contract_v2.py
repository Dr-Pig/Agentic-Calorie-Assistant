from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.runtime.contracts.pending_meal_intent import (
    PendingMealIntent,
    PendingMealIntentMealWindowPosture,
    PendingMealIntentScopeKeys,
)


def test_pending_meal_intent_v2_defaults_to_scoped_short_term_context() -> None:
    created_at = datetime(2026, 5, 14, 9, 0, tzinfo=UTC)
    intent = PendingMealIntent(
        intent_id="pending-ramen-1",
        user_id="user-1",
        candidate_title="ramen candidate for dinner",
        source_surface="chat",
        created_at=created_at,
        expires_at=created_at + timedelta(hours=6),
    )

    assert intent.contract_version == "2.0"
    assert intent.scope_keys.model_dump() == {
        "user_id": "user-1",
        "workspace_id": "default",
        "project_id": "default",
        "surface": "chat",
    }
    assert intent.ttl_policy.model_dump() == {
        "ttl_hours": 6,
        "max_ttl_hours": 6,
        "expiry_source": "default",
    }
    assert intent.meal_window_posture.followup_timing == "meal_window_end"
    assert intent.meal_window_posture.quiet_hours_policy == "chat_thread_message_only_no_push"
    assert intent.context_pack_identity.block_id == "pending_meal_intent:pending-ramen-1"
    assert intent.context_pack_identity.include_in_manager_context is True
    assert intent.context_pack_identity.canonical_write_authorized is False


def test_pending_meal_intent_rejects_scope_user_mismatch_and_excess_ttl() -> None:
    created_at = datetime(2026, 5, 14, 9, 0, tzinfo=UTC)

    with pytest.raises(ValidationError, match="scope_keys.user_id must match user_id"):
        PendingMealIntent(
            intent_id="pending-ramen-2",
            user_id="user-1",
            scope_keys=PendingMealIntentScopeKeys(user_id="other-user"),
            candidate_title="ramen candidate for dinner",
            source_surface="chat",
            created_at=created_at,
            expires_at=created_at + timedelta(hours=6),
        )

    with pytest.raises(ValidationError, match="expires_at exceeds ttl_policy.max_ttl_hours"):
        PendingMealIntent(
            intent_id="pending-ramen-3",
            user_id="user-1",
            candidate_title="ramen candidate for dinner",
            source_surface="chat",
            created_at=created_at,
            expires_at=created_at + timedelta(hours=7),
        )


def test_pending_meal_intent_context_pack_block_is_bounded_and_non_mutating() -> None:
    created_at = datetime(2026, 5, 14, 17, 0, tzinfo=UTC)
    intent = PendingMealIntent(
        intent_id="pending-hotpot-1",
        user_id="user-1",
        candidate_title="hotpot dinner option",
        source_surface="recommendation_card",
        created_at=created_at,
        expires_at=created_at + timedelta(hours=4),
        candidate_metadata={
            "candidate_id": "hotpot-1",
            "estimated_kcal": 780,
            "raw_transcript": "must not enter the manager context block",
        },
        meal_window_posture=PendingMealIntentMealWindowPosture(
            target_window="dinner",
            window_source="default",
        ),
    )

    block = intent.to_context_pack_block()

    assert block["block_type"] == "PENDING_MEAL_INTENT"
    assert block["block_id"] == "pending_meal_intent:pending-hotpot-1"
    assert block["state_category"] == "short_term_context"
    assert block["canonical_write_authorized"] is False
    assert block["intake_handoff_required"] is True
    assert block["meal_window_posture"]["target_window"] == "dinner"
    assert block["candidate_metadata_summary"] == {
        "candidate_id": "hotpot-1",
        "estimated_kcal": 780,
    }
    assert "raw_transcript" not in str(block)


def test_pending_meal_intent_trace_payload_exposes_v2_contract_boundaries() -> None:
    created_at = datetime(2026, 5, 14, 20, 0, tzinfo=UTC)
    intent = PendingMealIntent(
        intent_id="pending-bento-1",
        user_id="user-1",
        candidate_title="bento candidate",
        source_surface="chat",
        status="dismissed",
        created_at=created_at,
        expires_at=created_at + timedelta(hours=1),
    )

    trace = intent.to_trace_payload()

    assert trace["contract_scope"] == "pending_meal_intent_only"
    assert trace["contract_version"] == "2.0"
    assert trace["state_category"] == "short_term_context"
    assert trace["context_pack_block_id"] == "pending_meal_intent:pending-bento-1"
    assert trace["scope_keys"]["surface"] == "chat"
    assert trace["ttl_policy"]["ttl_hours"] == 6
    assert trace["meal_window_posture"]["followup_timing"] == "meal_window_end"
    assert trace["dismissed_scope"] == "current_intent_instance_only"
    assert trace["durable_memory_write_authorized"] is False
    assert trace["canonical_write_authorized"] is False
