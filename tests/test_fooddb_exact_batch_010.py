from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_imeifoods_chocolate_puff_65g",
    "exact_imeifoods_strawberry_wafer_22g",
    "exact_imeifoods_strawberry_thin_biscuit_24g",
    "exact_domori_100_dark_chocolate_5g",
    "exact_lotte_pepero_chocolate_cookie_stick_32g",
    "exact_uha_white_grape_candy_50g",
    "exact_quaker_unsweetened_nutrition_drink_250ml",
    "exact_georgia_caramel_cloud_latte_350ml",
}


def test_exact_batch_010_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_005.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] in {"per_serving", "per_package"}
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_010_resolves_with_visible_macros() -> None:
    cases = [
        (
            "imei chocolate puff 65g",
            "exact_imeifoods_chocolate_puff_65g",
            377.0,
            {"protein_g": 6.9, "carb_g": 30.8, "fat_g": 25.2},
        ),
        (
            "quaker unsweetened nutrition drink 250ml",
            "exact_quaker_unsweetened_nutrition_drink_250ml",
            250.0,
            {"protein_g": 9.3, "carb_g": 39.0, "fat_g": 7.2},
        ),
        (
            "georgia caramel cloud latte 350ml",
            "exact_georgia_caramel_cloud_latte_350ml",
            153.0,
            {"protein_g": 4.6, "carb_g": 21.0, "fat_g": 5.6},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
