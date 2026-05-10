from __future__ import annotations

from tests.test_runtime_lab_reviewed_memory_store import _review_loop_artifact, _scope


def _context_pack(tmp_path):
    from app.memory.application.runtime_lab_reviewed_memory_retrieval import (
        build_shadow_memory_context_pack_from_reviewed_store,
    )
    from app.memory.application.runtime_lab_reviewed_memory_store import (
        RuntimeLabReviewedMemoryStore,
    )

    store = RuntimeLabReviewedMemoryStore(tmp_path)
    store.write_review_loop_state(_review_loop_artifact())
    return build_shadow_memory_context_pack_from_reviewed_store(
        store,
        _scope(),
        token_budget=120,
    )


def _derived_views() -> dict:
    return {
        "rescue_history_summary": {
            "is_durable_memory_truth": False,
            "rescue_event_count": 1,
        },
        "adherence_summary": {
            "is_durable_memory_truth": False,
            "adherence_posture": "mixed",
        },
    }


def test_bridge_builds_consumer_summary_from_reviewed_context_pack(tmp_path) -> None:
    from app.memory.application.runtime_lab_reviewed_memory_consumer_bridge import (
        build_consumer_summary_projection_from_shadow_memory_context_pack,
    )

    projection = build_consumer_summary_projection_from_shadow_memory_context_pack(
        _context_pack(tmp_path)
    )

    assert projection["artifact_type"] == "runtime_lab_memory_consumer_summary_projection"
    assert projection["status"] == "pass"
    assert projection["source_context_pack_used"] is True
    assert projection["source_store_type"] == "runtime_lab_reviewed_memory_store"
    assert projection["reviewed_memory_store_used"] is True
    assert projection["preference_profile_summary"]["negative_preference_blockers"] == [
        "negative-preference-ingredient-cilantro"
    ]
    assert projection["golden_order_summary"]["orders"][0]["candidate_id"] == (
        "golden-order-morning-bar-oatmeal-latte"
    )
    assert projection["omission_trace"] == [
        {
            "candidate_id": "intake-estimation-bias-likely-underestimate",
            "reason": "deleted_by_reviewer",
        }
    ]
    assert projection["manager_context_packet_changed"] is False
    assert projection["runtime_effect_allowed"] is False
    assert projection["recommendation_served"] is False
    assert projection["rescue_proposal_committed"] is False
    assert projection["proactive_sent"] is False


def test_bridge_output_feeds_recommendation_rescue_and_proactive_consumers(tmp_path) -> None:
    from app.memory.application.runtime_lab_reviewed_memory_consumer_bridge import (
        build_consumer_summary_projection_from_shadow_memory_context_pack,
    )
    from app.recommendation.application.summary_consumer_quality import (
        build_recommendation_shadow_summary_consumer_quality_report,
    )
    from app.rescue.application.shadow_summary_context import (
        build_rescue_shadow_summary_context_projection,
    )
    from app.runtime.application.proactive_summary_consumer import (
        build_proactive_no_send_summary_consumer_projection,
    )

    projection = build_consumer_summary_projection_from_shadow_memory_context_pack(
        _context_pack(tmp_path)
    )
    recommendation = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=projection,
        prepared_candidates=[
            {
                "candidate_id": "rec-1",
                "title": "Morning Bar oatmeal",
                "estimated_kcal": 520,
                "remaining_budget_kcal": 700,
                "evidence_posture": "exact",
                "availability_posture": "available",
                "realistic_executable": True,
                "user_accessible": True,
                "source_refs": [
                    "memory_candidate:golden-order-morning-bar-oatmeal-latte"
                ],
            }
        ],
    )
    rescue = build_rescue_shadow_summary_context_projection(
        memory_summary_projection=projection,
        derived_memory_views=_derived_views(),
    )
    proactive = build_proactive_no_send_summary_consumer_projection(projection)

    assert recommendation["status"] == "pass"
    assert recommendation["candidate_evaluations"][0]["quality_gate_passed"] is True
    assert "memory_golden_order_projection_match" in recommendation[
        "candidate_evaluations"
    ][0]["quality_signals"]
    assert recommendation["recommendation_served"] is False
    assert rescue["status"] == "pass"
    assert rescue["memory_signal_summary"] == {
        "preference_candidate_count": 0,
        "negative_preference_blocker_count": 1,
        "suppression_blocker_count": 0,
    }
    assert rescue["rescue_committed"] is False
    assert rescue["proposal_committed"] is False
    assert proactive["status"] == "pass"
    assert proactive["summary"]["golden_order_context_count"] == 1
    assert proactive["summary"]["negative_preference_blocker_count"] == 1
    assert proactive["proactive_sent"] is False


def test_bridge_blocks_context_pack_claim_drift(tmp_path) -> None:
    from app.memory.application.runtime_lab_reviewed_memory_consumer_bridge import (
        build_consumer_summary_projection_from_shadow_memory_context_pack,
    )

    context_pack = _context_pack(tmp_path)
    context_pack["manager_context_packet_changed"] = True

    projection = build_consumer_summary_projection_from_shadow_memory_context_pack(
        context_pack
    )

    assert projection["status"] == "blocked"
    assert "shadow_memory_context_pack.manager_context_packet_changed" in projection[
        "blockers"
    ]
    assert projection["source_context_pack_used"] is False
    assert projection["manager_context_packet_changed"] is False
