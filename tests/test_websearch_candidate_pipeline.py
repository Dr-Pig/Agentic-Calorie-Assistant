from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_candidate_pipeline import (
    WebSearchPipelineCase,
    build_websearch_candidate_pipeline_diagnostic,
)
from app.nutrition.application.retrieval_intent import RetrievalIntent


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
    assert artifact["source_policy"]["artifact_type"] == "accurate_intake_websearch_source_policy_v1"
    assert artifact["source_policy"]["live_websearch_used"] is False
    assert artifact["source_policy"]["websearch_runtime_truth_allowed"] is False
    assert artifact["source_policy"]["max_search_attempts"] == 2
    assert artifact["source_policy"]["rate_policy"]["max_results"] == 5
    assert artifact["source_policy"]["license_policy"]["unknown_license_behavior"] == (
        "candidate_only_requires_review"
    )
    assert artifact["summary"]["case_count"] == 19
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["summary"]["exact_review_candidate_count"] >= 4
    assert artifact["summary"]["disambiguation_candidate_count"] >= 5
    assert artifact["summary"]["blocked_candidate_count"] >= 4
    assert artifact["summary"]["policy_blocked_exact_candidate_count"] >= 1
    assert artifact["summary"]["weak_candidate_count"] >= 3
    assert artifact["summary"]["candidate_packet_count"] == sum(
        artifact["summary"][key]
        for key in (
            "exact_review_candidate_count",
            "disambiguation_candidate_count",
            "blocked_candidate_count",
            "policy_blocked_exact_candidate_count",
            "weak_candidate_count",
        )
    )
    assert artifact["summary"]["source_class_counts"]["official_brand_or_chain_page"] >= 8
    assert artifact["summary"]["source_class_counts"]["official_nutrition_pdf"] >= 2
    assert artifact["summary"]["source_class_counts"]["brand_menu_page"] >= 3

    exact = _case_by_id(artifact, "pipeline_milksha_exact")
    assert exact["query_plan"]["max_search_attempts"] == 2
    assert exact["query_plan"]["search_attempts"][0]["purpose"] == "exact_brand_or_menu_candidate"
    assert "Milksha" in exact["query_plan"]["search_attempts"][0]["query"]
    assert exact["candidate_classifications"][0]["candidate_class"] == "exact_candidate_for_extract_review"
    assert exact["candidate_classifications"][0]["extract_candidate_allowed"] is True
    assert exact["candidate_classifications"][0]["runtime_truth_allowed"] is False

    sibling = _case_by_id(artifact, "pipeline_milksha_sibling")
    assert sibling["candidate_classifications"][0]["candidate_class"] == "blocked_source_policy_candidate"
    assert sibling["candidate_classifications"][0]["manager_signal"] == "source_policy_blocked"
    assert "identity_confidence_not_high" in sibling["candidate_classifications"][0]["source_policy_block_reasons"]

    weak = _case_by_id(artifact, "pipeline_third_party_weak")
    assert weak["candidate_classifications"][0]["candidate_class"] == "weak_or_unusable_candidate"
    assert weak["candidate_classifications"][0]["manager_signal"] == "source_not_sufficient"

    wrong_size = _case_by_id(artifact, "pipeline_starbucks_wrong_size")
    assert wrong_size["candidate_classifications"][0]["candidate_class"] == "near_exact_wrong_size_candidate"
    assert wrong_size["candidate_classifications"][0]["manager_signal"] == "needs_disambiguation"

    official_pdf = _case_by_id(artifact, "pipeline_official_pdf_exact")
    assert official_pdf["candidate_classifications"][0]["source_class"] == "official_nutrition_pdf"
    assert official_pdf["candidate_classifications"][0]["candidate_class"] == "exact_candidate_for_extract_review"
    assert official_pdf["candidate_classifications"][0]["extract_candidate_allowed"] is True

    brand_menu = _case_by_id(artifact, "pipeline_brand_menu_exact")
    assert brand_menu["candidate_classifications"][0]["source_class"] == "brand_menu_page"
    assert brand_menu["candidate_classifications"][0]["candidate_class"] == "exact_candidate_for_extract_review"
    assert brand_menu["candidate_classifications"][0]["extract_candidate_allowed"] is True

    robots_blocked = _case_by_id(artifact, "pipeline_robots_blocked")
    assert robots_blocked["candidate_classifications"][0]["candidate_class"] == "blocked_source_policy_candidate"
    assert "robots_blocked" in robots_blocked["candidate_classifications"][0]["source_policy_block_reasons"]

    missing_serving = _case_by_id(artifact, "pipeline_missing_serving_basis")
    assert missing_serving["candidate_classifications"][0]["candidate_class"] == "blocked_source_policy_candidate"
    assert "serving_basis_missing" in missing_serving["candidate_classifications"][0]["source_policy_block_reasons"]

    missing_kcal = _case_by_id(artifact, "pipeline_missing_kcal")
    assert missing_kcal["candidate_classifications"][0]["candidate_class"] == "blocked_source_policy_candidate"
    assert "kcal_missing" in missing_kcal["candidate_classifications"][0]["source_policy_block_reasons"]

    modifier_missing = _case_by_id(artifact, "pipeline_modifier_missing")
    assert modifier_missing["candidate_classifications"][0]["candidate_class"] == (
        "near_exact_modifier_unknown_candidate"
    )
    assert modifier_missing["candidate_classifications"][0]["manager_signal"] == "needs_disambiguation"
    assert modifier_missing["candidate_classifications"][0]["extract_candidate_allowed"] is False
    assert modifier_missing["candidate_classifications"][0]["runtime_truth_allowed"] is False
    assert modifier_missing["selected_extract_decision"]["selected_search_packet_id"] is None
    assert modifier_missing["selected_extract_decision"]["extract_allowed_by_policy"] is False
    assert modifier_missing["selected_extract_decision"]["extract_count"] == 0

    wrong_brand = _case_by_id(artifact, "pipeline_wrong_brand_official")
    assert wrong_brand["candidate_classifications"][0]["candidate_class"] == "weak_or_unusable_candidate"
    assert wrong_brand["candidate_classifications"][0]["manager_signal"] == "source_not_sufficient"
    assert wrong_brand["candidate_classifications"][0]["extract_candidate_allowed"] is False
    assert wrong_brand["candidate_classifications"][0]["runtime_truth_allowed"] is False
    assert wrong_brand["selected_extract_decision"]["selected_search_packet_id"] is None
    assert wrong_brand["selected_extract_decision"]["extract_count"] == 0

    social = _case_by_id(artifact, "pipeline_social_media_untrusted")
    assert social["candidate_classifications"][0]["candidate_class"] == "blocked_source_policy_candidate"
    assert social["candidate_classifications"][0]["extract_candidate_allowed"] is False
    assert social["candidate_classifications"][0]["runtime_truth_allowed"] is False
    assert "source_class_not_trusted" in social["candidate_classifications"][0][
        "source_policy_block_reasons"
    ]

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
            assert "source_class_hint" in packet
        for classification in case["candidate_classifications"]:
            assert classification["runtime_truth_allowed"] is False
            assert classification["packet_ready_truth_allowed"] is False
            assert "source_class" in classification
            assert "manager_expected_behavior" not in classification


def test_websearch_candidate_pipeline_applies_source_policy_to_unknown_license_hits() -> None:
    artifact = build_websearch_candidate_pipeline_diagnostic(
        (
            WebSearchPipelineCase(
                case_id="pipeline_unknown_license",
                intent=RetrievalIntent(
                    base_dish="pearl black tea latte",
                    aliases=["Milksha pearl black tea latte"],
                    brand_hint="Milksha",
                    size_hint=None,
                    modifier_hints=[],
                    listed_items=[],
                    retrieval_goal="exact_brand_lookup",
                ),
                raw_hits=(
                    {
                        "title": "Milksha pearl black tea latte",
                        "url": "https://milksha.example/menu/pearl-black-tea-latte",
                        "brand_detected": "Milksha",
                        "officialness": "official",
                        "source_quality_label": "high",
                        "identity_confidence": "high",
                        "serving_basis": "per_cup",
                        "nutrition_fields_present": ["kcal"],
                        "license_status": "unknown",
                        "robots_status": "unknown",
                        "raw_ref": "raw/websearch/unknown_license.json#0",
                    },
                ),
            ),
        )
    )

    classification = artifact["cases"][0]["candidate_classifications"][0]
    assert classification["candidate_class"] == "blocked_source_policy_candidate"
    assert classification["extract_candidate_allowed"] is False
    assert classification["runtime_truth_allowed"] is False
    assert "license_unknown" in classification["source_policy_block_reasons"]
    assert "robots_unknown" in classification["source_policy_block_reasons"]
    assert artifact["cases"][0]["selected_extract_decision"]["selected_search_packet_id"] is None
    assert artifact["cases"][0]["selected_extract_decision"]["extract_allowed_by_policy"] is False
    assert artifact["cases"][0]["selected_extract_decision"]["extract_count"] == 0
    assert artifact["cases"][0]["selected_extract_decision"]["extract_reason"] == (
        "source_policy_blocked_selected_extract"
    )
    assert "license_unknown" in artifact["cases"][0]["selected_extract_decision"][
        "source_policy_block_reasons"
    ]


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
