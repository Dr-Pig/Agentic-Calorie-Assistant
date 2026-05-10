from __future__ import annotations

from app.recommendation.application.three_node_shadow_contract import (
    build_fixture_recommendation_three_node_input,
    run_recommendation_three_node_shadow,
)
from app.recommendation.application.three_node_summary_bridge import (
    build_summary_quality_report_from_three_node_shadow_artifact,
)


def test_offer_shadow_packet_consumes_three_node_quality_without_serving() -> None:
    from app.recommendation.application.offer_shadow_packet import (
        build_recommendation_offer_shadow_packet,
    )

    payload = _payload_with_reviewed_memory_candidates()
    three_node_artifact = run_recommendation_three_node_shadow(payload)
    quality_report = build_summary_quality_report_from_three_node_shadow_artifact(
        memory_summary_projection=_memory_projection(),
        three_node_artifact=three_node_artifact,
        source_payload=payload,
    )

    packet = build_recommendation_offer_shadow_packet(
        recommendation_quality_report=quality_report,
        three_node_artifact=three_node_artifact,
        requested_surface="chat",
    )

    assert packet["artifact_type"] == "recommendation_offer_shadow_packet"
    assert packet["status"] == "pass"
    assert packet["canonical_recommendation_graph"] == "three_node"
    assert packet["physical_node_order"] == [
        "recommendation_planning",
        "candidate_retrieval_guard_scoring",
        "offer_synthesis",
    ]
    assert [row["logical_stage"] for row in packet["logical_stage_trace"]] == [
        "recommendation_context_result",
        "candidate_spec",
        "candidate_retrieval_guard_scoring",
        "ranking_result",
        "recommendation_response_result",
    ]
    assert packet["selected_primary"]["candidate_id"] == "golden-1"
    assert packet["backup_candidates"] == [
        {
            "candidate_id": "backup-1",
            "title": "7-11 salmon rice ball and salad chicken",
            "store_name": "7-11",
            "estimated_kcal": 500,
            "source_refs": ["memory_candidate:backup-1"],
        }
    ]
    assert packet["offer_synthesis_trace"]["owner"] == "llm_fixture"
    assert packet["offer_synthesis_trace"]["backup_candidate_ids"] == ["backup-1"]
    assert packet["ux_packet"] == {
        "surface": "chat",
        "serve_allowed": False,
        "primary_candidate_id": "golden-1",
        "backup_candidate_ids": ["backup-1"],
        "explanation": "Golden order fits the remaining budget and reviewed preferences.",
    }
    assert packet["decision_ownership"] == {
        "recommendation_planning": "llm_fixture",
        "candidate_retrieval_guard_scoring": "deterministic",
        "offer_synthesis": "llm_fixture",
        "deterministic_role": "validate_filter_score_and_reject_only",
        "llm_role": "plan_and_synthesize_without_mutation",
    }
    assert packet["runtime_effect_allowed"] is False
    assert packet["recommendation_served"] is False
    assert packet["user_facing_behavior_changed"] is False
    assert packet["intake_handoff_created"] is False
    assert packet["pending_meal_intent_created"] is False
    assert packet["canonical_product_mutation_allowed"] is False


def test_offer_shadow_packet_blocks_unreviewed_or_claim_drift_inputs() -> None:
    from app.recommendation.application.offer_shadow_packet import (
        build_recommendation_offer_shadow_packet,
    )

    payload = _payload_with_reviewed_memory_candidates()
    three_node_artifact = run_recommendation_three_node_shadow(payload)
    quality_report = build_summary_quality_report_from_three_node_shadow_artifact(
        memory_summary_projection=_memory_projection(),
        three_node_artifact=three_node_artifact,
        source_payload=payload,
    )
    quality_report["recommendation_served"] = True
    quality_report["candidate_evaluations"][0]["source_refs"] = [
        "memory_candidate:unreviewed-1"
    ]

    packet = build_recommendation_offer_shadow_packet(
        recommendation_quality_report=quality_report,
        three_node_artifact=three_node_artifact,
    )

    assert packet["status"] == "blocked"
    assert "recommendation_quality_report.recommendation_served" in packet["blockers"]
    assert "selected_primary.reviewed_memory_source_ref_missing" in packet["blockers"]
    assert packet["selected_primary"] is None
    assert packet["ux_packet"] is None
    assert packet["recommendation_served"] is False
    assert packet["canonical_product_mutation_allowed"] is False


def _payload_with_reviewed_memory_candidates() -> dict[str, object]:
    payload = build_fixture_recommendation_three_node_input()
    payload["negative_preference_summary"] = {"items": []}
    payload["memory_summary_projection"] = _memory_projection()
    payload["candidate_source_fixture"] = [
        _candidate("golden-1", "FamilyMart salad chicken and sweet potato", "FamilyMart", 520),
        _candidate("backup-1", "7-11 salmon rice ball and salad chicken", "7-11", 500),
        _candidate("blocked-1", "large pork cutlet rice", "Bento Shop", 920),
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
        "explanation": "Golden order fits the remaining budget and reviewed preferences.",
        "recommendation_served": False,
        "is_canonical_truth": False,
        "intake_commit_requested": False,
    }
    return payload


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
            "negative_preference_blockers": ["neg-1"],
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
