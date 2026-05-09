from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.recommendation.application.summary_consumer_quality import (
    build_recommendation_shadow_summary_consumer_quality_report,
)


ROOT = Path(__file__).resolve().parents[1]


def _memory_projection(**overrides: object) -> dict[str, object]:
    projection: dict[str, object] = {
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
    projection.update(overrides)
    return projection


def _recommendation_report() -> dict[str, object]:
    return build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=_memory_projection(),
        prepared_candidates=[
            {
                "candidate_id": "single-high",
                "title": "single-high prepared meal",
                "estimated_kcal": 520,
                "remaining_budget_kcal": 700,
                "availability_posture": "available",
                "evidence_posture": "exact",
                "realistic_executable": True,
                "user_accessible": True,
                "source_refs": ["memory_candidate:pref-dinner-light"],
                "candidate_copy": "Serve this now",
            }
        ],
    )


def test_runner_writes_proactive_summary_consumer_projection(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory_projection.json"
    recommendation_path = tmp_path / "recommendation_report.json"
    output_path = tmp_path / "proactive_summary_projection.json"
    memory_path.write_text(json.dumps(_memory_projection()), encoding="utf-8")
    recommendation_path.write_text(json.dumps(_recommendation_report()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_proactive_no_send_summary_consumer_projection.py"),
            "--memory-summary-projection",
            str(memory_path),
            "--recommendation-quality-report",
            str(recommendation_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    projection = json.loads(output_path.read_text(encoding="utf-8"))
    serialized = json.dumps(projection, ensure_ascii=False)
    assert projection["artifact_type"] == "proactive_no_send_summary_consumer_projection"
    assert projection["status"] == "pass"
    assert projection["summary"]["review_context_count"] == 3
    assert projection["recommendation_prompt_review"]["status"] == (
        "candidate_for_human_review"
    )
    assert projection["recommendation_prompt_review"]["actual_candidates_included"] is False
    assert projection["runtime_effect_allowed"] is False
    assert projection["proactive_sent"] is False
    assert projection["scheduler_enabled"] is False
    assert projection["push_or_line_delivery_connected"] is False
    assert projection["manager_context_injected"] is False
    assert projection["durable_memory_written"] is False
    assert projection["candidate_copy_generated"] is False
    assert projection["delivery_decision_made"] is False
    assert "Serve this now" not in serialized


def test_runner_writes_blocked_projection_for_memory_claim_drift(
    tmp_path: Path,
) -> None:
    memory_path = tmp_path / "blocked_memory_projection.json"
    output_path = tmp_path / "blocked_proactive_summary_projection.json"
    memory_path.write_text(
        json.dumps(_memory_projection(proactive_sent=True)),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_proactive_no_send_summary_consumer_projection.py"),
            "--memory-summary-projection",
            str(memory_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    projection = json.loads(output_path.read_text(encoding="utf-8"))
    assert projection["status"] == "blocked"
    assert projection["blockers"] == ["consumer_summary_projection.proactive_sent"]
    assert projection["summary"]["review_context_count"] == 0
    assert projection["proactive_sent"] is False
    assert projection["scheduler_enabled"] is False
