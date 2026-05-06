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
    assert artifact["summary"]["source_adapter_guard_status"] == "pass"
    assert artifact["summary"]["source_adapter_guard_case_count"] == 3
    assert artifact["summary"]["source_adapter_guard_max_results_hard_cap"] == 20
    assert artifact["summary"]["pipeline_case_count"] >= 4
    assert artifact["summary"]["extract_candidate_allowed_count"] >= 1
    assert artifact["summary"]["candidate_packet_case_count"] == 4
    assert artifact["summary"]["candidate_only_packet_count"] == 4
    assert artifact["summary"]["manager_projection_case_count"] == 4
    assert artifact["summary"]["manager_projection_compact_count"] == 4
    assert artifact["summary"]["upstream_fooddb_gate_status"] == "not_provided"
    assert artifact["summary"]["manager_contract_gate_status"] == "not_provided"
    assert artifact["next_required_slices"] == ["inspect_fooddb_status_packet"]


def test_websearch_candidate_lane_status_packet_blocks_when_source_adapter_guard_blocks() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        source_adapter_guard_artifact={
            "artifact_type": "accurate_intake_websearch_source_adapter_guard_v1",
            "status": "blocked",
            "blockers": ["raw_provider_truth_marker"],
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_provider_used": False,
            "live_websearch_used": False,
            "readiness_claimed": False,
            "summary": {
                "case_count": 3,
                "truth_field_leak_count": 1,
                "max_results_hard_cap": 20,
            },
        }
    )

    assert artifact["summary"]["source_adapter_guard_status"] == "blocked_on_source_adapter_guard"
    assert artifact["source_adapter_gate"]["truth_field_leak_count"] == 1
    assert artifact["next_required_slices"] == ["inspect_websearch_source_adapter_guard"]


def test_websearch_candidate_lane_status_packet_blocks_source_adapter_guard_overclaims() -> None:
    for forbidden_key in (
        "runtime_truth_changed",
        "mutation_changed",
        "live_provider_used",
        "live_websearch_used",
        "readiness_claimed",
    ):
        guard = {
            "artifact_type": "accurate_intake_websearch_source_adapter_guard_v1",
            "status": "pass",
            "blockers": [],
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_provider_used": False,
            "live_websearch_used": False,
            "readiness_claimed": False,
            "summary": {
                "case_count": 3,
                "truth_field_leak_count": 0,
                "max_results_hard_cap": 20,
            },
        }
        guard[forbidden_key] = True

        artifact = build_websearch_candidate_lane_status_packet(
            source_adapter_guard_artifact=guard
        )

        assert artifact["summary"]["source_adapter_guard_status"] == (
            "blocked_on_source_adapter_guard"
        )
        assert artifact["next_required_slices"] == ["inspect_websearch_source_adapter_guard"]


def test_websearch_candidate_lane_status_packet_blocks_inconsistent_source_adapter_guard_summary() -> None:
    base_guard = {
        "artifact_type": "accurate_intake_websearch_source_adapter_guard_v1",
        "status": "pass",
        "blockers": [],
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "case_count": 3,
            "truth_field_leak_count": 0,
            "max_results_hard_cap": 20,
        },
    }
    summary_mutations = (
        {"case_count": 0},
        {"truth_field_leak_count": 1},
        {"max_results_hard_cap": 999},
    )

    for mutation in summary_mutations:
        guard = {**base_guard, "summary": {**base_guard["summary"], **mutation}}

        artifact = build_websearch_candidate_lane_status_packet(
            source_adapter_guard_artifact=guard
        )

        assert artifact["summary"]["source_adapter_guard_status"] == (
            "blocked_on_source_adapter_guard"
        )
        assert artifact["next_required_slices"] == ["inspect_websearch_source_adapter_guard"]


def test_websearch_candidate_lane_status_packet_blocks_on_fooddb_manager_contract_gate() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet=_fooddb_status_packet()
    )

    assert artifact["summary"]["upstream_fooddb_gate_status"] == "blocked_on_fooddb_upstream_gate"
    assert artifact["summary"]["upstream_fooddb_next_required_slice"] == "await_manager_contract_owner_repair"
    assert artifact["next_required_slices"] == ["await_manager_contract_owner_repair"]


def test_websearch_candidate_lane_status_packet_allows_live_only_when_fooddb_explicitly_points_to_websearch() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact={
            "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
            "status": "websearch_contract_unblocked",
            "selected_next_step": "websearch_candidate_pipeline_narrow_expansion",
        },
    )

    assert artifact["summary"]["upstream_fooddb_gate_status"] == "clear_for_websearch_lane"
    assert artifact["summary"]["manager_contract_gate_status"] == "clear_for_websearch_lane"
    assert artifact["next_required_slices"] == ["grokfast_websearch_packet_live_diagnostic"]


def test_websearch_candidate_lane_status_packet_requires_manager_contract_handoff_when_fooddb_clear() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        }
    )

    assert artifact["summary"]["upstream_fooddb_gate_status"] == "clear_for_websearch_lane"
    assert artifact["summary"]["manager_contract_gate_status"] == "not_provided"
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_on_manager_contract_handoff() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact={
            "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
            "status": "ready_for_manager_contract_owner",
            "selected_next_step": "tighten_websearch_manager_contract_prompt_or_transport",
        },
    )

    assert artifact["summary"]["upstream_fooddb_gate_status"] == "clear_for_websearch_lane"
    assert artifact["summary"]["manager_contract_gate_status"] == "blocked_on_manager_contract_owner"
    assert artifact["next_required_slices"] == [
        "tighten_websearch_manager_contract_prompt_or_transport"
    ]


def test_websearch_candidate_lane_status_packet_allows_live_when_manager_contract_unblocked() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact={
            "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
            "status": "websearch_contract_unblocked",
            "selected_next_step": "websearch_candidate_pipeline_narrow_expansion",
        },
    )

    assert artifact["summary"]["manager_contract_gate_status"] == "clear_for_websearch_lane"
    assert artifact["next_required_slices"] == ["grokfast_websearch_packet_live_diagnostic"]


def test_websearch_candidate_lane_status_packet_rejects_unexpected_manager_contract_artifact() -> None:
    try:
        build_websearch_candidate_lane_status_packet(
            manager_contract_handoff_artifact={"artifact_type": "wrong"}
        )
    except ValueError as exc:
        assert "unsupported_websearch_status_manager_contract_handoff" in str(exc)
    else:
        raise AssertionError("unexpected manager contract artifact type must fail")


def test_websearch_candidate_lane_status_packet_rejects_unexpected_source_adapter_guard() -> None:
    try:
        build_websearch_candidate_lane_status_packet(
            source_adapter_guard_artifact={"artifact_type": "wrong"}
        )
    except ValueError as exc:
        assert "unsupported_websearch_status_source_adapter_guard" in str(exc)
    else:
        raise AssertionError("unexpected source adapter guard artifact type must fail")


def test_websearch_candidate_lane_status_packet_rejects_empty_source_adapter_guard() -> None:
    try:
        build_websearch_candidate_lane_status_packet(source_adapter_guard_artifact={})
    except ValueError as exc:
        assert "unsupported_websearch_status_source_adapter_guard" in str(exc)
    else:
        raise AssertionError("empty source adapter guard artifact must fail")


def test_websearch_candidate_lane_status_packet_sanitizes_manager_contract_next_step() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact={
            "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
            "status": "ready_for_manager_contract_owner",
            "selected_next_step": "raw_response_excerpt forbidden",
        },
    )

    serialized = str(artifact)
    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized
    assert artifact["next_required_slices"] == [
        "tighten_websearch_manager_contract_prompt_or_transport"
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


def test_websearch_candidate_lane_status_packet_sanitizes_fooddb_next_required_slice() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["raw_response_excerpt forbidden"],
        },
        manager_contract_handoff_artifact={
            "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
            "status": "websearch_contract_unblocked",
            "selected_next_step": "websearch_candidate_pipeline_narrow_expansion",
        },
    )

    serialized = str(artifact)
    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized
    assert artifact["summary"]["upstream_fooddb_next_required_slice"] == "inspect_fooddb_status_packet"
    assert artifact["next_required_slices"] == ["inspect_fooddb_status_packet"]


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
        "source_url",
        "raw_provider_truth_marker",
    ):
        assert token not in serialized


def test_websearch_candidate_lane_status_packet_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_candidate_lane_status_packet import main

    fooddb_input = tmp_path / "fooddb_status.json"
    output = tmp_path / "websearch_status.json"
    write_json_artifact(fooddb_input, _fooddb_status_packet())

    assert (
        main(
            [
                "--fooddb-status-packet",
                str(fooddb_input),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_candidate_lane_status_packet_v1"
    assert artifact["next_required_slices"] == ["await_manager_contract_owner_repair"]


def test_websearch_candidate_lane_status_packet_script_accepts_manager_contract_gate(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_candidate_lane_status_packet import main

    fooddb_input = tmp_path / "fooddb_status.json"
    handoff_input = tmp_path / "handoff.json"
    output = tmp_path / "websearch_status.json"
    write_json_artifact(
        fooddb_input,
        {
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
    )
    write_json_artifact(
        handoff_input,
        {
            "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
            "status": "ready_for_manager_contract_owner",
            "selected_next_step": "tighten_websearch_manager_contract_prompt_or_transport",
        },
    )

    assert (
        main(
            [
                "--fooddb-status-packet",
                str(fooddb_input),
                "--manager-contract-handoff-artifact",
                str(handoff_input),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["next_required_slices"] == [
        "tighten_websearch_manager_contract_prompt_or_transport"
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
