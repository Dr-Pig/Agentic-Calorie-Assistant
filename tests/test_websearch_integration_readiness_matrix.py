from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_integration_readiness_matrix import (
    build_websearch_integration_readiness_matrix,
)


def _fooddb_status() -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
        "status": "clear",
        "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "runtime_mutation_allowed": False,
        "readiness_claimed": False,
        "summary": {
            "runtime_truth_allowed_count": 0,
            "ready_for_runtime_truth_count": 0,
        },
    }


def _websearch_status() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
        "status": "clear",
        "next_required_slices": ["websearch_live_search_preflight_or_candidate_source_adapter"],
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "runtime_truth_allowed_count": 0,
            "ready_for_runtime_truth_count": 0,
        },
    }


def _source_adapter_preflight() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_source_adapter_preflight_v1",
        "status": "pass",
        "blockers": [],
        "ready_for_live_search_diagnostic": True,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "readiness_claimed": False,
    }


def _canary_report() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_search_canary_report_v1",
        "status": "trace_only_canary_clean",
        "selected_option": "trace_only_canary_continues",
        "runtime_web_activation_approved": False,
        "runtime_web_activation_recommended": False,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "readiness_claimed": False,
        "blockers": [],
        "decision_boundary": {
            "trace_canary_is_runtime_activation_evidence": False,
            "accepted_extract_packet_is_exact_truth": False,
            "mutation_allowed": False,
            "product_readiness_claim_allowed": False,
        },
        "summary": {
            "runtime_truth_allowed_count": 0,
            "ready_for_runtime_truth_count": 0,
        },
    }


def _exact_lane_status() -> dict:
    return {
        "artifact_type": "accurate_intake_exact_evidence_lane_status_packet_v1",
        "status": "clear",
        "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "runtime_truth_allowed_count": 0,
            "ready_for_runtime_truth_count": 0,
        },
    }


def _live_extract_preflight() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_extract_preflight_v1",
        "status": "pass",
        "blockers": [],
        "ready_for_live_extract_diagnostic": True,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "readiness_claimed": False,
        "summary": {
            "runtime_truth_allowed_count": 0,
            "ready_for_runtime_truth_count": 0,
        },
    }


def _clear_matrix() -> dict:
    return build_websearch_integration_readiness_matrix(
        fooddb_status_packet=_fooddb_status(),
        websearch_status_packet=_websearch_status(),
        source_adapter_preflight=_source_adapter_preflight(),
        live_search_canary_report=_canary_report(),
        exact_lane_status_packet=_exact_lane_status(),
        live_extract_preflight=_live_extract_preflight(),
    )


def test_websearch_integration_readiness_matrix_clears_all_dependency_edges() -> None:
    artifact = _clear_matrix()

    assert artifact["artifact_type"] == "accurate_intake_websearch_integration_readiness_matrix_v1"
    assert artifact["status"] == "clear"
    assert artifact["summary"]["edge_count"] == 13
    assert artifact["summary"]["clear_edge_count"] == 13
    assert artifact["summary"]["blocked_edge_count"] == 0
    assert artifact["summary"]["runtime_activation_ready_count"] == 0
    assert artifact["runtime_web_activation_approved"] is False
    assert artifact["runtime_web_activation_recommended"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["next_required_slice"] == (
        "websearch_exact_candidate_or_live_extract_trace_diagnostic"
    )
    assert all(edge["runtime_truth_allowed"] is False for edge in artifact["edges"])
    assert all(edge["runtime_mutation_allowed"] is False for edge in artifact["edges"])


def test_websearch_integration_readiness_matrix_blocks_missing_inputs() -> None:
    artifact = build_websearch_integration_readiness_matrix()

    assert artifact["status"] == "blocked"
    assert artifact["summary"]["blocked_edge_count"] == 13
    assert artifact["summary"]["missing_artifact_edge_count"] == 13
    assert artifact["next_required_slice"] == "inspect_fooddb_status_packet"


def test_websearch_integration_readiness_matrix_blocks_canary_activation_overclaim() -> None:
    canary = _canary_report()
    canary["runtime_web_activation_recommended"] = True

    artifact = build_websearch_integration_readiness_matrix(
        fooddb_status_packet=_fooddb_status(),
        websearch_status_packet=_websearch_status(),
        source_adapter_preflight=_source_adapter_preflight(),
        live_search_canary_report=canary,
        exact_lane_status_packet=_exact_lane_status(),
        live_extract_preflight=_live_extract_preflight(),
    )

    edge = next(edge for edge in artifact["edges"] if edge["edge_id"] == "source_adapter_to_live_search_canary")
    assert artifact["status"] == "blocked"
    assert edge["status"] == "blocked"
    assert "recommended_runtime_web_activation" in edge["blockers"]
    assert artifact["runtime_web_activation_recommended"] is False


def test_websearch_integration_readiness_matrix_blocks_live_or_nested_canary_overclaim() -> None:
    cases = [
        ("live_provider_used", "used_live_provider"),
        ("live_websearch_used", "used_live_websearch"),
        ("source_live_websearch_used", "used_source_live_websearch"),
        ("live_extract_used", "used_live_extract"),
    ]
    for key, blocker in cases:
        canary = _canary_report()
        canary[key] = True
        artifact = build_websearch_integration_readiness_matrix(
            fooddb_status_packet=_fooddb_status(),
            websearch_status_packet=_websearch_status(),
            source_adapter_preflight=_source_adapter_preflight(),
            live_search_canary_report=canary,
            exact_lane_status_packet=_exact_lane_status(),
            live_extract_preflight=_live_extract_preflight(),
        )
        edge = next(
            edge for edge in artifact["edges"] if edge["edge_id"] == "source_adapter_to_live_search_canary"
        )
        assert artifact["status"] == "blocked"
        assert blocker in edge["blockers"]

    nested_cases = [
        (
            "trace_canary_is_runtime_activation_evidence",
            "decision_boundary_runtime_activation_evidence",
        ),
        ("accepted_extract_packet_is_exact_truth", "decision_boundary_exact_truth"),
        ("mutation_allowed", "decision_boundary_mutation_allowed"),
        ("product_readiness_claim_allowed", "decision_boundary_readiness_allowed"),
    ]
    for key, blocker in nested_cases:
        canary = _canary_report()
        canary["decision_boundary"][key] = True
        artifact = build_websearch_integration_readiness_matrix(
            fooddb_status_packet=_fooddb_status(),
            websearch_status_packet=_websearch_status(),
            source_adapter_preflight=_source_adapter_preflight(),
            live_search_canary_report=canary,
            exact_lane_status_packet=_exact_lane_status(),
            live_extract_preflight=_live_extract_preflight(),
        )
        edge = next(
            edge
            for edge in artifact["edges"]
            if edge["edge_id"] == "source_adapter_to_live_search_canary"
        )
        assert artifact["status"] == "blocked"
        assert blocker in edge["blockers"]


def test_websearch_integration_readiness_matrix_blocks_nested_diagnostic_contract_overclaim() -> None:
    nested_cases = [
        ("live_call_allowed_by_this_artifact", "diagnostic_contract_allowed_live_call"),
        (
            "raw_content_allowed_in_manager_context",
            "diagnostic_contract_allowed_raw_content_in_manager_context",
        ),
        ("ledger_mutation_allowed", "diagnostic_contract_allowed_ledger_mutation"),
        ("exact_card_creation_allowed", "diagnostic_contract_allowed_exact_card_creation"),
    ]
    for key, blocker in nested_cases:
        source_adapter = _source_adapter_preflight()
        source_adapter["diagnostic_contract"] = {key: True}
        artifact = build_websearch_integration_readiness_matrix(
            fooddb_status_packet=_fooddb_status(),
            websearch_status_packet=_websearch_status(),
            source_adapter_preflight=source_adapter,
            live_search_canary_report=_canary_report(),
            exact_lane_status_packet=_exact_lane_status(),
            live_extract_preflight=_live_extract_preflight(),
        )
        edge = next(
            edge for edge in artifact["edges"] if edge["edge_id"] == "websearch_candidate_to_source_adapter"
        )
        assert artifact["status"] == "blocked"
        assert blocker in edge["blockers"]


def test_websearch_integration_readiness_matrix_blocks_runtime_truth_summary_leak() -> None:
    exact_lane = _exact_lane_status()
    exact_lane["summary"]["runtime_truth_allowed_count"] = 1

    artifact = build_websearch_integration_readiness_matrix(
        fooddb_status_packet=_fooddb_status(),
        websearch_status_packet=_websearch_status(),
        source_adapter_preflight=_source_adapter_preflight(),
        live_search_canary_report=_canary_report(),
        exact_lane_status_packet=exact_lane,
        live_extract_preflight=_live_extract_preflight(),
    )

    edge = next(edge for edge in artifact["edges"] if edge["edge_id"] == "exact_candidate_to_no_mutation")
    assert artifact["status"] == "blocked"
    assert "summary_runtime_truth_allowed" in edge["blockers"]
    assert artifact["ready_for_runtime_truth"] is False


def test_websearch_integration_readiness_matrix_blocks_wrong_next_slice() -> None:
    websearch_status = _websearch_status()
    websearch_status["next_required_slices"] = ["run_unbounded_live_websearch"]

    artifact = build_websearch_integration_readiness_matrix(
        fooddb_status_packet=_fooddb_status(),
        websearch_status_packet=websearch_status,
        source_adapter_preflight=_source_adapter_preflight(),
        live_search_canary_report=_canary_report(),
        exact_lane_status_packet=_exact_lane_status(),
        live_extract_preflight=_live_extract_preflight(),
    )

    edge = next(
        edge for edge in artifact["edges"] if edge["edge_id"] == "retrieval_router_to_websearch_candidate"
    )
    assert artifact["status"] == "blocked"
    assert (
        "required_next_slice_missing:websearch_live_search_preflight_or_candidate_source_adapter"
        in edge["blockers"]
    )


def test_websearch_integration_readiness_matrix_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_integration_readiness_matrix import main

    fooddb = tmp_path / "fooddb.json"
    websearch = tmp_path / "websearch.json"
    source_adapter = tmp_path / "source_adapter.json"
    canary = tmp_path / "canary.json"
    exact_lane = tmp_path / "exact_lane.json"
    live_extract = tmp_path / "live_extract.json"
    output = tmp_path / "matrix.json"
    write_json_artifact(fooddb, _fooddb_status())
    write_json_artifact(websearch, _websearch_status())
    write_json_artifact(source_adapter, _source_adapter_preflight())
    write_json_artifact(canary, _canary_report())
    write_json_artifact(exact_lane, _exact_lane_status())
    write_json_artifact(live_extract, _live_extract_preflight())

    assert (
        main(
            [
                "--fooddb-status-packet",
                str(fooddb),
                "--websearch-status-packet",
                str(websearch),
                "--source-adapter-preflight",
                str(source_adapter),
                "--live-search-canary-report",
                str(canary),
                "--exact-lane-status-packet",
                str(exact_lane),
                "--live-extract-preflight",
                str(live_extract),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_integration_readiness_matrix_v1"
    assert artifact["status"] == "clear"


def test_websearch_integration_readiness_matrix_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_integration_readiness_matrix.py"),
        Path("scripts/build_accurate_intake_websearch_integration_readiness_matrix.py"),
    ]
    forbidden = [
        "Tavily",
        "tavily",
        "OpenAI",
        "openai",
        "BuilderSpaceAdapter",
        "import requests",
        "from requests",
        "requests.",
        "import httpx",
        "from httpx",
        "httpx.",
        "ManagerContextPacket",
        "NutritionEvidenceStorePort",
        "PacketReadyAnchor",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
