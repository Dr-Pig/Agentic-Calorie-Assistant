from __future__ import annotations

from pathlib import Path

from app.shared.infra.json_artifacts import read_json_artifact
from scripts.run_accurate_intake_websearch_live_diagnostic_bundle import (
    _artifact_paths,
    main,
)


def _fooddb_status_packet(next_required_slice: str) -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
        "next_required_slices": [next_required_slice],
    }


def test_websearch_live_diagnostic_bundle_artifact_paths_fit_windows_budget() -> None:
    output_dir = Path(
        "C:/Users/User/.config/superpowers/worktrees/"
        "Agentic-Calorie-Assistant/grokfast-websearch-packet-live-diagnostic/"
        "artifacts/accurate_intake_websearch_live_diagnostic_bundle_fixture_baseline"
    )

    longest = max(len(str(path)) for path in _artifact_paths(output_dir).values())

    assert longest <= 240


def test_websearch_live_diagnostic_bundle_fixture_mode_builds_full_bundle(tmp_path: Path) -> None:
    exit_code = main(["--output-dir", str(tmp_path)])

    assert exit_code == 0
    manifest = read_json_artifact(tmp_path / "websearch_live_manifest.json")
    diagnostic = read_json_artifact(tmp_path / "grokfast_websearch_packet_smoke.json")
    report = read_json_artifact(tmp_path / "websearch_live_report.json")
    readiness = read_json_artifact(tmp_path / "websearch_live_readiness.json")
    handoff = read_json_artifact(tmp_path / "websearch_contract_handoff.json")
    status_packet = read_json_artifact(tmp_path / "websearch_evidence_status_packet.json")
    inspection = read_json_artifact(tmp_path / "websearch_status_packet_inspection.json")

    assert manifest["bundle_status"] == "pass"
    assert manifest["mode"] == "fixture"
    assert manifest["live_provider_used"] is False
    assert manifest["live_websearch_used"] is False
    assert manifest["runtime_truth_changed"] is False
    assert manifest["runtime_mutation_attempted"] is False
    assert manifest["readiness_claimed"] is False
    assert manifest["seam_status"] == "fixture_only_live_not_checked"
    assert manifest["next_recommended_slice"] == "inspect_fooddb_status_packet"
    assert manifest["manager_contract_handoff_status"] == "insufficient_contract_handoff_evidence"
    assert manifest["manager_contract_handoff_ready"] is False
    assert diagnostic["live_provider_used"] is False
    assert report["should_run_websearch_live_tool_loop"] is False
    assert readiness["ready_for_grokfast_websearch_packet_live_diagnostic"] is True
    assert handoff["status"] == "insufficient_contract_handoff_evidence"
    assert status_packet["artifact_type"] == "accurate_intake_websearch_evidence_status_packet_v1"
    assert status_packet["next_required_slices"] == ["inspect_fooddb_status_packet"]
    assert inspection["artifact_type"] == "accurate_intake_websearch_status_packet_inspection_v1"
    assert inspection["summary"]["next_safe_slice"] == "inspect_fooddb_status_packet"


def test_websearch_live_diagnostic_bundle_live_mode_requires_explicit_allow_live(
    tmp_path: Path,
) -> None:
    exit_code = main(["--mode", "live", "--output-dir", str(tmp_path)])

    assert exit_code == 2
    manifest = read_json_artifact(tmp_path / "websearch_live_manifest.json")
    diagnostic = read_json_artifact(tmp_path / "grokfast_websearch_packet_smoke.json")

    assert manifest["bundle_status"] == "blocked_or_failed"
    assert manifest["mode"] == "live"
    assert manifest["allow_live"] is False
    assert manifest["live_provider_used"] is False
    assert manifest["live_websearch_used"] is False
    assert manifest["runtime_truth_changed"] is False
    assert manifest["runtime_mutation_attempted"] is False
    assert diagnostic["status"] == "blocked"
    assert diagnostic["failure_family"] == "live_mode_requires_explicit_allow_live"


def test_websearch_live_diagnostic_bundle_records_all_required_artifact_refs(
    tmp_path: Path,
) -> None:
    main(["--output-dir", str(tmp_path)])

    manifest = read_json_artifact(tmp_path / "websearch_live_manifest.json")
    required_refs = {
        "case_matrix",
        "selected_extract",
        "extract_result",
        "review_packet",
        "preflight",
        "chain_status",
        "readiness",
        "diagnostic",
        "report",
        "manager_contract_probe",
        "manager_contract_repair_pack",
        "manager_contract_handoff",
        "websearch_evidence_status_packet",
        "websearch_status_packet_inspection",
    }

    assert set(manifest["artifacts"]) == required_refs
    for artifact_path in manifest["artifacts"].values():
        assert Path(artifact_path).exists()


def test_websearch_live_diagnostic_bundle_accepts_explicit_fooddb_status_packet(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import write_json_artifact

    fooddb_status_path = tmp_path / "fooddb_status.json"
    write_json_artifact(
        fooddb_status_path,
        _fooddb_status_packet("grokfast_websearch_packet_live_diagnostic"),
    )

    exit_code = main(
        [
            "--output-dir",
            str(tmp_path),
            "--fooddb-status-packet-artifact",
            str(fooddb_status_path),
        ]
    )

    assert exit_code == 0
    status_packet = read_json_artifact(tmp_path / "websearch_evidence_status_packet.json")

    assert (
        status_packet["summary"]["candidate_lane_next_required_slice"]
        == "inspect_websearch_manager_contract_handoff"
    )
    assert status_packet["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]
