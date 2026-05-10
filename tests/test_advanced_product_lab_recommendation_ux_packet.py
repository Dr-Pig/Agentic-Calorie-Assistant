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


def test_product_lab_recommendation_offer_packet_is_chat_first_and_confirmed(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("recommendation-ux-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
        lab_memory_context_pack=_memory_pack(tmp_path),
    )

    ux_packet = artifact["product_lab_recommendation_artifact"]["offer_synthesis"][
        "ux_packet"
    ]
    message = artifact["lab_chat_surface"]["messages"][0]

    assert ux_packet["chat_first"] is True
    assert ux_packet["primary_candidate"]["candidate_id"] == "memory-oatmeal"
    assert ux_packet["backup_candidate_ids"] == ["golden-1"]
    assert ux_packet["backup_candidates"][0]["candidate_id"] == "golden-1"
    assert ux_packet["actions"] == [
        {
            "action": "log_this",
            "requires_explicit_user_intake_action": True,
            "canonical_commit_requested": False,
        },
        {"action": "show_backups", "requires_explicit_user_intake_action": False},
        {"action": "dismiss", "requires_explicit_user_intake_action": False},
    ]
    assert ux_packet["non_serve_flags"] == {
        "served_to_mainline_user": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
    }
    assert message["recommendation_offer"]["primary_candidate_id"] == "memory-oatmeal"
    assert message["recommendation_offer"]["offer_actions"] == ux_packet["actions"]
    assert message["recommendation_offer"]["candidate_snapshot"]["candidate_id"] == (
        "memory-oatmeal"
    )
    assert message["recommendation_offer"][
        "source_pending_intake_handoff_artifact_type"
    ] == "advanced_product_lab_pending_intake_handoff"
    assert message["canonical_mutation_requested"] is False


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
