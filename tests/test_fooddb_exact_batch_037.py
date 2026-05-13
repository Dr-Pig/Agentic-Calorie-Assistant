from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_imei_vanilla_milk_wafer_rolls_31_8g",
    "exact_imei_langue_de_chat_milk_22g",
    "exact_imei_almond_milk_chocolate_balls_23_5g",
    "exact_duncan_hines_devil_cake_mix_43_2g",
    "exact_imei_cream_puffs_milk_65g",
    "exact_imei_cream_puffs_strawberry_65g",
    "exact_kitkat_strawberry_cocoa_wafer_11_6g",
    "exact_imei_almond_powder_no_added_sugar_30g",
}


def test_exact_batch_037_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_015.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_037_resolves_with_visible_macros() -> None:
    cases = [
        (
            "imei vanilla milk wafer rolls 31.8g",
            "exact_imei_vanilla_milk_wafer_rolls_31_8g",
            151.0,
            {"protein_g": 1.7, "carb_g": 23.7, "fat_g": 5.5},
        ),
        (
            "imei cream puffs milk 65g",
            "exact_imei_cream_puffs_milk_65g",
            384.0,
            {"protein_g": 6.1, "carb_g": 31.4, "fat_g": 26.0},
        ),
        (
            "kitkat strawberry cocoa wafer 11.6g",
            "exact_kitkat_strawberry_cocoa_wafer_11_6g",
            61.0,
            {"protein_g": 0.6, "carb_g": 7.2, "fat_g": 3.3},
        ),
        (
            "imei almond powder no added sugar 30g",
            "exact_imei_almond_powder_no_added_sugar_30g",
            144.0,
            {"protein_g": 6.8, "carb_g": 13.0, "fat_g": 7.3},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
