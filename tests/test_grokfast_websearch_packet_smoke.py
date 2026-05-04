from __future__ import annotations

from pathlib import Path

from app.nutrition.application.grokfast_websearch_packet_smoke import (
    GROKFAST_WEBSEARCH_PACKET_PROFILE,
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
)


def _manager_packet_artifact() -> dict:
    packet_artifact = build_websearch_candidate_packet_smoke()
    packets = tuple(case["websearch_candidate_packet"] for case in packet_artifact["cases"])
    tool_result = build_tool_evidence_result(
        tool_name="search_official_nutrition",
        tool_call_id="tool-call-grokfast-websearch-smoke",
        evidence_packets=packets,
        trace_context={
            "packet_artifact_type": packet_artifact["artifact_type"],
            "packet_claim_scope": packet_artifact["claim_scope"],
            "live_websearch_used": False,
        },
    )
    return build_websearch_manager_packet_projection(
        tool_evidence_artifact={
            "artifact_type": "accurate_intake_websearch_tool_evidence_result_smoke",
            "tool_evidence_result": tool_result,
        }
    )


def test_grokfast_websearch_packet_diagnostic_classifies_fixture_outputs() -> None:
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
    assert diagnostic["classification"] == "live_diagnostic_only"
    assert diagnostic["status"] == "pass"
    assert diagnostic["live_provider_used"] is False
    assert diagnostic["live_websearch_used"] is False
    assert diagnostic["websearch_runtime_truth_allowed"] is False
    assert diagnostic["readiness_claimed"] is False
    assert diagnostic["self_use_approved"] is False
    assert diagnostic["production_selected"] is False
    assert diagnostic["summary"]["case_count"] == 4
    assert diagnostic["summary"]["pass_count"] == 4
    assert diagnostic["provider_profile"]["model"] == "grok-4-fast"


def test_grokfast_websearch_packet_diagnostic_reuses_candidate_boundary_evaluator() -> None:
    packet_artifact = _manager_packet_artifact()
    packet_case = packet_artifact["cases"][0]
    diagnostic = build_grokfast_websearch_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=[
            {
                "case_id": packet_case["case_id"],
                "manager_output": {
                    "manager_action": "final",
                    "final_action": "commit",
                    "workflow_effect": "food_log_candidate",
                    "target_attachment": {"candidate_id": packet_case["case_id"]},
                    "tool_calls": [{"name": "write_ledger"}],
                    "item_results": [{"food_name": "invented", "likely_kcal": 1}],
                    "evidence_used": [f"{packet_case['case_id']} plus invented truth"],
                    "semantic_decision": {"mutation_intent_candidate": "canonical_write"},
                },
                "provider_trace": {
                    "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"],
                },
            }
        ],
        live_provider_used=True,
    )

    failure_families = diagnostic["summary"]["failure_families"]
    assert diagnostic["status"] == "diagnostic_fail"
    assert diagnostic["live_provider_used"] is True
    assert "websearch_truth_shortcut" in failure_families
    assert "websearch_truth_surface_leak" in failure_families
    assert "invented_websearch_evidence_reference" in failure_families
    assert "websearch_candidate_mutated_runtime" in failure_families
    assert "websearch_candidate_created_item_results" in failure_families


def test_grokfast_websearch_packet_diagnostic_sanitizes_manager_output_and_provider_trace() -> None:
    packet_artifact = _manager_packet_artifact()
    packet_case = packet_artifact["cases"][0]
    diagnostic = build_grokfast_websearch_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=[
            {
                "case_id": packet_case["case_id"],
                "manager_output": {
                    "manager_action": "final",
                    "final_action": "commit",
                    "workflow_effect": "food_log_candidate",
                    "target_attachment": {"candidate_id": packet_case["case_id"]},
                    "tool_calls": [{"name": "write_ledger"}],
                    "item_results": [{"food_name": "invented", "likely_kcal": 1}],
                    "evidence_used": [f"{packet_case['case_id']} plus invented truth"],
                    "semantic_decision": {"mutation_intent_candidate": "canonical_write"},
                },
                "provider_trace": {
                    "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"],
                    "trace": {
                        "parsed_object": {"exact_card_truth": {"kcal": 1}},
                        "raw_response_excerpt": "exact_card_truth and item_results should not persist",
                        "transport_attempts": [{"raw": "payload"}],
                        "parse_attempts": [{"raw_content_excerpt": "snippet"}],
                        "failure_family": "manager_output_contract_violation",
                    },
                },
            }
        ],
        live_provider_used=True,
    )

    case_payload = diagnostic["cases"][0]
    serialized = str(case_payload)
    assert "manager_output" not in case_payload
    assert "parsed_object" not in serialized
    assert "raw_response_excerpt" not in serialized
    assert "raw_content_excerpt" not in serialized
    assert "exact_card_truth" not in serialized
    assert "food_name" not in serialized
    assert "likely_kcal" not in serialized
    assert "write_ledger" not in serialized
    assert "websearch_candidate_created_item_results" in case_payload["failure_families"]
    assert case_payload["provider_trace"]["trace_summary"]["transport_attempt_count"] == 1
    assert case_payload["provider_trace"]["trace_summary"]["parse_attempt_count"] == 1


def test_grokfast_websearch_packet_diagnostic_surfaces_provider_failures() -> None:
    packet_artifact = _manager_packet_artifact()
    packet_case = packet_artifact["cases"][0]
    diagnostic = build_grokfast_websearch_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=[
            {
                "case_id": packet_case["case_id"],
                "manager_output": {},
                "provider_trace": {
                    "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"],
                    "failure_family": "provider_response_error",
                },
            }
        ],
        live_provider_used=True,
    )

    assert diagnostic["status"] == "diagnostic_fail"
    assert "provider_response_error" in diagnostic["summary"]["failure_families"]


def test_grokfast_websearch_packet_diagnostic_summarizes_success_transport_metadata() -> None:
    packet_artifact = _manager_packet_artifact()
    packet_case = packet_artifact["cases"][0]
    manager_outputs = build_fixture_grokfast_websearch_manager_outputs(
        packet_artifact=packet_artifact
    )
    manager_outputs[0]["provider_trace"].update(
        {
            "structured_output_transport_mode": "json_schema",
            "decision_transport_mode": "synthetic_tool_transport",
            "decision_transport_attempted": True,
            "decision_transport_contract_breach": False,
            "schema_name": "founder_live_manager_contract",
            "schema_version": "v1",
            "transport_attempts": [{"attempt": 1}],
            "parse_attempts": [{"attempt": 1}],
        }
    )

    diagnostic = build_grokfast_websearch_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=[manager_outputs[0]],
        live_provider_used=True,
    )

    trace_summary = diagnostic["cases"][0]["provider_trace"]["trace_summary"]
    assert diagnostic["cases"][0]["case_id"] == packet_case["case_id"]
    assert trace_summary["structured_output_transport_mode"] == "json_schema"
    assert trace_summary["decision_transport_mode"] == "synthetic_tool_transport"
    assert trace_summary["decision_transport_attempted"] is True
    assert trace_summary["decision_transport_contract_breach"] is False
    assert trace_summary["schema_name"] == "founder_live_manager_contract"
    assert trace_summary["schema_version"] == "v1"
    assert trace_summary["transport_attempt_count"] == 1
    assert trace_summary["parse_attempt_count"] == 1
    assert "transport_attempts" not in str(diagnostic["cases"][0])
    assert "parse_attempts" not in str(diagnostic["cases"][0])


def test_grokfast_websearch_live_payload_is_candidate_only_and_compact() -> None:
    packet_case = _manager_packet_artifact()["cases"][0]
    payload = build_live_websearch_manager_payload(packet_case=packet_case)

    assert payload["diagnostic_scope"] == "websearch_packet_manager_seam_smoke"
    assert payload["constraints"]["websearch_runtime_truth_allowed"] is False
    assert payload["constraints"]["runtime_mutation_allowed"] is False
    assert payload["websearch_evidence_packet"]["packet_type"] == "websearch_manager_evidence_packet_v1"
    payload_text = str(payload)
    assert "websearch_candidate_packet" not in payload_text
    assert "tavily_score" not in payload_text
    assert "snippet" not in payload_text
    assert "storage_backend" not in payload_text


def test_grokfast_websearch_live_script_adds_manager_contract_constraints() -> None:
    from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import (
        _build_live_manager_payload_with_contract,
    )

    packet_case = _manager_packet_artifact()["cases"][0]
    payload = _build_live_manager_payload_with_contract(packet_case=packet_case)

    constraints = payload["constraints"]
    assert constraints["manager_contract_profile_id"] == "founder_live_contract"
    assert constraints["manager_contract_transport_policy"] == "synthetic_tool_transport"
    assert constraints["manager_contract_provider_profile_id"] == (
        GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"]
    )
    assert constraints["websearch_packet_smoke"] is True
    assert constraints["websearch_runtime_truth_allowed"] is False
    assert constraints["runtime_mutation_allowed"] is False
    assert constraints["manager_contract_evidence_state"]["nutrition_evidence_present"] is False
    assert payload["manager_contract_diagnostic"]["runtime_truth_changed"] is False
    assert "manager_contract_policy" in constraints


def test_grokfast_websearch_packet_smoke_cli_defaults_to_fixture_and_blocks_accidental_live(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import main

    packet_path = tmp_path / "websearch_manager_packet.json"
    output = tmp_path / "grokfast_websearch.json"
    write_json_artifact(packet_path, _manager_packet_artifact())

    assert (
        main(["--mode", "fixture", "--manager-packet-artifact", str(packet_path), "--output", str(output)])
        == 0
    )
    artifact = read_json_artifact(output)
    assert artifact["status"] == "pass"
    assert artifact["live_provider_used"] is False
    assert artifact["summary"]["pass_count"] == 4

    blocked_output = tmp_path / "blocked_live.json"
    assert (
        main(
            [
                "--mode",
                "live",
                "--manager-packet-artifact",
                str(packet_path),
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


def test_grokfast_websearch_packet_smoke_keeps_kimi_and_tavily_out_of_module() -> None:
    source_paths = [
        Path("app/nutrition/application/grokfast_websearch_packet_smoke.py"),
        Path("scripts/run_accurate_intake_grokfast_websearch_packet_smoke.py"),
    ]
    forbidden = [
        "kimi-k2.5",
        "Tavily",
        "tavily",
        "requests.",
        "httpx.",
    ]

    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
