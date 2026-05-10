from __future__ import annotations

from app.recommendation.application.three_node_shadow_contract import (
    build_fixture_recommendation_three_node_input,
    run_recommendation_three_node_shadow,
)
from app.recommendation.application.three_node_summary_bridge import (
    build_summary_quality_report_from_three_node_shadow_artifact,
)


def test_bridge_feeds_three_node_pass_artifact_into_summary_report() -> None:
    payload = _safe_payload()
    three_node_artifact = run_recommendation_three_node_shadow(payload)

    report = build_summary_quality_report_from_three_node_shadow_artifact(
        memory_summary_projection=_memory_projection(),
        three_node_artifact=three_node_artifact,
        source_payload=payload,
    )

    assert report["artifact_type"] == "recommendation_shadow_summary_consumer_quality_report"
    assert report["status"] == "pass"
    assert report["source_recommendation_artifact_type"] == (
        "recommendation_three_node_shadow_artifact"
    )
    assert report["canonical_recommendation_graph"] == "three_node"
    assert report["three_node_lab_bridge_used"] is True
    assert report["five_node_lab_bridge_used"] is False
    assert [row["logical_stage"] for row in report["logical_stage_trace"]] == [
        "recommendation_context_result",
        "candidate_spec",
        "candidate_retrieval_guard_scoring",
        "ranking_result",
        "recommendation_response_result",
    ]
    assert report["candidate_count"] == 1
    assert report["candidate_evaluations"][0]["candidate_id"] == "golden-1"
    assert report["candidate_evaluations"][0]["source_refs"] == [
        "memory_candidate:pref-1",
        "memory_candidate:golden-1",
    ]
    assert report["recommendation_served"] is False
    assert report["proactive_sent"] is False
    assert report["runtime_connected"] is False
    assert report["mutation_changed"] is False
    assert report["manager_context_packet_changed"] is False


def test_bridge_rejects_blocked_three_node_artifact() -> None:
    payload = _safe_payload()
    payload["manager_recommendation_decision_fixture"]["top_candidate_id"] = "over-1"  # type: ignore[index]
    artifact = run_recommendation_three_node_shadow(payload)

    report = build_summary_quality_report_from_three_node_shadow_artifact(
        memory_summary_projection=_memory_projection(),
        three_node_artifact=artifact,
        source_payload=payload,
    )

    assert report["status"] == "blocked"
    assert report["blockers"] == ["recommendation_three_node_artifact.status_not_pass"]
    assert report["candidate_evaluations"] == []
    assert report["three_node_lab_bridge_used"] is False
    assert report["recommendation_served"] is False


def test_bridge_rejects_logical_trace_or_source_ref_drift() -> None:
    payload = _safe_payload()
    artifact = run_recommendation_three_node_shadow(payload)
    artifact["logical_stage_trace"] = []

    trace_report = build_summary_quality_report_from_three_node_shadow_artifact(
        memory_summary_projection=_memory_projection(),
        three_node_artifact=artifact,
        source_payload=payload,
    )

    unsafe_payload = _safe_payload()
    _candidate(unsafe_payload, "golden-1")["source_refs"] = ["fixture:golden-1"]
    unsafe_report = build_summary_quality_report_from_three_node_shadow_artifact(
        memory_summary_projection=_memory_projection(),
        three_node_artifact=run_recommendation_three_node_shadow(unsafe_payload),
        source_payload=unsafe_payload,
    )

    assert trace_report["status"] == "blocked"
    assert trace_report["blockers"] == [
        "recommendation_three_node_artifact.logical_stage_trace_mismatch"
    ]
    assert unsafe_report["status"] == "blocked"
    assert unsafe_report["blockers"] == [
        "source_candidate.unsafe_source_ref:fixture:golden-1"
    ]


def _safe_payload() -> dict[str, object]:
    payload = build_fixture_recommendation_three_node_input()
    golden = _candidate(payload, "golden-1")
    golden.update(
        {
            "estimated_kcal": 520,
            "evidence_posture": "exact",
            "availability_posture": "available",
            "realistic_executable": True,
            "user_accessible": True,
            "store_name": "FamilyMart",
            "store_metadata": {"chain": "familymart", "raw_menu_blob": "hidden"},
            "source_refs": ["memory_candidate:pref-1", "memory_candidate:golden-1"],
        }
    )
    return payload


def _candidate(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    for item in payload["candidate_source_fixture"]:  # type: ignore[index]
        if isinstance(item, dict) and item.get("candidate_id") == candidate_id:
            return item
    raise AssertionError(f"candidate not found: {candidate_id}")


def _memory_projection() -> dict[str, object]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": ["pref-1"],
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
