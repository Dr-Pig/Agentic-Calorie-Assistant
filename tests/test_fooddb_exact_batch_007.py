from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_lamole_plain_breadsticks_25g",
    "exact_vidal_fried_egg_gummy_30g",
    "exact_sunshine_red_yeast_cracker_20g",
    "exact_balocco_cocoa_bread_50g",
    "exact_fule_uht_milk_150ml",
    "exact_lifestyle_melon_pan_cookie_42g",
    "exact_pxselect_caramel_cheese_pudding_90g",
    "exact_mr_brown_platinum_coffee_240ml",
}


def test_exact_batch_007_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_004.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] in {"per_serving", "per_package"}
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_007_resolves_with_visible_macros() -> None:
    cases = [
        (
            "la mole plain breadsticks 25g",
            "exact_lamole_plain_breadsticks_25g",
            104.0,
            {"protein_g": 2.8, "carb_g": 18.8, "fat_g": 2.1},
        ),
        (
            "fule uht milk 150ml",
            "exact_fule_uht_milk_150ml",
            98.0,
            {"protein_g": 4.7, "carb_g": 7.2, "fat_g": 5.6},
        ),
        (
            "mr brown platinum coffee 240ml",
            "exact_mr_brown_platinum_coffee_240ml",
            98.0,
            {"protein_g": 1.7, "carb_g": 19.0, "fat_g": 1.7},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
