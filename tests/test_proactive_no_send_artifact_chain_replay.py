from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _proactive_summary_projection() -> dict[str, object]:
    return {
        "artifact_type": "proactive_no_send_summary_consumer_projection",
        "status": "pass",
        "runtime_effect_allowed": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "push_or_line_delivery_connected": False,
        "manager_context_injected": False,
        "durable_memory_written": False,
        "recommendation_served": False,
        "rescue_proposal_committed": False,
        "live_delivery_allowed": False,
        "scheduler_activation_allowed": False,
        "promotion_allowed": False,
        "recommendation_prompt_review": {
            "source_report_used": True,
            "status": "candidate_for_human_review",
            "recommendation_pool_decision": "primary_plus_backup",
            "prompt_posture": "invitation_only",
            "suppression_reasons": [],
            "blockers": [],
            "actual_candidates_included": False,
            "candidate_ids_exposed": False,
            "runtime_effect_allowed": False,
            "recommendation_served": False,
            "proactive_sent": False,
            "scheduler_enabled": False,
            "live_delivery_allowed": False,
            "scheduler_activation_allowed": False,
            "manager_context_injected": False,
        },
    }


def _rescue_context_projection() -> dict[str, object]:
    return {
        "artifact_type": "rescue_shadow_summary_context_projection",
        "status": "pass",
        "runtime_effect_allowed": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_memory_written": False,
        "manager_context_injected": False,
        "proactive_sent": False,
        "recommendation_served": False,
        "rescue_history_context": {"rescue_event_count": 2},
        "adherence_context": {"adherence_posture": "mixed"},
        "suppression_context": [{"trigger_type": "rescue_nudge", "summary": "dismissed once"}],
        "history_review_notes": [
            "rescue_history_present_for_future_viability_review",
            "adherence_summary_present_for_future_viability_review",
        ],
    }


def test_existing_clis_replay_proactive_no_send_artifact_chain_without_activation(
    tmp_path: Path,
) -> None:
    summary_projection_path = tmp_path / "proactive_summary_projection.json"
    rescue_context_path = tmp_path / "rescue_context_projection.json"
    simulation_path = tmp_path / "proactive_no_send_simulation.json"
    decision_pack_path = tmp_path / "proactive_no_send_decision_pack.json"
    summary_projection_path.write_text(
        json.dumps(_proactive_summary_projection()),
        encoding="utf-8",
    )
    rescue_context_path.write_text(
        json.dumps(_rescue_context_projection()),
        encoding="utf-8",
    )

    simulation_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_proactive_no_send_simulation.py"),
            "--summary-consumer-projection",
            str(summary_projection_path),
            "--rescue-summary-context-projection",
            str(rescue_context_path),
            "--output",
            str(simulation_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    decision_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_proactive_no_send_decision_pack.py"),
            "--input",
            str(simulation_path),
            "--output",
            str(decision_pack_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert simulation_result.returncode == 0, simulation_result.stderr
    assert decision_result.returncode == 0, decision_result.stderr
    simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    decision_pack = json.loads(decision_pack_path.read_text(encoding="utf-8"))
    serialized_pack = json.dumps(decision_pack, ensure_ascii=False)

    assert simulation["artifact_type"] == "proactive_no_send_simulation"
    assert decision_pack["artifact_type"] == "proactive_no_send_decision_pack"
    assert decision_pack["summary"]["run_count"] == 1
    assert decision_pack["summary"]["recommendation_prompt_review_status_counts"] == {
        "candidate_for_human_review": 1
    }
    assert decision_pack["summary"]["rescue_nudge_review_status_counts"] == {
        "context_available": 1
    }
    assert decision_pack["summary"]["rescue_nudge_blocker_counts"] == {}
    assert decision_pack["summary"]["rescue_nudge_suppression_reason_counts"] == {}
    assert decision_pack["live_delivery_allowed"] is False
    assert decision_pack["scheduler_activation_allowed"] is False
    assert decision_pack["promotion_allowed"] is False
    assert decision_pack["activation_guardrails"] == {
        "runtime_connected": False,
        "scheduler_connected": False,
        "push_or_line_delivery_connected": False,
        "manager_context_packet_connected": False,
        "mutation_path_connected": False,
        "live_llm_invoked": False,
    }
    assert decision_pack["promotion_gate"]["promotion_blockers"] == [
        "human_review_required_before_live_delivery",
        "live_scheduler_not_enabled",
        "minimum_clean_shadow_runs_not_met",
        "no_send_shadow_only",
    ]
    assert "rescue_event_count" not in serialized_pack
    assert "adherence_posture" not in serialized_pack
    assert "primary_plus_backup" not in serialized_pack
