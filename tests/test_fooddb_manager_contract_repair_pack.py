from __future__ import annotations

from pathlib import Path

from app.nutrition.application.fooddb_manager_contract_repair_pack import (
    build_fooddb_manager_contract_repair_pack,
)


def test_fooddb_manager_contract_repair_pack_summarizes_contract_inputs() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "cases": [
            {
                "case_id": "boba",
                "failure_families": ["fooddb_packet_not_used"],
                "provider_trace": {
                    "trace": {
                        "parsed_object": {
                            "intent_type": "log_food_consumption",
                            "workflow_effect": "ask_followup",
                            "target_attachment": {},
                            "confidence": "medium",
                        }
                    }
                },
            },
            {
                "case_id": "listed",
                "failure_families": ["manager_did_not_finalize_after_packet"],
                "provider_trace": {
                    "trace": {
                        "parsed_object": {
                            "intent_type": "log_food_consumption",
                            "evidence_source": "packet_only",
                        }
                    }
                },
            },
        ],
    }
    probe = {
        "artifact_type": "accurate_intake_fooddb_manager_contract_probe",
        "summary": {
            "aggregate_missing_required_fields": {
                "intent": 2,
                "evidence_posture": 1,
            }
        },
        "cases": [
            {
                "case_id": "boba",
                "missing_required_fields": ["intent"],
                "failing_component": "builderspace_runtime_contract.validate_manager_payload",
                "effective_response_format_type": "json_object",
                "decision_transport_mode": None,
            },
            {
                "case_id": "listed",
                "missing_required_fields": ["intent", "evidence_posture"],
                "failing_component": "builderspace_runtime_contract.validate_manager_payload",
                "effective_response_format_type": "json_object",
                "decision_transport_mode": None,
            },
        ],
    }

    report = build_fooddb_manager_contract_repair_pack(
        diagnostic_artifact=diagnostic,
        contract_probe_artifact=probe,
    )

    assert report["artifact_type"] == "accurate_intake_fooddb_manager_contract_repair_pack"
    assert report["classification"] == "diagnostic_repair_pack_only"
    assert report["next_recommended_slice"] == "tighten_fooddb_manager_contract_prompt_or_transport"
    assert report["summary"]["case_count"] == 2
    assert report["summary"]["aggregate_missing_required_fields"] == {
        "intent": 2,
        "evidence_posture": 1,
    }
    assert report["summary"]["present_field_counts"]["intent_type"] == 2
    assert report["summary"]["alias_hint_counts"] == {
        "evidence_posture": 1,
        "intent": 2,
    }
    assert report["summary"]["probe_match_status_counts"] == {"matched_probe_case": 2}
    assert report["summary"]["trace_status_counts"] == {"trace_present": 2}
    listed = next(case for case in report["cases"] if case["case_id"] == "listed")
    assert listed["alias_hints"] == [
        {
            "expected_field": "intent",
            "observed_field": "intent_type",
        },
        {
            "expected_field": "evidence_posture",
            "observed_field": "evidence_source",
        },
    ]
    assert listed["probe_match_status"] == "matched_probe_case"
    assert listed["trace_status"] == "trace_present"


def test_fooddb_manager_contract_repair_pack_sanitizes_raw_payload_fields() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "cases": [
            {
                "case_id": "case",
                "failure_families": ["fooddb_packet_not_used"],
                "provider_trace": {
                    "trace": {
                        "parsed_object": {
                            "intent_type": "log_food_consumption",
                            "food_name": "珍珠奶茶",
                        },
                        "raw_response_excerpt": "should not survive",
                    }
                },
                "manager_output": {"food_name": "invented"},
            }
        ],
    }
    probe = {
        "artifact_type": "accurate_intake_fooddb_manager_contract_probe",
        "summary": {"aggregate_missing_required_fields": {"intent": 1}},
        "cases": [
            {
                "case_id": "case",
                "missing_required_fields": ["intent"],
                "failing_component": "builderspace_runtime_contract.validate_manager_payload",
                "effective_response_format_type": "json_object",
                "decision_transport_mode": None,
            }
        ],
    }

    report = build_fooddb_manager_contract_repair_pack(
        diagnostic_artifact=diagnostic,
        contract_probe_artifact=probe,
    )

    assert not _contains_key(report, "raw_response_excerpt")
    assert not _contains_key(report, "manager_output")
    assert not _contains_key(report, "food_name")
    assert "珍珠奶茶" not in _scalar_values(report)
    assert "invented" not in _scalar_values(report)


def test_fooddb_manager_contract_repair_pack_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_fooddb_manager_contract_repair_pack import main

    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "cases": [
            {
                "case_id": "case",
                "failure_families": ["manager_did_not_finalize_after_packet"],
                "provider_trace": {
                    "trace": {
                        "parsed_object": {
                            "intent_type": "log_food_consumption",
                        }
                    }
                },
            }
        ],
    }
    probe = {
        "artifact_type": "accurate_intake_fooddb_manager_contract_probe",
        "summary": {"aggregate_missing_required_fields": {"intent": 1}},
        "cases": [
            {
                "case_id": "case",
                "missing_required_fields": ["intent"],
                "failing_component": "builderspace_runtime_contract.validate_manager_payload",
                "effective_response_format_type": "json_object",
                "decision_transport_mode": None,
            }
        ],
    }
    diagnostic_path = tmp_path / "diagnostic.json"
    probe_path = tmp_path / "probe.json"
    output_path = tmp_path / "repair_pack.json"
    write_json_artifact(diagnostic_path, diagnostic)
    write_json_artifact(probe_path, probe)

    assert (
        main(
            [
                "--diagnostic-artifact",
                str(diagnostic_path),
                "--contract-probe-artifact",
                str(probe_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    report = read_json_artifact(output_path)
    assert report["artifact_type"] == "accurate_intake_fooddb_manager_contract_repair_pack"
    assert report["summary"]["case_count"] == 1


def test_fooddb_manager_contract_repair_pack_flags_missing_probe_match() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "cases": [
            {
                "case_id": "orphan-case",
                "failure_families": ["provider_response_error"],
                "provider_trace": {"trace": {"parsed_object": {"intent_type": "log_food_consumption"}}},
            }
        ],
    }
    probe = {
        "artifact_type": "accurate_intake_fooddb_manager_contract_probe",
        "summary": {"aggregate_missing_required_fields": {}},
        "cases": [],
    }

    report = build_fooddb_manager_contract_repair_pack(
        diagnostic_artifact=diagnostic,
        contract_probe_artifact=probe,
    )

    assert report["next_recommended_slice"] == "repair_artifact_alignment_required"
    assert report["summary"]["probe_match_status_counts"] == {"missing_probe_case": 1}
    assert report["cases"][0]["probe_match_status"] == "missing_probe_case"
    assert report["cases"][0]["missing_required_fields"] == []


def test_fooddb_manager_contract_repair_pack_accepts_flat_live_provider_trace_shape() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "cases": [
            {
                "case_id": "live-flat-trace",
                "failure_families": ["manager_contract_required_fields_missing"],
                "provider_trace": {
                    "parsed_object": {
                        "intent_type": "log_food_consumption",
                        "evidence_source": "packet_only",
                    }
                },
            }
        ],
    }
    probe = {
        "artifact_type": "accurate_intake_fooddb_manager_contract_probe",
        "summary": {"aggregate_missing_required_fields": {"intent": 1, "evidence_posture": 1}},
        "cases": [
            {
                "case_id": "live-flat-trace",
                "missing_required_fields": ["intent", "evidence_posture"],
                "failing_component": "builderspace_runtime_contract.validate_manager_payload",
                "effective_response_format_type": "json_schema",
                "decision_transport_mode": None,
            }
        ],
    }

    report = build_fooddb_manager_contract_repair_pack(
        diagnostic_artifact=diagnostic,
        contract_probe_artifact=probe,
    )

    assert report["next_recommended_slice"] == "tighten_fooddb_manager_contract_prompt_or_transport"
    assert report["summary"]["trace_status_counts"] == {"trace_present": 1}
    assert report["summary"]["alias_hint_counts"] == {
        "evidence_posture": 1,
        "intent": 1,
    }
    assert report["cases"][0]["present_top_level_fields"] == ["evidence_source", "intent_type"]


def test_fooddb_manager_contract_repair_pack_extracts_fields_from_stringified_parsed_object() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "cases": [
            {
                "case_id": "stringified-trace",
                "failure_families": ["manager_contract_schema_validation_failed"],
                "provider_trace": {
                    "trace": {
                        "parsed_object": "{\"intent_type\": \"log_food_consumption\", \"evidence_source\": \"packet_only\"}"
                    }
                },
            }
        ],
    }
    probe = {
        "artifact_type": "accurate_intake_fooddb_manager_contract_probe",
        "summary": {"aggregate_missing_required_fields": {"intent": 1, "evidence_posture": 1}},
        "cases": [
            {
                "case_id": "stringified-trace",
                "missing_required_fields": ["intent", "evidence_posture"],
                "failing_component": "builderspace_adapter.extract_json_object",
                "effective_response_format_type": "json_schema",
                "decision_transport_mode": None,
            }
        ],
    }

    report = build_fooddb_manager_contract_repair_pack(
        diagnostic_artifact=diagnostic,
        contract_probe_artifact=probe,
    )

    assert report["next_recommended_slice"] == "tighten_fooddb_manager_contract_prompt_or_transport"
    assert report["summary"]["present_field_counts"] == {
        "evidence_source": 1,
        "intent_type": 1,
    }
    assert report["cases"][0]["present_top_level_fields"] == ["evidence_source", "intent_type"]


def test_fooddb_manager_contract_repair_pack_preserves_missing_trace_cases() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "cases": [
            {
                "case_id": "missing-trace",
                "failure_families": ["provider_response_error"],
                "provider_trace": {},
            }
        ],
    }
    probe = {
        "artifact_type": "accurate_intake_fooddb_manager_contract_probe",
        "summary": {"aggregate_missing_required_fields": {"intent": 1}},
        "cases": [
            {
                "case_id": "missing-trace",
                "missing_required_fields": ["intent"],
                "failing_component": "builderspace_runtime_contract.validate_manager_payload",
                "effective_response_format_type": "json_object",
                "decision_transport_mode": None,
            }
        ],
    }

    report = build_fooddb_manager_contract_repair_pack(
        diagnostic_artifact=diagnostic,
        contract_probe_artifact=probe,
    )

    assert report["next_recommended_slice"] == "repair_artifact_alignment_required"
    assert report["summary"]["trace_status_counts"] == {"missing_provider_trace": 1}
    assert report["summary"]["case_count"] == 1
    assert report["cases"][0]["trace_status"] == "missing_provider_trace"
    assert report["cases"][0]["present_top_level_fields"] == []


def test_fooddb_manager_contract_repair_pack_rejects_unexpected_sources() -> None:
    diagnostic = {"artifact_type": "unexpected"}
    probe = {"artifact_type": "accurate_intake_fooddb_manager_contract_probe", "cases": [], "summary": {}}

    try:
        build_fooddb_manager_contract_repair_pack(
            diagnostic_artifact=diagnostic,
            contract_probe_artifact=probe,
        )
    except ValueError as exc:
        assert "unsupported_fooddb_contract_repair_diagnostic_source" in str(exc)
    else:
        raise AssertionError("unexpected diagnostic artifact type must fail")

    good_diagnostic = {"artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke", "cases": []}
    bad_probe = {"artifact_type": "wrong"}
    try:
        build_fooddb_manager_contract_repair_pack(
            diagnostic_artifact=good_diagnostic,
            contract_probe_artifact=bad_probe,
        )
    except ValueError as exc:
        assert "unsupported_fooddb_contract_repair_probe_source" in str(exc)
    else:
        raise AssertionError("unexpected probe artifact type must fail")


def test_fooddb_manager_contract_repair_pack_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/fooddb_manager_contract_repair_pack.py"),
        Path("scripts/build_accurate_intake_fooddb_manager_contract_repair_pack.py"),
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
