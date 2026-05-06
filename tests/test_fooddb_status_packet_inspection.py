from __future__ import annotations

from pathlib import Path


def _status_packet(
    next_required_slice: str = "grokfast_fooddb_packet_live_diagnostic",
) -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "manager_fooddb_packet_seam_gate_status": "pass",
            "manager_contract_live_seam_status": "not_run",
            "manager_contract_handoff_status": "not_run",
            "manager_contract_owner_handoff_ready": False,
        },
        "next_required_slices": [next_required_slice],
    }


def _live_runner_readiness(
    *,
    status: str = "pass",
    next_required_slice: str = "run_explicit_grokfast_fooddb_packet_live_diagnostic",
) -> dict:
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_live_runner_readiness_packet_v1",
        "status": status,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "next_required_slice": next_required_slice,
    }


def _contract_handoff(
    *,
    status: str = "insufficient_contract_handoff_evidence",
    live_seam_status: str = "fixture_only_live_not_checked",
    selected_next_step: str = "inspect_fooddb_live_failure_taxonomy",
    handoff_ready: bool = False,
) -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_manager_contract_handoff_v1",
        "status": status,
        "selected_next_step": selected_next_step,
        "handoff_ready": handoff_ready,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "shared_contract_changed": False,
        "readiness_claimed": False,
        "summary": {
            "live_seam_status": live_seam_status,
        },
    }


def test_fooddb_status_packet_inspection_accepts_live_diagnostic_next_slice() -> None:
    from app.nutrition.application.fooddb_status_packet_inspection import (
        build_fooddb_status_packet_inspection,
    )

    artifact = build_fooddb_status_packet_inspection(
        fooddb_status_packet=_status_packet("grokfast_fooddb_packet_live_diagnostic"),
        live_runner_readiness_artifact=_live_runner_readiness(),
    )

    assert artifact["artifact_type"] == "accurate_intake_fooddb_status_packet_inspection_v1"
    assert artifact["status"] == "pass"
    assert artifact["summary"]["next_safe_slice"] == "grokfast_fooddb_packet_live_diagnostic"
    assert artifact["summary"]["live_runner_next_required_slice"] == (
        "run_explicit_grokfast_fooddb_packet_live_diagnostic"
    )


def test_fooddb_status_packet_inspection_advances_to_websearch_after_contract_unblocks() -> None:
    from app.nutrition.application.fooddb_status_packet_inspection import (
        build_fooddb_status_packet_inspection,
    )

    artifact = build_fooddb_status_packet_inspection(
        fooddb_status_packet=_status_packet("grokfast_websearch_packet_live_diagnostic"),
        contract_handoff_artifact=_contract_handoff(
            status="fooddb_contract_unblocked",
            live_seam_status="live_diagnostic_pass",
            selected_next_step="grokfast_websearch_packet_live_diagnostic",
        ),
        live_runner_readiness_artifact=_live_runner_readiness(),
    )

    assert artifact["status"] == "pass"
    assert artifact["summary"]["next_safe_slice"] == "grokfast_websearch_packet_live_diagnostic"
    assert artifact["summary"]["contract_handoff_status"] == "fooddb_contract_unblocked"


def test_fooddb_status_packet_inspection_blocks_runtime_or_live_overclaim() -> None:
    from app.nutrition.application.fooddb_status_packet_inspection import (
        build_fooddb_status_packet_inspection,
    )

    artifact = build_fooddb_status_packet_inspection(
        fooddb_status_packet={
            **_status_packet("grokfast_fooddb_packet_live_diagnostic"),
            "runtime_truth_changed": True,
        }
    )

    assert artifact["status"] == "blocked"
    assert "fooddb_status_packet_changed_runtime_truth" in artifact["blockers"]
    assert artifact["summary"]["next_safe_slice"] == "grokfast_fooddb_packet_live_diagnostic"


def test_fooddb_status_packet_inspection_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_fooddb_status_packet_inspection import main

    status_path = tmp_path / "status.json"
    live_runner_path = tmp_path / "live_runner.json"
    output = tmp_path / "inspection.json"
    write_json_artifact(status_path, _status_packet("inspect_contract_handoff_status"))
    write_json_artifact(live_runner_path, _live_runner_readiness())

    assert (
        main(
            [
                "--fooddb-status-packet",
                str(status_path),
                "--live-runner-readiness-artifact",
                str(live_runner_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_fooddb_status_packet_inspection_v1"
    assert artifact["summary"]["next_safe_slice"] == "inspect_contract_handoff_status"
