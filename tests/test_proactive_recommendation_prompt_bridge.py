from __future__ import annotations

import json

from app.recommendation.application.summary_consumer_quality import (
    build_recommendation_shadow_summary_consumer_quality_report,
)
from app.runtime.application.proactive_summary_consumer import (
    build_proactive_no_send_summary_consumer_projection,
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
        "suppression_summary": {"suppression_blockers": []},
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
    availability_posture: str = "available",
    evidence_posture: str = "exact",
    source_refs: list[str] | None = None,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "title": f"{candidate_id} prepared meal",
        "estimated_kcal": estimated_kcal,
        "remaining_budget_kcal": remaining_budget_kcal,
        "availability_posture": availability_posture,
        "evidence_posture": evidence_posture,
        "realistic_executable": True,
        "user_accessible": True,
        "source_refs": source_refs or [],
    }


def _recommendation_report(candidates: list[dict[str, object]]) -> dict[str, object]:
    return build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=_memory_projection(),
        prepared_candidates=candidates,
    )


def test_bridge_suppresses_recommendation_prompt_when_pool_is_silent() -> None:
    from app.runtime.application.proactive_recommendation_prompt_bridge import (
        build_recommendation_prompt_no_send_review,
    )

    review = build_recommendation_prompt_no_send_review(
        _recommendation_report(
            [
                _candidate("neg-1", source_refs=["memory_candidate:neg-1"]),
                _candidate("over-1", estimated_kcal=900, remaining_budget_kcal=600),
            ]
        )
    )

    assert review["status"] == "suppressed"
    assert review["recommendation_pool_decision"] == "silent_no_qualified_candidate"
    assert review["suppression_reasons"] == [
        "recommendation_pool_silent_no_qualified_candidate"
    ]
    assert review["review_decision"]["status"] == "suppressed_context_or_data"
    assert review["recommendation_served"] is False
    assert review["proactive_sent"] is False
    assert review["scheduler_enabled"] is False


def test_bridge_maps_offer_and_primary_pool_to_review_only_invitation() -> None:
    from app.runtime.application.proactive_recommendation_prompt_bridge import (
        build_recommendation_prompt_no_send_review,
    )

    offer = build_recommendation_prompt_no_send_review(
        _recommendation_report([_candidate("single-high")])
    )
    primary = build_recommendation_prompt_no_send_review(
        _recommendation_report(
            [
                _candidate("primary-1"),
                _candidate("backup-1", availability_posture="unknown"),
            ]
        )
    )

    assert offer["status"] == "candidate_for_human_review"
    assert offer["recommendation_pool_decision"] == "offer"
    assert primary["status"] == "candidate_for_human_review"
    assert primary["recommendation_pool_decision"] == "primary_plus_backup"
    assert offer["prompt_posture"] == "invitation_only"
    assert primary["prompt_posture"] == "invitation_only"
    assert offer["actual_candidates_included"] is False
    assert primary["actual_candidates_included"] is False
    assert "single-high" not in json.dumps(offer)
    assert "primary-1" not in json.dumps(primary)
    assert "backup-1" not in json.dumps(primary)


def test_bridge_blocks_overclaiming_recommendation_report() -> None:
    from app.runtime.application.proactive_recommendation_prompt_bridge import (
        build_recommendation_prompt_no_send_review,
    )

    report = _recommendation_report([_candidate("single-high")])
    report["recommendation_served"] = True

    review = build_recommendation_prompt_no_send_review(report)

    assert review["status"] == "blocked"
    assert review["blockers"] == ["recommendation_quality_report.recommendation_served"]
    assert review["recommendation_served"] is False
    assert review["proactive_sent"] is False


def test_proactive_summary_consumer_embeds_bridge_without_runtime_effects() -> None:
    artifact = build_proactive_no_send_summary_consumer_projection(
        _memory_projection(),
        recommendation_quality_report=_recommendation_report([_candidate("single-high")]),
    )

    review = artifact["recommendation_prompt_review"]
    assert review["status"] == "candidate_for_human_review"
    assert review["recommendation_pool_decision"] == "offer"
    assert artifact["recommendation_served"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["scheduler_enabled"] is False
    assert artifact["live_delivery_allowed"] is False
    assert artifact["manager_context_injected"] is False
