from __future__ import annotations

from pathlib import Path

from app.nutrition.application.fooddb_manager_contract_probe import (
    build_fooddb_manager_contract_probe,
)


def _diagnostic_artifact() -> dict:
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "cases": [
            {
                "case_id": "boba_large_half_sugar",
                "status": "fail",
                "failure_families": [
                    "fooddb_packet_not_used",
                    "manager_did_not_finalize_after_packet",
                ],
                "provider_trace": {
                    "failure_family": "provider_response_error",
                    "trace": {
                        "missing_required_fields": ["intent"],
                        "decision_transport_mode": "synthetic_tool_transport",
                        "decision_transport_schema_name": "founder_live_manager_contract",
                        "decision_transport_schema_version": "v1",
                        "decision_transport_contract_breach": True,
                        "decision_transport_accepted": False,
                        "decision_transport_fallback_reason": "manager_payload_missing_required_fields",
                        "failing_component": "builderspace_runtime_contract.validate_manager_payload",
                        "effective_response_format_type": "json_schema",
                        "observed_type": "dict",
                        "parse_attempts": [
                            {
                                "error": "manager payload missing required fields for intake_manager_round: ['intent']"
                            }
                        ],
                    },
                },
            },
            {
                "case_id": "listed_luwei_components",
                "status": "fail",
                "failure_families": ["fooddb_packet_not_used"],
                "provider_trace": {
                    "failure_family": "provider_response_error",
                    "trace": {
                        "missing_required_fields": [
                            "confidence",
                            "exactness",
                            "intent",
                            "repair_ack",
                        ],
                        "decision_transport_mode": "synthetic_tool_transport",
                        "decision_transport_schema_name": "founder_live_manager_contract",
                        "decision_transport_schema_version": "v1",
                        "decision_transport_contract_breach": True,
                        "decision_transport_accepted": False,
                        "decision_transport_fallback_reason": "manager_payload_missing_required_fields",
                        "failing_component": "builderspace_runtime_contract.validate_manager_payload",
                        "effective_response_format_type": "json_schema",
                        "observed_type": "dict",
                        "parse_attempts": [
                            {
                                "error": "manager payload missing required fields for intake_manager_round: ['confidence', 'exactness', 'intent', 'repair_ack']"
                            }
                        ],
                    },
                },
            },
        ],
    }


def test_fooddb_manager_contract_probe_aggregates_missing_fields_and_transport() -> None:
    probe = build_fooddb_manager_contract_probe(diagnostic_artifact=_diagnostic_artifact())

    assert probe["artifact_type"] == "accurate_intake_fooddb_manager_contract_probe"
    assert probe["classification"] == "diagnostic_report_only"
    assert probe["claim_scope"] == "fooddb_manager_live_contract_probe"
    assert probe["source_live_provider_used"] is True
    assert probe["contract_failure_detected"] is True
    assert probe["readiness_claimed"] is False
    assert probe["next_recommended_slice"] == "tighten_fooddb_manager_contract_prompt_or_transport"
    assert probe["summary"]["contract_breach_count"] == 2
    assert probe["summary"]["decision_transport_accepted_count"] == 0
    assert probe["summary"]["aggregate_missing_required_fields"] == {
        "confidence": 1,
        "exactness": 1,
        "intent": 2,
        "repair_ack": 1,
    }
    assert probe["summary"]["decision_transport_modes"] == {"synthetic_tool_transport": 2}
    assert probe["summary"]["schema_names"] == {"founder_live_manager_contract": 2}
    assert probe["summary"]["schema_versions"] == {"v1": 2}
    assert probe["summary"]["fallback_reason_counts"] == {
        "manager_payload_missing_required_fields": 2
    }


def test_fooddb_manager_contract_probe_requires_explicit_live_run_if_source_not_live() -> None:
    artifact = _diagnostic_artifact()
    artifact["live_provider_used"] = False

    probe = build_fooddb_manager_contract_probe(diagnostic_artifact=artifact)

    assert probe["source_live_provider_used"] is False
    assert probe["next_recommended_slice"] == "run_explicit_grokfast_fooddb_packet_live_diagnostic"


def test_fooddb_manager_contract_probe_handles_non_contract_failures() -> None:
    artifact = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "cases": [
            {
                "case_id": "bare_luwei",
                "status": "fail",
                "failure_families": ["bare_basket_missing_followup"],
                "provider_trace": {
                    "trace": {
                        "decision_transport_mode": "synthetic_tool_transport",
                        "decision_transport_schema_name": "founder_live_manager_contract",
                        "decision_transport_schema_version": "v1",
                        "decision_transport_contract_breach": False,
                        "decision_transport_accepted": True,
                    }
                },
            }
        ],
    }

    probe = build_fooddb_manager_contract_probe(diagnostic_artifact=artifact)

    assert probe["contract_failure_detected"] is False
    assert probe["next_recommended_slice"] == "narrow_fooddb_packet_boundary_or_prompt_probe"
    assert probe["summary"]["decision_transport_accepted_count"] == 1


def test_fooddb_manager_contract_probe_parses_missing_fields_from_parse_attempt_errors() -> None:
    artifact = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "cases": [
            {
                "case_id": "case",
                "status": "fail",
                "failure_families": [],
                "provider_trace": {
                    "trace": {
                        "parse_attempts": [
                            {
                                "error": "manager payload missing required fields for intake_manager_round: ['intent', 'workflow_effect']"
                            }
                        ]
                    }
                },
            }
        ],
    }

    probe = build_fooddb_manager_contract_probe(diagnostic_artifact=artifact)

    assert probe["summary"]["aggregate_missing_required_fields"] == {
        "intent": 1,
        "workflow_effect": 1,
    }


def test_fooddb_manager_contract_probe_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_fooddb_manager_contract_probe import main

    input_path = tmp_path / "diagnostic.json"
    output_path = tmp_path / "probe.json"
    write_json_artifact(input_path, _diagnostic_artifact())

    assert main(["--diagnostic-artifact", str(input_path), "--output", str(output_path)]) == 0

    probe = read_json_artifact(output_path)
    assert probe["artifact_type"] == "accurate_intake_fooddb_manager_contract_probe"
    assert probe["summary"]["aggregate_missing_required_fields"]["intent"] == 2


def test_fooddb_manager_contract_probe_rejects_unexpected_source_artifact_type() -> None:
    artifact = {
        "artifact_type": "other_artifact",
        "status": "pass",
        "live_provider_used": True,
        "cases": [],
    }

    try:
        build_fooddb_manager_contract_probe(diagnostic_artifact=artifact)
    except ValueError as exc:
        assert "unsupported_fooddb_manager_contract_probe_source" in str(exc)
    else:
        raise AssertionError("unexpected source artifact type must fail")


def test_fooddb_manager_contract_probe_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/fooddb_manager_contract_probe.py"),
        Path("scripts/build_accurate_intake_fooddb_manager_contract_probe.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "requests.",
        "httpx.",
        "allow_live",
        "Tavily",
        "tavily",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
