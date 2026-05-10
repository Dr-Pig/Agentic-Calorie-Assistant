from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import (
    ProductLabMemoryStore,
    build_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from tests.test_advanced_product_lab_runtime import _turn


def test_recommendation_creates_pending_intake_handoff_without_commit(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("recommendation-handoff-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
        lab_memory_context_pack=_memory_pack(tmp_path),
    )

    recommendation = artifact["product_lab_recommendation_artifact"]
    handoff = recommendation["pending_intake_handoff_packet"]
    message_offer = artifact["lab_chat_surface"]["messages"][0][
        "recommendation_offer"
    ]

    assert recommendation["recommendation_intent_state_created"] is True
    assert handoff["artifact_type"] == "advanced_product_lab_pending_intake_handoff"
    assert handoff["handoff_state"] == "pending_user_intake_confirmation"
    assert handoff["candidate_id"] == "memory-oatmeal"
    assert handoff["lab_intake_intent_created"] is True
    assert handoff["canonical_commit_requested"] is False
    assert handoff["canonical_product_mutation_allowed"] is False
    assert message_offer["intake_handoff_state"] == "pending_user_intake_confirmation"
    assert message_offer["canonical_commit_requested"] is False


def _memory_pack(tmp_path: Path) -> dict[str, object]:
    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="closure-session",
        turn_id="t1",
        events=[
            {
                "memory_id": "memory-oatmeal",
                "memory_type": "golden_order",
                "summary": "Morning Bar oatmeal is reliable before meetings.",
                "review_status": "accepted_lab",
                "source_object_refs": ["turn:t1:user"],
                "store_name": "Morning Bar",
                "item_names": ["oatmeal"],
                "estimated_kcal": 420,
                "intended_consumers": ["recommendation", "proactive"],
            }
        ],
    )
    return build_product_lab_memory_context_pack(
        store=store,
        session_id="closure-session",
        turn_id="t2",
        consumers=["recommendation", "proactive"],
        token_budget=120,
    )
