from __future__ import annotations

from pathlib import Path

from app.nutrition.application.retrieval_request_lineage_probe import (
    build_retrieval_request_lineage_probe,
)


def test_retrieval_request_lineage_probe_passes_for_manager_owned_canary_and_packet_only_live_runners() -> None:
    artifact = build_retrieval_request_lineage_probe()

    assert artifact["artifact_type"] == "accurate_intake_retrieval_request_lineage_probe_v1"
    assert artifact["status"] == "pass"
    assert artifact["summary"]["packet_only_live_runner_count"] == 2
    assert artifact["summary"]["raw_text_guard_clear"] is True
    assert artifact["summary"]["manager_owned_canary_clear"] is True
    assert artifact["packet_only_live_runner_audit"]["unexpected_prohibited_call_files"] == []


def test_retrieval_request_lineage_probe_blocks_manager_case_missing_manager_owned_source() -> None:
    artifact = build_retrieval_request_lineage_probe(
        manager_case_trace={
            "retrieval_request_source": "diagnostic_fixture",
            "semantic_authority_source": "synthetic_retrieval_fixture",
            "retrieval_goal": "exact_brand_lookup",
            "attempted": True,
            "skip_reason": None,
        }
    )

    assert artifact["status"] == "blocked"
    assert "manager_canary_wrong_request_source" in artifact["blockers"]
    assert "manager_canary_wrong_semantic_authority_source" in artifact["blockers"]


def test_retrieval_request_lineage_probe_blocks_raw_text_runtime_attempt() -> None:
    artifact = build_retrieval_request_lineage_probe(
        raw_text_case_trace={
            "retrieval_request_source": "raw_text_hint",
            "semantic_authority_source": "deterministic_raw_text_hint_only",
            "retrieval_goal": "exact_brand_lookup",
            "attempted": True,
            "skip_reason": "not_blocked",
        }
    )

    assert artifact["status"] == "blocked"
    assert "raw_text_canary_attempted_runtime_execution" in artifact["blockers"]
    assert "raw_text_canary_missing_manager_guard" in artifact["blockers"]


def test_retrieval_request_lineage_probe_blocks_packet_live_runner_script_with_retrieval_builder() -> None:
    artifact = build_retrieval_request_lineage_probe(
        prohibited_call_files=(
            "scripts/run_accurate_intake_grokfast_fooddb_packet_smoke.py",
        )
    )

    assert artifact["status"] == "blocked"
    assert (
        "packet_only_live_runner_prohibited_call:scripts/run_accurate_intake_grokfast_fooddb_packet_smoke.py"
        in artifact["blockers"]
    )


def test_retrieval_request_lineage_probe_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_retrieval_request_lineage_probe import main

    output = tmp_path / "retrieval_request_lineage_probe.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_retrieval_request_lineage_probe_v1"
    assert artifact["status"] == "pass"
