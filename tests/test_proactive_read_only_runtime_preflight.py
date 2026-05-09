from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _recommendation_stage(**overrides: object) -> dict[str, object]:
    artifact: dict[str, object] = {
        "artifact_type": "recommendation_read_only_runtime_stage_decision",
        "status": "approved",
        "capability": "recommendation",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "activation_stage_after_decision": "read_only_runtime",
        "stage_change_recorded": True,
        "manual_promotion_approved": True,
        "automatic_stage_promotion_allowed": False,
        "recommendation_read_only_runtime_promoted": True,
        "recommendation_served": False,
        "live_search_used": False,
        "ranking_llm_invoked": False,
        "intake_handoff_created": False,
        "manager_context_packet_changed": False,
        "manager_context_injected": False,
        "mutation_changed": False,
        "durable_memory_written": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "no_go_flags": {"recommendation_served": False},
    }
    artifact.update(overrides)
    return artifact


def _rescue_stage(**overrides: object) -> dict[str, object]:
    artifact: dict[str, object] = {
        "artifact_type": "rescue_read_only_runtime_stage_decision",
        "status": "approved",
        "capability": "rescue",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "activation_stage_after_decision": "read_only_runtime",
        "stage_change_recorded": True,
        "manual_promotion_approved": True,
        "automatic_stage_promotion_allowed": False,
        "rescue_read_only_runtime_promoted": True,
        "rescue_proposal_committed": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "ledger_entry_created": False,
        "day_budget_mutated": False,
        "manager_context_packet_changed": False,
        "manager_context_injected": False,
        "mutation_changed": False,
        "durable_memory_written": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "no_go_flags": {"rescue_proposal_committed": False},
    }
    artifact.update(overrides)
    return artifact


def _decision_pack(**overrides: object) -> dict[str, object]:
    pack: dict[str, object] = {
        "artifact_type": "proactive_no_send_decision_pack",
        "shadow_mode": True,
        "live_delivery_allowed": False,
        "scheduler_activation_allowed": False,
        "promotion_allowed": False,
        "input_integrity": {"passed": True, "blockers": []},
        "summary": {
            "run_count": 3,
            "clean_run_count": 3,
            "copy_suppressed_count": 0,
        },
        "promotion_gate": {
            "minimum_clean_shadow_runs": 3,
            "human_review_required": True,
            "repeated_clean_shadow_evidence": True,
            "promotion_blockers": [
                "human_review_required_before_live_delivery",
                "live_scheduler_not_enabled",
                "no_send_shadow_only",
            ],
        },
        "activation_guardrails": {
            "runtime_connected": False,
            "scheduler_connected": False,
            "push_or_line_delivery_connected": False,
            "manager_context_packet_connected": False,
            "mutation_path_connected": False,
            "live_llm_invoked": False,
        },
    }
    pack.update(overrides)
    return pack


def test_proactive_preflight_passes_only_as_no_send_manual_review_gate() -> None:
    from app.runtime.application.proactive_read_only_runtime_preflight import (
        build_proactive_read_only_runtime_preflight_report,
    )

    report = build_proactive_read_only_runtime_preflight_report(
        recommendation_stage_decision=_recommendation_stage(),
        rescue_stage_decision=_rescue_stage(),
        no_send_decision_pack=_decision_pack(),
    )

    assert report["artifact_type"] == "proactive_read_only_runtime_preflight_report"
    assert report["status"] == "pass"
    assert report["capability"] == "proactive"
    assert report["current_stage"] == "shadow"
    assert report["target_stage"] == "read_only_runtime"
    assert report["manual_promotion_review_allowed"] is True
    assert report["automatic_stage_promotion_allowed"] is False
    assert report["proactive_read_only_runtime_promoted"] is False
    assert report["scheduler_activation_allowed"] is False
    assert report["live_delivery_allowed"] is False
    assert report["proactive_sent"] is False
    assert report["manager_context_packet_changed"] is False
    assert report["mutation_changed"] is False
    assert "not_proactive_stage_promotion_decision" in report["non_claims"]


def test_proactive_preflight_blocks_upstream_stage_overclaim() -> None:
    from app.runtime.application.proactive_read_only_runtime_preflight import (
        build_proactive_read_only_runtime_preflight_report,
    )

    report = build_proactive_read_only_runtime_preflight_report(
        recommendation_stage_decision=_recommendation_stage(recommendation_served=True),
        rescue_stage_decision=_rescue_stage(rescue_proposal_committed=True),
        no_send_decision_pack=_decision_pack(),
    )

    assert report["status"] == "blocked"
    assert "recommendation_stage.recommendation_served" in report["blockers"]
    assert "rescue_stage.rescue_proposal_committed" in report["blockers"]
    assert report["manual_promotion_review_allowed"] is False
    assert report["recommendation_served"] is False
    assert report["rescue_committed"] is False


def test_proactive_preflight_blocks_no_send_pack_without_clean_shadow_evidence() -> None:
    from app.runtime.application.proactive_read_only_runtime_preflight import (
        build_proactive_read_only_runtime_preflight_report,
    )

    report = build_proactive_read_only_runtime_preflight_report(
        recommendation_stage_decision=_recommendation_stage(),
        rescue_stage_decision=_rescue_stage(),
        no_send_decision_pack=_decision_pack(
            input_integrity={"passed": False, "blockers": ["run_1_proactive_sent"]},
            summary={"run_count": 1, "clean_run_count": 1, "copy_suppressed_count": 1},
            promotion_gate={
                "minimum_clean_shadow_runs": 3,
                "human_review_required": True,
                "repeated_clean_shadow_evidence": False,
                "promotion_blockers": [
                    "copy_review_issues_present",
                    "input_integrity_failed",
                    "minimum_clean_shadow_runs_not_met",
                ],
            },
        ),
    )

    assert report["status"] == "blocked"
    assert "no_send_decision_pack.input_integrity_failed" in report["blockers"]
    assert "no_send_decision_pack.minimum_clean_shadow_runs_not_met" in report[
        "blockers"
    ]
    assert "no_send_decision_pack.copy_review_issues_present" in report["blockers"]
    assert "no_send_decision_pack.run_1_proactive_sent" in report["blockers"]


def test_proactive_preflight_rejects_no_send_pack_activation_claims() -> None:
    from app.runtime.application.proactive_read_only_runtime_preflight import (
        build_proactive_read_only_runtime_preflight_report,
    )

    report = build_proactive_read_only_runtime_preflight_report(
        recommendation_stage_decision=_recommendation_stage(),
        rescue_stage_decision=_rescue_stage(),
        no_send_decision_pack=_decision_pack(
            live_delivery_allowed=True,
            scheduler_activation_allowed=True,
            promotion_allowed=True,
        ),
    )

    assert report["status"] == "blocked"
    assert "no_send_decision_pack.live_delivery_allowed" in report["blockers"]
    assert "no_send_decision_pack.scheduler_activation_allowed" in report["blockers"]
    assert "no_send_decision_pack.promotion_allowed" in report["blockers"]
    assert report["live_delivery_allowed"] is False
    assert report["scheduler_activation_allowed"] is False


def test_proactive_preflight_runner_requires_artifact_inputs(tmp_path: Path) -> None:
    rec_path = tmp_path / "recommendation_stage.json"
    rescue_path = tmp_path / "rescue_stage.json"
    pack_path = tmp_path / "no_send_decision_pack.json"
    output_path = tmp_path / "proactive_preflight.json"
    rec_path.write_text(json.dumps(_recommendation_stage()), encoding="utf-8")
    rescue_path.write_text(json.dumps(_rescue_stage()), encoding="utf-8")
    pack_path.write_text(json.dumps(_decision_pack()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_proactive_read_only_runtime_preflight.py"),
            "--recommendation-stage-decision-json",
            str(rec_path),
            "--rescue-stage-decision-json",
            str(rescue_path),
            "--no-send-decision-pack-json",
            str(pack_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["artifact_type"] == "proactive_read_only_runtime_preflight_report"
    assert artifact["status"] == "pass"
    assert artifact["real_artifact_input_required"] is True
