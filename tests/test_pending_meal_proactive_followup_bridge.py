from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_pending_intake_surface import (
    pending_intake_chat_packets,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
from app.runtime.contracts.pending_meal_intent import (
    PendingMealIntent,
    PendingMealIntentMealWindowPosture,
)
from tests.test_product_lab_proactive_wake_sources import (
    _memory_pack,
    _recommendation_artifact,
    _rescue_artifact,
)


def test_pending_meal_intent_context_wakes_pending_intake_followup() -> None:
    artifact = run_product_lab_proactive(
        turn={"session_id": "s1", "turn_id": "t1", "surface": "chat"},
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=_memory_pack(),
        recommendation_artifact=_recommendation_artifact(),
        rescue_artifact=_rescue_artifact(),
        action_state={
            "artifact_type": "advanced_product_lab_action_state",
            "active_pending_meal_intents": [_intent("intent-1").model_dump(mode="json")],
            "active_pending_meal_intent_source_refs": [
                "pending_meal_intent:intent-1"
            ],
        },
    )

    candidate = next(
        item
        for item in artifact["candidates"]
        if item["trigger_type"] == "pending_intake_followup"
    )
    delivery_trace = artifact["delivery_packet"]["candidate_traces_by_candidate"][
        "pending_intake_followup"
    ]
    [surface_packet] = pending_intake_chat_packets(product_proactive=artifact)

    assert candidate["source_output_refs"] == [
        "advanced_product_lab_action_state",
        "pending_meal_intent:intent-1",
    ]
    assert candidate["source_bridge_trace"] == {
        "downstream_workflow_family": "pending_meal_intent",
        "active_pending_intake_draft_ids": [],
        "active_pending_meal_intent_ids": ["intent-1"],
        "target_windows": ["dinner"],
        "followup_timing": ["meal_window_end"],
        "quiet_hours_policy": ["chat_thread_message_only_no_push"],
        "canonical_write_authorized": False,
        "meal_thread_mutated": False,
        "ledger_entry_created": False,
    }
    assert delivery_trace["downstream_workflow_family"] == "pending_meal_intent"
    assert surface_packet["pending_meal_intent_ids"] == ["intent-1"]
    assert surface_packet["canonical_mutation_requested"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_closed_pending_meal_intent_does_not_wake_followup() -> None:
    closed = _intent("intent-closed").model_dump(mode="json")
    closed["status"] = "dismissed"

    artifact = run_product_lab_proactive(
        turn={"session_id": "s1", "turn_id": "t1", "surface": "chat"},
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=_memory_pack(),
        recommendation_artifact=_recommendation_artifact(),
        rescue_artifact=_rescue_artifact(),
        action_state={
            "artifact_type": "advanced_product_lab_action_state",
            "active_pending_meal_intents": [closed],
        },
    )

    assert [
        item["trigger_type"]
        for item in artifact["candidates"]
        if item["trigger_type"] == "pending_intake_followup"
    ] == []


def _intent(intent_id: str) -> PendingMealIntent:
    created = datetime(2026, 5, 14, 18, 0, tzinfo=UTC)
    return PendingMealIntent(
        intent_id=intent_id,
        user_id="user-1",
        candidate_title="FamilyMart salad chicken",
        source_surface="chat",
        created_at=created,
        expires_at=created + timedelta(hours=6),
        meal_window_posture=PendingMealIntentMealWindowPosture(
            target_window="dinner",
            window_source="user_explicit",
            followup_timing="meal_window_end",
        ),
        candidate_metadata={
            "candidate_id": "golden-1",
            "store_name": "FamilyMart",
            "estimated_kcal": 520,
        },
    )
