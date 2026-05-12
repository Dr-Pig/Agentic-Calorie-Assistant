from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_wandan_uht_whole_milk_200ml",
    "exact_kikkoman_adjusted_soy_milk_200ml",
    "exact_hersheys_choco_bites_cocoa_90g",
    "exact_chulu_strawberry_lactic_drink_200ml",
    "exact_weichuan_bedtime_milk_200ml",
    "exact_weichuan_milk_200ml",
    "exact_ferrero_rocher_milk_chocolate_bar_18g",
    "exact_godiva_milk_chocolate_11_2g",
}


def test_exact_batch_030_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_012.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_030_resolves_with_visible_macros() -> None:
    cases = [
        (
            "wandan uht whole milk 200ml",
            "exact_wandan_uht_whole_milk_200ml",
            131.0,
            {"protein_g": 6.2, "carb_g": 9.8, "fat_g": 7.4},
        ),
        (
            "kikkoman adjusted soy milk 200ml",
            "exact_kikkoman_adjusted_soy_milk_200ml",
            95.4,
            {"protein_g": 7.8, "carb_g": 4.8, "fat_g": 5.0},
        ),
        (
            "weichuan bedtime milk 200ml",
            "exact_weichuan_bedtime_milk_200ml",
            106.0,
            {"protein_g": 5.6, "carb_g": 12.8, "fat_g": 3.6},
        ),
        (
            "ferrero rocher milk chocolate bar 18g",
            "exact_ferrero_rocher_milk_chocolate_bar_18g",
            106.0,
            {"protein_g": 1.2, "carb_g": 8.8, "fat_g": 7.3},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
