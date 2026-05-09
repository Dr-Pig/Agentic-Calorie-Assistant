from __future__ import annotations

import ast
from pathlib import Path

from app.recommendation.application.summary_consumer_quality import (
    build_recommendation_shadow_summary_consumer_quality_report,
)


ROOT = Path(__file__).resolve().parents[1]


def test_summary_consumer_reads_memory_projection_without_runtime_effects() -> None:
    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=_memory_projection(),
        prepared_candidates=[
            _candidate(
                "c1",
                "FamilyMart salad chicken and sweet potato",
                source_refs=["memory_candidate:pref-1", "memory_candidate:golden-1"],
            )
        ],
    )

    assert report["artifact_type"] == "recommendation_shadow_summary_consumer_quality_report"
    assert report["status"] == "pass"
    assert report["owner"] == "app/recommendation"
    assert report["source_memory_artifact_type"] == "runtime_lab_memory_consumer_summary_projection"
    assert report["memory_summary_projection_used"] is True
    assert report["recommendation_served"] is False
    assert report["proactive_sent"] is False
    assert report["live_search_used"] is False
    assert report["ranking_llm_invoked"] is False
    assert report["manager_context_packet_changed"] is False
    assert report["durable_memory_written"] is False

    evaluation = report["candidate_evaluations"][0]
    assert evaluation["quality_gate_passed"] is True
    assert evaluation["quality_tier"] == "high"
    assert evaluation["presentation_posture"] == "shadow_activation_candidate"
    assert "memory_positive_summary_match" in evaluation["quality_signals"]
    assert "memory_golden_order_projection_match" in evaluation["quality_signals"]


def test_summary_consumer_rejects_negative_preference_matches() -> None:
    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=_memory_projection(),
        prepared_candidates=[
            _candidate(
                "c2",
                "fried tofu snack",
                source_refs=["memory_candidate:neg-1"],
            )
        ],
    )

    evaluation = report["candidate_evaluations"][0]
    assert evaluation["quality_gate_passed"] is False
    assert evaluation["presentation_posture"] == "silent"
    assert "negative_preference" in evaluation["disqualifier_flags"]
    assert evaluation["memory_rejection_reasons"] == ["negative_preference_blocker"]


def test_summary_consumer_downgrades_stale_or_sparse_memory() -> None:
    projection = _memory_projection(freshness_posture="stale")

    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=projection,
        prepared_candidates=[
            _candidate("c3", "salad chicken combo", source_refs=["memory_candidate:pref-1"])
        ],
    )

    evaluation = report["candidate_evaluations"][0]
    assert evaluation["quality_gate_passed"] is True
    assert evaluation["quality_tier"] == "medium"
    assert evaluation["proactive_intensity"] == "offer"
    assert evaluation["presentation_posture"] == "low_friction_offer_only"
    assert evaluation["memory_confidence_posture"] == "stale"
    assert "memory_summary_not_fresh" in evaluation["quality_signals"]


def test_summary_consumer_keeps_generic_candidates_silent_only() -> None:
    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=_memory_projection(),
        prepared_candidates=[
            _candidate(
                "c4",
                "something light",
                evidence_posture="generic",
                source_refs=["memory_candidate:pref-1"],
            )
        ],
    )

    evaluation = report["candidate_evaluations"][0]
    assert evaluation["quality_gate_passed"] is False
    assert evaluation["proactive_intensity"] == "none"
    assert evaluation["presentation_posture"] == "silent"
    assert "generic_evidence_not_proactive" in evaluation["disqualifier_flags"]


def test_summary_consumer_blocks_projection_claim_drift() -> None:
    projection = _memory_projection()
    projection["recommendation_served"] = True

    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=projection,
        prepared_candidates=[_candidate("c5", "chicken bento")],
    )

    assert report["status"] == "blocked"
    assert "consumer_summary_projection.recommendation_served" in report["blockers"]
    assert report["candidate_evaluations"] == []
    assert report["recommendation_served"] is False


def test_summary_consumer_does_not_import_runtime_manager_scheduler_or_persistence() -> None:
    paths = [
        ROOT / "app" / "recommendation" / "application" / "summary_consumer_quality.py",
        ROOT / "app" / "recommendation" / "application" / "summary_consumer_candidate.py",
    ]
    forbidden_import_prefixes = (
        "app.runtime.agent",
        "app.runtime.application.manager_service",
        "app.proactive",
        "app.rescue.application.proposal_read_model",
        "sqlalchemy",
        "requests",
        "httpx",
    )

    violations: list[str] = []
    for path in paths:
        violations.extend(
            imported
            for imported in _absolute_imports(path)
            if imported.startswith(forbidden_import_prefixes)
        )

    assert not violations


def _memory_projection(*, freshness_posture: str = "fresh") -> dict:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": freshness_posture,
            "accepted_shadow_candidate_ids": ["pref-1"],
            "preference_summaries": [{"candidate_id": "pref-1", "summary": "likes chicken"}],
            "negative_preference_blockers": ["neg-1"],
        },
        "golden_order_summary": {
            "orders": [
                {
                    "candidate_id": "golden-1",
                    "store_name": "FamilyMart",
                    "item_names": ["salad chicken", "sweet potato"],
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


def _candidate(
    candidate_id: str,
    title: str,
    *,
    evidence_posture: str = "exact",
    source_refs: list[str] | None = None,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "title": title,
        "estimated_kcal": 520,
        "remaining_budget_kcal": 700,
        "evidence_posture": evidence_posture,
        "availability_posture": "available",
        "realistic_executable": True,
        "user_accessible": True,
        "source_refs": source_refs or [],
    }


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports
