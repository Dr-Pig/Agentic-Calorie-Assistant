from __future__ import annotations

import json


def test_offer_packet_projects_to_no_send_review_without_exposing_candidates() -> None:
    from app.recommendation.application.reviewed_memory_offer_runner import (
        build_reviewed_memory_recommendation_offer_packet,
    )
    from app.runtime.application.proactive_recommendation_offer_packet_bridge import (
        build_recommendation_offer_packet_no_send_review,
    )

    packet = build_reviewed_memory_recommendation_offer_packet(
        memory_summary_projection=_memory_projection(),
        remaining_budget_kcal=700,
    )

    review = build_recommendation_offer_packet_no_send_review(packet)
    serialized = json.dumps(review, ensure_ascii=False)

    assert review["artifact_type"] == "recommendation_offer_packet_no_send_review"
    assert review["status"] == "candidate_for_human_review"
    assert review["source_offer_packet_used"] is True
    assert review["source_offer_packet_artifact_type"] == "recommendation_offer_shadow_packet"
    assert review["recommendation_pool_decision"] == "offer_packet_available"
    assert review["prompt_posture"] == "invitation_only"
    assert review["actual_candidates_included"] is False
    assert review["candidate_ids_exposed"] is False
    assert review["source_ref_count"] == 1
    assert review["source_refs_preserved"] is True
    assert review["redaction"] == {
        "candidate_ids_removed": True,
        "candidate_titles_removed": True,
        "candidate_copy_removed": True,
    }
    assert review["review_decision"] == {
        "status": "candidate_for_human_review",
        "reviewer_next_step": "review_invitation_posture_without_serving_candidates",
    }
    assert "golden-order-morning-bar-oatmeal-latte" not in serialized
    assert "FamilyMart oatmeal and latte" not in serialized
    assert "Reviewed memory golden order fits" not in serialized
    assert review["recommendation_served"] is False
    assert review["proactive_sent"] is False
    assert review["scheduler_enabled"] is False
    assert review["live_delivery_allowed"] is False
    assert review["manager_context_injected"] is False
    assert review["canonical_product_mutation_allowed"] is False


def test_offer_packet_review_can_feed_existing_no_send_candidate_bridge() -> None:
    from app.recommendation.application.reviewed_memory_offer_runner import (
        build_reviewed_memory_recommendation_offer_packet,
    )
    from app.runtime.application.proactive_no_send_nudge_bridge import (
        build_no_send_nudge_candidate_bridge,
    )
    from app.runtime.application.proactive_recommendation_offer_packet_bridge import (
        build_recommendation_offer_packet_no_send_review,
    )

    review = build_recommendation_offer_packet_no_send_review(
        build_reviewed_memory_recommendation_offer_packet(
            memory_summary_projection=_memory_projection(),
            remaining_budget_kcal=700,
        )
    )

    bridge = build_no_send_nudge_candidate_bridge(
        recommendation_prompt_review=review,
        rescue_nudge_review=None,
        user_control_models={
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool")
        },
    )
    serialized = json.dumps(bridge, ensure_ascii=False)

    assert bridge["status"] == "pass"
    assert bridge["candidate_count"] == 1
    assert bridge["candidates"][0]["trigger_type"] == "recommendation_prompt"
    assert bridge["simulation_input_metadata"] == [
        {
            "trigger_type": "recommendation_prompt",
            "wake_source": "app_open",
            "delivery_surface": "app_open",
            "candidate_kind": "recommendation_prompt_review",
            "has_required_user_controls": True,
        }
    ]
    assert "golden-order-morning-bar-oatmeal-latte" not in serialized
    assert bridge["recommendation_served"] is False
    assert bridge["proactive_sent"] is False
    assert bridge["scheduler_enabled"] is False


def test_offer_packet_bridge_blocks_claim_drift() -> None:
    from app.recommendation.application.reviewed_memory_offer_runner import (
        build_reviewed_memory_recommendation_offer_packet,
    )
    from app.runtime.application.proactive_recommendation_offer_packet_bridge import (
        build_recommendation_offer_packet_no_send_review,
    )

    packet = build_reviewed_memory_recommendation_offer_packet(
        memory_summary_projection=_memory_projection(),
        remaining_budget_kcal=700,
    )
    packet["recommendation_served"] = True

    review = build_recommendation_offer_packet_no_send_review(packet)

    assert review["status"] == "blocked"
    assert review["blockers"] == ["recommendation_offer_packet.recommendation_served"]
    assert review["source_offer_packet_used"] is False
    assert review["actual_candidates_included"] is False
    assert review["candidate_ids_exposed"] is False
    assert review["recommendation_served"] is False
    assert review["proactive_sent"] is False


def _memory_projection() -> dict[str, object]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": [
                "golden-order-morning-bar-oatmeal-latte"
            ],
            "negative_preference_blockers": [
                "negative-preference-ingredient-cilantro"
            ],
        },
        "golden_order_summary": {
            "orders": [
                {
                    "candidate_id": "golden-order-morning-bar-oatmeal-latte",
                    "store_name": "FamilyMart",
                    "summary": "FamilyMart oatmeal and latte",
                    "item_names": ["oatmeal", "latte"],
                    "estimated_kcal": 520,
                }
            ]
        },
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "rescue_proposal_committed": False,
        "retrieval_ranking_changed": False,
    }


def _controls(next_signal: str) -> dict[str, object]:
    return {
        "dismiss_reason_choices": [
            "not_relevant_now",
            "already_handled",
            "too_frequent",
        ],
        "snooze_window": {"kind": "duration", "minutes": 180},
        "undo_scope": "current_no_send_candidate_only",
        "next_signal_required": next_signal,
    }
