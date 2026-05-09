from __future__ import annotations

from app.recommendation.application.summary_consumer_quality import (
    build_recommendation_shadow_summary_consumer_quality_report,
)


def _memory_projection() -> dict[str, object]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": ["pref-1"],
            "negative_preference_blockers": ["neg-1"],
        },
        "golden_order_summary": {"orders": []},
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "rescue_proposal_committed": False,
        "retrieval_ranking_changed": False,
    }


def _candidate(
    candidate_id: str,
    *,
    estimated_kcal: int = 520,
    remaining_budget_kcal: int = 700,
    evidence_posture: str = "exact",
    availability_posture: str = "available",
    source_refs: list[str] | None = None,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "title": f"{candidate_id} prepared meal",
        "estimated_kcal": estimated_kcal,
        "remaining_budget_kcal": remaining_budget_kcal,
        "evidence_posture": evidence_posture,
        "availability_posture": availability_posture,
        "realistic_executable": True,
        "user_accessible": True,
        "source_refs": source_refs or [],
    }


def test_summary_consumer_exposes_primary_plus_backup_pool_posture() -> None:
    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=_memory_projection(),
        prepared_candidates=[
            _candidate("primary-1"),
            _candidate("backup-1", availability_posture="unknown"),
            _candidate("generic-1", evidence_posture="generic"),
        ],
    )

    assert report["pool_decision"] == "primary_plus_backup"
    assert report["primary_candidate_id"] == "primary-1"
    assert report["backup_candidate_ids"] == ["backup-1"]
    assert report["offer_candidate_ids"] == []
    assert report["rejected_candidate_ids"] == ["generic-1"]


def test_summary_consumer_exposes_offer_pool_posture_without_backup() -> None:
    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=_memory_projection(),
        prepared_candidates=[_candidate("single-high")],
    )

    assert report["pool_decision"] == "offer"
    assert report["primary_candidate_id"] is None
    assert report["backup_candidate_ids"] == []
    assert report["offer_candidate_ids"] == ["single-high"]


def test_summary_consumer_exposes_silent_pool_posture_when_all_rejected() -> None:
    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=_memory_projection(),
        prepared_candidates=[
            _candidate("neg-1", source_refs=["memory_candidate:neg-1"]),
            _candidate("over-1", estimated_kcal=900, remaining_budget_kcal=600),
        ],
    )

    assert report["pool_decision"] == "silent_no_qualified_candidate"
    assert report["primary_candidate_id"] is None
    assert report["backup_candidate_ids"] == []
    assert report["offer_candidate_ids"] == []
    assert report["rejected_candidate_ids"] == ["neg-1", "over-1"]
    assert report["recommendation_served"] is False
    assert report["proactive_sent"] is False
    assert report["intake_handoff_created"] is False
    assert report["manager_context_injected"] is False
    assert report["mutation_changed"] is False


def test_summary_consumer_omits_pool_posture_when_projection_is_blocked() -> None:
    projection = _memory_projection()
    projection["recommendation_served"] = True

    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=projection,
        prepared_candidates=[_candidate("candidate-1")],
    )

    assert report["status"] == "blocked"
    assert report["pool_decision"] == "blocked"
    assert report["primary_candidate_id"] is None
    assert report["backup_candidate_ids"] == []
    assert report["offer_candidate_ids"] == []
    assert report["rejected_candidate_ids"] == []
