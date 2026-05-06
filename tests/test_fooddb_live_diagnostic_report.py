from __future__ import annotations

from pathlib import Path

from app.nutrition.application.fooddb_live_diagnostic_report import (
    build_fooddb_live_diagnostic_report,
)
from app.nutrition.application.grokfast_fooddb_packet_smoke import (
    build_fixture_manager_outputs,
    build_grokfast_fooddb_packet_diagnostic,
)
from app.nutrition.application.fooddb_manager_packet_smoke import (
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.fooddb_retrieval_policy import (
    build_runtime_retrieval_records_from_small_anchor_payload,
)
import json


def _packet_artifact() -> dict:
    payload = json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))
    records = build_runtime_retrieval_records_from_small_anchor_payload(payload)
    return build_fooddb_manager_packet_smoke(retrieval_records=records)


def test_fooddb_live_diagnostic_report_treats_fixture_pass_as_live_not_checked() -> None:
    diagnostic = build_grokfast_fooddb_packet_diagnostic(
        packet_artifact=_packet_artifact(),
        manager_outputs=build_fixture_manager_outputs(packet_artifact=_packet_artifact()),
        live_provider_used=False,
    )

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["artifact_type"] == "accurate_intake_fooddb_live_diagnostic_report"
    assert report["source_status"] == "pass"
    assert report["source_live_provider_used"] is False
    assert report["seam_status"] == "fixture_only_live_not_checked"
    assert report["can_expand_to_websearch_live_diagnostic"] is False
    assert report["next_recommended_slice"] == "run_explicit_grokfast_fooddb_packet_live_diagnostic"
    assert "no_live_provider_call" in report["non_claims"]


def test_fooddb_live_diagnostic_report_blocks_provider_contract_failures() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "summary": {
            "case_count": 5,
            "pass_count": 0,
            "fail_count": 5,
            "failure_families": ["provider_response_error"],
        },
        "cases": [
            {
                "case_id": "boba_large_half_sugar",
                "status": "fail",
                "failure_families": [],
                "provider_trace": {
                    "failure_family": "provider_response_error",
                    "trace": {"failure_family": "manager_output_contract_violation"},
                },
            }
        ],
    }

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "provider_contract_blocked"
    assert report["provider_contract_blocked"] is True
    assert report["packet_boundary_blocked"] is False
    assert report["next_recommended_slice"] == "narrow_grokfast_fooddb_manager_contract_probe"


def test_fooddb_live_diagnostic_report_distinguishes_packet_boundary_failures() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "summary": {
            "case_count": 5,
            "pass_count": 0,
            "fail_count": 5,
            "failure_families": [
                "fooddb_packet_not_used",
                "generic_meal_overclaimed_exact",
            ],
        },
        "cases": [
            {
                "case_id": "chicken_bento_less_rice",
                "status": "fail",
                "failure_families": [
                    "fooddb_packet_not_used",
                    "generic_meal_overclaimed_exact",
                ],
                "provider_trace": {},
            }
        ],
    }

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "packet_boundary_blocked"
    assert report["provider_contract_blocked"] is False
    assert report["packet_boundary_blocked"] is True
    assert report["next_recommended_slice"] == "narrow_fooddb_packet_boundary_or_prompt_probe"


def test_fooddb_live_diagnostic_report_treats_modifier_adjustment_misuse_as_packet_boundary_failure() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "summary": {
            "case_count": 5,
            "pass_count": 4,
            "fail_count": 1,
            "failure_families": ["modifier_adjusted_kcal_without_packet_adjustment"],
        },
        "cases": [
            {
                "case_id": "chicken_bento_less_rice",
                "status": "fail",
                "failure_families": ["modifier_adjusted_kcal_without_packet_adjustment"],
                "provider_trace": {},
            }
        ],
    }

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "packet_boundary_blocked"
    assert report["packet_boundary_blocked"] is True
    assert report["next_recommended_slice"] == "narrow_fooddb_packet_boundary_or_prompt_probe"


def test_fooddb_live_diagnostic_report_advances_to_websearch_only_after_live_pass() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "summary": {
            "case_count": 5,
            "pass_count": 5,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [],
    }

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "live_diagnostic_pass"
    assert report["can_expand_to_websearch_live_diagnostic"] is True
    assert report["next_recommended_slice"] == "grokfast_websearch_packet_live_diagnostic"
    assert report["readiness_claimed"] is False
    assert "no_live_provider_call" not in report["non_claims"]


def test_fooddb_live_diagnostic_report_sanitizes_raw_payloads() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "summary": {"case_count": 1, "pass_count": 0, "fail_count": 1, "failure_families": []},
        "cases": [
            {
                "case_id": "case",
                "status": "fail",
                "failure_families": ["invented_evidence_reference"],
                "manager_output": {
                    "item_results": [{"food_name": "invented", "likely_kcal": 123}],
                    "evidence_used": ["fake_anchor"],
                },
                "provider_trace": {
                    "raw_response_excerpt": "invented fake_anchor likely_kcal",
                    "parsed_object": {"runtime_truth_allowed": True},
                },
            }
        ],
    }

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert not _contains_key(report, "manager_output")
    assert not _contains_key(report, "raw_response_excerpt")
    assert not _contains_key(report, "parsed_object")
    assert not _contains_key(report, "food_name")
    assert not _contains_key(report, "likely_kcal")
    assert "invented" not in _scalar_values(report)
    assert "fake_anchor" not in _scalar_values(report)


def test_fooddb_live_diagnostic_report_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_fooddb_live_diagnostic_report import main

    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "summary": {
            "case_count": 5,
            "pass_count": 5,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [],
    }
    input_path = tmp_path / "diagnostic.json"
    output_path = tmp_path / "report.json"
    write_json_artifact(input_path, diagnostic)

    assert main(["--diagnostic-artifact", str(input_path), "--output", str(output_path)]) == 0

    report = read_json_artifact(output_path)
    assert report["seam_status"] == "live_diagnostic_pass"
    assert report["next_recommended_slice"] == "grokfast_websearch_packet_live_diagnostic"


def test_fooddb_live_diagnostic_report_rejects_unexpected_source_artifact_type() -> None:
    diagnostic = {
        "artifact_type": "some_other_artifact",
        "status": "pass",
        "live_provider_used": True,
        "summary": {"case_count": 0, "pass_count": 0, "fail_count": 0, "failure_families": []},
        "cases": [],
    }

    try:
        build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)
    except ValueError as exc:
        assert "unsupported_fooddb_live_diagnostic_artifact_type" in str(exc)
    else:
        raise AssertionError("unexpected source artifact type must fail")


def test_fooddb_live_diagnostic_report_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/fooddb_live_diagnostic_report.py"),
        Path("scripts/build_accurate_intake_fooddb_live_diagnostic_report.py"),
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
