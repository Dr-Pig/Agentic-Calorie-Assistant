from __future__ import annotations

from pathlib import Path

from app.nutrition.application.grokfast_websearch_packet_smoke import (
    build_fixture_grokfast_websearch_manager_outputs,
    build_grokfast_websearch_packet_diagnostic,
    build_live_websearch_manager_payload,
)
from app.nutrition.application.tool_evidence_result import build_tool_evidence_result
from app.nutrition.application.websearch_candidate_packet_smoke import (
    build_websearch_candidate_packet_smoke,
)
from app.nutrition.application.websearch_manager_packet_smoke import (
    build_websearch_manager_packet_projection,
    is_compact_websearch_manager_packet,
)
from app.runtime.agent.manager_branch_contract import should_attempt_b1_pass2_structured_output_transport


def _manager_packet_artifact() -> dict:
    packet_artifact = build_websearch_candidate_packet_smoke()
    packets = tuple(case["websearch_candidate_packet"] for case in packet_artifact["cases"])
    tool_result = build_tool_evidence_result(
        tool_name="search_official_nutrition",
        tool_call_id="tool-call-websearch-candidate-grokfast",
        evidence_packets=packets,
        trace_context={
            "packet_artifact_type": packet_artifact["artifact_type"],
            "packet_claim_scope": packet_artifact["claim_scope"],
            "live_websearch_used": False,
            "websearch_runtime_truth_allowed": False,
        },
    )
    return build_websearch_manager_packet_projection(
        tool_evidence_artifact={
            "artifact_type": "accurate_intake_websearch_tool_evidence_result_smoke",
            "tool_evidence_result": tool_result,
        }
    )


def test_grokfast_websearch_candidate_packet_fixture_diagnostic_passes_without_truth() -> None:
    packet_artifact = _manager_packet_artifact()
    manager_outputs = build_fixture_grokfast_websearch_manager_outputs(
        packet_artifact=packet_artifact
    )

    diagnostic = build_grokfast_websearch_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=manager_outputs,
        live_provider_used=False,
    )

    assert diagnostic["artifact_type"] == "accurate_intake_grokfast_websearch_packet_smoke"
    assert diagnostic["packet_artifact_type"] == "accurate_intake_websearch_manager_packet_projection"
    assert diagnostic["classification"] == "live_diagnostic_only"
    assert diagnostic["status"] == "pass"
    assert diagnostic["summary"]["case_count"] == packet_artifact["summary"]["case_count"]
    assert diagnostic["live_provider_used"] is False
    assert diagnostic["live_websearch_used"] is False
    assert diagnostic["websearch_runtime_truth_allowed"] is False
    assert diagnostic["runtime_truth_changed"] is False
    assert diagnostic["runtime_mutation_attempted"] is False
    assert diagnostic["readiness_claimed"] is False


def test_grokfast_websearch_candidate_live_payload_uses_compact_candidate_packet() -> None:
    packet_artifact = _manager_packet_artifact()
    packet_case = packet_artifact["cases"][0]
    payload = build_live_websearch_manager_payload(packet_case=packet_case)

    assert payload["diagnostic_scope"] == "websearch_packet_manager_seam_smoke"
    assert payload["constraints"]["phase_b1_manager_role"] == "pass_2_synthesis"
    assert payload["constraints"]["websearch_runtime_truth_allowed"] is False
    assert payload["constraints"]["runtime_mutation_allowed"] is False
    assert should_attempt_b1_pass2_structured_output_transport(payload["constraints"]) is True
    assert any(
        "semantic_decision.target_attachment empty" in instruction
        for instruction in payload["instructions"]
    )

    manager_packet = payload["websearch_evidence_packet"]
    source_url = manager_packet["evidence_items"][0]["source_url"]
    assert manager_packet["packet_type"] == "websearch_manager_evidence_packet_v1"
    assert is_compact_websearch_manager_packet(manager_packet)
    assert payload["allowed_evidence_refs"] == [manager_packet["packet_id"], source_url]
    assert manager_packet["truth_selection_forbidden"] is True
    assert manager_packet["raw_search_results_included"] is False
    assert manager_packet["candidate_only_records_included"] is False
    assert "review_packets" not in payload
    assert "exact_card_review_packet" not in payload
    assert "websearch_candidate_packet" not in str(manager_packet)


def test_grokfast_websearch_candidate_packet_smoke_cli_defaults_to_fixture_and_blocks_live(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_websearch_candidate_packet_smoke import main

    manager_packet_path = tmp_path / "manager_packet.json"
    output = tmp_path / "diagnostic.json"
    write_json_artifact(manager_packet_path, _manager_packet_artifact())

    assert (
        main(
            [
                "--mode",
                "fixture",
                "--manager-packet-artifact",
                str(manager_packet_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    artifact = read_json_artifact(output)
    assert artifact["status"] == "pass"
    assert artifact["live_provider_used"] is False
    assert artifact["packet_artifact_type"] == "accurate_intake_websearch_manager_packet_projection"

    blocked_output = tmp_path / "blocked_live.json"
    assert (
        main(
            [
                "--mode",
                "live",
                "--manager-packet-artifact",
                str(manager_packet_path),
                "--output",
                str(blocked_output),
            ]
        )
        == 2
    )
    blocked = read_json_artifact(blocked_output)
    assert blocked["status"] == "blocked"
    assert blocked["failure_family"] == "live_mode_requires_explicit_allow_live"
    assert blocked["live_provider_used"] is False
    assert blocked["live_websearch_used"] is False


def test_grokfast_websearch_candidate_runner_does_not_import_live_websearch_or_exact_lane() -> None:
    source_paths = [
        Path("app/nutrition/application/grokfast_websearch_packet_smoke.py"),
        Path("scripts/run_accurate_intake_grokfast_websearch_candidate_packet_smoke.py"),
    ]
    forbidden = [
        "Tavily",
        "tavily",
        "websearch_exact_candidate_review_packet",
        "websearch_selected_extract",
        "websearch_live_extract_preflight",
        "exact_card_candidate_promotion_readiness",
        "NutritionEvidenceStorePort",
        "ManagerContextPacket",
        "PacketReadyAnchor",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source

    app_source = Path("app/nutrition/application/grokfast_websearch_packet_smoke.py").read_text(
        encoding="utf-8"
    )
    assert "BuilderSpaceAdapter" not in app_source


def test_grokfast_websearch_candidate_default_output_does_not_collide_with_exact_review_runner() -> None:
    from scripts.run_accurate_intake_grokfast_websearch_candidate_packet_smoke import (
        DEFAULT_OUTPUT as CANDIDATE_OUTPUT,
    )
    from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import (
        DEFAULT_OUTPUT as EXACT_REVIEW_OUTPUT,
    )

    assert CANDIDATE_OUTPUT.name == "accurate_intake_grokfast_websearch_candidate_packet_smoke.json"
    assert CANDIDATE_OUTPUT != EXACT_REVIEW_OUTPUT
