from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_evidence_status_packet import (
    build_websearch_evidence_status_packet,
)


def _candidate_lane(next_required_slice: str) -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
        "summary": {
            "upstream_fooddb_gate_status": "clear_for_websearch_lane",
            "upstream_fooddb_next_required_slice": "grokfast_websearch_packet_live_diagnostic",
            "manager_contract_gate_status": "clear_for_websearch_lane",
            "manager_contract_next_required_slice": next_required_slice,
        },
        "upstream_gate": {"status": "clear_for_websearch_lane", "blocked": False},
        "manager_contract_gate": {
            "status": "clear_for_websearch_lane",
            "blocked": False,
            "next_required_slice": next_required_slice,
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


def _exact_lane(next_required_slice: str) -> dict:
    return {
        "artifact_type": "accurate_intake_exact_evidence_lane_status_packet_v1",
        "summary": {
            "upstream_websearch_gate_status": "clear_for_exact_websearch_followthrough",
            "upstream_websearch_next_required_slice": "grokfast_websearch_packet_live_diagnostic",
            "exact_candidate_chain_status": "clear_for_websearch_exact_candidate_chain",
            "exact_candidate_chain_next_required_slice": next_required_slice,
        },
        "upstream_gate": {
            "status": "clear_for_exact_websearch_followthrough",
            "blocked": False,
            "next_required_slice": "grokfast_websearch_packet_live_diagnostic",
        },
        "exact_candidate_chain_gate": {
            "status": "clear_for_websearch_exact_candidate_chain",
            "blocked": False,
            "next_required_slice": next_required_slice,
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


def _contract_handoff(status: str, selected_next_step: str) -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
        "status": status,
        "selected_next_step": selected_next_step,
        "handoff_ready": False,
        "summary": {
            "live_seam_status": "live_diagnostic_pass",
            "contract_failure_detected": False,
        },
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "shared_contract_changed": False,
        "readiness_claimed": False,
    }


def _narrow_expansion(status: str = "pass", next_required_slice: str = "inspect_websearch_status_packet") -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_candidate_pipeline_narrow_expansion_v1",
        "status": status,
        "next_required_slice": next_required_slice,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
    }


def test_websearch_evidence_status_packet_defaults_to_candidate_lane_next_step() -> None:
    artifact = build_websearch_evidence_status_packet(
        candidate_lane_status_packet=_candidate_lane("grokfast_fooddb_packet_live_diagnostic")
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_evidence_status_packet_v1"
    assert artifact["status"] == "blocked_on_candidate_lane"
    assert artifact["next_required_slices"] == ["grokfast_fooddb_packet_live_diagnostic"]
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["shared_contract_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False


def test_websearch_evidence_status_packet_advances_to_exact_chain_review_after_live_status_inspection() -> None:
    artifact = build_websearch_evidence_status_packet(
        candidate_lane_status_packet=_candidate_lane("inspect_websearch_status_packet"),
        exact_lane_status_packet=_exact_lane("inspect_websearch_exact_candidate_chain_status"),
    )

    assert artifact["status"] == "pass"
    assert artifact["summary"]["candidate_lane_next_required_slice"] == "inspect_websearch_status_packet"
    assert artifact["summary"]["exact_lane_next_required_slice"] == (
        "inspect_websearch_exact_candidate_chain_status"
    )
    assert artifact["next_required_slices"] == ["inspect_websearch_exact_candidate_chain_status"]


def test_websearch_evidence_status_packet_sanitizes_post_live_repeat_into_narrow_expansion() -> None:
    artifact = build_websearch_evidence_status_packet(
        candidate_lane_status_packet=_candidate_lane("inspect_websearch_status_packet"),
        exact_lane_status_packet=_exact_lane("grokfast_websearch_packet_live_diagnostic"),
        manager_contract_handoff_artifact=_contract_handoff(
            "websearch_contract_unblocked",
            "inspect_websearch_status_packet",
        ),
    )

    assert artifact["status"] == "pass"
    assert artifact["summary"]["manager_contract_handoff_status"] == "websearch_contract_unblocked"
    assert artifact["next_required_slices"] == ["websearch_candidate_pipeline_narrow_expansion"]


def test_websearch_evidence_status_packet_advances_after_narrow_expansion_artifact_passes() -> None:
    artifact = build_websearch_evidence_status_packet(
        candidate_lane_status_packet=_candidate_lane("inspect_websearch_status_packet"),
        exact_lane_status_packet=_exact_lane("grokfast_websearch_packet_live_diagnostic"),
        manager_contract_handoff_artifact=_contract_handoff(
            "websearch_contract_unblocked",
            "inspect_websearch_status_packet",
        ),
        candidate_pipeline_narrow_expansion_artifact=_narrow_expansion(),
    )

    assert artifact["status"] == "pass"
    assert artifact["summary"]["candidate_pipeline_narrow_expansion_status"] == "pass"
    assert artifact["summary"]["candidate_pipeline_narrow_expansion_next_required_slice"] == (
        "inspect_websearch_status_packet"
    )
    assert artifact["next_required_slices"] == ["inspect_websearch_status_packet"]


def test_websearch_evidence_status_packet_rejects_unexpected_candidate_lane_type() -> None:
    try:
        build_websearch_evidence_status_packet(
            candidate_lane_status_packet={"artifact_type": "wrong"}
        )
    except ValueError as exc:
        assert "unsupported_websearch_evidence_status_candidate_lane" in str(exc)
    else:
        raise AssertionError("unexpected candidate lane artifact type must fail")


def test_websearch_evidence_status_packet_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_evidence_status_packet import main

    candidate_path = tmp_path / "candidate_lane.json"
    exact_path = tmp_path / "exact_lane.json"
    handoff_path = tmp_path / "handoff.json"
    output = tmp_path / "websearch_status.json"
    write_json_artifact(candidate_path, _candidate_lane("inspect_websearch_status_packet"))
    write_json_artifact(exact_path, _exact_lane("inspect_websearch_exact_candidate_chain_status"))
    write_json_artifact(
        handoff_path,
        _contract_handoff("websearch_contract_unblocked", "inspect_websearch_status_packet"),
    )

    assert (
        main(
            [
                "--candidate-lane-status-packet",
                str(candidate_path),
                "--exact-lane-status-packet",
                str(exact_path),
                "--manager-contract-handoff-artifact",
                str(handoff_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_evidence_status_packet_v1"
    assert artifact["next_required_slices"] == ["inspect_websearch_exact_candidate_chain_status"]
