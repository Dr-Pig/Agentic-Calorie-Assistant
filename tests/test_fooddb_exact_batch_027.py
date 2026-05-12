from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_laoyang_salted_egg_yolk_cracker_40g",
    "exact_unipresident_honey_soy_milk_250ml",
    "exact_kuangchuan_egg_soy_milk_330ml",
    "exact_weichuan_peanut_soy_milk_250ml",
    "exact_imei_low_sugar_soy_milk_250ml",
    "exact_aoba_organic_red_bean_soup_250g",
    "exact_lipton_original_milk_tea_250ml",
    "exact_quaker_complete_nutrition_plant_protein_250ml",
}


def test_exact_batch_027_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_011.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_027_resolves_with_visible_macros() -> None:
    cases = [
        (
            "laoyang salted egg yolk cracker 40g",
            "exact_laoyang_salted_egg_yolk_cracker_40g",
            201.0,
            {"protein_g": 3.4, "carb_g": 25.0, "fat_g": 9.7},
        ),
        (
            "unipresident honey soy milk 250ml",
            "exact_unipresident_honey_soy_milk_250ml",
            138.0,
            {"protein_g": 6.5, "carb_g": 19.0, "fat_g": 4.0},
        ),
        (
            "quaker complete nutrition plant protein 250ml",
            "exact_quaker_complete_nutrition_plant_protein_250ml",
            250.0,
            {"protein_g": 9.3, "carb_g": 39.0, "fat_g": 7.2},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
