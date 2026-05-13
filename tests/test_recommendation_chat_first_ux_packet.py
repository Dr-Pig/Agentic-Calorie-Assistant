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


def test_recommendation_chat_first_ux_packet_exposes_offer_explanation_and_controls(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("recommendation-chat-ux-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
        lab_memory_context_pack=_memory_pack(tmp_path),
    )

    ux_packet = artifact["product_lab_recommendation_artifact"]["offer_synthesis"][
        "ux_packet"
    ]
    message = artifact["lab_chat_surface"]["messages"][0]["recommendation_offer"]

    assert ux_packet["explanation_card"] == {
        "primary_candidate_id": "memory-oatmeal",
        "why_this": "Morning Bar oatmeal fits the current budget and remembered preference context.",
        "backup_count": 1,
        "source_refs": ["memory_candidate:memory-oatmeal"],
    }
    assert ux_packet["backup_options"][0]["candidate_id"] == "golden-1"
    assert ux_packet["backup_options"][0]["presentation_role"] == "backup"
    assert ux_packet["control_model"] == {
        "dismiss_reason_choices": [
            "not_relevant_now",
            "already_handled",
            "too_frequent",
        ],
        "snooze_window": {"kind": "duration", "minutes": 180},
        "undo_scope": "current_recommendation_offer_only",
        "next_signal_required": "new_app_open_with_qualified_pool",
    }
    assert message["explanation_card"] == ux_packet["explanation_card"]
    assert message["backup_options"] == ux_packet["backup_options"]
    assert message["control_model"] == ux_packet["control_model"]
    assert artifact["lab_chat_surface"]["served_to_mainline_user"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_recommendation_train_records_pr11_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 13
    assert plan["last_completed_pr_number"] >= 11
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 12
    assert {
        "pr_number": 11,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_chat_first_ux_packet_completed_locally",
    } in plan["last_merge_evidence"]["completed_prs"]


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
