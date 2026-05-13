from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_agv_high_protein_oat_powder_40g",
    "exact_agv_collagen_oat_drink_290ml",
    "exact_red_cow_whey_protein_cocoa_35g",
    "exact_77_nougat_mixed_nuts_8_9g",
    "exact_life_good_cocoa_candy_42g",
    "exact_lipton_green_milk_tea_267_5ml",
    "exact_assam_dual_tea_milk_tea_400ml",
    "exact_mr_brown_brown_sugar_milk_tea_290ml",
}


def test_exact_batch_039_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_016.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_039_resolves_with_visible_macros() -> None:
    cases = [
        (
            "agv high protein oat powder 40g",
            "exact_agv_high_protein_oat_powder_40g",
            158.0,
            {"protein_g": 11.8, "carb_g": 22.4, "fat_g": 2.9},
        ),
        (
            "red cow whey protein cocoa 35g",
            "exact_red_cow_whey_protein_cocoa_35g",
            140.0,
            {"protein_g": 28.0, "carb_g": 2.1, "fat_g": 2.2},
        ),
        (
            "life good cocoa candy 42g",
            "exact_life_good_cocoa_candy_42g",
            223.0,
            {"protein_g": 3.4, "carb_g": 24.8, "fat_g": 12.7},
        ),
        (
            "assam dual tea milk tea 400ml",
            "exact_assam_dual_tea_milk_tea_400ml",
            159.6,
            {"protein_g": 0.4, "carb_g": 33.2, "fat_g": 2.8},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
