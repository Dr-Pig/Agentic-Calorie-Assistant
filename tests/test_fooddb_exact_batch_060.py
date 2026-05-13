from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_master_chocolate_hazelnut_dual_spread_10g",
    "exact_master_chocolate_hazelnut_spread_10g",
    "exact_pocky_ultra_thin_chocolate_sticks_33_5g",
    "exact_milka_oreo_chocolate_sandwich_18_4g",
    "exact_meadows_cocoa_sandwich_biscuits_33_5g",
    "exact_huayuan_potato_chips_taiwan_steak_32g",
    "exact_lays_fukuoka_mentaiko_potato_chips_23_3g",
    "exact_imei_chocolate_wafer_rolls_33g",
    "exact_seikatsu_chocolate_puff_pastry_75g",
    "exact_pocky_milk_cookie_share_pack_33g",
    "exact_koikeya_yuzu_salt_potato_chips_20g",
    "exact_kitani_light_salt_potato_chips_35g",
}


def test_exact_batch_060_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_025.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_060_resolves_with_visible_macros() -> None:
    cases = [
        (
            "milka oreo chocolate sandwich 18.4g",
            "exact_milka_oreo_chocolate_sandwich_18_4g",
            95.0,
            {"protein_g": 1.0, "carb_g": 11.6, "fat_g": 5.0},
        ),
        (
            "huayuan potato chips taiwan steak 32g",
            "exact_huayuan_potato_chips_taiwan_steak_32g",
            178.5,
            {"protein_g": 2.3, "carb_g": 17.8, "fat_g": 10.9},
        ),
        (
            "seikatsu chocolate puff pastry 75g",
            "exact_seikatsu_chocolate_puff_pastry_75g",
            372.0,
            {"protein_g": 5.5, "carb_g": 50.4, "fat_g": 16.9},
        ),
        (
            "kitani light salt potato chips 35g",
            "exact_kitani_light_salt_potato_chips_35g",
            196.0,
            {"protein_g": 2.0, "carb_g": 18.0, "fat_g": 13.2},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
