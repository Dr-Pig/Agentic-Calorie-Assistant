from __future__ import annotations

from tests.test_runtime_lab_reviewed_memory_consumer_bridge import _context_pack


def _memory_projection(tmp_path):
    from app.memory.application.runtime_lab_reviewed_memory_consumer_bridge import (
        build_consumer_summary_projection_from_shadow_memory_context_pack,
    )

    return build_consumer_summary_projection_from_shadow_memory_context_pack(
        _context_pack(tmp_path)
    )


def test_reviewed_memory_bridge_builds_three_node_payload(tmp_path) -> None:
    from app.recommendation.application.three_node_shadow_contract import (
        run_recommendation_three_node_shadow,
    )
    from app.recommendation.application.reviewed_memory_candidate_bridge import (
        build_reviewed_memory_recommendation_three_node_payload,
    )

    payload = build_reviewed_memory_recommendation_three_node_payload(
        _memory_projection(tmp_path),
        remaining_budget_kcal=700,
    )
    artifact = run_recommendation_three_node_shadow(payload)

    assert payload["source_memory_artifact_type"] == (
        "runtime_lab_memory_consumer_summary_projection"
    )
    assert payload["reviewed_memory_projection_used"] is True
    assert payload["bridge_blockers"] == []
    assert payload["negative_preference_summary"]["items"] == [
        {
            "candidate_id": "negative-preference-ingredient-cilantro",
            "pattern": "negative-preference-ingredient-cilantro",
            "status": "confirmed_negative_preference",
        }
    ]
    assert artifact["status"] == "pass"
    assert artifact["candidate_guard"]["allowed_candidate_ids"] == [
        "golden-order-morning-bar-oatmeal-latte"
    ]
    assert artifact["shadow_offer_packet"]["source_refs"] == [
        "memory_candidate:golden-order-morning-bar-oatmeal-latte"
    ]
    assert artifact["activation_flags"]["recommendation_served"] is False
    assert artifact["activation_flags"]["manager_context_packet_changed"] is False


def test_reviewed_memory_bridge_feeds_existing_summary_bridge(tmp_path) -> None:
    from app.recommendation.application.three_node_shadow_contract import (
        run_recommendation_three_node_shadow,
    )
    from app.recommendation.application.three_node_summary_bridge import (
        build_summary_quality_report_from_three_node_shadow_artifact,
    )
    from app.recommendation.application.reviewed_memory_candidate_bridge import (
        build_reviewed_memory_recommendation_three_node_payload,
    )

    memory = _memory_projection(tmp_path)
    payload = build_reviewed_memory_recommendation_three_node_payload(
        memory,
        remaining_budget_kcal=700,
    )
    three_node = run_recommendation_three_node_shadow(payload)
    report = build_summary_quality_report_from_three_node_shadow_artifact(
        memory_summary_projection=memory,
        three_node_artifact=three_node,
        source_payload=payload,
    )

    assert report["status"] == "pass"
    assert report["three_node_lab_bridge_used"] is True
    assert report["five_node_lab_bridge_used"] is False
    assert report["candidate_evaluations"][0]["candidate_id"] == (
        "golden-order-morning-bar-oatmeal-latte"
    )
    assert "memory_golden_order_projection_match" in report["candidate_evaluations"][
        0
    ]["quality_signals"]
    assert report["recommendation_served"] is False
    assert report["live_search_used"] is False


def test_reviewed_memory_bridge_keeps_candidate_silent_when_over_budget(tmp_path) -> None:
    from app.recommendation.application.three_node_shadow_contract import (
        run_recommendation_three_node_shadow,
    )
    from app.recommendation.application.reviewed_memory_candidate_bridge import (
        build_reviewed_memory_recommendation_three_node_payload,
    )

    payload = build_reviewed_memory_recommendation_three_node_payload(
        _memory_projection(tmp_path),
        remaining_budget_kcal=300,
    )
    artifact = run_recommendation_three_node_shadow(payload)

    assert artifact["status"] == "blocked"
    assert artifact["candidate_guard"]["filtered_candidates"] == [
        {
            "candidate_id": "golden-order-morning-bar-oatmeal-latte",
            "reason_codes": ["over_budget"],
        }
    ]
    assert artifact["activation_flags"]["recommendation_served"] is False


def test_reviewed_memory_bridge_blocks_projection_claim_drift(tmp_path) -> None:
    from app.recommendation.application.reviewed_memory_candidate_bridge import (
        build_reviewed_memory_recommendation_three_node_payload,
    )

    memory = _memory_projection(tmp_path)
    memory["recommendation_served"] = True

    payload = build_reviewed_memory_recommendation_three_node_payload(
        memory,
        remaining_budget_kcal=700,
    )

    assert payload["reviewed_memory_projection_used"] is False
    assert payload["bridge_blockers"] == [
        "consumer_summary_projection.recommendation_served"
    ]
    assert payload["candidate_source_fixture"] == []
    assert payload["shadow_offer_packet_fixture"]["recommendation_served"] is False
