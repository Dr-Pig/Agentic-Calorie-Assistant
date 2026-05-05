from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_live_extract_diagnostic_gate import (
    build_websearch_live_extract_diagnostic_gate,
)


def _matrix() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_integration_readiness_matrix_v1",
        "status": "clear",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "runtime_mutation_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "runtime_web_activation_approved": False,
        "runtime_web_activation_recommended": False,
        "readiness_claimed": False,
        "ready_for_runtime_truth": False,
        "ready_for_runtime_mutation": False,
        "next_required_slice": "websearch_exact_candidate_or_live_extract_trace_diagnostic",
        "summary": {
            "blocked_edge_count": 0,
            "runtime_truth_allowed_count": 0,
            "ready_for_runtime_truth_count": 0,
            "runtime_activation_ready_count": 0,
        },
    }


def _preflight() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_extract_preflight_v1",
        "status": "pass",
        "blockers": [],
        "ready_for_live_extract_diagnostic": True,
        "ready_for_runtime_truth": False,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "readiness_claimed": False,
        "diagnostic_contract": {
            "live_call_allowed_by_this_artifact": False,
            "requires_explicit_allow_live_flag": True,
            "raw_content_allowed_in_manager_context": False,
            "ledger_mutation_allowed": False,
            "exact_card_creation_allowed": False,
        },
        "review_packet_refs": [
            {
                "packet_id": "pkt_exact_card_review_abc",
                "source_url": "https://example.test/menu",
                "canonical_name": "Test Brand Latte",
                "packet_digest": "digest123",
            }
        ],
        "summary": {
            "runtime_truth_allowed_count": 0,
            "ready_for_runtime_truth_count": 0,
        },
    }


def test_live_extract_diagnostic_gate_passes_trace_only_without_runtime_activation() -> None:
    artifact = build_websearch_live_extract_diagnostic_gate(
        integration_matrix_artifact=_matrix(),
        live_extract_preflight_artifact=_preflight(),
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_live_extract_diagnostic_gate_v1"
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "deterministic_live_extract_diagnostic_gate_only"
    assert artifact["ready_for_trace_only_live_extract_diagnostic"] is True
    assert artifact["runtime_web_activation_approved"] is False
    assert artifact["runtime_web_activation_recommended"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["live_extract_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["review_packet_ref_count"] == 1
    assert artifact["summary"]["runtime_activation_ready_count"] == 0
    assert artifact["diagnostic_contract"]["live_call_allowed_by_this_artifact"] is False
    assert artifact["diagnostic_contract"]["requires_explicit_allow_live_flag"] is True
    assert artifact["diagnostic_contract"]["extract_result_role"] == "review_candidate_only"
    assert artifact["next_required_slice"] == "websearch_live_extract_diagnostic_canary_harness"


def test_live_extract_diagnostic_gate_blocks_unclear_matrix() -> None:
    matrix = _matrix()
    matrix["status"] = "blocked"
    matrix["summary"]["blocked_edge_count"] = 1

    artifact = build_websearch_live_extract_diagnostic_gate(
        integration_matrix_artifact=matrix,
        live_extract_preflight_artifact=_preflight(),
    )

    assert artifact["status"] == "blocked"
    assert "integration_matrix:status_not_clear:blocked" in artifact["blockers"]
    assert "integration_matrix:blocked_edges_present" in artifact["blockers"]
    assert artifact["next_required_slice"] == "inspect_websearch_integration_readiness_matrix"


def test_live_extract_diagnostic_gate_blocks_matrix_activation_or_truth_leak() -> None:
    for key, blocker in {
        "runtime_web_activation_recommended": "recommended_runtime_web_activation",
        "ready_for_runtime_truth": "claimed_ready_for_runtime_truth",
        "runtime_mutation_allowed": "allowed_runtime_mutation",
    }.items():
        matrix = _matrix()
        matrix[key] = True
        artifact = build_websearch_live_extract_diagnostic_gate(
            integration_matrix_artifact=matrix,
            live_extract_preflight_artifact=_preflight(),
        )
        assert artifact["status"] == "blocked"
        assert f"integration_matrix:{blocker}" in artifact["blockers"]
        assert artifact["runtime_web_activation_recommended"] is False


def test_live_extract_diagnostic_gate_blocks_live_usage_flags() -> None:
    for source, key, blocker in (
        ("matrix", "live_provider_used", "used_live_provider"),
        ("matrix", "live_websearch_used", "used_live_websearch"),
        ("preflight", "source_live_websearch_used", "used_source_live_websearch"),
        ("preflight", "live_extract_used", "used_live_extract"),
    ):
        matrix = _matrix()
        preflight = _preflight()
        if source == "matrix":
            matrix[key] = True
        else:
            preflight[key] = True
        artifact = build_websearch_live_extract_diagnostic_gate(
            integration_matrix_artifact=matrix,
            live_extract_preflight_artifact=preflight,
        )
        assert artifact["status"] == "blocked"
        assert any(item.endswith(blocker) for item in artifact["blockers"])


def test_live_extract_diagnostic_gate_blocks_preflight_contract_overclaim() -> None:
    for key, blocker in {
        "live_call_allowed_by_this_artifact": "contract_allowed_live_call",
        "raw_content_allowed_in_manager_context": "contract_allowed_raw_content_in_manager_context",
        "extract_snippet_truth_allowed": "contract_allowed_extract_snippet_truth",
        "ledger_mutation_allowed": "contract_allowed_ledger_mutation",
        "exact_card_creation_allowed": "contract_allowed_exact_card_creation",
        "runtime_activation_allowed": "contract_allowed_runtime_activation",
    }.items():
        preflight = _preflight()
        preflight["diagnostic_contract"][key] = True
        artifact = build_websearch_live_extract_diagnostic_gate(
            integration_matrix_artifact=_matrix(),
            live_extract_preflight_artifact=preflight,
        )
        assert artifact["status"] == "blocked"
        assert f"live_extract_preflight:{blocker}" in artifact["blockers"]
        assert artifact["ready_for_trace_only_live_extract_diagnostic"] is False


def test_live_extract_diagnostic_gate_blocks_missing_review_packet_refs() -> None:
    preflight = _preflight()
    preflight["review_packet_refs"] = []

    artifact = build_websearch_live_extract_diagnostic_gate(
        integration_matrix_artifact=_matrix(),
        live_extract_preflight_artifact=preflight,
    )

    assert artifact["status"] == "blocked"
    assert "live_extract_preflight:review_packet_refs_missing" in artifact["blockers"]
    assert artifact["next_required_slice"] == "inspect_websearch_live_extract_preflight"


def test_live_extract_diagnostic_gate_blocks_malformed_review_packet_refs() -> None:
    for packet, blocker in (
        ({}, "review_packet_ref_missing_packet_id"),
        (
            {"packet_id": "pkt", "packet_digest": "digest"},
            "review_packet_ref_missing_source_url",
        ),
        (
            {"packet_id": "pkt", "source_url": "https://example.test/menu"},
            "review_packet_ref_missing_packet_digest",
        ),
    ):
        preflight = _preflight()
        preflight["review_packet_refs"] = [packet]
        artifact = build_websearch_live_extract_diagnostic_gate(
            integration_matrix_artifact=_matrix(),
            live_extract_preflight_artifact=preflight,
        )
        assert artifact["status"] == "blocked"
        assert f"live_extract_preflight:{blocker}" in artifact["blockers"]
        assert artifact["ready_for_trace_only_live_extract_diagnostic"] is False


def test_live_extract_diagnostic_gate_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_live_extract_diagnostic_gate import main

    matrix = tmp_path / "matrix.json"
    preflight = tmp_path / "preflight.json"
    output = tmp_path / "gate.json"
    write_json_artifact(matrix, _matrix())
    write_json_artifact(preflight, _preflight())

    assert (
        main(
            [
                "--integration-matrix",
                str(matrix),
                "--live-extract-preflight",
                str(preflight),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_live_extract_diagnostic_gate_v1"
    assert artifact["status"] == "pass"


def test_live_extract_diagnostic_gate_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_live_extract_diagnostic_gate.py"),
        Path("scripts/build_accurate_intake_websearch_live_extract_diagnostic_gate.py"),
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
