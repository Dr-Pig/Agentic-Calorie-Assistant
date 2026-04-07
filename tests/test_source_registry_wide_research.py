from __future__ import annotations

import json

from data_build.wide_research.source_registry_v1 import (
    SCHEMA_VERSION,
    SOURCE_FAMILY_SHARDS,
    aggregate_run,
    scaffold_run,
    validate_run,
)


def test_source_registry_manifest_has_expected_shards() -> None:
    shard_ids = [shard["id"] for shard in SOURCE_FAMILY_SHARDS]
    assert shard_ids == [
        "tw_gov_nutrition",
        "tw_packaged_beverage_official",
        "tw_convenience_store_official",
        "tw_fast_food_chain_official",
        "tw_chain_restaurant_nutrition",
        "tw_drink_chain_official",
        "tw_retailer_official_product_pages",
        "tw_pattern_reference_candidates",
    ]


def test_scaffold_run_creates_layout_and_prompt_files(tmp_path) -> None:
    run_dir = scaffold_run(tmp_path, run_id="source-registry-v1-test", schema_signature="sig")
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "notes.json").exists()
    assert (run_dir / "prompts" / "tw_gov_nutrition.md").exists()
    assert (run_dir / "dry_run.ps1").exists()
    assert (run_dir / "run_all.ps1").exists()


def test_validate_run_catches_scope_and_aggregator_errors(tmp_path) -> None:
    run_dir = scaffold_run(tmp_path, run_id="source-registry-v1-test")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "shard_id": "tw_pattern_reference_candidates",
        "sources": [
            {
                "id": "bad-pattern-source",
                "name": "FatSecret Tomato",
                "tier": "P2",
                "applies_to": ["base_nutrition"],
                "source_type": "nutrition_aggregator",
                "url": "https://www.fatsecret.com/calories-nutrition/example",
                "verification_method": "manual_review",
                "refresh_policy": "manual_periodic",
                "why_reliable": "This is intentionally wrong for the test.",
                "notes": ""
            }
        ],
        "excluded_candidates": []
    }
    (run_dir / "child_outputs" / "tw_pattern_reference_candidates.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = validate_run(run_dir)
    codes = {issue["code"] for issue in report["issues"]}
    assert "p2_scope_violation" in codes
    assert "shard_source_type_violation" in codes
    assert "missing_output" in codes


def test_aggregate_run_dedupes_exact_duplicates_and_keeps_conflicts(tmp_path) -> None:
    run_dir = scaffold_run(tmp_path, run_id="source-registry-v1-test")
    payload_a = {
        "schema_version": SCHEMA_VERSION,
        "shard_id": "tw_gov_nutrition",
        "sources": [
            {
                "id": "tfda-food-composition",
                "name": "TFDA Food Composition",
                "tier": "P0",
                "applies_to": ["base_nutrition"],
                "source_type": "government_nutrition_dataset",
                "url": "https://example.gov.tw/nutrition",
                "verification_method": "official_page_check",
                "refresh_policy": "periodic_recheck",
                "why_reliable": "Government source",
                "notes": ""
            }
        ],
        "excluded_candidates": []
    }
    payload_b = {
        "schema_version": SCHEMA_VERSION,
        "shard_id": "tw_packaged_beverage_official",
        "sources": [
            {
                "id": "tfda-food-composition",
                "name": "TFDA Food Composition",
                "tier": "P0",
                "applies_to": ["base_nutrition"],
                "source_type": "government_nutrition_dataset",
                "url": "https://example.gov.tw/nutrition",
                "verification_method": "official_page_check",
                "refresh_policy": "periodic_recheck",
                "why_reliable": "Government source",
                "notes": ""
            },
            {
                "id": "same-url-different-shape",
                "name": "Same URL Different Tier",
                "tier": "P1",
                "applies_to": ["exact_item"],
                "source_type": "official_brand_product_page",
                "url": "https://example.gov.tw/nutrition",
                "verification_method": "official_page_check",
                "refresh_policy": "periodic_recheck",
                "why_reliable": "Conflict case",
                "notes": ""
            }
        ],
        "excluded_candidates": []
    }
    (run_dir / "child_outputs" / "tw_gov_nutrition.json").write_text(
        json.dumps(payload_a, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "child_outputs" / "tw_packaged_beverage_official.json").write_text(
        json.dumps(payload_b, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    aggregated = aggregate_run(run_dir)
    assert len(aggregated["candidates"]["sources"]) == 1
    assert len(aggregated["candidates"]["conflicts"]) == 1
