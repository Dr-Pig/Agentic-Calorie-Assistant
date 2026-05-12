from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_oak_full_cream_milk_powder_32g",
    "exact_enutrition_protein_formula_237ml",
    "exact_red_bull_whey_protein_35g",
    "exact_red_bull_full_cream_milk_powder_40g",
    "exact_weet_bix_wholegrain_cereal_15_6g",
    "exact_imei_nutrition_biscuits_34_2g",
    "exact_golden_bridge_96_dark_chocolate_10g",
    "exact_unipresident_milk_soybean_drink_250ml",
}


def test_exact_batch_014_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_006.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] in {"per_serving", "per_package"}
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_014_resolves_with_visible_macros() -> None:
    cases = [
        (
            "oak full cream milk powder 32g",
            "exact_oak_full_cream_milk_powder_32g",
            160.7,
            {"protein_g": 7.7, "carb_g": 12.9, "fat_g": 8.7},
        ),
        (
            "enutrition protein formula 237ml",
            "exact_enutrition_protein_formula_237ml",
            190.0,
            {"protein_g": 20.0, "carb_g": 12.7, "fat_g": 7.5},
        ),
        (
            "unipresident milk soybean drink 250ml",
            "exact_unipresident_milk_soybean_drink_250ml",
            138.0,
            {"protein_g": 6.5, "carb_g": 19.0, "fat_g": 4.0},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
