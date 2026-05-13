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


def test_pending_intake_handoff_declares_non_committing_contract(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("recommendation-handoff-contract-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
        lab_memory_context_pack=_memory_pack(tmp_path),
    )

    handoff = artifact["product_lab_recommendation_artifact"][
        "pending_intake_handoff_packet"
    ]
    message_offer = artifact["lab_chat_surface"]["messages"][0][
        "recommendation_offer"
    ]

    assert handoff["contract_scope"] == "pending_intake_handoff_only"
    assert handoff["requires_user_confirmation_before_commit"] is True
    assert handoff["allowed_next_actions"] == [
        "confirm_log_this",
        "edit_before_log",
        "dismiss",
    ]
    assert handoff["forbidden_side_effects"] == [
        "meal_thread_mutation",
        "ledger_entry_creation",
        "day_budget_mutation",
        "durable_memory_write",
    ]
    assert handoff["source_ux_action"]["action"] == "log_this"
    assert handoff["source_ux_action"]["canonical_commit_requested"] is False
    assert handoff["meal_thread_mutated"] is False
    assert handoff["intake_committed"] is False
    assert handoff["ledger_entry_created"] is False
    assert handoff["day_budget_mutated"] is False
    assert handoff["durable_product_memory_written"] is False
    assert message_offer["handoff_contract"] == handoff["handoff_contract"]
    assert artifact["canonical_product_mutation_allowed"] is False


def test_recommendation_train_records_pr12_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 12
    assert plan["last_completed_pr_number"] >= 12
    assert plan["active_pr_number"] >= 13
    assert {
        "pr_number": 12,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_pending_intake_handoff_completed_locally",
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
