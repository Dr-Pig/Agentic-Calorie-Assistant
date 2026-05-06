from __future__ import annotations

from app.nutrition.application.websearch_candidate_pipeline import (
    build_websearch_candidate_pipeline_diagnostic,
)


def _case_by_id(artifact: dict, case_id: str) -> dict:
    return {case["case_id"]: case for case in artifact["cases"]}[case_id]


def test_candidate_pipeline_multi_source_case_prefers_official_exact_candidate() -> None:
    artifact = build_websearch_candidate_pipeline_diagnostic()
    case = _case_by_id(artifact, "pipeline_multi_source_official_preferred")

    assert len(case["candidate_packets"]) == 3
    assert case["selected_extract_decision"]["selected_search_packet_id"] == case["candidate_packets"][2]["packet_id"]
    assert case["candidate_classifications"][0]["candidate_class"] == "weak_or_unusable_candidate"
    assert case["candidate_classifications"][1]["candidate_class"] == "weak_or_unusable_candidate"
    assert case["candidate_classifications"][2]["candidate_class"] == "exact_candidate_for_extract_review"


def test_candidate_pipeline_supports_convenience_store_and_chain_restaurant_exact_candidates() -> None:
    artifact = build_websearch_candidate_pipeline_diagnostic()
    convenience_store = _case_by_id(artifact, "pipeline_convenience_store_rice_ball_exact")
    chain_restaurant = _case_by_id(artifact, "pipeline_chain_restaurant_menu_item_exact")

    assert convenience_store["selected_extract_decision"]["selected_search_packet_id"] == (
        convenience_store["candidate_packets"][0]["packet_id"]
    )
    assert convenience_store["candidate_packets"][0]["source_class_hint"] == (
        "official_brand_or_chain_page"
    )
    assert convenience_store["candidate_packets"][0]["serving_basis_candidate"] == "per_piece"
    assert convenience_store["candidate_classifications"][0]["candidate_class"] == (
        "exact_candidate_for_extract_review"
    )

    assert chain_restaurant["selected_extract_decision"]["selected_search_packet_id"] == (
        chain_restaurant["candidate_packets"][0]["packet_id"]
    )
    assert chain_restaurant["candidate_packets"][0]["source_class_hint"] == "brand_menu_page"
    assert chain_restaurant["candidate_packets"][0]["serving_basis_candidate"] == "per_bowl"
    assert chain_restaurant["candidate_classifications"][0]["candidate_class"] == (
        "exact_candidate_for_extract_review"
    )


def test_candidate_pipeline_prefers_official_pdf_when_multiple_exact_sources_are_eligible() -> None:
    artifact = build_websearch_candidate_pipeline_diagnostic()
    case = _case_by_id(artifact, "pipeline_official_pdf_priority")

    assert len(case["candidate_packets"]) == 2
    assert case["candidate_classifications"][0]["candidate_class"] == "exact_candidate_blocked_by_policy"
    assert case["candidate_classifications"][1]["candidate_class"] == "exact_candidate_for_extract_review"
    assert case["candidate_packets"][1]["source_class_hint"] == "official_nutrition_pdf"
    assert case["selected_extract_decision"]["selected_search_packet_id"] == case["candidate_packets"][1]["packet_id"]
    assert case["selected_extract_decision"]["extract_allowed_by_policy"] is True


def test_candidate_pipeline_prefers_large_size_and_matching_modifier_candidates() -> None:
    artifact = build_websearch_candidate_pipeline_diagnostic()
    size_case = _case_by_id(artifact, "pipeline_large_size_preferred")
    unknown_size_case = _case_by_id(artifact, "pipeline_size_unknown_requires_followup")
    modifier_case = _case_by_id(artifact, "pipeline_modifier_match_preferred")

    assert size_case["selected_extract_decision"]["selected_search_packet_id"] == size_case["candidate_packets"][1]["packet_id"]
    assert size_case["candidate_classifications"][0]["candidate_class"] == "near_exact_wrong_size_candidate"
    assert size_case["candidate_classifications"][1]["candidate_class"] == "exact_candidate_for_extract_review"

    assert unknown_size_case["selected_extract_decision"]["selected_search_packet_id"] is None
    assert unknown_size_case["selected_extract_decision"]["extract_allowed_by_policy"] is False
    assert unknown_size_case["candidate_classifications"][0]["candidate_class"] == "near_exact_size_unknown_candidate"

    assert modifier_case["selected_extract_decision"]["selected_search_packet_id"] == modifier_case["candidate_packets"][1]["packet_id"]
    assert modifier_case["candidate_classifications"][0]["candidate_class"] == "near_exact_modifier_unknown_candidate"
    assert modifier_case["candidate_classifications"][1]["candidate_class"] == "exact_candidate_for_extract_review"


def test_candidate_pipeline_marks_same_brand_wrong_flavor_as_sibling_variant() -> None:
    artifact = build_websearch_candidate_pipeline_diagnostic()
    case = _case_by_id(artifact, "pipeline_same_brand_wrong_flavor_variant")

    assert case["selected_extract_decision"]["selected_search_packet_id"] is None
    assert case["selected_extract_decision"]["extract_allowed_by_policy"] is False
    assert case["candidate_classifications"][0]["candidate_class"] == "near_exact_sibling_candidate"
    assert case["candidate_packets"][0]["sibling_variant_risk"]["present"] is True


def test_candidate_pipeline_reports_no_extract_when_all_candidates_are_blocked() -> None:
    artifact = build_websearch_candidate_pipeline_diagnostic()
    case = _case_by_id(artifact, "pipeline_all_candidates_blocked")

    assert case["selected_extract_decision"]["selected_search_packet_id"] is None
    assert case["selected_extract_decision"]["extract_allowed_by_policy"] is False
    assert case["selected_extract_decision"]["extract_reason"] == "source_policy_blocked_selected_extract"
    assert "license_unknown" in case["selected_extract_decision"]["source_policy_block_reasons"]
    assert "robots_blocked" in case["selected_extract_decision"]["source_policy_block_reasons"]


def test_candidate_pipeline_summary_surfaces_exact_disambiguation_and_weak_boundaries() -> None:
    artifact = build_websearch_candidate_pipeline_diagnostic()
    summary = artifact["summary"]

    assert summary["case_count"] == 21
    assert summary["exact_review_candidate_count"] >= 6
    assert summary["disambiguation_candidate_count"] >= 5
    assert summary["blocked_candidate_count"] >= 4
    assert summary["policy_blocked_exact_candidate_count"] >= 1
    assert summary["weak_candidate_count"] >= 3
    assert summary["candidate_packet_count"] == sum(
        summary[key]
        for key in (
            "exact_review_candidate_count",
            "disambiguation_candidate_count",
            "blocked_candidate_count",
            "policy_blocked_exact_candidate_count",
            "weak_candidate_count",
        )
    )
