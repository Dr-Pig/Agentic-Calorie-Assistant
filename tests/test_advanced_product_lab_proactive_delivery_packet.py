from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import (
    ProductLabMemoryStore,
    build_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_recommendation import (
    run_product_lab_recommendation,
)
from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue


def test_product_lab_proactive_delivery_packet_keeps_scheduler_wall(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive

    fixture_inputs = build_product_lab_fixture_inputs()
    memory_pack = _memory_pack(tmp_path)
    recommendation = run_product_lab_recommendation(
        turn=_turn(),
        fixture_inputs=fixture_inputs,
        memory_context_pack=memory_pack,
    )
    rescue = run_product_lab_rescue(fixture_inputs=fixture_inputs)

    artifact = run_product_lab_proactive(
        turn=_turn(),
        fixture_inputs=fixture_inputs,
        memory_context_pack=memory_pack,
        recommendation_artifact=recommendation,
        rescue_artifact=rescue,
    )
    delivery = artifact["delivery_packet"]

    assert delivery["artifact_type"] == "advanced_product_lab_proactive_delivery_packet"
    assert delivery["delivery_surface"] == "chat"
    assert delivery["chat_delivery_allowed"] is True
    assert delivery["scheduler_delivery_attempted"] is False
    assert delivery["notification_delivery_attempted"] is False
    assert delivery["candidate_ids"] == ["recommendation_prompt", "rescue_nudge"]
    assert delivery["controls_by_candidate"]["recommendation_prompt"] == {
        "dismiss": True,
        "snooze": True,
        "undo": True,
    }
    assert delivery["served_to_mainline_user"] is False


def _memory_pack(tmp_path: Path) -> dict[str, object]:
    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="proactive-session",
        turn_id="t1",
        events=[
            {
                "memory_id": "memory-oatmeal",
                "memory_type": "golden_order",
                "summary": "Morning Bar oatmeal is a reliable breakfast option.",
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
        session_id="proactive-session",
        turn_id="t2",
        consumers=["recommendation", "proactive"],
        token_budget=120,
    )


def _turn() -> dict[str, object]:
    return {
        "session_id": "proactive-session",
        "turn_id": "t2",
        "semantic_intent_fixture": "next_meal_recommendation",
        "surface": "chat",
    }
