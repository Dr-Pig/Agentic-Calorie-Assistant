from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_lamole_focaccia_crackers_25g",
    "exact_mulino_bianco_pistachio_cookie_28g",
    "exact_chfoods_pepper_soda_crackers_28g",
    "exact_wawel_100_dark_chocolate_80g",
    "exact_lamole_rosemary_crispbread_25g",
    "exact_zess_chocolate_biscuits_14_8g",
    "exact_godiva_72_dark_chocolate_11_2g",
    "exact_unipresident_egg_soybean_drink_250ml",
}


def test_exact_batch_015_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_007.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] in {"per_serving", "per_package"}
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_015_resolves_with_visible_macros() -> None:
    cases = [
        (
            "la mole focaccia crackers 25g",
            "exact_lamole_focaccia_crackers_25g",
            117.0,
            {"protein_g": 2.8, "carb_g": 15.7, "fat_g": 5.0},
        ),
        (
            "wawel 100 dark chocolate 80g",
            "exact_wawel_100_dark_chocolate_80g",
            494.0,
            {"protein_g": 10.4, "carb_g": 5.0, "fat_g": 48.0},
        ),
        (
            "unipresident egg soybean drink 250ml",
            "exact_unipresident_egg_soybean_drink_250ml",
            139.0,
            {"protein_g": 5.0, "carb_g": 22.5, "fat_g": 3.2},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
