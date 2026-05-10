from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_broad_coverage_taxonomy import (
    build_fooddb_broad_coverage_taxonomy,
)


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def test_broad_coverage_taxonomy_groups_existing_non_runtime_anchors() -> None:
    taxonomy = build_fooddb_broad_coverage_taxonomy(small_anchor_payload=_small_anchor_payload())

    assert taxonomy["artifact_type"] == "accurate_intake_fooddb_broad_coverage_taxonomy"
    assert taxonomy["runtime_truth_changed"] is False
    assert taxonomy["summary"] == {
        "total_anchor_count": 59,
        "runtime_visible_common_serving_count": 55,
        "existing_generic_not_runtime_count": 0,
        "semantic_only_basket_count": 4,
        "next_runtime_batch_candidate_count": 0,
    }
    groups = taxonomy["runtime_groups"]
    assert {item["anchor_id"] for item in groups["single_items"] if item["anchor_id"].startswith("single_item_")} == {
        "single_item_tea_egg",
        "single_item_salt_crispy_chicken",
        "single_item_sweet_potato",
    }
    assert len(groups["customizable_drinks"]) == 7
    assert len(groups["breakfast_and_staples"]) == 5
    assert len(groups["listed_basket_components"]) == 30
    assert len(groups["composite_meals"]) == 10


def test_broad_coverage_taxonomy_keeps_bare_baskets_semantic_only() -> None:
    taxonomy = build_fooddb_broad_coverage_taxonomy(small_anchor_payload=_small_anchor_payload())

    assert taxonomy["basket_boundary"]["bare_basket_behavior"] == "ask_followup_no_estimate"
    assert taxonomy["basket_boundary"]["listed_basket_behavior"] == (
        "estimate_approved_runtime_component_anchors_only"
    )
    assert len(taxonomy["semantic_only_baskets"]) == 4
    assert all(item["runtime_truth_allowed"] is False for item in taxonomy["semantic_only_baskets"])


def test_broad_coverage_taxonomy_candidates_are_report_only() -> None:
    taxonomy = build_fooddb_broad_coverage_taxonomy(small_anchor_payload=_small_anchor_payload())

    assert taxonomy["candidate_groups"] == {
        "single_items": [],
        "customizable_drinks": [],
        "breakfast_and_staples": [],
        "listed_basket_components": [],
        "composite_meals": [],
    }
    for group_items in taxonomy["runtime_groups"].values():
        for item in group_items:
            assert item["promotion_status"] == "runtime_visible"
            assert item["runtime_truth_allowed_after_report"] is True
            assert item["missing_runtime_fields"] == []
            assert item["kcal_point"] > 0
            assert item["kcal_range"][0] <= item["kcal_point"] <= item["kcal_range"][1]


def test_broad_coverage_taxonomy_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    output = tmp_path / "taxonomy.json"

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_broad_coverage_taxonomy import main

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["summary"]["next_runtime_batch_candidate_count"] == 0
    assert artifact["product_loop_integration_claimed"] is False
