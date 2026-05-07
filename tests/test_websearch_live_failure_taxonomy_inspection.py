from __future__ import annotations

from pathlib import Path


def _live_report(
    *,
    seam_status: str = "fixture_only_live_not_checked",
    next_recommended_slice: str = "run_explicit_grokfast_websearch_packet_live_diagnostic",
    failure_counts: dict[str, int] | None = None,
    source_live_provider_used: bool = False,
    source_status: str = "diagnostic_fail",
) -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_diagnostic_report",
        "seam_status": seam_status,
        "next_recommended_slice": next_recommended_slice,
        "source_live_provider_used": source_live_provider_used,
        "source_status": source_status,
        "provider_contract_blocked": seam_status == "provider_contract_blocked",
        "candidate_boundary_blocked": seam_status == "candidate_boundary_blocked",
        "preflight_evidence_healthy": seam_status == "live_diagnostic_pass",
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "failure_matrix": {
            "case_count": 5,
            "pass_count": 0,
            "fail_count": 5,
            "failure_counts": failure_counts or {},
        },
    }


def _handoff(
    *,
    status: str = "insufficient_contract_handoff_evidence",
    selected_next_step: str = "inspect_websearch_live_failure_taxonomy",
) -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
        "status": status,
        "selected_next_step": selected_next_step,
        "handoff_ready": False,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "shared_contract_changed": False,
        "readiness_claimed": False,
        "summary": {
            "live_seam_status": "fixture_only_live_not_checked",
            "contract_failure_detected": False,
            "probe_case_count": 0,
            "repair_case_count": 0,
            "alignment_blocker_count": 0,
        },
        "alignment_blockers": [],
    }


def _status_inspection(
    *,
    next_safe_slice: str = "inspect_websearch_status_packet",
) -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_status_packet_inspection_v1",
        "status": "pass",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "readiness_claimed": False,
        "summary": {
            "next_safe_slice": next_safe_slice,
            "status_packet_next_required_slice": next_safe_slice,
        },
    }


def test_websearch_live_failure_taxonomy_inspection_prefers_explicit_live_probe_for_fixture_gap() -> None:
    from app.nutrition.application.websearch_live_failure_taxonomy_inspection import (
        build_websearch_live_failure_taxonomy_inspection,
    )

    artifact = build_websearch_live_failure_taxonomy_inspection(
        live_diagnostic_report=_live_report(),
        manager_contract_handoff_artifact=_handoff(),
        status_packet_inspection_artifact=_status_inspection(),
    )

    assert artifact["artifact_type"] == (
        "accurate_intake_websearch_live_failure_taxonomy_inspection_v1"
    )
    assert artifact["status"] == "pass"
    assert artifact["summary"]["dominant_failure_lane"] == "live_activation_ordering"
    assert (
        artifact["summary"]["next_safe_slice"]
        == "run_explicit_grokfast_websearch_packet_live_diagnostic"
    )


def test_websearch_live_failure_taxonomy_inspection_advances_live_clear_status_loop() -> None:
    from app.nutrition.application.websearch_live_failure_taxonomy_inspection import (
        build_websearch_live_failure_taxonomy_inspection,
    )

    artifact = build_websearch_live_failure_taxonomy_inspection(
        live_diagnostic_report=_live_report(
            seam_status="live_diagnostic_pass",
            next_recommended_slice="inspect_websearch_status_packet",
            source_live_provider_used=True,
            source_status="pass",
        ),
        manager_contract_handoff_artifact=_handoff(
            status="websearch_contract_unblocked",
            selected_next_step="inspect_websearch_status_packet",
        ),
        status_packet_inspection_artifact=_status_inspection(
            next_safe_slice="inspect_websearch_status_packet"
        ),
    )

    assert artifact["status"] == "pass"
    assert artifact["summary"]["dominant_failure_lane"] == "no_runtime_integration_wall"
    assert artifact["summary"]["next_safe_slice"] == "inspect_fooddb_websearch_no_runtime_wall"


def test_websearch_live_failure_taxonomy_inspection_uses_candidate_boundary_lane_for_known_failures() -> None:
    from app.nutrition.application.websearch_live_failure_taxonomy_inspection import (
        build_websearch_live_failure_taxonomy_inspection,
    )

    artifact = build_websearch_live_failure_taxonomy_inspection(
        live_diagnostic_report=_live_report(
            seam_status="diagnostic_fail_unclassified",
            next_recommended_slice="inspect_sanitized_failure_taxonomy",
            failure_counts={
                "websearch_candidate_not_used": 1,
                "websearch_truth_shortcut": 1,
            },
            source_live_provider_used=True,
        ),
        manager_contract_handoff_artifact=_handoff(),
        status_packet_inspection_artifact=_status_inspection(),
    )

    assert artifact["status"] == "pass"
    assert artifact["summary"]["dominant_failure_lane"] == "packet_boundary_owner"
    assert (
        artifact["summary"]["next_safe_slice"]
        == "narrow_websearch_packet_boundary_or_prompt_probe"
    )


def test_websearch_live_failure_taxonomy_inspection_respects_alignment_blocker() -> None:
    from app.nutrition.application.websearch_live_failure_taxonomy_inspection import (
        build_websearch_live_failure_taxonomy_inspection,
    )

    artifact = build_websearch_live_failure_taxonomy_inspection(
        live_diagnostic_report=_live_report(
            seam_status="provider_contract_blocked",
            next_recommended_slice="narrow_grokfast_websearch_manager_contract_probe",
            failure_counts={"provider_response_error": 1},
            source_live_provider_used=True,
        ),
        manager_contract_handoff_artifact=_handoff(
            status="blocked_contract_handoff_alignment",
            selected_next_step="repair_artifact_alignment_required",
        ),
        status_packet_inspection_artifact=_status_inspection(),
    )

    assert artifact["summary"]["dominant_failure_lane"] == "artifact_alignment"
    assert artifact["summary"]["next_safe_slice"] == "repair_artifact_alignment_required"


def test_websearch_live_failure_taxonomy_inspection_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_live_failure_taxonomy_inspection import main

    report_path = tmp_path / "report.json"
    handoff_path = tmp_path / "handoff.json"
    inspection_path = tmp_path / "status_inspection.json"
    output_path = tmp_path / "taxonomy.json"

    write_json_artifact(report_path, _live_report())
    write_json_artifact(handoff_path, _handoff())
    write_json_artifact(inspection_path, _status_inspection())

    assert (
        main(
            [
                "--live-diagnostic-report",
                str(report_path),
                "--manager-contract-handoff",
                str(handoff_path),
                "--status-packet-inspection",
                str(inspection_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output_path)
    assert artifact["status"] == "pass"
    assert (
        artifact["summary"]["next_safe_slice"]
        == "run_explicit_grokfast_websearch_packet_live_diagnostic"
    )
