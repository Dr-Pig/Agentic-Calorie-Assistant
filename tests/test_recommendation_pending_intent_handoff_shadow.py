from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.recommendation.application.offer_shadow_packet import (
    build_recommendation_offer_shadow_packet,
)
from app.recommendation.application.three_node_shadow_contract import (
    build_fixture_recommendation_three_node_input,
    run_recommendation_three_node_shadow,
)
from app.recommendation.application.three_node_summary_bridge import (
    build_summary_quality_report_from_three_node_shadow_artifact,
)


def test_pending_intent_shadow_requires_explicit_acceptance_without_intake_commit() -> None:
    from app.recommendation.application.pending_intent_handoff_shadow import (
        build_recommendation_pending_intent_shadow_packet,
    )

    created_at = datetime(2026, 5, 10, 18, 0, tzinfo=UTC)
    packet = build_recommendation_pending_intent_shadow_packet(
        offer_shadow_packet=_offer_packet(),
        acceptance_event={
            "event_type": "recommendation_acceptance",
            "acceptance_kind": "pending_meal_intent",
            "source_surface": "chat",
            "user_action_id": "action-1",
        },
        user_id="user-1",
        created_at=created_at,
    )

    assert packet["artifact_type"] == "recommendation_pending_meal_intent_shadow_packet"
    assert packet["status"] == "pass"
    assert packet["pending_meal_intent_created"] is True
    trace = packet["pending_meal_intent_trace"]
    assert trace["contract_scope"] == "pending_meal_intent_only"
    assert trace["contract_version"] == "2.0"
    assert trace["intent_id"] == "pending-meal-golden-1-action-1"
    assert trace["status"] == "created"
    assert trace["source_surface"] == "chat"
    assert trace["scope_keys"]["surface"] == "chat"
    assert trace["context_pack_block_id"] == "pending_meal_intent:pending-meal-golden-1-action-1"
    assert trace["canonical_write_authorized"] is False
    assert trace["durable_memory_write_authorized"] is False
    assert trace["dismissed_scope"] is None
    assert packet["selected_candidate"]["candidate_id"] == "golden-1"
    assert packet["selected_candidate"]["source_refs"] == ["memory_candidate:golden-1"]
    assert packet["expires_at"] == (created_at + timedelta(hours=6)).isoformat()
    assert packet["acceptance_trace"]["acceptance_required"] is True
    assert packet["acceptance_trace"]["acceptance_kind"] == "pending_meal_intent"
    assert packet["recommendation_intent_state_created"] is False
    assert packet["intake_commit_requested"] is False
    assert packet["intake_handoff_created"] is False
    assert packet["canonical_product_mutation_allowed"] is False
    assert packet["manager_context_packet_changed"] is False
    assert packet["user_facing_behavior_changed"] is False


def test_pending_intent_shadow_blocks_missing_acceptance_and_intake_commit_events() -> None:
    from app.recommendation.application.pending_intent_handoff_shadow import (
        build_recommendation_pending_intent_shadow_packet,
    )

    missing_acceptance = build_recommendation_pending_intent_shadow_packet(
        offer_shadow_packet=_offer_packet(),
        acceptance_event={},
        user_id="user-1",
        created_at=datetime(2026, 5, 10, 18, 0, tzinfo=UTC),
    )
    intake_commit = build_recommendation_pending_intent_shadow_packet(
        offer_shadow_packet=_offer_packet(),
        acceptance_event={
            "event_type": "recommendation_acceptance",
            "acceptance_kind": "intake_commit_request",
            "source_surface": "chat",
            "user_action_id": "action-2",
        },
        user_id="user-1",
        created_at=datetime(2026, 5, 10, 18, 0, tzinfo=UTC),
    )

    assert missing_acceptance["status"] == "blocked"
    assert "acceptance_event.event_type_missing" in missing_acceptance["blockers"]
    assert "acceptance_event.acceptance_kind_not_pending_meal_intent" in (
        missing_acceptance["blockers"]
    )
    assert intake_commit["status"] == "blocked"
    assert "acceptance_event.intake_commit_request_not_pending_intent" in (
        intake_commit["blockers"]
    )
    assert missing_acceptance["pending_meal_intent_created"] is False
    assert intake_commit["pending_meal_intent_created"] is False


def test_pending_intent_shadow_blocks_offer_claim_drift() -> None:
    from app.recommendation.application.pending_intent_handoff_shadow import (
        build_recommendation_pending_intent_shadow_packet,
    )

    offer_packet = _offer_packet()
    offer_packet["recommendation_served"] = True

    packet = build_recommendation_pending_intent_shadow_packet(
        offer_shadow_packet=offer_packet,
        acceptance_event={
            "event_type": "recommendation_acceptance",
            "acceptance_kind": "pending_meal_intent",
            "source_surface": "chat",
            "user_action_id": "action-3",
        },
        user_id="user-1",
        created_at=datetime(2026, 5, 10, 18, 0, tzinfo=UTC),
    )

    assert packet["status"] == "blocked"
    assert "offer_shadow_packet.recommendation_served" in packet["blockers"]
    assert packet["pending_meal_intent"] is None
    assert packet["pending_meal_intent_created"] is False
    assert packet["intake_handoff_created"] is False
    assert packet["canonical_product_mutation_allowed"] is False


def _offer_packet() -> dict[str, object]:
    payload = build_fixture_recommendation_three_node_input()
    payload["negative_preference_summary"] = {"items": []}
    payload["memory_summary_projection"] = _memory_projection()
    payload["candidate_source_fixture"] = [
        _candidate("golden-1", "FamilyMart chicken bento", "FamilyMart", 520),
        _candidate("backup-1", "7-11 salmon rice ball", "7-11", 500),
    ]
    payload["manager_recommendation_decision_fixture"] = {
        "decision_mode": "llm_fixture",
        "top_candidate_id": "golden-1",
        "decision_summary": "LLM fixture selected the reviewed golden order.",
    }
    payload["shadow_offer_packet_fixture"] = {
        "decision_mode": "llm_fixture",
        "candidate_id": "golden-1",
        "backup_candidate_ids": ["backup-1"],
        "explanation": "Golden order fits the remaining budget.",
        "recommendation_served": False,
        "is_canonical_truth": False,
        "intake_commit_requested": False,
    }
    three_node = run_recommendation_three_node_shadow(payload)
    quality = build_summary_quality_report_from_three_node_shadow_artifact(
        memory_summary_projection=_memory_projection(),
        three_node_artifact=three_node,
        source_payload=payload,
    )
    return build_recommendation_offer_shadow_packet(
        recommendation_quality_report=quality,
        three_node_artifact=three_node,
    )


def _candidate(
    candidate_id: str,
    title: str,
    store_name: str,
    kcal: int,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "title": title,
        "store_name": store_name,
        "store_metadata": {"chain": store_name.lower().replace(" ", "_")},
        "source_type": "golden_order" if candidate_id == "golden-1" else "memory_candidate",
        "estimated_kcal_range": {"min": max(kcal - 80, 0), "max": kcal},
        "estimated_kcal": kcal,
        "remaining_budget_kcal": 700,
        "evidence_posture": "exact",
        "availability_posture": "available",
        "realistic_executable": True,
        "user_accessible": True,
        "item_patterns": ["reviewed_memory_candidate"],
        "hard_avoid_flags": [],
        "source_refs": [f"memory_candidate:{candidate_id}"],
    }


def _memory_projection() -> dict[str, object]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": ["golden-1", "backup-1"],
            "negative_preference_blockers": [],
        },
        "golden_order_summary": {
            "orders": [{"candidate_id": "golden-1", "store_name": "FamilyMart"}]
        },
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "rescue_proposal_committed": False,
        "retrieval_ranking_changed": False,
    }
