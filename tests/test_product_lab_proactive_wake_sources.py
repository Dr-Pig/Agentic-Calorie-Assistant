from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
from app.advanced_shadow_lab.product_lab_proactive_wake_sources import (
    build_product_lab_proactive_wake_sources,
)


def test_wake_source_adapters_separate_context_only_memory_from_candidates() -> None:
    artifact = build_product_lab_proactive_wake_sources(
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=_memory_pack(),
        recommendation_artifact=_recommendation_artifact(),
        rescue_artifact=_rescue_artifact(),
        action_state=_action_state(),
    )

    assert artifact["artifact_type"] == (
        "advanced_product_lab_proactive_wake_source_adapter_artifact"
    )
    assert artifact["status"] == "pass"
    assert artifact["wake_source_count"] == 4
    assert artifact["candidate_spec_trigger_types"] == [
        "recommendation_prompt",
        "pending_intake_followup",
        "rescue_nudge",
    ]
    assert artifact["context_only_source_families"] == ["memory"]
    memory_source = artifact["wake_sources"][0]
    assert memory_source["source_family"] == "memory"
    assert memory_source["candidate_spec"] is None
    assert memory_source["wake_source_is_user_benefit"] is False
    assert memory_source["user_relevant_reason"] == ""
    assert artifact["scheduler_delivery_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_product_lab_proactive_uses_wake_source_adapter_trace() -> None:
    artifact = run_product_lab_proactive(
        turn={"session_id": "s1", "turn_id": "t1", "surface": "chat"},
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=_memory_pack(),
        recommendation_artifact=_recommendation_artifact(),
        rescue_artifact=_rescue_artifact(),
        action_state=_action_state(),
    )

    assert artifact["status"] == "pass"
    assert artifact["candidate_count"] == 3
    assert artifact["wake_source_adapter"]["candidate_spec_trigger_types"] == [
        "recommendation_prompt",
        "pending_intake_followup",
        "rescue_nudge",
    ]
    assert artifact["wake_source_adapter"]["context_only_source_families"] == [
        "memory"
    ]
    assert artifact["source_outputs_read"] == [
        "advanced_product_lab_recommendation_runtime_artifact",
        "advanced_product_lab_rescue_runtime_artifact",
        "",
        "advanced_product_lab_action_state",
        "",
        "advanced_product_lab_proactive_wake_source_adapter_artifact",
        "",
    ]


def _memory_pack() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_memory_context_pack",
        "status": "pass",
        "selected_record_ids": ["memory-oatmeal"],
        "entries": [
            {
                "record_id": "memory-oatmeal",
                "memory_type": "golden_order",
                "summary": "Morning Bar oatmeal is reliable.",
                "intended_consumers": ["recommendation", "proactive"],
            }
        ],
    }


def _recommendation_artifact() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_runtime_artifact",
        "status": "pass",
        "recommendation_served_to_lab": True,
        "proactive_recommendation_candidate_allowed": True,
        "offer_synthesis": {
            "selected_primary": {"candidate_id": "memory-oatmeal"}
        },
    }


def _rescue_artifact() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_rescue_runtime_artifact",
        "status": "pass",
        "proposal_presented_to_lab": True,
        "proposal_card": {"card_kind": "same_day_rescue_lab"},
        "guardrail_math": {
            "rescue_needed": True,
            "recovery_viability": "viable",
            "recommended_days": 2,
            "daily_kcal_adjustment": -150,
        },
        "pending_rescue_commit_packet": {
            "handoff_state": "pending_user_rescue_commit_confirmation",
            "requires_explicit_user_rescue_commit": True,
            "canonical_commit_requested": False,
        },
        "proposal_committed": False,
        "day_budget_mutated": False,
    }


def _action_state() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_action_state",
        "active_pending_intake_draft_ids": ["draft-1"],
        "active_pending_intake_source_refs": ["pending:draft-1"],
    }
