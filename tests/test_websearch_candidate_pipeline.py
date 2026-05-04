from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_candidate_pipeline import (
    build_websearch_candidate_pipeline_diagnostic,
)


def _case_by_id(artifact: dict, case_id: str) -> dict:
    return {case["case_id"]: case for case in artifact["cases"]}[case_id]


def test_websearch_candidate_pipeline_builds_offline_query_plan_and_classifications() -> None:
    artifact = build_websearch_candidate_pipeline_diagnostic()

    assert artifact["artifact_type"] == "accurate_intake_websearch_candidate_pipeline_v1"
    assert artifact["classification"] == "offline_candidate_pipeline_only"
    assert artifact["live_websearch_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["summary"]["case_count"] == 4
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0

    exact = _case_by_id(artifact, "pipeline_milksha_exact")
    assert exact["query_plan"]["max_search_attempts"] == 2
    assert exact["query_plan"]["search_attempts"][0]["purpose"] == "exact_brand_or_menu_candidate"
    assert "Milksha" in exact["query_plan"]["search_attempts"][0]["query"]
    assert exact["candidate_classifications"][0]["candidate_class"] == "exact_candidate_for_extract_review"
    assert exact["candidate_classifications"][0]["extract_candidate_allowed"] is True
    assert exact["candidate_classifications"][0]["runtime_truth_allowed"] is False

    sibling = _case_by_id(artifact, "pipeline_milksha_sibling")
    assert sibling["candidate_classifications"][0]["candidate_class"] == "near_exact_sibling_candidate"
    assert sibling["candidate_classifications"][0]["manager_expected_behavior"] == "ask_followup"

    weak = _case_by_id(artifact, "pipeline_third_party_weak")
    assert weak["candidate_classifications"][0]["candidate_class"] == "weak_or_unusable_candidate"
    assert weak["candidate_classifications"][0]["manager_expected_behavior"] == "reject_or_request_better_source"

    wrong_size = _case_by_id(artifact, "pipeline_starbucks_wrong_size")
    assert wrong_size["candidate_classifications"][0]["candidate_class"] == "near_exact_wrong_size_candidate"
    assert wrong_size["candidate_classifications"][0]["manager_expected_behavior"] == "ask_followup"


def test_websearch_candidate_pipeline_excludes_raw_hits_and_truth_fields() -> None:
    artifact = build_websearch_candidate_pipeline_diagnostic()

    serialized = str(artifact)
    assert "raw_hits" not in serialized
    assert "final_truth" not in serialized
    assert "runtime_truth_allowed': True" not in serialized
    assert "likely_kcal" not in serialized
    assert "kcal_range" not in serialized

    for case in artifact["cases"]:
        assert case["live_websearch_used"] is False
        assert case["runtime_truth_changed"] is False
        for packet in case["candidate_packets"]:
            assert packet["truth_level"] == "candidate"
            assert packet["source_type"] == "web_search"
        for classification in case["candidate_classifications"]:
            assert classification["runtime_truth_allowed"] is False
            assert classification["packet_ready_truth_allowed"] is False


def test_websearch_candidate_pipeline_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_websearch_candidate_pipeline import main

    output = tmp_path / "websearch_candidate_pipeline.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_candidate_pipeline_v1"
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0


def test_websearch_candidate_pipeline_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_candidate_pipeline.py"),
        Path("scripts/build_accurate_intake_websearch_candidate_pipeline.py"),
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
