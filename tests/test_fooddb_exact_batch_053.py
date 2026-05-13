from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_mr_brown_deep_roast_latte_240ml",
    "exact_freshdelight_good_sleep_high_calcium_milk_200ml",
    "exact_chulu_ranch_strawberry_lactic_drink_200ml",
    "exact_klim_mixed_berry_milk_198ml",
    "exact_weichuan_linfengying_original_probiotic_yogurt_216ml",
    "exact_imei_sesame_egg_roll_30g",
    "exact_skyflakes_sweet_milk_sandwich_crackers_30g",
    "exact_imei_seaweed_soda_crackers_30g",
    "exact_kaho_buckwheat_multigrain_crisps_30g",
    "exact_kaho_buckwheat_brown_rice_crackers_30g",
    "exact_lifestyle_pickled_radish_cheese_senbei_30g",
    "exact_kong_yen_apple_honey_instant_curry_20_8g",
}


def test_exact_batch_053_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_018.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_053_resolves_with_visible_macros() -> None:
    cases = [
        (
            "mr brown deep roast latte 240ml",
            "exact_mr_brown_deep_roast_latte_240ml",
            85.0,
            {"protein_g": 1.9, "carb_g": 16.2, "fat_g": 1.4},
        ),
        (
            "linfengying original probiotic yogurt 216ml",
            "exact_weichuan_linfengying_original_probiotic_yogurt_216ml",
            158.0,
            {"protein_g": 8.0, "carb_g": 18.4, "fat_g": 5.8},
        ),
        (
            "imei sesame egg roll 30g",
            "exact_imei_sesame_egg_roll_30g",
            176.0,
            {"protein_g": 2.1, "carb_g": 16.2, "fat_g": 11.4},
        ),
        (
            "kong yen apple honey instant curry 20.8g",
            "exact_kong_yen_apple_honey_instant_curry_20_8g",
            103.5,
            {"protein_g": 1.2, "carb_g": 9.7, "fat_g": 6.7},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
