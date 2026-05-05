from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_candidate_lane_status_packet import (
    build_websearch_candidate_lane_status_packet,
)


def _fooddb_status_packet() -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
        "next_required_slices": ["await_manager_contract_owner_repair"],
    }


def _fooddb_clear_for_websearch() -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
        "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
    }


def _live_diagnostic_report(
    *,
    seam_status: str = "live_diagnostic_pass",
    can_expand: bool = True,
    next_recommended_slice: str = "websearch_candidate_pipeline_narrow_expansion",
) -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_diagnostic_report",
        "seam_status": seam_status,
        "can_expand_websearch_candidate_pipeline": can_expand,
        "source_live_websearch_used": False,
        "runtime_truth_changed": False,
        "readiness_claimed": False,
        "next_recommended_slice": next_recommended_slice,
    }


def test_websearch_candidate_lane_status_packet_summarizes_deterministic_lane() -> None:
    artifact = build_websearch_candidate_lane_status_packet()

    assert artifact["artifact_type"] == "accurate_intake_websearch_candidate_lane_status_packet_v1"
    assert artifact["classification"] == "deterministic_websearch_candidate_lane_status_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["source_policy_max_search_attempts"] == 2
    assert artifact["summary"]["source_policy_max_results"] == 5
    assert artifact["summary"]["pipeline_case_count"] >= 4
    assert artifact["summary"]["extract_candidate_allowed_count"] >= 1
    assert artifact["summary"]["candidate_packet_case_count"] == 7
    assert artifact["summary"]["candidate_only_packet_count"] == 7
    assert artifact["summary"]["manager_projection_case_count"] == 7
    assert artifact["summary"]["manager_projection_compact_count"] == 7
    assert artifact["summary"]["upstream_fooddb_gate_status"] == "not_provided"
    assert artifact["summary"]["grokfast_websearch_seam_status"] == "not_checked_upstream_blocked"
    assert artifact["summary"]["grokfast_websearch_can_expand"] is False
    assert artifact["next_required_slices"] == ["inspect_fooddb_status_packet"]


def test_websearch_candidate_lane_status_packet_blocks_on_fooddb_manager_contract_gate() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet=_fooddb_status_packet()
    )

    assert artifact["summary"]["upstream_fooddb_gate_status"] == "blocked_on_fooddb_upstream_gate"
    assert artifact["summary"]["upstream_fooddb_next_required_slice"] == "await_manager_contract_owner_repair"
    assert artifact["next_required_slices"] == ["await_manager_contract_owner_repair"]


def test_websearch_candidate_lane_status_packet_allows_live_only_when_fooddb_explicitly_points_to_websearch() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet=_fooddb_clear_for_websearch()
    )

    assert artifact["summary"]["upstream_fooddb_gate_status"] == "clear_for_websearch_lane"
    assert artifact["summary"]["grokfast_websearch_seam_status"] == "not_provided"
    assert artifact["next_required_slices"] == [
        "run_explicit_grokfast_websearch_packet_live_diagnostic"
    ]


def test_websearch_candidate_lane_status_packet_allows_next_source_adapter_after_live_report_pass() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet=_fooddb_clear_for_websearch(),
        live_diagnostic_report=_live_diagnostic_report(),
    )

    assert artifact["summary"]["upstream_fooddb_gate_status"] == "clear_for_websearch_lane"
    assert artifact["summary"]["grokfast_websearch_seam_status"] == "live_diagnostic_pass"
    assert artifact["summary"]["grokfast_websearch_can_expand"] is True
    assert artifact["live_diagnostic_gate"]["blocked"] is False
    assert artifact["next_required_slices"] == [
        "websearch_live_search_preflight_or_candidate_source_adapter"
    ]


def test_websearch_candidate_lane_status_packet_blocks_on_live_report_failure() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet=_fooddb_clear_for_websearch(),
        live_diagnostic_report=_live_diagnostic_report(
            seam_status="candidate_boundary_blocked",
            can_expand=False,
            next_recommended_slice="narrow_websearch_packet_boundary_or_prompt_probe",
        ),
    )

    assert artifact["summary"]["grokfast_websearch_seam_status"] == "candidate_boundary_blocked"
    assert artifact["summary"]["grokfast_websearch_can_expand"] is False
    assert artifact["live_diagnostic_gate"]["blocked"] is True
    assert artifact["next_required_slices"] == [
        "narrow_websearch_packet_boundary_or_prompt_probe"
    ]


def test_websearch_candidate_lane_status_packet_blocks_live_websearch_or_truth_claims() -> None:
    for unsafe_key in (
        "source_live_websearch_used",
        "live_websearch_used",
        "runtime_truth_changed",
        "readiness_claimed",
    ):
        report = _live_diagnostic_report()
        report[unsafe_key] = True
        artifact = build_websearch_candidate_lane_status_packet(
            fooddb_status_packet=_fooddb_clear_for_websearch(),
            live_diagnostic_report=report,
        )
        assert artifact["summary"]["grokfast_websearch_seam_status"] == (
            "unsupported_live_diagnostic_boundary"
        )
        assert artifact["next_required_slices"] == ["inspect_websearch_live_diagnostic_report"]


def test_websearch_candidate_lane_status_packet_blocks_inconsistent_live_report_flags() -> None:
    for blocked_key in (
        "provider_contract_blocked",
        "provider_runtime_residual_blocked",
        "candidate_boundary_blocked",
    ):
        report = _live_diagnostic_report(
            next_recommended_slice="narrow_websearch_packet_boundary_or_prompt_probe"
        )
        report[blocked_key] = True
        artifact = build_websearch_candidate_lane_status_packet(
            fooddb_status_packet=_fooddb_clear_for_websearch(),
            live_diagnostic_report=report,
        )
        assert artifact["summary"]["grokfast_websearch_seam_status"] == (
            "blocked_live_diagnostic_report"
        )
        assert artifact["next_required_slices"] == [
            "narrow_websearch_packet_boundary_or_prompt_probe"
        ]


def test_websearch_candidate_lane_status_packet_blocks_other_fooddb_pending_states() -> None:
    for next_required in (
        "common_serving_anchor_expansion",
        "manager_fooddb_packet_seam_smoke",
        "grokfast_fooddb_packet_live_diagnostic",
    ):
        artifact = build_websearch_candidate_lane_status_packet(
            fooddb_status_packet={
                "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
                "next_required_slices": [next_required],
            }
        )
        assert artifact["summary"]["upstream_fooddb_gate_status"] == "blocked_on_fooddb_upstream_gate"
        assert artifact["next_required_slices"] == [next_required]


def test_websearch_candidate_lane_status_packet_excludes_raw_and_truth_payloads() -> None:
    artifact = build_websearch_candidate_lane_status_packet()
    serialized = str(artifact)

    for token in (
        "raw_hits",
        "raw_search_results",
        "runtime_truth_allowed': True",
        "likely_kcal",
        "kcal_range",
        "adapter_kind",
        "storage_backend",
        "supabase",
        "snippet",
    ):
        assert token not in serialized


def test_websearch_candidate_lane_status_packet_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_candidate_lane_status_packet import main

    fooddb_input = tmp_path / "fooddb_status.json"
    live_report_input = tmp_path / "live_report.json"
    output = tmp_path / "websearch_status.json"
    write_json_artifact(fooddb_input, _fooddb_clear_for_websearch())
    write_json_artifact(live_report_input, _live_diagnostic_report())

    assert (
        main(
            [
                "--fooddb-status-packet",
                str(fooddb_input),
                "--live-diagnostic-report",
                str(live_report_input),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_candidate_lane_status_packet_v1"
    assert artifact["next_required_slices"] == [
        "websearch_live_search_preflight_or_candidate_source_adapter"
    ]


def test_websearch_candidate_lane_status_packet_rejects_unexpected_fooddb_artifact_type() -> None:
    try:
        build_websearch_candidate_lane_status_packet(
            fooddb_status_packet={"artifact_type": "wrong", "next_required_slices": []}
        )
    except ValueError as exc:
        assert "unsupported_websearch_status_fooddb_packet" in str(exc)
    else:
        raise AssertionError("unexpected FoodDB status packet type must fail")


def test_websearch_candidate_lane_status_packet_rejects_unexpected_live_report_type() -> None:
    try:
        build_websearch_candidate_lane_status_packet(
            fooddb_status_packet=_fooddb_clear_for_websearch(),
            live_diagnostic_report={"artifact_type": "wrong"},
        )
    except ValueError as exc:
        assert "unsupported_websearch_status_live_diagnostic_report" in str(exc)
    else:
        raise AssertionError("unexpected WebSearch live diagnostic report type must fail")


def test_websearch_candidate_lane_status_packet_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_candidate_lane_status_packet.py"),
        Path("scripts/build_accurate_intake_websearch_candidate_lane_status_packet.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "Tavily",
        "requests.",
        "httpx.",
        "allow_live",
        "run_live",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
