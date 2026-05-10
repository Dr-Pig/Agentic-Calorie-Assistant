from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.journey_terminal_contract import expected_terminal_output
from app.advanced_shadow_lab.journey_chat_packet_projection import (
    build_journey_chat_packets,
)
from scripts import build_advanced_shadow_comparison_artifact as runner


EXPECTED_UX_JOURNEY_IDS = ["F", "F2", "I", "L", "M", "N"]


def test_comparison_runner_reads_existing_json_and_writes_existing_artifact(
    tmp_path: Path,
) -> None:
    output = tmp_path / "comparison.json"
    paths = {
        "fixture": _write(tmp_path / "fixture.json", _fixture_chain()),
        "dogfood": _write(tmp_path / "dogfood.json", _dogfood_replay()),
        "recommendation_live": _write(tmp_path / "recommendation_live.json", _live_diagnostic()),
        "rescue_live": _write(tmp_path / "rescue_live.json", _rescue_live_diagnostic()),
        "baseline_cases": _write(tmp_path / "baseline_cases.json", [_case_artifact("case-1", "baseline_trace")]),
        "advanced_cases": _write(tmp_path / "advanced_cases.json", [_case_artifact("case-1", "advanced_trace")]),
    }

    exit_code = runner.main([
        "--fixture-chain", str(paths["fixture"]),
        "--dogfood-replay", str(paths["dogfood"]),
        "--recommendation-live", str(paths["recommendation_live"]),
        "--rescue-live", str(paths["rescue_live"]),
        "--baseline-cases", str(paths["baseline_cases"]),
        "--advanced-cases", str(paths["advanced_cases"]),
        "--output", str(output),
    ])
    artifact = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["artifact_type"] == "advanced_shadow_comparison_artifact"
    assert artifact["status"] == "pass"
    assert artifact["pairing_summary"]["status"] == "pairable"
    assert artifact["runtime_connected"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["product_readiness_claimed"] is False


def test_comparison_runner_source_stays_pure_diagnostic() -> None:
    source = Path("scripts/build_advanced_shadow_comparison_artifact.py").read_text(
        encoding="utf-8"
    )

    forbidden_tokens = [
        "app.routes",
        "app.database",
        "app.models",
        "app.providers",
        "manager_service",
        "provider_runtime",
        "scheduler",
        "send_notification",
        "create_engine",
    ]
    for token in forbidden_tokens:
        assert token not in source


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _fixture_chain() -> dict[str, object]:
    journey_evidence = [
        _journey_terminal_evidence(journey_id)
        for journey_id in EXPECTED_UX_JOURNEY_IDS
    ]
    journey_packets, journey_summary = build_journey_chat_packets(journey_evidence)
    return {
        "artifact_type": "advanced_shadow_e2e_fixture_chain_artifact",
        "status": "pass",
        "chat_ux_packet": {
            "artifact_type": "advanced_shadow_chat_ux_packet_artifact",
            "status": "pass",
            "copy_alignment_summary": {
                "status": "pass",
                "aligned_count": 2,
                "not_applicable_count": 0,
                "blocked_count": 0,
                "not_run_count": 0,
            },
            "journey_chat_packet_summary": journey_summary,
            "journey_chat_packets": journey_packets,
        },
        "terminal_review_sink": {
            "status": "pass",
            "record_count": 2,
            "control_path_evidence": _control_evidence(),
        },
        "journey_terminal_evidence": journey_evidence,
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "scheduler_enabled": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _journey_terminal_evidence(journey_id: str) -> dict[str, object]:
    return {
        "journey_id": journey_id,
        "journey_name": f"fixture_{journey_id}",
        "status": "pass",
        "comparison_scope": "ux_journey_terminal_lab_only_evidence",
        "source_artifact_refs": ["fixture_source"],
        "product_contract_refs": ["fixture_contract"],
        "required_trace_fields": ["fixture_trace_field"],
        "ux_terminal_output": expected_terminal_output(journey_id),
        "terminal_artifact_refs": [
            "advanced_shadow_e2e_fixture_chain_artifact",
            "proactive_no_send_review_sink_artifact",
            "advanced_shadow_chat_ux_packet_artifact",
        ],
        "no_send_control_evidence": {
            "status": "pass",
            "configured_paths": {"dismiss": True, "snooze": True, "undo": True},
            "next_signal_required_present": True,
        },
        "semantic_decision_inferred_by_runner": False,
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "recommendation_served": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
        "product_readiness_claimed": False,
    }


def _dogfood_replay() -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_dogfood_replay_artifact",
        "status": "pass",
        "terminal_review_sink_summary": {
            "status": "pass",
            "record_count": 2,
            "control_path_evidence": _control_evidence(include_count=False),
        },
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "scheduler_enabled": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _live_diagnostic() -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_recommendation_copy_live_diagnostic_artifact",
        "status": "pass",
        "provider_mode": "builderspace_live_diagnostic",
        "live_invoked": True,
        "live_provider_used": True,
        "output_guard": {"status": "pass"},
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "scheduler_enabled": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _rescue_live_diagnostic() -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_rescue_copy_live_diagnostic_artifact",
        "status": "pass",
        "provider_mode": "builderspace_live_diagnostic",
        "live_invoked": True,
        "live_provider_used": True,
        "output_guard": {"status": "pass"},
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "scheduler_enabled": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _case_artifact(case_id: str, artifact_type: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "artifact_type": artifact_type,
        "status": "pass",
        "runtime_connected": False,
        "delivery_attempted": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
        "product_readiness_claimed": False,
    }


def _control_evidence(*, include_count: bool = True) -> dict[str, object]:
    evidence: dict[str, object] = {
        "status": "pass",
        "all_candidates_have_required_controls": True,
        "configured_paths": {"dismiss": True, "snooze": True, "undo": True},
        "interaction_actions_observed": ["dismiss", "snooze"],
        "observed_all_interaction_actions": False,
        "next_signal_required_present": True,
    }
    if include_count:
        evidence["candidate_count"] = 2
    return evidence
