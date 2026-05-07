from __future__ import annotations

from app.nutrition.application.evidence_track_live_handoff import (
    build_evidence_track_live_handoff,
)


def _fooddb_manifest(
    *,
    bundle_status: str = "pass",
    seam_status: str = "live_diagnostic_pass",
    next_recommended_slice: str = "grokfast_websearch_packet_live_diagnostic",
    live_provider_used: bool = True,
) -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_fooddb_live_diagnostic_bundle_manifest",
        "bundle_status": bundle_status,
        "seam_status": seam_status,
        "next_recommended_slice": next_recommended_slice,
        "live_provider_used": live_provider_used,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
    }


def _fooddb_status_packet(
    *,
    next_required_slices: list[str] | None = None,
    live_seam_status: str = "live_diagnostic_pass",
    handoff_status: str = "fooddb_contract_unblocked",
) -> dict[str, object]:
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
            "manager_contract_live_seam_status": live_seam_status,
            "manager_contract_handoff_status": handoff_status,
            "manager_contract_owner_handoff_ready": False,
        },
        "next_required_slices": next_required_slices
        or ["grokfast_websearch_packet_live_diagnostic"],
    }


def _websearch_manifest(
    *,
    bundle_status: str = "pass",
    seam_status: str = "live_diagnostic_pass",
    next_recommended_slice: str = "inspect_websearch_status_packet",
    live_provider_used: bool = True,
) -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_websearch_live_diagnostic_bundle_manifest",
        "bundle_status": bundle_status,
        "seam_status": seam_status,
        "next_recommended_slice": next_recommended_slice,
        "live_provider_used": live_provider_used,
        "live_websearch_used": False,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
    }


def _websearch_status_inspection(*, status: str = "pass") -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_websearch_status_packet_inspection_v1",
        "status": status,
        "blockers": [] if status == "pass" else ["websearch_status_packet_candidate_lane_not_clear_for_inspection"],
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "next_safe_slice": "inspect_websearch_status_packet",
        },
    }


def test_evidence_track_live_handoff_stays_on_fooddb_live_step_when_fooddb_is_fixture_only() -> None:
    artifact = build_evidence_track_live_handoff(
        fooddb_manifest=_fooddb_manifest(
            seam_status="fixture_only_live_not_checked",
            next_recommended_slice="grokfast_fooddb_packet_live_diagnostic",
            live_provider_used=False,
        ),
        fooddb_status_post_contract=None,
        websearch_manifest=None,
        websearch_status_packet_inspection=None,
    )

    assert artifact["artifact_type"] == "accurate_intake_evidence_track_live_handoff_v1"
    assert artifact["status"] == "fixture_only_live_not_checked"
    assert artifact["selected_next_step"] == "grokfast_fooddb_packet_live_diagnostic"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["readiness_claimed"] is False


def test_evidence_track_live_handoff_passes_after_fooddb_and_websearch_live_clear() -> None:
    artifact = build_evidence_track_live_handoff(
        fooddb_manifest=_fooddb_manifest(),
        fooddb_status_post_contract=_fooddb_status_packet(),
        websearch_manifest=_websearch_manifest(),
        websearch_status_packet_inspection=_websearch_status_inspection(),
    )

    assert artifact["status"] == "evidence_track_live_diagnostic_pass"
    assert artifact["selected_next_step"] == "external_manager_runtime_packet_probe"
    assert artifact["summary"]["fooddb_live_provider_used"] is True
    assert artifact["summary"]["websearch_live_provider_used"] is True
    assert artifact["summary"]["websearch_status_inspection_passed"] is True
    assert artifact["blockers"] == []


def test_evidence_track_live_handoff_blocks_when_websearch_status_packet_inspection_is_blocked() -> None:
    artifact = build_evidence_track_live_handoff(
        fooddb_manifest=_fooddb_manifest(),
        fooddb_status_post_contract=_fooddb_status_packet(),
        websearch_manifest=_websearch_manifest(),
        websearch_status_packet_inspection=_websearch_status_inspection(status="blocked"),
    )

    assert artifact["status"] == "blocked"
    assert "websearch_status_packet_inspection_not_pass" in artifact["blockers"]
    assert artifact["selected_next_step"] == "inspect_websearch_status_packet"
