from __future__ import annotations

from pathlib import Path

from app.nutrition.application.grokfast_websearch_packet_smoke import (
    build_fixture_grokfast_websearch_manager_outputs,
    build_grokfast_websearch_packet_diagnostic,
)
from app.nutrition.application.tool_evidence_result import build_tool_evidence_result
from app.nutrition.application.websearch_candidate_packet_smoke import (
    build_websearch_candidate_packet_smoke,
)
from app.nutrition.application.websearch_live_diagnostic_report import (
    build_websearch_live_diagnostic_report,
)
from app.nutrition.application.websearch_manager_packet_smoke import (
    build_websearch_manager_packet_projection,
)


def _manager_packet_artifact() -> dict:
    packet_artifact = build_websearch_candidate_packet_smoke()
    packets = tuple(case["websearch_candidate_packet"] for case in packet_artifact["cases"])
    tool_result = build_tool_evidence_result(
        tool_name="search_official_nutrition",
        tool_call_id="tool-call-websearch-live-report",
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


def test_websearch_live_diagnostic_report_blocks_expansion_after_provider_contract_failure() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "live_websearch_used": False,
        "summary": {
            "case_count": 4,
            "pass_count": 0,
            "fail_count": 4,
            "failure_families": [
                "provider_response_error",
                "websearch_candidate_not_used",
            ],
        },
        "cases": [
            {
                "case_id": "pkt_web_search_milksha_exact",
                "status": "fail",
                "failure_families": ["websearch_candidate_not_used"],
                "provider_trace": {
                    "trace_summary": {
                        "failure_family": "manager_output_contract_violation",
                        "failing_component": "builderspace_runtime_contract.validate_manager_payload",
                        "transport_attempt_count": 2,
                        "parse_attempt_count": 2,
                    }
                },
            }
        ],
    }

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["artifact_type"] == "accurate_intake_websearch_live_diagnostic_report"
    assert report["seam_status"] == "provider_contract_blocked"
    assert report["provider_contract_blocked"] is True
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["should_run_websearch_live_tool_loop"] is False
    assert report["next_recommended_slice"] == "narrow_grokfast_websearch_manager_contract_probe"
    assert report["readiness_claimed"] is False
    assert report["runtime_truth_changed"] is False


def test_websearch_live_diagnostic_report_distinguishes_post_contract_candidate_boundary_failures() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "live_websearch_used": False,
        "summary": {
            "case_count": 4,
            "pass_count": 0,
            "fail_count": 4,
            "failure_families": [
                "provider_response_error",
                "websearch_candidate_not_used",
                "websearch_weak_candidate_not_rejected",
            ],
        },
        "cases": [
            {
                "case_id": "pkt_web_search_milksha_exact",
                "status": "fail",
                "failure_families": ["websearch_candidate_not_used"],
                "provider_trace": {
                    "trace_summary": {
                        "structured_output_transport_mode": "json_schema",
                        "decision_transport_mode": "synthetic_tool_transport",
                        "decision_transport_attempted": True,
                        "decision_transport_contract_breach": False,
                        "schema_name": "founder_live_manager_contract",
                        "schema_version": "v1",
                    }
                },
            },
            {
                "case_id": "pkt_web_search_third_party_weak",
                "status": "fail",
                "failure_families": [
                    "provider_response_error",
                    "websearch_weak_candidate_not_rejected",
                ],
                "provider_trace": {
                    "failure_family": "provider_response_error",
                    "trace_summary": {
                        "failing_component": "builderspace_adapter.complete_with_trace",
                        "structured_output_transport_mode": "json_schema",
                        "decision_transport_mode": "synthetic_tool_transport",
                        "decision_transport_attempted": True,
                        "decision_transport_contract_breach": False,
                        "schema_name": "founder_live_manager_contract",
                        "schema_version": "v1",
                    },
                },
            },
        ],
    }

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "candidate_boundary_blocked"
    assert report["provider_contract_blocked"] is False
    assert report["provider_runtime_residual_blocked"] is True
    assert report["candidate_boundary_blocked"] is True
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["next_recommended_slice"] == "narrow_websearch_packet_boundary_or_prompt_probe"
    assert report["contract_transport"]["healthy"] is True
    assert report["contract_transport"]["healthy_case_count"] == 2
    assert report["contract_transport"]["observed_decision_transport_modes"] == [
        "synthetic_tool_transport"
    ]
    assert report["contract_transport"]["observed_schema_names"] == [
        "founder_live_manager_contract"
    ]


def test_websearch_live_diagnostic_report_treats_fixture_pass_as_live_not_checked() -> None:
    packet_artifact = _manager_packet_artifact()
    diagnostic = build_grokfast_websearch_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=build_fixture_grokfast_websearch_manager_outputs(
            packet_artifact=packet_artifact
        ),
        live_provider_used=False,
    )

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["source_status"] == "pass"
    assert report["source_live_provider_used"] is False
    assert report["seam_status"] == "fixture_only_live_not_checked"
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["next_recommended_slice"] == "run_explicit_grokfast_websearch_packet_live_diagnostic"


def test_websearch_live_diagnostic_report_sanitizes_raw_payloads_from_source_artifact() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "live_websearch_used": False,
        "summary": {"case_count": 1, "pass_count": 0, "fail_count": 1, "failure_families": []},
        "cases": [
            {
                "case_id": "case",
                "status": "fail",
                "failure_families": ["websearch_truth_shortcut"],
                "manager_output": {
                    "exact_card_truth": {"kcal": 123},
                    "item_results": [{"food_name": "invented", "likely_kcal": 123}],
                },
                "provider_trace": {
                    "trace_summary": {
                        "failure_family": "manager_output_contract_violation",
                    },
                    "raw_response_excerpt": "snippet exact_card_truth likely_kcal",
                    "parsed_object": {"runtime_truth_allowed": True},
                },
            }
        ],
    }

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert not _contains_key(report, "manager_output")
    assert not _contains_key(report, "raw_response_excerpt")
    assert not _contains_key(report, "parsed_object")
    assert not _contains_key(report, "food_name")
    assert not _contains_key(report, "likely_kcal")
    assert not _contains_key(report, "runtime_truth_allowed")
    assert "invented" not in _scalar_values(report)
    assert "websearch_truth_shortcut" in report["failure_matrix"]["failure_counts"]
    assert "manager_output_contract_violation" in report["failure_matrix"]["failure_counts"]


def test_websearch_live_diagnostic_report_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_live_diagnostic_report import main

    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "live_websearch_used": False,
        "summary": {
            "case_count": 4,
            "pass_count": 0,
            "fail_count": 4,
            "failure_families": ["provider_response_error"],
        },
        "cases": [],
    }
    input_path = tmp_path / "diagnostic.json"
    output_path = tmp_path / "report.json"
    write_json_artifact(input_path, diagnostic)

    assert main(["--diagnostic-artifact", str(input_path), "--output", str(output_path)]) == 0

    report = read_json_artifact(output_path)
    assert report["seam_status"] == "provider_contract_blocked"
    assert report["source_live_websearch_used"] is False
    assert report["should_run_websearch_live_tool_loop"] is False


def test_websearch_live_diagnostic_report_rejects_unexpected_source_artifact_type() -> None:
    diagnostic = {
        "artifact_type": "some_other_artifact",
        "status": "pass",
        "live_provider_used": True,
        "live_websearch_used": False,
        "summary": {"case_count": 0, "pass_count": 0, "fail_count": 0, "failure_families": []},
        "cases": [],
    }

    try:
        build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)
    except ValueError as exc:
        assert "unsupported_websearch_live_diagnostic_artifact_type" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("unexpected source artifact type must fail")


def test_websearch_live_diagnostic_report_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_live_diagnostic_report.py"),
        Path("scripts/build_accurate_intake_websearch_live_diagnostic_report.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "Tavily",
        "tavily",
        "requests.",
        "httpx.",
        "allow_live",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source


def _contains_key(value: object, target_key: str) -> bool:
    if isinstance(value, dict):
        return target_key in value or any(_contains_key(child, target_key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, target_key) for item in value)
    return False


def _scalar_values(value: object) -> set[str]:
    if isinstance(value, dict):
        return {item for child in value.values() for item in _scalar_values(child)}
    if isinstance(value, list):
        return {item for child in value for item in _scalar_values(child)}
    return {str(value)}
