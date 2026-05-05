from __future__ import annotations

from app.nutrition.application.websearch_cache_rate_license_wall import (
    build_websearch_cache_key,
    build_websearch_cache_rate_license_wall,
    build_websearch_extract_request_policy,
    build_websearch_search_request_policy,
)


def test_websearch_cache_rate_license_wall_documents_bounded_non_live_policy() -> None:
    artifact = build_websearch_cache_rate_license_wall()

    assert artifact["artifact_type"] == "accurate_intake_websearch_cache_rate_license_wall_v1"
    assert artifact["classification"] == "deterministic_websearch_governance_only"
    assert artifact["status"] == "pass"
    assert artifact["live_websearch_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["case_count"] == 4
    assert artifact["summary"]["fail_count"] == 0
    assert artifact["next_required_slice"] == "websearch_candidate_packet_smoke"


def test_websearch_search_request_policy_keeps_exact_brand_search_bounded() -> None:
    request = build_websearch_search_request_policy(
        normalized_query="Milksha pearl black tea latte",
        exact_phrase="Milksha pearl black tea latte",
    )

    assert request["search_depth"] == "basic"
    assert request["auto_parameters"] is False
    assert request["max_results"] == 5
    assert request["include_answer"] is False
    assert request["include_raw_content"] is False
    assert request["exact_match"] is True
    assert request["query"] == '"Milksha pearl black tea latte"'


def test_websearch_search_request_policy_clamps_limits_and_blocks_advanced_by_default() -> None:
    request = build_websearch_search_request_policy(
        normalized_query="Starbucks latte",
        max_results=999,
        search_depth="advanced",
    )

    assert request["search_depth"] == "basic"
    assert request["advanced_depth_downgraded"] is True
    assert request["max_results"] == 5
    assert request["auto_parameters"] is False


def test_websearch_extract_request_policy_uses_bounded_chunks_not_full_page_truth() -> None:
    request = build_websearch_extract_request_policy(
        urls=("https://brand.example/menu/item",),
        query="Milksha pearl black tea latte calories",
        chunks_per_source=99,
        extract_depth="advanced",
    )

    assert request["extract_depth"] == "basic"
    assert request["advanced_depth_downgraded"] is True
    assert request["chunks_per_source"] == 3
    assert request["include_images"] is False
    assert request["raw_content_truth_allowed"] is False
    assert request["runtime_truth_allowed"] is False


def test_websearch_cache_key_uses_policy_inputs_not_snippet_or_raw_content() -> None:
    first = build_websearch_cache_key(
        normalized_query="Milksha pearl black tea latte",
        source_class_order=("official_brand_or_chain_page", "brand_menu_page"),
        search_depth="basic",
        max_results=5,
        exact_match=True,
        include_raw_content=False,
    )
    second = build_websearch_cache_key(
        normalized_query="Milksha pearl black tea latte",
        source_class_order=("official_brand_or_chain_page", "brand_menu_page"),
        search_depth="basic",
        max_results=5,
        exact_match=True,
        include_raw_content=False,
        raw_snippet="this must not affect the cache key",
    )

    assert first == second
    assert "raw_snippet" not in first
    assert "this must not affect" not in first
    assert first.startswith("websearch_candidate_v1:")


def test_websearch_cache_rate_license_wall_script_roundtrip(tmp_path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_websearch_cache_rate_license_wall import main

    output = tmp_path / "websearch_wall.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_cache_rate_license_wall_v1"
    assert artifact["status"] == "pass"
