from __future__ import annotations

import json
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


def test_product_lab_e2e_surface_uses_product_outputs_and_controls(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("product-closure-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
        lab_memory_context_pack=_memory_pack(tmp_path),
    )
    messages = artifact["lab_chat_surface"]["messages"]
    serialized = json.dumps(artifact["lab_chat_surface"], ensure_ascii=False)

    assert artifact["status"] == "pass"
    assert artifact["product_lab_recommendation_artifact"]["offer_synthesis"][
        "selected_primary"
    ]["candidate_id"] == "memory-oatmeal"
    assert messages[0]["workflow_family"] == "recommendation"
    assert "Morning Bar oatmeal" in messages[0]["copy"]
    assert messages[0]["product_runtime_output_refs"] == [
        "advanced_product_lab_recommendation_runtime_artifact",
        "advanced_product_lab_proactive_runtime_artifact",
    ]
    assert messages[1]["workflow_family"] == "rescue"
    assert "Smooth today over 2 days" in messages[1]["copy"]
    assert messages[1]["product_runtime_output_refs"] == [
        "advanced_product_lab_rescue_runtime_artifact",
        "advanced_product_lab_proactive_runtime_artifact",
    ]
    assert all(message["controls_visible"] is True for message in messages)
    assert artifact["product_lab_proactive_artifact"]["candidate_count"] == 2
    assert artifact["lab_chat_response_packet"]["product_outputs_applied"] is True
    assert "no_send" not in serialized


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
