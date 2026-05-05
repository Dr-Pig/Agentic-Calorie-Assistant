from __future__ import annotations

POLICY_VERSION = "fooddb_internal_seed_anchor_batch_v1"

INTERNAL_SEED_BATCH_ANCHOR_IDS = (
    "single_item_tea_egg",
    "breakfast_staple_egg_pancake",
    "custom_drink_latte",
    "generic_meal_chicken_bento",
    "listed_item_kelp",
    "listed_item_meatball",
    "listed_item_greens_home_cooked",
)

MVP_COVERAGE_TARGETS = (
    "single_item_tea_egg",
    "custom_drink_boba_milk_tea",
    "custom_drink_latte",
    "generic_meal_chicken_bento",
    "listed_item_tofu_dried",
    "listed_item_kelp",
    "listed_item_meatball",
    "listed_item_greens_home_cooked",
    "breakfast_staple_egg_pancake",
)

PORTION_DEFAULTS = {
    "single_item_tea_egg": {
        "portion_unit": "egg",
        "portion_quantity": 1,
        "portion_grams": 60,
        "label": "one tea egg",
        "runtime_usage_boundary": "stable_single_item_common_serving",
    },
    "breakfast_staple_egg_pancake": {
        "portion_unit": "serving",
        "portion_quantity": 1,
        "portion_grams": 130,
        "label": "one Taiwan breakfast egg pancake",
        "runtime_usage_boundary": "generic_range_estimate_with_refinement_not_exact",
    },
    "custom_drink_latte": {
        "portion_unit": "medium_cup",
        "portion_quantity": 1,
        "portion_ml": 360,
        "label": "one medium latte",
        "runtime_usage_boundary": "generic_drink_range_estimate_with_refinement",
    },
    "generic_meal_chicken_bento": {
        "portion_unit": "box",
        "portion_quantity": 1,
        "label": "one generic chicken bento",
        "runtime_usage_boundary": "generic_range_estimate_only_not_exact",
    },
    "listed_item_kelp": {
        "portion_unit": "piece",
        "portion_quantity": 1,
        "portion_grams": 30,
        "label": "one listed luwei kelp component",
        "runtime_usage_boundary": "listed_component_only",
    },
    "listed_item_meatball": {
        "portion_unit": "piece",
        "portion_quantity": 1,
        "portion_grams": 35,
        "label": "one listed luwei meatball component",
        "runtime_usage_boundary": "listed_component_only",
    },
    "listed_item_greens_home_cooked": {
        "portion_unit": "listed_component_portion",
        "portion_quantity": 1,
        "portion_grams": 100,
        "label": "one listed greens component portion",
        "runtime_usage_boundary": "listed_component_only_not_generic_vegetable_truth",
    },
}

FORBIDDEN_PROMOTIONS = [
    "new_food",
    "tfda_per_100g_as_common_serving",
    "open_food_facts_runtime_truth",
    "usda_runtime_truth",
    "old_base_db_runtime_truth",
    "official_brand_exact_card_runtime_truth",
]

__all__ = [
    "FORBIDDEN_PROMOTIONS",
    "INTERNAL_SEED_BATCH_ANCHOR_IDS",
    "MVP_COVERAGE_TARGETS",
    "POLICY_VERSION",
    "PORTION_DEFAULTS",
]
