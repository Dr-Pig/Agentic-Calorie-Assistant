from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_manager_contract_probe import (
    build_websearch_manager_contract_probe,
)
from app.nutrition.application.websearch_manager_contract_repair_pack import (
    build_websearch_manager_contract_repair_pack,
)


def test_websearch_manager_contract_repair_pack_summarizes_contract_inputs() -> None:
    probe = build_websearch_manager_contract_probe()

    report = build_websearch_manager_contract_repair_pack(
        contract_probe_artifact=probe,
    )

    assert report["artifact_type"] == "accurate_intake_websearch_manager_contract_repair_pack"
    assert report["classification"] == "diagnostic_repair_pack_only"
    assert report["next_recommended_slice"] == "tighten_websearch_manager_contract_prompt_or_transport"
    assert report["manager_contract_changed"] is False
    assert report["prompt_changed"] is False
    assert report["schema_changed"] is False
    assert report["runtime_truth_changed"] is False
    assert report["summary"]["case_count"] == 2
    assert report["summary"]["aggregate_missing_required_fields"] == {"intent": 2}
    assert report["summary"]["shape_pattern_counts"]["intent_type_present_intent_missing"] == 2
    assert report["summary"]["alias_hint_counts"] == {"intent": 2}

    for case in report["cases"]:
        assert case["missing_required_fields"] == ["intent"]
        assert case["alias_hints"] == [
            {
                "expected_field": "intent",
                "observed_field": "intent_type",
            }
        ]
        assert case["recommended_owner"] == "manager_runtime_contract"


def test_websearch_manager_contract_repair_pack_sanitizes_raw_payload_fields() -> None:
    probe = {
        "artifact_type": "accurate_intake_websearch_manager_contract_probe",
        "summary": {"case_count": 1, "fail_count": 1, "next_recommended_slice": "probe"},
        "cases": [
            {
                "case_id": "case",
                "status": "fail",
                "failure_families": ["manager_output_contract_violation"],
                "observed_keys": [
                    "intent_type",
                    "source_url",
                    "raw_response_excerpt",
                    "candidate_packet_id",
                ],
                "missing_required_fields": ["intent"],
                "shape_patterns": ["intent_type_present_intent_missing"],
                "observed_manager_output": {"food_name": "invented"},
                "candidate_packet": {"source_url": "https://example.test"},
            }
        ],
    }

    report = build_websearch_manager_contract_repair_pack(contract_probe_artifact=probe)
    serialized = str(report)

    assert "source_url" not in serialized
    assert "raw_response_excerpt" not in serialized
    assert "candidate_packet_id" not in serialized
    assert "observed_manager_output" not in serialized
    assert "candidate_packet" not in serialized
    assert "invented" not in serialized
    assert report["cases"][0]["present_top_level_fields"] == ["intent_type"]
    assert report["cases"][0]["failure_families"] == [
        "manager_output_contract_violation"
    ]
    assert report["cases"][0]["shape_patterns"] == ["intent_type_present_intent_missing"]


def test_websearch_manager_contract_repair_pack_whitelists_untrusted_enums() -> None:
    probe = {
        "artifact_type": "accurate_intake_websearch_manager_contract_probe",
        "summary": {
            "case_count": 1,
            "fail_count": 1,
            "next_recommended_slice": "raw_response_excerpt forbidden",
        },
        "cases": [
            {
                "case_id": "raw_response_excerpt forbidden",
                "status": "raw_response_excerpt forbidden",
                "failure_families": ["manager_output_contract_violation", "raw_response_excerpt"],
                "observed_keys": ["intent_type"],
                "missing_required_fields": ["intent", "raw_response_excerpt"],
                "shape_patterns": ["intent_type_present_intent_missing", "raw_response_excerpt"],
                "validation_error_family": "raw_response_excerpt forbidden",
            }
        ],
    }

    report = build_websearch_manager_contract_repair_pack(contract_probe_artifact=probe)
    serialized = str(report)

    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized
    assert report["summary"]["probe_next_recommended_slice"] is None
    assert report["summary"]["status_counts"] == {"unknown": 1}
    assert report["summary"]["aggregate_missing_required_fields"] == {"intent": 1}
    assert report["cases"][0]["case_id"] == "case_001"
    assert report["cases"][0]["status"] == "unknown"
    assert report["cases"][0]["failure_families"] == [
        "manager_output_contract_violation"
    ]
    assert report["cases"][0]["validation_error_family"] is None


def test_websearch_manager_contract_repair_pack_pass_case_unblocks_live_diagnostic() -> None:
    probe = {
        "artifact_type": "accurate_intake_websearch_manager_contract_probe",
        "status": "pass",
        "summary": {
            "case_count": 1,
            "pass_count": 1,
            "fail_count": 0,
            "next_recommended_slice": "websearch_candidate_pipeline_narrow_expansion",
        },
        "cases": [
            {
                "case_id": "case",
                "status": "pass",
                "failure_families": [],
                "observed_keys": ["intent", "manager_action", "workflow_effect"],
                "missing_required_fields": [],
                "shape_patterns": [],
            }
        ],
    }

    report = build_websearch_manager_contract_repair_pack(contract_probe_artifact=probe)

    assert report["next_recommended_slice"] == "websearch_candidate_pipeline_narrow_expansion"
    assert report["summary"]["aggregate_missing_required_fields"] == {}
    assert report["summary"]["alias_hint_counts"] == {}


def test_websearch_manager_contract_repair_pack_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_manager_contract_repair_pack import main

    probe_path = tmp_path / "probe.json"
    output_path = tmp_path / "repair_pack.json"
    write_json_artifact(probe_path, build_websearch_manager_contract_probe())

    assert (
        main(
            [
                "--contract-probe-artifact",
                str(probe_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    report = read_json_artifact(output_path)
    assert report["artifact_type"] == "accurate_intake_websearch_manager_contract_repair_pack"
    assert report["summary"]["case_count"] == 2


def test_websearch_manager_contract_repair_pack_rejects_unexpected_source() -> None:
    try:
        build_websearch_manager_contract_repair_pack(
            contract_probe_artifact={"artifact_type": "wrong"}
        )
    except ValueError as exc:
        assert "unsupported_websearch_contract_repair_probe_source" in str(exc)
    else:
        raise AssertionError("unexpected probe artifact type must fail")


def test_websearch_manager_contract_repair_pack_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_manager_contract_repair_pack.py"),
        Path("scripts/build_accurate_intake_websearch_manager_contract_repair_pack.py"),
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
