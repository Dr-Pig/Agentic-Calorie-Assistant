from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_food_kb_inventory import build_food_kb_inventory


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "docs" / "quality" / "accurate_intake_food_kb_v1_inventory.json"


def _load_inventory_doc() -> dict[str, object]:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def test_food_kb_inventory_doc_preserves_evidence_only_boundary() -> None:
    inventory = _load_inventory_doc()

    assert inventory["artifact_type"] == "accurate_intake_food_kb_v1_inventory"
    assert inventory["scope"] == "local_evidence_support_inventory"
    assert inventory["truth_owner"] == "none"
    assert inventory["mutation_authority"] == "none"
    assert inventory["food_seed_can_decide_logged_draft_or_no_mutation"] is False
    assert inventory["live_llm_required"] is False
    assert inventory["web_tavily_required"] is False
    assert inventory["production_db_required"] is False
    assert inventory["readiness_claimed"] is False
    assert inventory["product_readiness_claimed"] is False


def test_food_kb_inventory_matches_repo_contained_seed_counts() -> None:
    inventory = build_food_kb_inventory()

    assert inventory["repo_contained_seed_counts"] == {
        "small_anchor_total": 23,
        "generic_anchor": 19,
        "generic_semantic_only": 4,
        "exact_item_cards": 5,
    }
    assert inventory["tfda_base_pipeline"]["base_nutrition_db_present"] is False
    assert inventory["tfda_base_pipeline"]["staging_inputs_present"] is False
    assert inventory["tfda_base_pipeline"]["data_build_package_present"] is False


def test_food_kb_inventory_lists_mvp_gap_families_without_authorizing_semantics() -> None:
    inventory = _load_inventory_doc()
    gap_ids = {gap["gap_id"] for gap in inventory["coverage_gaps"]}

    assert {
        "taiwan_breakfast_staples",
        "taiwan_lunch_dinner_staples",
        "drink_modifiers_and_chain_drinks",
        "basket_components_common_items",
        "home_cooked_plate_components",
        "exact_item_card_corpus",
        "tfda_base_nutrition_pipeline",
    } <= gap_ids
    assert all(gap["recommended_role"] in {"generic_anchor", "generic_semantic_only", "exact_item_card", "pipeline_infra"} for gap in inventory["coverage_gaps"])
    assert all(gap["semantic_authority"] == "none" for gap in inventory["coverage_gaps"])


def test_food_kb_inventory_safe_pr_slices_keep_sources_behind_ports() -> None:
    inventory = _load_inventory_doc()
    slice_ids = [item["slice_id"] for item in inventory["recommended_pr_slices"]]

    assert slice_ids == [
        "coverage_tests_first",
        "generic_anchor_seed_batches",
        "listed_basket_component_expansion",
        "exact_item_card_expansion",
        "tfda_pipeline_repair",
    ]
    assert all(item["must_preserve"] == "NutritionEvidenceStorePort" for item in inventory["recommended_pr_slices"])
    assert all(item["forbidden"] == "food_seed_semantic_or_mutation_authority" for item in inventory["recommended_pr_slices"])
