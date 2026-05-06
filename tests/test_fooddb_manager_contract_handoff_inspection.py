from __future__ import annotations

from pathlib import Path

from app.nutrition.application.fooddb_manager_contract_handoff import (
    build_fooddb_manager_contract_handoff,
)


def _live_report(*, seam_status: str = "provider_contract_blocked") -> dict:
    next_step = {
        "provider_contract_blocked": "narrow_grokfast_fooddb_manager_contract_probe",
        "packet_boundary_blocked": "narrow_fooddb_packet_boundary_or_prompt_probe",
        "live_diagnostic_pass": "grokfast_websearch_packet_live_diagnostic",
        "fixture_only_live_not_checked": "run_explicit_grokfast_fooddb_packet_live_diagnostic",
    }.get(seam_status, "inspect_fooddb_live_failure_taxonomy")
    return {
        "artifact_type": "accurate_intake_fooddb_live_diagnostic_report",
        "seam_status": seam_status,
        "source_live_provider_used": seam_status != "fixture_only_live_not_checked",
        "source_artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "source_status": "pass" if seam_status == "live_diagnostic_pass" else "diagnostic_fail",
        "upstream_evidence_required": seam_status == "live_diagnostic_pass",
        "upstream_evidence_healthy": seam_status != "live_diagnostic_pass" or True,
        "can_expand_to_websearch_live_diagnostic": seam_status == "live_diagnostic_pass",
        "next_recommended_slice": next_step,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
    }


def _probe(*, contract_failure_detected: bool = True) -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_manager_contract_probe",
        "contract_failure_detected": contract_failure_detected,
        "next_recommended_slice": "tighten_fooddb_manager_contract_prompt_or_transport",
        "summary": {
            "case_count": 5,
            "aggregate_missing_required_fields": {"intent": 5},
        },
    }


def _repair_pack(
    *, next_recommended_slice: str = "tighten_fooddb_manager_contract_prompt_or_transport"
) -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_manager_contract_repair_pack",
        "next_recommended_slice": next_recommended_slice,
        "summary": {
            "case_count": 5,
            "alias_hint_counts": {"intent": 5},
            "probe_match_status_counts": {"matched_probe_case": 5},
            "trace_status_counts": {"trace_present": 5},
        },
    }


def _handoff(*, seam_status: str = "provider_contract_blocked", contract_failure_detected: bool = True) -> dict:
    return build_fooddb_manager_contract_handoff(
        live_diagnostic_report=_live_report(seam_status=seam_status),
        contract_probe_artifact=_probe(contract_failure_detected=contract_failure_detected),
        repair_pack_artifact=_repair_pack(),
    )


def test_fooddb_manager_contract_handoff_inspection_returns_specific_next_slice_for_fixture_gap() -> None:
    from app.nutrition.application.fooddb_manager_contract_handoff_inspection import (
        build_fooddb_manager_contract_handoff_inspection,
    )

    handoff = _handoff(seam_status="fixture_only_live_not_checked", contract_failure_detected=False)
    artifact = build_fooddb_manager_contract_handoff_inspection(
        manager_contract_handoff_artifact=handoff,
        live_diagnostic_report=_live_report(seam_status="fixture_only_live_not_checked"),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact=_repair_pack(),
    )

    assert artifact["artifact_type"] == "accurate_intake_fooddb_manager_contract_handoff_inspection_v1"
    assert artifact["status"] == "pass"
    assert artifact["summary"]["next_safe_slice"] == "inspect_fooddb_live_failure_taxonomy"


def test_fooddb_manager_contract_handoff_inspection_unblocks_websearch_live_after_verified_live_pass() -> None:
    from app.nutrition.application.fooddb_manager_contract_handoff_inspection import (
        build_fooddb_manager_contract_handoff_inspection,
    )

    handoff = _handoff(seam_status="live_diagnostic_pass", contract_failure_detected=False)
    artifact = build_fooddb_manager_contract_handoff_inspection(
        manager_contract_handoff_artifact=handoff,
        live_diagnostic_report=_live_report(seam_status="live_diagnostic_pass"),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact=_repair_pack(),
    )

    assert artifact["status"] == "pass"
    assert artifact["summary"]["next_safe_slice"] == "grokfast_websearch_packet_live_diagnostic"


def test_fooddb_manager_contract_handoff_inspection_blocks_derivation_mismatch() -> None:
    from app.nutrition.application.fooddb_manager_contract_handoff_inspection import (
        build_fooddb_manager_contract_handoff_inspection,
    )

    handoff = _handoff(seam_status="provider_contract_blocked")
    handoff["selected_next_step"] = "grokfast_websearch_packet_live_diagnostic"
    artifact = build_fooddb_manager_contract_handoff_inspection(
        manager_contract_handoff_artifact=handoff,
        live_diagnostic_report=_live_report(),
        contract_probe_artifact=_probe(),
        repair_pack_artifact=_repair_pack(),
    )

    assert artifact["status"] == "blocked"
    assert "manager_contract_handoff_derivation_mismatch" in artifact["blockers"]


def test_fooddb_manager_contract_handoff_inspection_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_fooddb_manager_contract_handoff_inspection import main

    live_path = tmp_path / "live.json"
    probe_path = tmp_path / "probe.json"
    repair_path = tmp_path / "repair.json"
    handoff_path = tmp_path / "handoff.json"
    output_path = tmp_path / "inspection.json"
    write_json_artifact(live_path, _live_report(seam_status="fixture_only_live_not_checked"))
    write_json_artifact(probe_path, _probe(contract_failure_detected=False))
    write_json_artifact(repair_path, _repair_pack())
    write_json_artifact(
        handoff_path,
        _handoff(seam_status="fixture_only_live_not_checked", contract_failure_detected=False),
    )

    assert (
        main(
            [
                "--manager-contract-handoff-artifact",
                str(handoff_path),
                "--live-diagnostic-report",
                str(live_path),
                "--contract-probe-artifact",
                str(probe_path),
                "--repair-pack-artifact",
                str(repair_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output_path)
    assert artifact["status"] == "pass"
    assert artifact["summary"]["next_safe_slice"] == "inspect_fooddb_live_failure_taxonomy"
