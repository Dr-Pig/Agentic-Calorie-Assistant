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
            "accepted_shadow_candidate_ids": ["pref-1"],
            "negative_preference_blockers": ["neg-1"],
        },
        "suppression_summary": {
            "suppression_blockers": [
                {
                    "candidate_id": "suppress-1",
                    "trigger_type": "rescue_nudge",
                    "summary": "user often ignores rescue nudges",
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


def _derived_views() -> dict[str, object]:
    return {
        "artifact_type": "derived_memory_views_shadow_eval",
        "rescue_history_summary": {
            "source_kind": "derived_read_model",
            "is_durable_memory_truth": False,
            "rescue_event_count": 2,
            "overshoot_day_count": 3,
            "rescue_viability_posture": "shadow_candidate_only",
        },
        "adherence_summary": {
            "source_kind": "derived_read_model",
            "is_durable_memory_truth": False,
            "budget_day_count": 7,
            "at_or_under_target_day_count": 4,
            "overshoot_day_count": 3,
            "average_overshoot_kcal": 220.0,
            "adherence_posture": "mixed",
        },
    }


def test_runner_writes_rescue_shadow_summary_context_projection(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory_projection.json"
    derived_views_path = tmp_path / "derived_views.json"
    output_path = tmp_path / "rescue_context.json"
    memory_path.write_text(json.dumps(_memory_projection()), encoding="utf-8")
    derived_views_path.write_text(json.dumps(_derived_views()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_rescue_shadow_summary_context.py"),
            "--memory-summary-projection",
            str(memory_path),
            "--derived-memory-views-json",
            str(derived_views_path),
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
    assert projection["artifact_type"] == "rescue_shadow_summary_context_projection"
    assert projection["status"] == "pass"
    assert projection["memory_summary_projection_used"] is True
    assert projection["memory_signal_summary"] == {
        "preference_candidate_count": 1,
        "negative_preference_blocker_count": 1,
        "suppression_blocker_count": 1,
    }
    assert projection["rescue_history_context"]["rescue_event_count"] == 2
    assert projection["adherence_context"]["adherence_posture"] == "mixed"
    assert projection["runtime_effect_allowed"] is False
    assert projection["rescue_committed"] is False
    assert projection["proposal_committed"] is False
    assert projection["proactive_sent"] is False
    assert projection["recommendation_served"] is False
    assert projection["manager_context_injected"] is False
    assert projection["durable_memory_written"] is False
    assert projection["proposal_card"] is None
    assert projection["candidate_copy"] is None
    assert "not_rescue_proposal" in projection["non_claims"]
    assert "proposal accepted" not in serialized


def test_runner_writes_blocked_rescue_context_for_memory_claim_drift(
    tmp_path: Path,
) -> None:
    memory_path = tmp_path / "blocked_memory_projection.json"
    derived_views_path = tmp_path / "derived_views.json"
    output_path = tmp_path / "blocked_rescue_context.json"
    memory_path.write_text(
        json.dumps(_memory_projection(rescue_proposal_committed=True)),
        encoding="utf-8",
    )
    derived_views_path.write_text(json.dumps(_derived_views()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_rescue_shadow_summary_context.py"),
            "--memory-summary-projection",
            str(memory_path),
            "--derived-memory-views-json",
            str(derived_views_path),
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
    assert projection["blockers"] == [
        "consumer_summary_projection.rescue_proposal_committed"
    ]
    assert projection["memory_summary_projection_used"] is False
    assert projection["rescue_committed"] is False
    assert projection["proposal_committed"] is False
