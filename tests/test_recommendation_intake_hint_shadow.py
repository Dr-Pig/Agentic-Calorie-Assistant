from __future__ import annotations

import json

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


def _candidate(candidate_id: str, **overrides: object) -> dict[str, object]:
    candidate = {
        "candidate_id": candidate_id,
        "title": f"{candidate_id} prepared meal",
        "store_name": "Corner Bento",
        "store_metadata": {"chain": "corner", "raw_menu_blob": "hidden raw menu"},
        "estimated_kcal": 520,
        "remaining_budget_kcal": 700,
        "evidence_posture": "exact",
        "availability_posture": "available",
        "realistic_executable": True,
        "user_accessible": True,
        "source_refs": [f"memory_candidate:{candidate_id}", "trace:hidden-trace"],
        "candidate_copy": "Hidden recommendation copy",
        "primary_actions": ["commit_intake"],
    }
    candidate.update(overrides)
    return candidate


def _report(candidates: list[dict[str, object]]) -> dict[str, object]:
    return build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=_memory_projection(),
        prepared_candidates=candidates,
    )


def test_hint_shadow_packet_sanitizes_selected_candidate_without_intake_commit() -> None:
    from app.recommendation.application.intake_hint_shadow import (
        build_recommendation_intake_hint_shadow_packet,
    )

    report = _report([_candidate("primary-1"), _candidate("backup-1")])
    packet = build_recommendation_intake_hint_shadow_packet(
        recommendation_quality_report=report,
        selected_candidate_id="primary-1",
        current_surface_channel="chat_open",
    )
    serialized = json.dumps(packet, ensure_ascii=False)

    assert packet["artifact_type"] == "recommendation_intake_hint_shadow_packet"
    assert packet["status"] == "pass"
    assert packet["owner"] == "app/recommendation"
    assert packet["consumer"] == "future_intake_flow_shadow_review"
    assert packet["selected_candidate_id"] == "primary-1"
    assert packet["hint_packet"] == {
        "candidate_id": "primary-1",
        "title": "primary-1 prepared meal",
        "store_metadata": {"store_name": "Corner Bento", "chain": "corner"},
        "estimated_kcal_hint": 520,
        "current_surface_channel": "chat_open",
        "source_refs": ["memory_candidate:primary-1"],
    }
    assert packet["intake_handoff_created"] is False
    assert packet["recommendation_served"] is False
    assert packet["meal_thread_mutated"] is False
    assert packet["ledger_entry_created"] is False
    assert packet["day_budget_mutated"] is False
    assert "Hidden recommendation copy" not in serialized
    assert "commit_intake" not in serialized
    assert "hidden raw menu" not in serialized
    assert "hidden-trace" not in serialized


def test_hint_shadow_rejects_blocked_or_silent_report() -> None:
    from app.recommendation.application.intake_hint_shadow import (
        build_recommendation_intake_hint_shadow_packet,
    )

    blocked_report = _report([_candidate("primary-1")])
    blocked_report["status"] = "blocked"
    silent_report = _report(
        [
            _candidate("neg-1", source_refs=["memory_candidate:neg-1"]),
            _candidate("over-1", estimated_kcal=900, remaining_budget_kcal=600),
        ]
    )

    blocked = build_recommendation_intake_hint_shadow_packet(
        recommendation_quality_report=blocked_report,
        selected_candidate_id="primary-1",
    )
    silent = build_recommendation_intake_hint_shadow_packet(
        recommendation_quality_report=silent_report,
        selected_candidate_id="neg-1",
    )

    assert blocked["status"] == "blocked"
    assert "recommendation_quality_report.status_not_pass" in blocked["blockers"]
    assert silent["status"] == "blocked"
    assert "recommendation_quality_report.pool_not_handoff_eligible" in silent["blockers"]
    assert blocked["hint_packet"] is None
    assert silent["hint_packet"] is None


def test_hint_shadow_rejects_failed_generic_or_negative_candidates() -> None:
    from app.recommendation.application.intake_hint_shadow import (
        build_recommendation_intake_hint_shadow_packet,
    )

    report = _report(
        [
            _candidate("generic-1", evidence_posture="generic"),
            _candidate("neg-1", source_refs=["memory_candidate:neg-1"]),
            _candidate("good-1"),
        ]
    )

    generic = build_recommendation_intake_hint_shadow_packet(
        recommendation_quality_report=report,
        selected_candidate_id="generic-1",
    )
    negative = build_recommendation_intake_hint_shadow_packet(
        recommendation_quality_report=report,
        selected_candidate_id="neg-1",
    )

    assert generic["status"] == "blocked"
    assert "selected_candidate.quality_gate_not_passed" in generic["blockers"]
    assert "selected_candidate.not_handoff_eligible" in generic["blockers"]
    assert negative["status"] == "blocked"
    assert "selected_candidate.quality_gate_not_passed" in negative["blockers"]
    assert "selected_candidate.negative_preference_blocker" in negative["blockers"]


def test_hint_shadow_rejects_unselected_candidate_and_claim_drift() -> None:
    from app.recommendation.application.intake_hint_shadow import (
        build_recommendation_intake_hint_shadow_packet,
    )

    report = _report([_candidate("primary-1"), _candidate("backup-1")])
    report["recommendation_served"] = True

    packet = build_recommendation_intake_hint_shadow_packet(
        recommendation_quality_report=report,
        selected_candidate_id="backup-1",
    )

    assert packet["status"] == "blocked"
    assert "recommendation_quality_report.recommendation_served" in packet["blockers"]
    assert "selected_candidate.not_selected_by_pool" in packet["blockers"]
    assert packet["hint_packet"] is None
    assert packet["recommendation_served"] is False
    assert packet["intake_handoff_created"] is False
