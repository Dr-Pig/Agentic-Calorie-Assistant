from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_status_packet_inspection import (
    build_websearch_status_packet_inspection,
)


def _status_packet(next_required_slice: str = "inspect_websearch_status_packet") -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_evidence_status_packet_v1",
        "status": "pass",
        "summary": {
            "candidate_lane_status": "deterministic_websearch_candidate_lane_status_only",
            "candidate_lane_next_required_slice": "inspect_websearch_status_packet",
            "exact_lane_status": "clear_for_websearch_exact_candidate_chain",
            "exact_lane_next_required_slice": "grokfast_websearch_packet_live_diagnostic",
            "manager_contract_handoff_status": "websearch_contract_unblocked",
            "manager_contract_selected_next_step": "inspect_websearch_status_packet",
            "live_seam_status": "live_diagnostic_pass",
        },
        "next_required_slices": [next_required_slice],
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
    }


def _router_readiness(next_required_slice: str = "inspect_websearch_status_packet") -> dict:
    return {
        "artifact_type": "accurate_intake_food_evidence_retriever_router_readiness_v1",
        "status": "pass",
        "summary": {
            "case_count": 4,
            "fail_count": 0,
            "exact_brand_websearch_ready": True,
            "websearch_status_gate_present": True,
            "next_required_slice": next_required_slice,
        },
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
    }


def _exact_chain(next_required_slice: str = "grokfast_websearch_packet_live_diagnostic") -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_exact_candidate_chain_status_v1",
        "status": "pass",
        "next_required_slice": next_required_slice,
        "ready_for_live_diagnostic": True,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "packetizer_format_changed": False,
        "live_websearch_used": False,
        "live_extract_used": False,
        "live_provider_used": False,
        "readiness_claimed": False,
    }


def _live_runner_readiness(next_required_slice: str = "run_explicit_grokfast_websearch_packet_live_diagnostic") -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_runner_readiness_packet_v1",
        "status": "pass",
        "ready_for_grokfast_websearch_packet_live_diagnostic": True,
        "next_required_slice": next_required_slice,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "live_extract_used": False,
        "readiness_claimed": False,
    }


def test_websearch_status_packet_inspection_passes_aligned_status_chain() -> None:
    artifact = build_websearch_status_packet_inspection(
        websearch_status_packet=_status_packet("websearch_candidate_pipeline_narrow_expansion"),
        router_readiness_artifact=_router_readiness(),
        exact_candidate_chain_status_artifact=_exact_chain(),
        live_runner_readiness_artifact=_live_runner_readiness(),
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_status_packet_inspection_v1"
    assert artifact["status"] == "pass"
    assert artifact["summary"]["next_safe_slice"] == "websearch_candidate_pipeline_narrow_expansion"
    assert artifact["summary"]["router_next_required_slice"] == "inspect_websearch_status_packet"
    assert artifact["summary"]["live_runner_next_required_slice"] == (
        "run_explicit_grokfast_websearch_packet_live_diagnostic"
    )
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["shared_contract_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["readiness_claimed"] is False


def test_websearch_status_packet_inspection_blocks_runtime_truth_or_live_overclaims() -> None:
    status_packet = _status_packet()
    status_packet["runtime_truth_changed"] = True
    status_packet["live_provider_used"] = True

    artifact = build_websearch_status_packet_inspection(
        websearch_status_packet=status_packet,
        router_readiness_artifact=_router_readiness(),
    )

    assert artifact["status"] == "blocked"
    assert "websearch_status_packet_changed_runtime_truth" in artifact["blockers"]
    assert "websearch_status_packet_used_live_provider" in artifact["blockers"]
    assert artifact["summary"]["next_safe_slice"] == "inspect_websearch_status_packet"


def test_websearch_status_packet_inspection_blocks_router_alignment_drift() -> None:
    artifact = build_websearch_status_packet_inspection(
        websearch_status_packet=_status_packet(),
        router_readiness_artifact=_router_readiness("grokfast_fooddb_packet_live_diagnostic"),
    )

    assert artifact["status"] == "blocked"
    assert "router_readiness_next_slice_mismatch" in artifact["blockers"]


def test_websearch_status_packet_inspection_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_status_packet_inspection import main

    status_path = tmp_path / "status.json"
    router_path = tmp_path / "router.json"
    chain_path = tmp_path / "chain.json"
    readiness_path = tmp_path / "readiness.json"
    output = tmp_path / "inspection.json"

    write_json_artifact(status_path, _status_packet("websearch_candidate_pipeline_narrow_expansion"))
    write_json_artifact(router_path, _router_readiness())
    write_json_artifact(chain_path, _exact_chain())
    write_json_artifact(readiness_path, _live_runner_readiness())

    assert (
        main(
            [
                "--websearch-status-packet",
                str(status_path),
                "--router-readiness-artifact",
                str(router_path),
                "--exact-candidate-chain-status-artifact",
                str(chain_path),
                "--live-runner-readiness-artifact",
                str(readiness_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["status"] == "pass"
    assert artifact["summary"]["next_safe_slice"] == "websearch_candidate_pipeline_narrow_expansion"
