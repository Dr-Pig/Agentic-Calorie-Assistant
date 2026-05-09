from __future__ import annotations

from app.recommendation.application.five_node_shadow_fixture import (
    build_fixture_recommendation_five_node_input,
)
from app.recommendation.application.five_node_shadow_runner import (
    run_recommendation_five_node_lab_runner,
)
from app.recommendation.application.five_node_summary_bridge import (
    build_summary_quality_report_from_five_node_lab_artifact,
)


def test_bridge_feeds_five_node_pass_artifact_into_existing_summary_report() -> None:
    payload = _safe_payload()
    five_node_artifact = run_recommendation_five_node_lab_runner(payload)

    report = build_summary_quality_report_from_five_node_lab_artifact(
        memory_summary_projection=_memory_projection(),
        five_node_artifact=five_node_artifact,
        source_payload=payload,
    )

    assert report["artifact_type"] == "recommendation_shadow_summary_consumer_quality_report"
    assert report["status"] == "pass"
    assert report["source_recommendation_artifact_type"] == (
        "recommendation_five_node_lab_runner_artifact"
    )
    assert report["five_node_lab_bridge_used"] is True
    assert report["candidate_count"] == 1
    assert report["candidate_evaluations"][0]["candidate_id"] == "golden-1"
    assert report["candidate_evaluations"][0]["source_refs"] == [
        "memory_candidate:pref-1",
        "memory_candidate:golden-1",
    ]
    assert report["candidate_evaluations"][0]["quality_gate_passed"] is True
    assert "memory_positive_summary_match" in report["candidate_evaluations"][0][
        "quality_signals"
    ]
    assert "memory_golden_order_projection_match" in report["candidate_evaluations"][0][
        "quality_signals"
    ]
    assert report["recommendation_served"] is False
    assert report["proactive_sent"] is False
    assert report["runtime_connected"] is False
    assert report["mutation_changed"] is False
    assert report["manager_context_packet_changed"] is False


def test_bridge_rejects_blocked_five_node_artifact() -> None:
    payload = _safe_payload()
    payload["ranking_synthesis_fixture"]["selected_candidate_id"] = "over-1"
    five_node_artifact = run_recommendation_five_node_lab_runner(payload)

    report = build_summary_quality_report_from_five_node_lab_artifact(
        memory_summary_projection=_memory_projection(),
        five_node_artifact=five_node_artifact,
        source_payload=payload,
    )

    assert report["artifact_type"] == "recommendation_shadow_summary_consumer_quality_report"
    assert report["status"] == "blocked"
    assert report["blockers"] == ["recommendation_five_node_artifact.status_not_pass"]
    assert report["candidate_evaluations"] == []
    assert report["five_node_lab_bridge_used"] is False
    assert report["recommendation_served"] is False


def test_bridge_rejects_candidate_not_selected_or_allowed_by_artifact() -> None:
    payload = _safe_payload()
    five_node_artifact = run_recommendation_five_node_lab_runner(payload)
    five_node_artifact["ranking_synthesis"]["selected_candidate_id"] = "over-1"

    report = build_summary_quality_report_from_five_node_lab_artifact(
        memory_summary_projection=_memory_projection(),
        five_node_artifact=five_node_artifact,
        source_payload=payload,
    )

    assert report["status"] == "blocked"
    assert report["blockers"] == [
        "recommendation_five_node_artifact.selected_candidate_not_allowed:over-1",
        "recommendation_five_node_artifact.response_candidate_mismatch:golden-1",
    ]
    assert report["candidate_count"] == 0


def test_bridge_rejects_missing_or_unsafe_source_refs() -> None:
    missing_payload = _safe_payload()
    _candidate(missing_payload, "golden-1")["source_refs"] = []
    missing_report = build_summary_quality_report_from_five_node_lab_artifact(
        memory_summary_projection=_memory_projection(),
        five_node_artifact=run_recommendation_five_node_lab_runner(missing_payload),
        source_payload=missing_payload,
    )

    unsafe_payload = _safe_payload()
    _candidate(unsafe_payload, "golden-1")["source_refs"] = [
        "memory_candidate:pref-1",
        "fixture:golden-1",
    ]
    unsafe_report = build_summary_quality_report_from_five_node_lab_artifact(
        memory_summary_projection=_memory_projection(),
        five_node_artifact=run_recommendation_five_node_lab_runner(unsafe_payload),
        source_payload=unsafe_payload,
    )

    assert missing_report["status"] == "blocked"
    assert missing_report["blockers"] == [
        "source_candidate.safe_source_refs_missing:golden-1"
    ]
    assert unsafe_report["status"] == "blocked"
    assert unsafe_report["blockers"] == [
        "source_candidate.unsafe_source_ref:fixture:golden-1"
    ]


def _safe_payload() -> dict[str, object]:
    payload = build_fixture_recommendation_five_node_input()
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
