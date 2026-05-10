from __future__ import annotations

from app.advanced_shadow_lab.product_lab_closure_summary import (
    build_product_lab_closure_summary,
)


def test_product_lab_closure_summary_requires_user_actions_and_activation_wall() -> None:
    summary = build_product_lab_closure_summary(
        {
            "status": "pass",
            "lab_memory_store_written": True,
            "lab_memory_context_injected": True,
            "product_recommendation_selected_candidate_ids": ["golden-1"],
            "product_proactive_delivery_packet_ready": True,
            "product_outputs_applied_to_chat_surface": True,
            "lab_chat_action_outcome_types": ["recommendation_intake_draft"],
            "lab_chat_action_blockers": [],
            "mainline_activation_enabled": True,
            "canonical_product_mutation_allowed": False,
            "durable_product_memory_written": False,
            "production_scheduler_delivery_allowed": False,
        }
    )

    assert summary["advanced_product_lab_product_loop_closed"] is False
    assert summary["advanced_product_lab_closure_missing"] == [
        "rescue_commit_action_replayed",
        "activation_wall_intact",
    ]
