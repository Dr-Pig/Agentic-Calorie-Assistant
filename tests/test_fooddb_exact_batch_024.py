from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_ganbaishi_96_dark_chocolate_10g",
    "exact_nature_pepper_soda_crackers_28g",
    "exact_mr_brown_coffee_milk_unsweetened_240ml",
    "exact_wayne_mocha_coffee_320ml",
    "exact_houyi_quinoa_cracker_lemon_11_1g",
    "exact_lipton_taiwan_taro_milk_tea_17_5g",
    "exact_rixiang_white_pepper_cracker_35g",
    "exact_xingwu_blueberry_black_cherry_chocolate_cake_70g",
}


def test_exact_batch_024_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_010.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_024_resolves_with_visible_macros() -> None:
    cases = [
        (
            "wayne mocha coffee 320ml",
            "exact_wayne_mocha_coffee_320ml",
            145.0,
            {"protein_g": 2.2, "carb_g": 29.8, "fat_g": 1.9},
        ),
        (
            "lipton taiwan taro milk tea 17.5g",
            "exact_lipton_taiwan_taro_milk_tea_17_5g",
            72.0,
            {"protein_g": 1.0, "carb_g": 14.7, "fat_g": 1.1},
        ),
        (
            "rixiang white pepper cracker 35g",
            "exact_rixiang_white_pepper_cracker_35g",
            199.2,
            {"protein_g": 2.2, "carb_g": 19.1, "fat_g": 12.6},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
