from __future__ import annotations

from app.nutrition.application.websearch_source_policy import (
    build_websearch_source_policy_artifact,
    classify_websearch_source_candidate,
)


def test_websearch_source_policy_documents_cache_rate_and_license_boundaries() -> None:
    artifact = build_websearch_source_policy_artifact()

    assert artifact["artifact_type"] == "accurate_intake_websearch_source_policy_v1"
    assert artifact["claim_scope"] == "websearch_source_cache_rate_license_policy_only"
    assert artifact["live_websearch_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["max_search_attempts"] == 2
    assert artifact["search_depth_policy"]["default"] == "basic"
    assert artifact["search_depth_policy"]["advanced_allowed"] == "diagnostic_exception_only"
    assert artifact["cache_policy"]["cache_key_fields"] == [
        "normalized_query",
        "source_class_order",
        "search_depth",
        "max_results",
    ]
    assert artifact["rate_policy"]["max_results"] == 5
    assert artifact["rate_policy"]["max_results_hard_cap"] == 20
    assert artifact["license_policy"]["unknown_license_behavior"] == "candidate_only_requires_review"
    assert "public_menu_page" in artifact["license_policy"]["extract_allowed_license_statuses"]
    assert set(artifact["non_claims"]) == {
        "no_live_websearch_call",
        "no_websearch_runtime_truth",
        "no_runtime_truth_promotion",
        "no_exact_card_truth_promotion",
        "no_runtime_mutation",
        "no_readiness_claim",
    }


def test_official_source_with_license_and_serving_basis_is_extract_candidate_only() -> None:
    classification = classify_websearch_source_candidate(
        {
            "source_url": "https://brand.example/menu/boba",
            "source_class": "official_brand_or_chain_page",
            "license_status": "public_menu_page",
            "robots_status": "allowed",
            "identity_confidence": "high",
            "serving_basis_candidate": "per_cup",
            "nutrition_fields_present": ["kcal"],
        }
    )

    assert classification["candidate_class"] == "exact_candidate_for_extract_review"
    assert classification["extract_candidate_allowed"] is True
    assert classification["runtime_truth_allowed"] is False
    assert classification["cache_allowed"] is True


def test_unknown_license_or_robots_blocks_extract_candidate() -> None:
    classification = classify_websearch_source_candidate(
        {
            "source_url": "https://unknown.example/menu/boba",
            "source_class": "official_brand_or_chain_page",
            "license_status": "unknown",
            "robots_status": "unknown",
            "identity_confidence": "high",
            "serving_basis_candidate": "per_cup",
            "nutrition_fields_present": ["kcal"],
        }
    )

    assert classification["candidate_class"] == "blocked_source_policy_candidate"
    assert classification["extract_candidate_allowed"] is False
    assert classification["runtime_truth_allowed"] is False
    assert "license_unknown" in classification["block_reasons"]
    assert "robots_unknown" in classification["block_reasons"]


def test_disallowed_license_status_blocks_extract_candidate() -> None:
    classification = classify_websearch_source_candidate(
        {
            "source_url": "https://brand.example/menu/boba",
            "source_class": "official_brand_or_chain_page",
            "license_status": "Blocked",
            "robots_status": "Allowed",
            "identity_confidence": "High",
            "serving_basis_candidate": "per_cup",
            "nutrition_fields_present": ["KCAL"],
        }
    )

    assert classification["candidate_class"] == "blocked_source_policy_candidate"
    assert classification["extract_candidate_allowed"] is False
    assert classification["runtime_truth_allowed"] is False
    assert classification["cache_allowed"] is False
    assert "license_not_allowed" in classification["block_reasons"]


def test_license_and_robots_status_are_case_normalized_before_policy() -> None:
    classification = classify_websearch_source_candidate(
        {
            "source_url": "https://unknown.example/menu/boba",
            "source_class": "OFFICIAL_BRAND_OR_CHAIN_PAGE",
            "license_status": "Unknown",
            "robots_status": "Unknown",
            "identity_confidence": "HIGH",
            "serving_basis_candidate": "per_cup",
            "nutrition_fields_present": ["KCAL"],
        }
    )

    assert classification["candidate_class"] == "blocked_source_policy_candidate"
    assert classification["extract_candidate_allowed"] is False
    assert classification["runtime_truth_allowed"] is False
    assert classification["cache_allowed"] is False
    assert "license_unknown" in classification["block_reasons"]
    assert "robots_unknown" in classification["block_reasons"]


def test_third_party_source_stays_weak_candidate() -> None:
    classification = classify_websearch_source_candidate(
        {
            "source_url": "https://calorie-blog.example/boba",
            "source_class": "third_party_blog_or_scrape",
            "license_status": "unknown",
            "robots_status": "allowed",
            "identity_confidence": "high",
            "serving_basis_candidate": "per_cup",
            "nutrition_fields_present": ["kcal"],
        }
    )

    assert classification["candidate_class"] == "weak_or_unusable_candidate"
    assert classification["extract_candidate_allowed"] is False
    assert classification["runtime_truth_allowed"] is False


def test_unknown_serving_basis_blocks_extract_candidate() -> None:
    classification = classify_websearch_source_candidate(
        {
            "source_url": "https://brand.example/menu/boba",
            "source_class": "official_brand_or_chain_page",
            "license_status": "public_menu_page",
            "robots_status": "allowed",
            "identity_confidence": "high",
            "serving_basis_candidate": "unknown",
            "nutrition_fields_present": ["kcal"],
        }
    )

    assert classification["candidate_class"] == "blocked_source_policy_candidate"
    assert classification["extract_candidate_allowed"] is False
    assert classification["runtime_truth_allowed"] is False
    assert "serving_basis_missing" in classification["block_reasons"]
