from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_quality_plan import build_fooddb_quality_improvement_plan


def test_fooddb_quality_plan_keeps_first_batch_as_review_material() -> None:
    plan = build_fooddb_quality_improvement_plan(
        inventory={
            "repo_contained_seed_counts": {
                "small_anchor_total": 44,
                "exact_item_cards": 5,
                "basket_components": 19,
            },
            "missing_source_metadata_count": 49,
        },
        food_gap_register={
            "food_gap_candidates": [
                {"gap_family": "breakfast_combo"},
                {"gap_family": "chicken_bento_rice_modifier"},
                {"gap_family": "bubble_tea_sugar_size_modifier"},
            ]
        },
    )

    assert plan["artifact_type"] == "accurate_intake_fooddb_quality_improvement_plan"
    assert plan["food_kb_truth_updated"] is False
    assert plan["nutrition_seed_created"] is False
    assert plan["exact_card_created"] is False
    assert plan["bulk_food_db_expansion"] is False
    assert plan["inventory_snapshot"]["missing_source_metadata_count"] == 49
    assert plan["first_batch_review_families"] == [
        "breakfast_combo",
        "chicken_bento_rice_modifier",
        "bubble_tea_sugar_size_modifier",
        "luwei_listed_components",
    ]
    assert all(item["status"] == "review_packet_only" for item in plan["first_batch_review_packets"])


def test_fooddb_quality_plan_defines_acceptance_for_later_truth_promotion_pr() -> None:
    plan = build_fooddb_quality_improvement_plan(inventory={}, food_gap_register={})

    assert "source_quality_policy_green" in plan["later_truth_promotion_acceptance"]
    assert "human_review_approved" in plan["later_truth_promotion_acceptance"]
    assert "promotion_policy_allows_requested_stage" in plan["later_truth_promotion_acceptance"]
    assert "one_day_dogfood_rerun_after_truth_promotion" in plan["later_truth_promotion_acceptance"]
    assert plan["not_claiming"] == [
        "fooddb_quality_complete",
        "first_batch_truth_promoted",
        "one_day_dogfood_pass",
        "product_readiness",
    ]


def test_fooddb_quality_plan_makes_first_batch_macro_review_only() -> None:
    plan = build_fooddb_quality_improvement_plan(inventory={}, food_gap_register={})

    macro_policy = plan["first_batch_macro_review_policy"]
    assert macro_policy["packet_fields"] == [
        "protein_g",
        "carbs_g",
        "fat_g",
        "macro_visibility_status",
        "macro_source_basis",
        "macro_confidence",
    ]
    assert macro_policy["missing_macro_policy"] == "preserve_null_do_not_invent"
    assert macro_policy["missing_macro_blocks_kcal_logging"] is False
    assert macro_policy["review_candidate_can_create_macro_truth"] is False
    assert macro_policy["forbidden_macro_sources"] == [
        "food_name",
        "kcal_reverse_inference",
        "llm_hint",
        "websearch_snippet",
    ]
    assert macro_policy["source_class_policy_choices"] == [
        "exact_brand_item",
        "generic_common_serving",
        "listed_component",
        "basket_family_alias_modifier",
        "source_evidence_candidate",
    ]
    assert all(
        "macro_review_policy" in packet
        for packet in plan["first_batch_review_packets"]
    )
    assert all(
        packet["macro_review_policy"]["review_candidate_can_create_macro_truth"] is False
        for packet in plan["first_batch_review_packets"]
    )


def test_fooddb_quality_plan_builder_writes_review_plan_only(tmp_path: Path) -> None:
    inventory = tmp_path / "inventory.json"
    gap_register = tmp_path / "gap_register.json"
    output = tmp_path / "fooddb_quality_plan.json"
    inventory.write_text(
        json.dumps(
            {
                "repo_contained_seed_counts": {"small_anchor_total": 44},
                "missing_source_metadata_count": 49,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    gap_register.write_text(
        json.dumps({"food_gap_candidates": [{"gap_family": "breakfast_combo"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.build_accurate_intake_fooddb_quality_plan import main

    assert main(
        [
            "--inventory-json",
            str(inventory),
            "--food-gap-register",
            str(gap_register),
            "--output",
            str(output),
        ]
    ) == 0

    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["nutrition_seed_created"] is False
    assert artifact["bulk_food_db_expansion"] is False
