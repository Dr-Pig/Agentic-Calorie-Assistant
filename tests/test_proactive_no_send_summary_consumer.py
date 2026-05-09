from __future__ import annotations


def _consumer_projection() -> dict[str, object]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "preference_summaries": [
                {
                    "candidate_id": "pref-dinner-light",
                    "summary": "prefers lighter dinner prompts",
                    "source_object_refs": ["meal:2026-05-08:dinner"],
                }
            ],
            "negative_preference_blockers": ["neg-no-late-push"],
            "is_durable_memory_truth": False,
        },
        "golden_order_summary": {
            "orders": [
                {
                    "candidate_id": "golden-bento",
                    "store_name": "Corner Bento",
                    "item_names": ["grilled fish bento"],
                    "summary": "known steady order",
                }
            ],
            "real_golden_order_materialized": False,
            "is_durable_memory_truth": False,
        },
        "suppression_summary": {
            "suppression_blockers": [
                {
                    "candidate_id": "suppress-dinner-nudge",
                    "trigger_type": "recommendation_prompt",
                    "summary": "dismissed dinner recommendation nudges twice",
                }
            ],
            "is_durable_memory_truth": False,
        },
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "rescue_proposal_committed": False,
        "retrieval_ranking_changed": False,
    }


def test_proactive_summary_consumer_reads_memory_projection_without_sending() -> None:
    from app.runtime.application.proactive_summary_consumer import (
        build_proactive_no_send_summary_consumer_projection,
    )

    artifact = build_proactive_no_send_summary_consumer_projection(_consumer_projection())

    assert artifact["artifact_type"] == "proactive_no_send_summary_consumer_projection"
    assert artifact["status"] == "pass"
    assert artifact["owner"] == "app/runtime"
    assert artifact["consumer"] == "future_proactive_no_send_review"
    assert artifact["allowed_input"] == "runtime_lab_memory_consumer_summary_projection"
    assert artifact["shadow_mode"] is True
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["scheduler_enabled"] is False
    assert artifact["push_or_line_delivery_connected"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["summary"] == {
        "preference_context_count": 1,
        "negative_preference_blocker_count": 1,
        "golden_order_context_count": 1,
        "suppression_context_count": 1,
        "memory_driven_trigger_count": 0,
        "review_context_count": 3,
    }


def test_proactive_summary_consumer_turns_suppression_into_review_context_only() -> None:
    from app.runtime.application.proactive_summary_consumer import (
        build_proactive_no_send_summary_consumer_projection,
    )

    artifact = build_proactive_no_send_summary_consumer_projection(_consumer_projection())
    suppression = artifact["suppression_review_context"]

    assert suppression == [
        {
            "candidate_id": "suppress-dinner-nudge",
            "trigger_type": "recommendation_prompt",
            "summary": "dismissed dinner recommendation nudges twice",
            "review_role": "suppression_context_only",
            "runtime_effect_allowed": False,
            "proactive_sent": False,
        }
    ]
    row = suppression[0]
    assert "candidate_copy" not in row
    assert "send_or_skip" not in row
    assert "triggered" not in row


def test_proactive_summary_consumer_blocks_projection_claim_drift() -> None:
    from app.runtime.application.proactive_summary_consumer import (
        build_proactive_no_send_summary_consumer_projection,
    )

    projection = _consumer_projection()
    projection["proactive_sent"] = True

    artifact = build_proactive_no_send_summary_consumer_projection(projection)

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["consumer_summary_projection.proactive_sent"]
    assert artifact["summary"]["review_context_count"] == 0
    assert artifact["proactive_sent"] is False
    assert artifact["scheduler_enabled"] is False


def test_proactive_summary_consumer_does_not_generate_copy_or_delivery_decision() -> None:
    from app.runtime.application.proactive_summary_consumer import (
        build_proactive_no_send_summary_consumer_projection,
    )

    artifact = build_proactive_no_send_summary_consumer_projection(_consumer_projection())

    assert artifact["candidate_copy_generated"] is False
    assert artifact["delivery_decision_made"] is False
    assert artifact["scheduler_activation_allowed"] is False
    assert artifact["live_delivery_allowed"] is False
    assert artifact["promotion_allowed"] is False
    assert artifact["non_claims"] == [
        "not_scheduler_activation",
        "not_live_delivery",
        "not_proactive_readiness",
        "not_manager_context_injection",
        "not_runtime_memory_truth",
    ]
    for row in artifact["review_context"]:
        assert "candidate_copy" not in row
        assert "send_or_skip" not in row
        assert "triggered" not in row
