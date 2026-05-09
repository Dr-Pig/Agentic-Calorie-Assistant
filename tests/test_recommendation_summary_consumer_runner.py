from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _memory_projection(**overrides: object) -> dict[str, object]:
    projection: dict[str, object] = {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": ["pref-1"],
            "preference_summaries": [
                {"candidate_id": "pref-1", "summary": "likes chicken"}
            ],
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
    projection.update(overrides)
    return projection


def _candidate(candidate_id: str, **overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "candidate_id": candidate_id,
        "title": f"{candidate_id} prepared meal",
        "store_name": "FamilyMart",
        "store_metadata": {"chain": "familymart", "raw_menu_blob": "must not leak"},
        "estimated_kcal": 520,
        "remaining_budget_kcal": 700,
        "evidence_posture": "exact",
        "availability_posture": "available",
        "realistic_executable": True,
        "user_accessible": True,
        "source_refs": ["memory_candidate:pref-1", "memory_candidate:golden-1"],
        "candidate_copy": "Serve this candidate now",
        "primary_actions": ["commit_intake"],
    }
    candidate.update(overrides)
    return candidate


def test_runner_writes_recommendation_summary_consumer_report(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory_projection.json"
    candidates_path = tmp_path / "prepared_candidates.json"
    output_path = tmp_path / "recommendation_report.json"
    memory_path.write_text(json.dumps(_memory_projection()), encoding="utf-8")
    candidates_path.write_text(
        json.dumps([_candidate("primary-1"), _candidate("backup-1")]),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_recommendation_summary_consumer_quality_report.py"),
            "--memory-summary-projection",
            str(memory_path),
            "--prepared-candidates-json",
            str(candidates_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output_path.read_text(encoding="utf-8"))
    serialized = json.dumps(report, ensure_ascii=False)
    assert report["artifact_type"] == "recommendation_shadow_summary_consumer_quality_report"
    assert report["status"] == "pass"
    assert report["source_memory_artifact_type"] == "runtime_lab_memory_consumer_summary_projection"
    assert report["memory_summary_projection_used"] is True
    assert report["recommendation_served"] is False
    assert report["proactive_sent"] is False
    assert report["live_search_used"] is False
    assert report["ranking_llm_invoked"] is False
    assert report["manager_context_packet_changed"] is False
    assert report["durable_memory_written"] is False
    assert report["candidate_evaluations"][0]["presentation_posture"] == (
        "shadow_activation_candidate"
    )
    assert "memory_positive_summary_match" in report["candidate_evaluations"][0][
        "quality_signals"
    ]
    assert "Serve this candidate now" not in serialized
    assert "commit_intake" not in serialized
    assert "must not leak" not in serialized


def test_runner_writes_blocked_report_for_blocked_memory_projection(
    tmp_path: Path,
) -> None:
    memory_path = tmp_path / "blocked_memory_projection.json"
    candidates_path = tmp_path / "prepared_candidates.json"
    output_path = tmp_path / "blocked_recommendation_report.json"
    memory_path.write_text(
        json.dumps(_memory_projection(recommendation_served=True)),
        encoding="utf-8",
    )
    candidates_path.write_text(json.dumps([_candidate("primary-1")]), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_recommendation_summary_consumer_quality_report.py"),
            "--memory-summary-projection",
            str(memory_path),
            "--prepared-candidates-json",
            str(candidates_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["status"] == "blocked"
    assert report["blockers"] == ["consumer_summary_projection.recommendation_served"]
    assert report["candidate_evaluations"] == []
    assert report["recommendation_served"] is False
    assert report["intake_handoff_created"] is False
