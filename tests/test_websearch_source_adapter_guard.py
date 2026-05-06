from __future__ import annotations

from pathlib import Path

from app.nutrition.application.web_search_candidate_producer import (
    MAX_WEBSEARCH_RESULTS_HARD_CAP,
    bounded_websearch_max_results,
)
from app.nutrition.application.websearch_source_adapter_guard import (
    FORBIDDEN_PROVIDER_TRUTH_FIELDS,
    build_websearch_source_adapter_guard,
)


def _case_by_id(artifact: dict, case_id: str) -> dict:
    return {case["case_id"]: case for case in artifact["cases"]}[case_id]


def test_websearch_source_adapter_guard_passes_without_live_or_truth_claims() -> None:
    artifact = build_websearch_source_adapter_guard()

    assert artifact["artifact_type"] == "accurate_intake_websearch_source_adapter_guard_v1"
    assert artifact["classification"] == "deterministic_source_adapter_guard_only"
    assert artifact["status"] == "pass"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["case_count"] == 3
    assert artifact["summary"]["truth_field_leak_count"] == 0
    assert artifact["summary"]["max_results_hard_cap"] == 20
    assert artifact["next_required_slice"] == "websearch_candidate_lane_status_packet"


def test_websearch_source_adapter_guard_ignores_raw_provider_truth_fields() -> None:
    artifact = build_websearch_source_adapter_guard()
    case = _case_by_id(artifact, "raw_provider_truth_fields_ignored")

    assert case["status"] == "pass"
    assert case["truth_field_violations"] == []
    assert case["checks"]["raw_fields_filtered_ok"] is True
    assert case["checks"]["candidate_only_source_type"] is True
    assert case["checks"]["candidate_payload_present"] is True
    assert FORBIDDEN_PROVIDER_TRUTH_FIELDS


def test_websearch_source_adapter_guard_degrades_malformed_optional_fields() -> None:
    artifact = build_websearch_source_adapter_guard()
    case = _case_by_id(artifact, "malformed_optional_fields_degraded")

    assert case["status"] == "pass"
    assert case["checks"]["source_title_degraded"] is True
    assert case["checks"]["score_degraded"] is True
    assert case["checks"]["quality_degraded"] is True
    assert case["checks"]["identity_confidence_degraded"] is True


def test_websearch_source_adapter_guard_caps_candidate_count() -> None:
    artifact = build_websearch_source_adapter_guard()
    case = _case_by_id(artifact, "candidate_count_capped")

    assert case["status"] == "pass"
    assert case["candidate_count"] == MAX_WEBSEARCH_RESULTS_HARD_CAP
    assert case["checks"]["candidate_count_capped"] is True
    assert artifact["summary"]["bounded_examples"] == {
        "-1": 0,
        "5": 5,
        "999": MAX_WEBSEARCH_RESULTS_HARD_CAP,
        "true": 5,
    }
    assert bounded_websearch_max_results(999) == MAX_WEBSEARCH_RESULTS_HARD_CAP


def test_websearch_source_adapter_guard_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_websearch_source_adapter_guard import main

    output = tmp_path / "source_adapter_guard.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_source_adapter_guard_v1"
    assert artifact["status"] == "pass"


def test_websearch_source_adapter_guard_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_source_adapter_guard.py"),
        Path("scripts/build_accurate_intake_websearch_source_adapter_guard.py"),
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
